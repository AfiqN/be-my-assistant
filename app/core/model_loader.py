import logging
from typing import Any, Optional
from sentence_transformers import SentenceTransformer, CrossEncoder

logger = logging.getLogger(__name__)

def initialize_embedding_model(model_name: str) -> Optional[Any]:
    """
    Initializes and loads a Sentence Transformer embedding model.

    Args:
        model_name (str): The name/path of the Sentence Transformer model.

    Returns:
        Optional[SentenceTransformer]: The loaded model instance, or None on failure.
    """
    logger.info(f"Initializing Sentence Transformer embedding model: {model_name}")
    try:
        embedding_model = SentenceTransformer(model_name)
        logger.info(f"Sentence Transformer embedding model '{model_name}' loaded successfully.")
        return embedding_model
    except Exception as e:
        logger.error(f"Failed to load Sentence Transformer embedding model '{model_name}': {e}", exc_info=True)
        return None