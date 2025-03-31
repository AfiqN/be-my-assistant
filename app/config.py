import logging
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

# Setup logger for this module
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Defines application settings, loading values from environment variables
    or a .env file. Uses pydantic-settings for validation and type hints.
    """
    # --- Core Model & RAG Configuration ---
    # Define configuration variables with type hints.
    # Default values are used if the corresponding environment variable isn't set.
    EMBEDDING_MODEL_NAME: str = "paraphrase-multilingual-MiniLM-L12-v2"
    LLM_MODEL_NAME: str = "gemini-1.5-flash"
    VECTOR_STORE_PATH: str = "app/data/chroma_db" # Default path for the main vector database
    VECTOR_COLLECTION_NAME: str = "documents"    # Default collection name
    RAG_NUM_RESULTS: int = 3                     # Default number of documents to retrieve for RAG
    RAG_TEMPERATURE: float = 0.7                 # Default temperature for LLM generation

    # --- API Keys ---
    # Use Optional[str] = None for secrets. This makes it explicit if they
    # are missing, allowing for better error handling/warnings.
    GOOGLE_API_KEY: Optional[str] = None

    # --- File Upload Configuration ---
    # Directory for temporarily storing uploaded files before processing.
    # Ensure this directory is writable by the application process.
    # Using '/tmp/' is common on Linux/macOS. Adjust if needed for Windows
    # or specific deployment environments.
    UPLOAD_TEMP_DIR: str = "/tmp/bma_uploads"

    # --- Pydantic-Settings Configuration ---
    # Tells pydantic-settings how to load the configuration.
    model_config = SettingsConfigDict(
        env_file='.env',          # Specifies the name of the .env file to load.
        env_file_encoding='utf-8', # Specifies the encoding of the .env file.
        extra='ignore'            # Instructs pydantic to ignore extra environment
                                  # variables that are not defined in this Settings model.
    )

# --- Instantiate Settings ---
# Create a single instance of the Settings class.
# This instance will be imported and used by other modules in the application.
settings = Settings()

# --- Post-Initialization Validation and Setup ---

# Validate that critical settings like API keys are actually loaded.
if not settings.GOOGLE_API_KEY:
    # Log a warning if the API key is missing. Depending on the app's requirements,
    # you might want to raise a critical error here instead to prevent startup.
    logger.warning("-----------------------------------------------------")
    logger.warning("WARNING: GOOGLE_API_KEY is not set in environment variables or .env file.")
    logger.warning("LLM-dependent features (like /chat) will likely fail.")
    logger.warning("-----------------------------------------------------")
    # Example: raise ValueError("Missing critical configuration: GOOGLE_API_KEY")

# Ensure the temporary directory for uploads exists.
try:
    os.makedirs(settings.UPLOAD_TEMP_DIR, exist_ok=True)
    logger.info(f"Ensured temporary upload directory exists at: {settings.UPLOAD_TEMP_DIR}")
except OSError as e:
    logger.error(f"CRITICAL: Could not create temporary upload directory {settings.UPLOAD_TEMP_DIR}: {e}")
    # This could be a fatal error depending on whether file uploads are essential.
    # raise RuntimeError(f"Failed to create upload directory: {e}") from e