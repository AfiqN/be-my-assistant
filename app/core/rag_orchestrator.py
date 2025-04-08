import logging
from typing import Optional, List, Tuple, Any, Dict

# Import functions and classes from other core modules
from .vector_store_manager import (
    query_vector_store,
    embed_texts
)
# Import LLM function from llm_interface
from .llm_interface import invoke_llm_langchain
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas import ChatMessage, RetrievedChunkInfo

# Access environment variables (still needed for API Key check)
import os
from dotenv import load_dotenv

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Prompt Template Definition ---
SYSTEM_PROMPT_TEMPLATE = """You are '{ai_name}', an assistant with a '{ai_tone}' persona, acting as {ai_name} for {company}.
Your primary goal is to assist users by answering their questions *strictly* based on the provided 'Retrieved Context' (which is in Indonesian) and the ongoing 'Conversation History'.

**Core Instructions: Number 1 is the most important. Make sure do not miss it**
1. **Language Handling : DETECT the language of the user's CURRENT question below (it will be either Indonesian or English). Your final response MUST be ONLY in THAT language. Use the Indonesian 'Retrieved Context' ONLY for information, NOT for determining the response language. Example: If the question is English, answer ONLY in English. If the question is Indonesian, answer ONLY in Indonesian. DO NOT translate or mix languages.**
2. **Embody Your Character:** Fully immerse yourself in the role of '{ai_name}'. While your responses should naturally reflect your {ai_tone} traits, do not mention or reference these traits when introducing yourself or when directly asked about your identity.
3. **Base Answers on Provided Information:** Answer the user's current question using *only* the information found in the Indonesian 'Retrieved Context' below or the 'Conversation History'. Do NOT use any external knowledge or make assumptions.
4. **Fact Source:** The 'Retrieved Context' (in Indonesian) is the primary source for facts about the company/store. Prioritize it for specific details.
5. **Conversational Context:** Utilize the 'Conversation History' (previous `Human:` and `Assistant:` messages) to understand follow-up questions and maintain a natural conversational flow.
6. **Avoid Meta-References:** Do NOT mention internal references such as 'Retrieved Context', 'Conversation History', 'documents', or 'context chunks' in your answer.
7. **Adopt the Persona Subtly:** Infuse every response with the nuances of your {ai_tone} character. However, if asked directly "Siapa anda?" or "Who are you?", simply introduce yourself as '{ai_name}' from {company} without referencing your tone.
8. **Be Conversational:** Respond naturally. If the user says "hello" or "thank you", respond appropriately (e.g., "Hello! How can I help?", "Sama-sama!" / "You're welcome!"). Don't use the fallback message for simple greetings or closings.
9. **Clarity and Formatting:** Use clear language. Use bullet points (*) for lists if appropriate. Ensure the output is clean, engaging, and ready for display.
10. **Unavailable Information:** If the necessary information to answer the question is not found in *either* the Indonesian 'Retrieved Context' or the 'Conversation History', respond *only* with one of the following short phrases:
    * (Jika pertanyaan dalam Bahasa Indonesia): "Maaf, saya belum bisa menjawab pertanyaan tersebut."
    * (If in English): "Sorry, I cannot answer that question right now."
    * Do NOT add any further explanation.

---
Retrieved Context:
{context}
---
"""

# Human prompt template includes the actual user question
HUMAN_PROMPT_TEMPLATE = "Question: {question}"

# Combine into a ChatPromptTemplate
RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_TEMPLATE),
    ("human", HUMAN_PROMPT_TEMPLATE),
])

# --- Helper Function for Formatting Retrieved Documents ---
def format_docs(docs: Optional[List[Tuple[str, float]]]) -> str:
    """
    Formats the retrieved documents into a single string for the prompt context.

    Args:
        docs (Optional[List[Tuple[str, float]]]): The list of (document_text, distance_score) tuples
                                                 from query_vector_store, or None.

    Returns:
        str: A single string containing the formatted document texts, separated by double newlines,
             or a string indicating no context was found if no documents were provided.
    """
    if not docs:
        # Provide a neutral indicator for the LLM, not user-facing
        return "No relevant context was found in the documents."
    return "".join(doc[0] for doc in docs)


