from pydantic import BaseModel
from typing import Optional, List, Dict, Any # Add List and Dict

# --- Chat Endpoint Schemas ---
class ChatMessage(BaseModel):
    """Represents a single message in the chat history."""
    role: str # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    """
    Schema defining the structure for the request body
    when a user sends a question to the /chat endpoint.
    """
    question: str # The user's question as a string.
    chat_history: Optional[List[ChatMessage]] = None # Add chat history field

class ChatResponse(BaseModel):
    """
    Schema defining the structure for the response body
    sent back by the /chat endpoint containing the answer.
    """
    answer: str # The generated answer as a string.

# --- Upload Endpoint Schemas (Optional but good practice) ---

class UploadSuccessResponse(BaseModel):
    """
    Schema defining the structure for a successful response
    from the /upload endpoint after processing a file.
    """
    filename: str            # The name of the file that was uploaded.
    message: str             # A confirmation message (e.g., "File processed successfully").
    chunks_added: Optional[int] = None # Optional: How many text chunks were added to the store.

class AdminPreviewRequest(BaseModel):
    """Schema for the admin context preview request."""
    question: str

class RetrievedChunkInfo(BaseModel):
    """Schema for information about a single retrieved chunk."""
    source: Optional[str] = "Unknown Source" # Filename or URL
    content_preview: str # First N characters of the chunk
    full_content: str
    distance: Optional[float] = None # Similarity score/distance

class AdminPreviewResponse(BaseModel):
    """Schema for the admin context preview response."""
    retrieved_chunks: List[RetrievedChunkInfo]
    draft_answer: str

class PersonaSettings(BaseModel):
    """Schema representing the AI persona settings."""
    ai_name: str
    ai_role: str
    ai_tone: str
    company: str

class SetPersonaRequest(PersonaSettings):
    """Schema for the request body when updating persona settings."""
    pass # Inherits fields from PersonaSettings