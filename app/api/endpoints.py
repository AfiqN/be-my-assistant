import logging
import os
import tempfile # Using tempfile for better temporary file management
import shutil   # For copying file contents
from typing import Dict, Any, Optional # Added Optional for type hints

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, status

# Import defined Pydantic schemas
from app.schemas import ChatRequest, ChatResponse, UploadSuccessResponse

# Import core logic functions from sibling 'core' directory
# Assuming 'app' is the root package recognized by the Python path
from app.core.document_processor import load_pdf_text, split_text_into_chunks
from app.core.vector_store_manager import embed_texts, add_texts_to_vector_store
from app.core.rag_orchestrator import get_rag_response

# Import application settings instance
from app.config import settings

# Setup logger for this module
logger = logging.getLogger(__name__)

# Create an API Router - this groups related endpoints
router = APIRouter()

# --- Dependency Injection Helpers ---
# These functions allow FastAPI to inject shared resources (initialized at startup)
# into our endpoint functions when requests are made.

async def get_embedding_model(request: Request) -> Any:
    """
    Dependency function to retrieve the pre-loaded embedding model
    from the application state.
    """
    # Access the model stored in app.state by the lifespan manager in main.py
    model = request.app.state.embedding_model
    if model is None:
        logger.error("Embedding model requested but not found in app state. Was it initialized?")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Embedding model is not available."
        )
    return model

async def get_vector_collection(request: Request) -> Any:
    """
    Dependency function to retrieve the pre-initialized vector store collection
    from the application state.
    """
    # Access the collection stored in app.state by the lifespan manager in main.py
    collection = request.app.state.vector_collection
    if collection is None:
        logger.error("Vector collection requested but not found in app state. Was it initialized?")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vector store collection is not available."
        )
    return collection

# --- API Endpoint Implementations ---