def get_preview_llm_response(
    question: str,
    context_string: str,
    persona_settings: Any,
) -> Optional[str]:
    """
    Generates a draft LLM response based ONLY on the provided context string and question.
    Uses a simplified prompt template for this purpose.
    """
    if not GOOGLE_API_KEY:
        logger.error("Cannot proceed with preview LLM call: GOOGLE_API_KEY is not configured.")
        return "Error: LLM API Key is not configured."

    if not question:
        return "Error: Question is empty."
    if not context_string:
         # If no context was retrieved, we can't generate an answer based on it
         return "No relevant context snippets were found to generate a draft answer."

    logger.debug("Generating draft LLM response for admin preview...")

    try:
         # Format the prompt using the specific Admin Preview template
         messages = RAG_PROMPT.format_messages(
            ai_name=persona_settings.ai_name,         # <--- AMBIL DARI SETTINGS
            ai_role=persona_settings.ai_role,         # <--- AMBIL DARI SETTINGS
            ai_tone=persona_settings.ai_tone,         # <--- AMBIL DARI SETTINGS
            company=persona_settings.company,         # <--- AMBIL DARI SETTINGS
            context=context_string,
            question=question
        )

         # Call the LLM via the standard interface, but with the preview prompt
         draft_answer = invoke_llm_langchain(
             prompt_input=messages,
             model_name=settings.LLM_MODEL_NAME,
             temperature=settings.RAG_TEMPERATURE # Use same temp for consistency, or maybe lower?
         )

         if draft_answer is None:
             logger.error("Preview LLM call returned None.")
             return "Error: Failed to get response from the language model for preview."

         logger.debug(f"Draft Answer (snippet): '{draft_answer[:100]}...'")
         return draft_answer

    except Exception as e:
         logger.error(f"Error generating preview LLM response: {e}", exc_info=True)
         return f"Error: Failed to generate draft answer - {e}"


# --- Core RAG Orchestration Function ---
def get_rag_response(
    question: str,
    embedding_model: Any, # Expecting an initialized SentenceTransformer model
    vector_collection: Any, # Expecting an initialized Chroma Collection object
    chat_history: Optional[List[ChatMessage]] = None,
    ai_name: str = "AI Assistant", # Default name
    ai_role: str = "Customer Service AI", # Default role
    ai_tone: str = "friendly, helpful, enthusiastic and engaging", # Default tone
    company: str = "-", # Default Company
) -> Optional[str]:
    """
    Orchestrates the RAG pipeline: retrieves context, builds prompt, calls LLM via llm_interface.

    Args:
        question (str): The user's input question.
        embedding_model (Any): The initialized sentence embedding model.

    Returns:
        Optional[str]: The final answer generated by the LLM based on the context,
                       or None/error message if a critical error occurs.
    """
    logger.info(f"RAG request. Question: '{question}'. History length: {len(chat_history) if chat_history else 0}")

    if not GOOGLE_API_KEY:
        logger.error("Cannot proceed with RAG: GOOGLE_API_KEY is not configured.")
        return "Error: LLM API Key is not configured." # Return user-facing error

    # --- 1. Retrieve Relevant Documents ---
    logger.debug("Step 1: Querying vector store...")
    retrieved_docs: Optional[List[Tuple[str, float]]] = None # Initialize
    try:
        retrieved_docs = query_vector_store(
            collection=vector_collection,
            query_text=question,
            embedding_model=embedding_model,
            n_results=settings.RAG_NUM_RESULTS
        )
        if retrieved_docs is None:
             logger.warning("Vector store query returned None, assuming no results.")
             retrieved_docs = [] # Treat as empty list
        logger.info(f"Retrieved {len(retrieved_docs)} documents from vector store.")
    except Exception as e:
        logger.error(f"Error querying vector store: {e}", exc_info=True)
        return "Error: Failed to retrieve context information." # Return user-facing error

    # --- 2. Format Retrieved Documents ---
    logger.debug("Step 2: Formatting retrieved documents...")
    context_string = format_docs(retrieved_docs)
    logger.debug(f"Formatted context string (snippet): '{context_string[:200]}...'")

    # --- 3. Construct Message List for LLM ---
    logger.debug("Step 3: Constructing message list for LLM...")
    messages: List[BaseMessage] = []
    # Add the main system prompt with instructions and RAG context

    try:
        # Format the prompt manually using the template and retrieved context
        messages : List[BaseMessage] = []
        system_prompt_content = SYSTEM_PROMPT_TEMPLATE.format(
            ai_name=ai_name,
            ai_role=ai_role,
            ai_tone=ai_tone,
            company=company,
            context=context_string
        )
        messages.append(SystemMessage(content=system_prompt_content))
        logger.debug(f"Final prompt ready to be sent to llm_interface (snippet): '...{messages[250:]}'")

        # Add past messages from chat history
        if chat_history:
            for msg in chat_history:
                if msg.role.lower() == 'user':
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role.lower() == 'assistant':
                    messages.append(AIMessage(content=msg.content))
                else: # Ignore other roles if any
                    logger.warning(f"Ignoring message with unknown role in history: {msg.role}")
        # Add the current user question
        messages.append(HumanMessage(content=question))

        logger.debug(f"Constructed {len(messages)} messages for LLM.")
    except Exception as e:
         logger.error(f"Error formatting final prompt: {e}", exc_info=True)
         return "Error: Failed to build prompt for the language model."

    # --- 4. Call LLM via llm_interface ---
    logger.debug("Step 4: Calling LLM via llm_interface...")
    try:
        # Call the function from llm_interface.py
        final_answer = invoke_llm_langchain(
            prompt_input=messages,
            model_name=settings.LLM_MODEL_NAME,
            temperature=settings.RAG_TEMPERATURE
        )

        # Check if llm_interface returned None (indicating an error there)
        if final_answer is None:
            logger.error("LLM call via llm_interface returned None.")
            return "Error: Failed to get response from the language model (via llm_interface)."

        logger.info("Successfully called LLM via llm_interface and received answer.")
        logger.debug(f"Final Answer (snippet): '{final_answer[:100]}...'")

        return final_answer

    except Exception as e:
        # Catch unexpected errors during the call to invoke_llm_langchain
        logger.error(f"Unexpected error calling invoke_llm_langchain: {e}", exc_info=True)
        return "Error: Failed to generate final answer de to LLM call issue."
    
