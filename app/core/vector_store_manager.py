import logging
import os
import uuid
from typing import List, Optional, Tuple, Any # Any for SentenceTransformer model type hint

import chromadb
from chromadb import Collection
from chromadb.config import Settings # Import Settings for configuration
from sentence_transformers import SentenceTransformer

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Embedding Model Handling ---

def initialize_embedding_model(model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> Any:
    """
    Initializes and loads a Sentence Transformer model.

    Args:
        model_name (str): The name of the pre-trained Sentence Transformer model to load.
                          Defaults to "all-MiniLM-L6-v2", a popular and efficient choice.

    Returns:
        SentenceTransformer: An instance of the loaded Sentence Transformer model.
                             Returns None if the model cannot be loaded.
    """
    logger.info(f"Initializing Sentence Transformer model: {model_name}")
    try:
        # Load the specified model from Hugging Face (or cache)
        embedding_model = SentenceTransformer(model_name)
        logger.info(f"Sentence Transformer model '{model_name}' loaded successfully.")
        return embedding_model
    except Exception as e:
        logger.error(f"Failed to load Sentence Transformer model '{model_name}': {e}")
        # Depending on requirements, you might want to raise the exception
        # or handle it differently. Returning None indicates failure here.
        return None

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
        # Note: Settings are optional but can be used for more control if needed.
        # e.g., settings = Settings(persist_directory=persist_directory, is_persistent=True)
        client = chromadb.PersistentClient(path=persist_directory)

        # Get or create the collection
        # Note: You can specify metadata for the collection, like the embedding function name,
        # but since we embed outside and pass vectors directly, it's less critical here.
        # Example with embedding func:
        # from chromadb.utils import embedding_functions
        # emb_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        # collection = client.get_or_create_collection(name=collection_name, embedding_function=emb_func)
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
            metadatas=metadatas, # Pass None if not provided
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
    n_results: int = 3
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
        # Results format is like: {'ids': [['id1', 'id2']], 'distances': [[0.1, 0.2]], 'documents': [['doc1', 'doc2']], ...}
        # We access the first (and only) list inside each key.
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

# --- Example Usage Block ---
if __name__ == '__main__':
    # This block demonstrates how to use the functions in this module.
    # It's useful for quick tests.

    print("--- Initializing Embedding Model ---")
    model = initialize_embedding_model()

    if model:
        print("--- Initializing Vector Store ---")
        # Using a different directory for testing to not interfere with main app data
        test_persist_dir = "app/data/chroma_db_test"
        test_collection_name = "test_docs"
        vector_collection = initialize_vector_store(
            persist_directory=test_persist_dir,
            collection_name=test_collection_name
        )

        if vector_collection:
            # Clear the collection for a clean test run (optional)
            # print(f"Attempting to delete existing test collection '{test_collection_name}'...")
            # try:
            #     client = chromadb.PersistentClient(path=test_persist_dir)
            #     client.delete_collection(test_collection_name)
            #     print("Existing test collection deleted.")
            #     vector_collection = initialize_vector_store(test_persist_dir, test_collection_name) # Re-initialize
            # except Exception as del_e:
            #     print(f"Could not delete collection (may not exist): {del_e}")


            print(f"\n--- Preparing Dummy Data ---")
            dummy_texts = [
                "The quick brown fox jumps over the lazy dog.",
                "LangChain provides tools for building applications with LLMs.",
                "Vector databases store and query high-dimensional data.",
                "Sentence transformers create meaningful text embeddings.",
                "ChromaDB is an open-source vector store.",
                "A lazy dog sleeps under the tree."
            ]
            print(f"Dummy Texts:\n" + "\n".join(f"- {t}" for t in dummy_texts))

            print("\n--- Embedding Dummy Texts ---")
            dummy_embeddings = embed_texts(dummy_texts, model)

            if dummy_embeddings:
                print(f"Generated {len(dummy_embeddings)} embeddings.")

                print("\n--- Adding Texts to Vector Store ---")
                # Example adding metadata (optional)
                dummy_metadatas = [{"source": f"dummy_doc_{i+1}"} for i in range(len(dummy_texts))]
                success = add_texts_to_vector_store(
                    vector_collection,
                    dummy_texts,
                    dummy_embeddings,
                    metadatas=dummy_metadatas # Passing metadata
                )

                if success:
                    print(f"Successfully added documents. Collection count: {vector_collection.count()}")

                    print("\n--- Querying Vector Store ---")
                    # query = "What is ChromaDB?"
                    query = "information about sleepy animals"
                    print(f"Query: '{query}'")
                    search_results = query_vector_store(vector_collection, query, model, n_results=3)

                    if search_results:
                        print("\n--- Search Results (Document, Distance Score) ---")
                        for doc, score in search_results:
                            print(f"- Score: {score:.4f}\n  Text: {doc}\n")
                    elif search_results == []: # Explicitly check for empty list
                         print("Query returned no results.")
                    else:
                        print("Query failed.")
                else:
                    print("Failed to add documents to the vector store.")
            else:
                print("Failed to generate embeddings for dummy data.")
        else:
            print("Failed to initialize vector store.")
    else:
        print("Failed to initialize embedding model.")

    # Clean up test data (optional)
    import shutil
    if os.path.exists(test_persist_dir):
        print(f"\n--- Cleaning up test directory: {test_persist_dir} ---")
        # shutil.rmtree(test_persist_dir)
        print("Test directory cleanup skipped (uncomment shutil.rmtree to enable).")