@router.post(
    "/upload",
    response_model=UploadSuccessResponse,
    summary="Upload and Process PDF Document",
    description="Accepts a PDF file, extracts text, generates embeddings, and stores them in the vector database."
)
async def upload_document(
    *, # Use * to make following arguments keyword-only
    file: UploadFile = File(..., description="The PDF document to upload."), # Use FastAPI's File for uploads
    embedding_model: Any = Depends(get_embedding_model), # Inject embedding model
    vector_collection: Any = Depends(get_vector_collection) # Inject vector store collection
):
    """
    Endpoint to upload, process, and store a PDF document.
    """
    # --- 1. Validate File Type ---
    if file.content_type != "application/pdf":
        logger.warning(f"Upload failed: Invalid file type '{file.content_type}' for file '{file.filename}'.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are accepted."
        )
    logger.info(f"Received PDF file for upload: {file.filename}")

    # --- 2. Save File Temporarily ---
    # Create a temporary directory managed by tempfile context manager
    # This ensures cleanup even if errors occur.
    temp_file_path: Optional[str] = None
    try:
        # Create a temporary file within the configured temp directory
        # We use mkstemp for a secure way to create a temp file path
        fd, temp_file_path = tempfile.mkstemp(suffix=".pdf", prefix="upload_", dir=settings.UPLOAD_TEMP_DIR)
        os.close(fd) # Close the file descriptor as we'll open it in binary write mode

        logger.info(f"Saving uploaded content to temporary file: {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            # Copy the contents of the uploaded file to the temporary file
            shutil.copyfileobj(file.file, buffer)
        logger.debug(f"Temporary file saved successfully: {temp_file_path}")

    except Exception as e:
        logger.error(f"Failed to save uploaded file temporarily: {e}", exc_info=True)
        # Clean up temp file if it was created before error
        if temp_file_path and os.path.exists(temp_file_path):
             try:
                 os.remove(temp_file_path)
             except OSError:
                 logger.error(f"Could not clean up temp file during save error: {temp_file_path}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save uploaded file for processing."
        )
    finally:
        # Always close the uploaded file object
        await file.close()

    # --- 3. Process the Document (Load, Split, Embed, Store) ---
    total_chunks_added = 0
    try:
        # Load text from the temporary PDF file
        logger.debug(f"Loading text from {temp_file_path}")
        document_text = load_pdf_text(temp_file_path)

        if not document_text:
            logger.warning(f"No text could be extracted from PDF: {file.filename}")
            # Return success, indicating 0 chunks were added
            return UploadSuccessResponse(
                filename=file.filename,
                message="File processed, but no text content was found or extracted.",
                chunks_added=0
            )

        # Split the extracted text into manageable chunks
        logger.debug("Splitting text into chunks...")
        # Consider making chunk_size/overlap configurable via settings
        text_chunks = split_text_into_chunks(document_text)

        if not text_chunks:
            logger.warning(f"Text extracted, but splitting resulted in zero chunks for: {file.filename}")
            return UploadSuccessResponse(
                filename=file.filename,
                message="File processed and text extracted, but no chunks were generated after splitting.",
                chunks_added=0
            )
        logger.info(f"Document split into {len(text_chunks)} chunks.")

        # Generate embeddings for the text chunks using the injected model
        logger.debug("Generating embeddings for text chunks...")
        embeddings = embed_texts(text_chunks, embedding_model)

        if embeddings is None: # Check if embedding failed
            logger.error(f"Embedding generation failed for file: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate text embeddings for the document."
            )
        if not embeddings: # Check for empty list if chunks existed but embedding yielded nothing
            logger.warning(f"Embedding process resulted in zero embeddings for: {file.filename}")
            return UploadSuccessResponse(
                 filename=file.filename,
                 message="File processed, chunks generated, but failed to create embeddings.",
                 chunks_added=0
            )
        logger.info("Embeddings generated successfully.")

        # Add the text chunks and their embeddings to the vector store
        logger.debug("Adding text chunks and embeddings to the vector store...")
        # Create simple metadata indicating the source file
        metadatas = [{'source': file.filename} for _ in text_chunks]

        # Call the function to add data to the injected vector collection
        success = add_texts_to_vector_store(
            collection=vector_collection,
            texts=text_chunks,
            embeddings=embeddings,
            metadatas=metadatas
            # Optionally generate custom IDs: ids=[f"{file.filename}_{i}" for i in range(len(text_chunks))]
        )

        if not success:
            logger.error(f"Failed to add document chunks to vector store for file: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store document chunks in the vector database."
            )

        total_chunks_added = len(text_chunks)
        logger.info(f"Successfully processed and stored {total_chunks_added} chunks from {file.filename}.")

    except HTTPException as http_exc:
        # If an HTTPException was raised intentionally, re-raise it
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors during processing
        logger.error(f"Unexpected error processing document {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred while processing the document: {e}"
        )
    finally:
        # --- 4. Clean up the temporary file ---
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except OSError as e:
                # Log error but don't necessarily fail the request if cleanup fails
                logger.error(f"Error removing temporary file {temp_file_path}: {e}")

    # --- 5. Return Success Response ---
    return UploadSuccessResponse(
        filename=file.filename,
        message="Document processed and added to vector store successfully.",
        chunks_added=total_chunks_added
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with RAG Assistant",
    description="Sends a question to the RAG system, retrieves relevant context from uploaded documents, and generates an answer using an LLM."
)
async def chat_with_rag(
    chat_request: ChatRequest, # Use the Pydantic schema for request body validation
    embedding_model: Any = Depends(get_embedding_model), # Inject dependencies
    vector_collection: Any = Depends(get_vector_collection)
):
    """
    Endpoint to handle chat requests using the RAG pipeline.
    """
    question = chat_request.question
    logger.info(f"Received chat request with question: '{question}'")

    # --- 1. Validate Input ---
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    # --- 2. Call RAG Orchestrator ---
    try:
        # Call the main RAG function, passing the question and injected resources
        answer = get_rag_response(
            question=question,
            embedding_model=embedding_model,
            vector_collection=vector_collection,
            # Get LLM config from central settings
            llm_model_name=settings.LLM_MODEL_NAME,
            n_results=settings.RAG_NUM_RESULTS,
            temperature=settings.RAG_TEMPERATURE
        )

        # --- 3. Handle Response/Errors from RAG ---
        if answer is None:
            # If RAG returns None, it indicates an internal failure
            logger.error(f"RAG orchestrator returned None for question: '{question}'")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response due to an internal error in the RAG process."
            )
        elif answer.startswith("Error:"):
            # If RAG returns a string starting with "Error:", treat it as an internal error
            logger.error(f"RAG orchestrator indicated an error for question '{question}': {answer}")
            # You might want to return the specific error detail or a generic message
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                # detail=answer # Option 1: Return specific error
                detail="Failed to generate response due to an internal processing error." # Option 2: Generic
            )

        # --- 4. Return Successful Response ---
        logger.info(f"Successfully generated RAG response for question: '{question}'")
        return ChatResponse(answer=answer)

    except HTTPException as http_exc:
         # Re-raise HTTPExceptions to let FastAPI handle them
         raise http_exc
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error during chat processing for question '{question}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred: {e}"
        )