def get_admin_preview(
    question: str,
    embedding_model: Any,
    vector_collection: Any,
    persona_settings: Any,
) -> Optional[Tuple[List[RetrievedChunkInfo], str]]:
    """
    Handles the logic for the admin preview: retrieve chunks, get draft answer.
    """
    logger.info(f"Admin Preview request. Question: '{question}'")

    if not GOOGLE_API_KEY:
        logger.error("Cannot proceed with Admin Preview: GOOGLE_API_KEY is not configured.")
        # Return an error tuple structure expected by the endpoint
        return ([], "Error: LLM API Key is not configured.")

    retrieved_chunk_info: List[RetrievedChunkInfo] = []
    draft_answer = "Error: Preview generation failed." # Default error message

    # --- 1. Retrieve Relevant Documents (including metadata) ---
    logger.debug("Admin Preview Step 1: Querying vector store...")
    retrieved_docs_with_meta: Optional[List[Tuple[Any, float, Dict]]] = None
    try:
        query_embedding = embed_texts([question], embedding_model)
        if not query_embedding:
             raise ValueError("Failed to generate query embedding.")

        query_results = vector_collection.query(
            query_embeddings=query_embedding,
            n_results=settings.RAG_NUM_RESULTS,
            include=['documents', 'distances', 'metadatas'] # Crucial: include metadatas
        )

        if query_results and query_results.get('ids') and query_results['ids'][0]:
            docs_content = query_results['documents'][0]
            distances = query_results['distances'][0]
            metadatas = query_results['metadatas'][0] if query_results.get('metadatas') else [{}] * len(docs_content)
            if len(metadatas) != len(docs_content):
                 metadatas = [{}] * len(docs_content) # Fallback

            retrieved_docs_with_meta = list(zip(docs_content, distances, metadatas))
            logger.info(f"Admin Preview: Retrieved {len(retrieved_docs_with_meta)} documents with metadata.")

            # Process into RetrievedChunkInfo schema
            for content, dist, meta in retrieved_docs_with_meta:
                 preview_text = content[:150] + "..." if len(content) > 150 else content # Buat preview
                 source_name = meta.get('source', 'Unknown Source') if meta else 'Unknown Source'
                 retrieved_chunk_info.append(RetrievedChunkInfo(
                     source=source_name,
                     content_preview=preview_text,
                     full_content=content,
                     distance=dist
                 ))
        else:
            logger.info("Admin Preview: Query returned no results.")
            retrieved_docs_with_meta = [] # Ensure it's an empty list

    except Exception as e:
        logger.error(f"Admin Preview Error: Failed during vector store query: {e}", exc_info=True)
        # Return current state (potentially empty list) and an error message
        return (retrieved_chunk_info, f"Error: Failed to retrieve context information - {e}")

    # --- 2. Format Context for Preview LLM ---
    logger.debug("Admin Preview Step 2: Formatting context for LLM...")
    # Format only the text content for the LLM prompt
    context_string_for_llm = format_docs([(doc[0], doc[1]) for doc in retrieved_docs_with_meta]) if retrieved_docs_with_meta else format_docs(None)

    # --- 3. Generate Draft Answer using Preview LLM ---
    logger.debug("Admin Preview Step 3: Generating draft answer...")
    try:
         draft_answer = get_preview_llm_response(
             question=question,
             context_string=context_string_for_llm,
             persona_settings=persona_settings
         )
         if draft_answer is None or draft_answer.startswith("Error:"):
             logger.error(f"Admin Preview: Failed to get draft answer from LLM. Reason: {draft_answer}")
             # Keep the error message in draft_answer
             if draft_answer is None: draft_answer = "Error: LLM generation failed for preview."
         else:
              logger.info("Admin Preview: Successfully generated draft answer.")

    except Exception as e:
         logger.error(f"Admin Preview Error: Failed during draft answer generation: {e}", exc_info=True)
         draft_answer = f"Error: Failed to generate draft answer - {e}"

    # --- 4. Return Results ---
    return (retrieved_chunk_info, draft_answer)