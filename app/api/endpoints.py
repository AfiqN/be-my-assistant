import logging
import os
import io
import mimetypes # Add this
import tempfile 
import shutil   
from typing import Dict, Any, Optional 

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, status, Response, Path

from app.schemas import ( # Group imports
    ChatRequest, ChatResponse, UploadSuccessResponse,
    AdminPreviewRequest, AdminPreviewResponse, RetrievedChunkInfo # Added Admin schemas
)

# Import core logic functions from sibling 'core' directory
from app.core.document_processor import load_document, split_text_into_chunks
from app.core.vector_store_manager import embed_texts, add_texts_to_vector_store, delete_documents_by_source
from app.core.rag_orchestrator import get_rag_response, get_admin_preview

# Import application settings instance
from app.config import settings

# Setup logger for this module
logger = logging.getLogger(__name__)

# Create an API Router - this groups related endpoints
router = APIRouter()

# --- Dependency Injection Helpers ---
async def get_embedding_model(request: Request) -> Any:
    """Retrieves the pre-loaded embedding model."""
    model = getattr(request.app.state, 'embedding_model', None)
    if model is None:
        logger.error("Dependency Error: Embedding model not available in app state.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Embedding model is not ready.")
    return model

async def get_vector_collection(request: Request) -> Any:
    """Retrieves the pre-initialized vector store collection."""
    collection = getattr(request.app.state, 'vector_collection', None) 
    if collection is None:
        logger.error("Dependency Error: Vector collection not available in app state.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Vector store is not ready.")
    return collection

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
    "text/markdown",
    "text/x-markdown",
}

# --- API Endpoint Implementations ---
@router.post(
    "/upload",
    response_model=UploadSuccessResponse,
    summary="Upload and Process PDF Document",
    description="Accepts PDF, TXT, DOCX, or MD files, extracts text, generates embeddings, and stores them."
)
async def upload_document(
    *, # Use * to make following arguments keyword-only
    file: UploadFile = File(..., description="The document (PDF, TXT, DOCX, MD) to upload."),
    embedding_model: Any = Depends(get_embedding_model), # Inject embedding model
    vector_collection: Any = Depends(get_vector_collection) # Inject vector store collection
):
    """
    Endpoint to upload, process, and store a PDF document.
    """
    # --- 1. Validate File Type ---
    content_type = file.content_type
    
    if content_type not in ALLOWED_MIME_TYPES:
         guessed_type, _ = mimetypes.guess_type(file.filename)
         if guessed_type in ALLOWED_MIME_TYPES:
             content_type = guessed_type
             logger.info(f"Using guessed content type '{content_type}' for file '{file.filename}'.")
         else:
              logger.warning(f"Upload failed: Invalid or unsupported file type '{file.content_type}' or guessed type '{guessed_type}' for file '{file.filename}'. Allowed: {ALLOWED_MIME_TYPES}")
              raise HTTPException(
                  status_code=status.HTTP_400_BAD_REQUEST,
                  detail=f"Invalid file type. Allowed types: PDF, TXT, DOCX, MD."
              )
    logger.info(f"Received file for upload: {file.filename} (Type: {content_type})")


    filename_to_process = file.filename
    logger.info(f"Attempting to delete existing context for: {filename_to_process}")
    try:
        delete_success = delete_documents_by_source(
            collection=vector_collection,
            source_filename=filename_to_process
        )
        if not delete_success:
            # Log error tapi tetap lanjutkan (mungkin file belum pernah ada)
            logger.warning(f"Could not ensure deletion of old context for {filename_to_process}, proceeding with upload.")
        else:
            logger.info(f"Successfully issued deletion command for old context of {filename_to_process}.")
    except Exception as delete_exc:
        logger.error(f"Error during pre-upload deletion for {filename_to_process}: {delete_exc}", exc_info=True)
        # Pertimbangkan apakah akan menghentikan proses atau melanjutkan
        # Untuk sekarang, kita log error dan lanjutkan
        logger.warning(f"Proceeding with upload despite error during pre-deletion for {filename_to_process}.")

    # --- 2. Read File Content into Memory (as BytesIO stream) ---
    file_content_stream: Optional[io.BytesIO] = None
    try:
         # Read the entire file content into a BytesIO stream
         content_bytes = await file.read()
         file_content_stream = io.BytesIO(content_bytes)
         logger.debug(f"File content read into memory stream ({len(content_bytes)} bytes).")

    except Exception as e:
         logger.error(f"Failed to read uploaded file content into memory: {e}", exc_info=True)
         raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail="Could not read uploaded file content."
         )
    finally:
         await file.close()

    # --- 3. Process the Document (Load, Split, Embed, Store) ---
    total_chunks_added = 0
    processed_source = file.filename # Default identifier
    try:
        # Load text using the new dispatcher function, passing the stream and type
        logger.debug(f"Loading text using load_document for: {file.filename}")
        load_result = load_document(
             content_source=file.filename, # Pass filename for identification/guessing
             content_type=content_type,
             file_stream=file_content_stream
        )

        if load_result is None:
            logger.warning(f"Failed to load or extract text from file: {file.filename}")
            raise HTTPException(
                 status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, # Use 422 for processing errors
                 detail="Could not extract text content from the uploaded file."
            )

        document_text, processed_source = load_result
        if not document_text:
             logger.warning(f"No text content extracted from file: {processed_source}")
             return UploadSuccessResponse(
                 filename=processed_source,
                 message="File processed, but no text content was found or extracted.",
                 chunks_added=0
             )

        # Split the extracted text into manageable chunks
        logger.debug("Splitting text into chunks...")
        text_chunks = split_text_into_chunks(text=document_text)

        if not text_chunks:
            logger.warning(f"Text extracted, but splitting resulted in zero chunks for: {processed_source}")
            return UploadSuccessResponse(
                filename=processed_source,
                message="File processed and text extracted, but no chunks were generated.",
                chunks_added=0
            )
        logger.info(f"Document split into {len(text_chunks)} chunks.")

        # Generate embeddings
        logger.debug("Generating embeddings...")
        embeddings = embed_texts(text_chunks, embedding_model)

        if embeddings is None or not embeddings:
            logger.error(f"Embedding generation failed or yielded no results for file: {processed_source}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate or obtain text embeddings for the document."
            )
        logger.info("Embeddings generated successfully.")

        # Add to vector store
        logger.debug("Adding chunks and embeddings to the vector store...")
        metadatas = [{'source': processed_source} for _ in text_chunks]
        success = add_texts_to_vector_store(
            collection=vector_collection,
            texts=text_chunks,
            embeddings=embeddings,
            metadatas=metadatas
            # IDs will be auto-generated by the function
        )

        if not success:
            logger.error(f"Failed to add document chunks to vector store for file: {processed_source}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store document chunks in the vector database."
            )

        total_chunks_added = len(text_chunks)
        logger.info(f"Successfully processed and stored {total_chunks_added} chunks from {processed_source}.")

    except HTTPException as http_exc:
        raise http_exc # Re-raise intentional HTTP exceptions
    except Exception as e:
        logger.error(f"Unexpected error processing document {processed_source}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {e}"
        )
    finally:
        # Clean up the in-memory stream
        if file_content_stream:
            file_content_stream.close()
            logger.debug("Closed in-memory file stream.")

    # --- 4. Return Success Response ---
    return UploadSuccessResponse(
        filename=processed_source,
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
    vector_collection: Any = Depends(get_vector_collection),
):
    """
    Endpoint to handle chat requests using the RAG pipeline.
    """
    question = chat_request.question
    chat_history = chat_request.chat_history
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
            chat_history=chat_history
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
    

