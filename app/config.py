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
    EMBEDDING_MODEL_NAME: str = "paraphrase-multilingual-MiniLM-L12-v2"
    LLM_MODEL_NAME: str = "gemini-2.0-flash"
    VECTOR_STORE_PATH: str = "app/data/chroma_db" # Default path for the main vector database
    VECTOR_COLLECTION_NAME: str = "documents"    # Default collection name
    RAG_NUM_RESULTS: int = 4                     # Default number of documents to retrieve for RAG
    RAG_TEMPERATURE: float = 0.6                # Default temperature for LLM generation

    # --- API Keys ---
    GOOGLE_API_KEY: Optional[str] = None

    # --- Pydantic-Settings Configuration ---
    model_config = SettingsConfigDict(
        env_file='.env',          # Specifies the name of the .env file to load.
        env_file_encoding='utf-8', # Specifies the encoding of the .env file.
        extra='ignore'            # Instructs pydantic to ignore extra environment
                                  # variables that are not defined in this Settings model.
    )

# --- Instantiate Settings ---
settings = Settings()

# Validate that critical settings like API keys are actually loaded.
if not settings.GOOGLE_API_KEY:
    logger.warning("-----------------------------------------------------")
    logger.warning("WARNING: GOOGLE_API_KEY is not set in environment variables or .env file.")
    logger.warning("LLM-dependent features (like /chat) will likely fail.")
    logger.warning("-----------------------------------------------------")