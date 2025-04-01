from pydantic import BaseModel
from typing import Optional, List, Dict # Add List and Dict

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