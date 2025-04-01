import logging
import os
import uuid
from typing import List, Optional, Tuple, Any # Any for SentenceTransformer model type hint

import chromadb
from chromadb import Collection

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def embed_texts(texts: List[str], embedding_model: Any) -> Optional[List[List[float]]]:
    """
    Generates embeddings for a list of text chunks using the provided model.

    Args:
        texts (List[str]): A list of text strings to embed.
        embedding_model (SentenceTransformer): The initialized Sentence Transformer model instance.

    Returns:
        Optional[List[List[float]]]: A list of embedding vectors (each vector is a list of floats).
                                     Returns None if embedding fails or the model is invalid.
    """
    if not embedding_model:
        logger.error("Embedding model is not initialized. Cannot embed texts.")
        return None
    if not texts:
        logger.warning("Input text list is empty. No embeddings to generate.")
        return []

    logger.info(f"Generating embeddings for {len(texts)} text chunk(s)...")
    try:
        # The encode method returns numpy arrays by default, convert them to lists
        embeddings = embedding_model.encode(texts, convert_to_tensor=False).tolist()
        logger.info("Embeddings generated successfully.")
        logger.debug(f"Dimension of embeddings: {len(embeddings[0]) if embeddings else 'N/A'}")
        return embeddings
    except Exception as e:
        logger.error(f"An error occurred during text embedding: {e}")
        return None

# --- ChromaDB Vector Store Handling ---
def initialize_vector_store(
    persist_directory: str = "app/data/chroma_db",
    collection_name: str = "documents"
) -> Optional[Collection]:
    """
    Initializes a persistent ChromaDB client and gets or creates a collection.

    Args:
        persist_directory (str): The directory path where ChromaDB should store its data on disk.
                                 Defaults to "app/data/chroma_db".
        collection_name (str): The name of the collection to use within ChromaDB.
                               Defaults to "documents".

    Returns:
        Optional[chromadb.Collection]: The ChromaDB collection object, or None if initialization fails.
    """
    logger.info(f"Initializing ChromaDB persistent client at: {persist_directory}")
    try:
        # Ensure the persistence directory exists
        os.makedirs(persist_directory, exist_ok=True)

        # Initialize the persistent client
        client = chromadb.PersistentClient(path=persist_directory)

        # Get or create the collection
        collection = client.get_or_create_collection(name=collection_name)

        logger.info(f"ChromaDB collection '{collection_name}' obtained successfully. Current count: {collection.count()}")
        return collection
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB client or collection: {e}")
        return None


def add_texts_to_vector_store(
    collection: Collection,
    texts: List[str],
    embeddings: List[List[float]],
    metadatas: Optional[List[dict]] = None,
    ids: Optional[List[str]] = None
) -> bool:
    """
    Adds texts, their embeddings, and optional metadata to the ChromaDB collection.

    Args:
        collection (Collection): The initialized ChromaDB collection object.
        texts (List[str]): The list of original text chunks.
        embeddings (List[List[float]]): The list of corresponding embedding vectors.
        metadatas (Optional[List[dict]]): Optional list of dictionaries containing metadata for each chunk.
                                         Must be the same length as texts and embeddings if provided.
        ids (Optional[List[str]]): Optional list of unique IDs for each chunk. Chroma requires unique IDs.
                                   If None, unique IDs will be generated using UUID.
                                   Must be the same length as texts and embeddings if provided.

    Returns:
        bool: True if the addition was successful, False otherwise.
    """
    if not collection:
        logger.error("ChromaDB collection is not initialized. Cannot add documents.")
        return False
    if not texts or not embeddings:
        logger.warning("Texts or embeddings list is empty. Nothing to add.")
        return True # Nothing to add, considered successful in a way

    num_items = len(texts)
    if len(embeddings) != num_items:
        logger.error(f"Mismatch in length: {num_items} texts vs {len(embeddings)} embeddings.")
        return False
    if metadatas and len(metadatas) != num_items:
        logger.error(f"Mismatch in length: {num_items} texts vs {len(metadatas)} metadatas.")
        return False
    if ids and len(ids) != num_items:
        logger.error(f"Mismatch in length: {num_items} texts vs {len(ids)} ids.")
        return False

    # Generate unique IDs if not provided
    if ids is None:
        ids = [f"doc_{uuid.uuid4()}" for _ in range(num_items)]
        logger.info(f"Generated {num_items} unique IDs for documents.")

    logger.info(f"Adding {num_items} document(s) to ChromaDB collection '{collection.name}'...")
    try:
        # Add data in batches (ChromaDB handles batching internally, but good practice if manually batching large datasets)
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Successfully added {num_items} documents. New collection count: {collection.count()}")
        return True
    except Exception as e:
        logger.error(f"Failed to add documents to ChromaDB: {e}")
        return False


def query_vector_store(
    collection: Collection,
    query_text: str,
    embedding_model: Any,
    n_results: int = 4
) -> Optional[List[Tuple[str, float]]]:
    """
    Queries the vector store to find documents similar to the query text.

    Args:
        collection (Collection): The initialized ChromaDB collection object.
        query_text (str): The user's query text.
        embedding_model (SentenceTransformer): The initialized Sentence Transformer model instance.
        n_results (int): The maximum number of similar documents to retrieve. Defaults to 5.

    Returns:
        Optional[List[Tuple[str, float]]]: A list of tuples, where each tuple contains
                                           (document_text, distance_score). Lower distance means higher similarity.
                                           Returns None if querying fails or no results are found.
    """
    if not collection:
        logger.error("ChromaDB collection is not initialized. Cannot query.")
        return None
    if not embedding_model:
        logger.error("Embedding model is not initialized. Cannot embed query.")
        return None
    if not query_text:
        logger.warning("Query text is empty.")
        return []

    logger.info(f"Querying vector store for: '{query_text[:100]}...' (Top {n_results} results)")
    try:
        # 1. Embed the query text
        query_embedding = embed_texts([query_text], embedding_model)
        if not query_embedding:
            logger.error("Failed to generate embedding for the query text.")
            return None

        # 2. Perform the query on the collection
        results = collection.query(
            query_embeddings=query_embedding, # Must be a list of embeddings
            n_results=n_results,
            include=['documents', 'distances'] # Specify what data to include in the results
        )

        # 3. Process the results
        if not results or not results.get('ids') or not results['ids'][0]:
             logger.info("Query returned no results from the vector store.")
             return [] # Return empty list if no documents found for the query

        # Extract documents and their distances
        result_documents = results['documents'][0]
        result_distances = results['distances'][0]

        # Combine documents and distances into a list of tuples
        doc_distance_pairs = list(zip(result_documents, result_distances))

        logger.info(f"Found {len(doc_distance_pairs)} relevant document(s).")
        logger.debug(f"Top result distance: {doc_distance_pairs[0][1] if doc_distance_pairs else 'N/A'}")

        return doc_distance_pairs

    except Exception as e:
        logger.error(f"An error occurred during vector store query: {e}")
        return None