@router.delete(
    "/delete_context/{filename}",
    status_code=status.HTTP_204_NO_CONTENT, # Use 204 No Content for successful deletions
    summary="Delete Context by Filename",
    description="Deletes all vector store entries associated with the given source filename."
)
async def delete_context(
    *, # Keyword-only arguments
    filename: str = Path(..., description="The URL-encoded filename to delete context for."),
    vector_collection: Any = Depends(get_vector_collection) # Inject vector store
):
    """
    Endpoint to delete all documents/embeddings associated with a specific source filename.
    """
    logger.info(f"Received request to delete context for filename: {filename}")

    # Basic validation
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    try:
        # Call the new deletion function from the vector store manager
        success = delete_documents_by_source(
            collection=vector_collection,
            source_filename=filename # Pass the decoded filename
        )

        if not success:
            # If the deletion function reported an issue (logged internally)
            logger.error(f"Deletion failed for filename: {filename} in vector_store_manager.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete context for filename '{filename}' from the vector store."
            )

        logger.info(f"Successfully processed deletion request for filename: {filename}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException as http_exc:
         # Re-raise known HTTP exceptions
         raise http_exc
    except Exception as e:
        # Catch unexpected errors
        logger.error(f"Unexpected error during context deletion for filename '{filename}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred while deleting context: {e}"
        )
    
@router.post(
    "/admin/preview_context",
    response_model=AdminPreviewResponse,
    summary="Admin Context Preview",
    description="Allows admin to test a question and see retrieved context chunks and the draft AI answer based *only* on those chunks."
)
async def preview_context(
    preview_request: AdminPreviewRequest,
    embedding_model: Any = Depends(get_embedding_model),
    vector_collection: Any = Depends(get_vector_collection),
):
    """
    Endpoint for admin context preview functionality.
    """
    question = preview_request.question
    logger.info(f"Received admin preview request for question: '{question}'")

    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty for preview."
        )

    try:
        # Call the dedicated admin preview function from the orchestrator
        preview_result = get_admin_preview(
            question=question,
            embedding_model=embedding_model,
            vector_collection=vector_collection,
        )

        if preview_result is None:
            # Should ideally not happen if get_admin_preview handles errors, but good practice
            logger.error(f"Admin preview orchestrator returned None for question: '{question}'")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate preview due to an internal error in the RAG process."
            )

        # Unpack the result tuple
        retrieved_chunks, draft_answer = preview_result

        # Check if the draft_answer indicates an error occurred during preview generation
        if draft_answer.startswith("Error:"):
            logger.error(f"Admin preview generation indicated an error for question '{question}': {draft_answer}")
            # Return the retrieved chunks (if any) but include the error in the draft answer field
            return AdminPreviewResponse(
                retrieved_chunks=retrieved_chunks,
                draft_answer=draft_answer # Pass the error message through
            )

        # Return successful preview response
        logger.info(f"Successfully generated admin preview for question: '{question}'")
        return AdminPreviewResponse(
            retrieved_chunks=retrieved_chunks,
            draft_answer=draft_answer
        )

    except HTTPException as http_exc:
         # Re-raise HTTPExceptions
         raise http_exc
    except Exception as e:
        # Catch any other unexpected errors during the preview process
        logger.error(f"Unexpected error during admin preview for question '{question}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred during preview: {e}"
        )
