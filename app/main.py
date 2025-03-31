import logging
from contextlib import asynccontextmanager # Required for lifespan management
from fastapi import FastAPI, Request, HTTPException, status # Import Request, HTTPException, status

# Import the API router from endpoints.py and the application settings
from app.api.endpoints import router as api_router
from app.config import settings

# Import the initializer functions from core modules
from app.core.vector_store_manager import initialize_embedding_model, initialize_vector_store

# Setup basic logging (configure as needed, e.g., using file handlers)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Lifespan Management for Shared Resources ---
# This async context manager handles application startup and shutdown events.
# It's used to initialize and clean up resources like models and DB connections.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === Code here runs ON STARTUP ===
    logger.info("Application startup sequence initiated...")

    # Initialize and store the Embedding Model
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
    embedding_model = initialize_embedding_model(settings.EMBEDDING_MODEL_NAME)
    if embedding_model is None:
        logger.error("CRITICAL FAILURE: Embedding model could not be initialized on startup.")
        # Raise an error to potentially stop the application from starting
        # if the model is absolutely essential.
        raise RuntimeError("Could not initialize embedding model during application startup.")
    # Store the initialized model in the application state object (`app.state`)
    # This makes it accessible via `request.app.state.embedding_model` in dependencies/endpoints.
    app.state.embedding_model = embedding_model
    logger.info("Embedding model loaded and stored in application state.")

    # Initialize and store the Vector Store Collection
    logger.info(f"Initializing vector store at '{settings.VECTOR_STORE_PATH}' with collection '{settings.VECTOR_COLLECTION_NAME}'")
    vector_collection = initialize_vector_store(
        persist_directory=settings.VECTOR_STORE_PATH,
        collection_name=settings.VECTOR_COLLECTION_NAME
    )
    if vector_collection is None:
        logger.error("CRITICAL FAILURE: Vector store collection could not be initialized on startup.")
        raise RuntimeError("Could not initialize vector store collection during application startup.")
    # Store the initialized collection object in the application state.
    app.state.vector_collection = vector_collection
    try:
        # Log the count to confirm connection/initialization success
        count = vector_collection.count()
        logger.info(f"Vector store collection '{settings.VECTOR_COLLECTION_NAME}' initialized. Current document count: {count}")
    except Exception as e:
        logger.warning(f"Could not get initial count from vector store collection, but initialization seemed okay: {e}")


    logger.info("Application startup sequence completed successfully.")

    yield # The application runs while the context manager is active (after yield)

    # === Code here runs ON SHUTDOWN ===
    logger.info("Application shutdown sequence initiated...")
    # Perform any cleanup if necessary (e.g., closing database connections if not persistent)
    # For SentenceTransformer and Chroma PersistentClient, explicit cleanup is often not needed.
    # Clear the state variables
    app.state.embedding_model = None
    app.state.vector_collection = None
    logger.info("Shared resources cleaned up from application state.")
    logger.info("Application shutdown sequence completed.")


# Create the main FastAPI application instance
# Register the 'lifespan' manager to handle startup/shutdown events.
app = FastAPI(
    title="Be My Assistant API",
    description="API for RAG Chatbot Assistant",
    version="0.1.0",
    lifespan=lifespan # <--- Register the lifespan context manager
)

# --- Root Endpoint ---
@app.get("/", tags=["General"]) # Added tags for better organization in docs
async def read_root():
    """
    Root endpoint providing a simple welcome message.
    Useful for checking if the server is running.
    """
    return {"message": "Welcome to Be My Assistant API! Visit /docs for API documentation."}

# --- Health Check Endpoint (Updated) ---
@app.get("/health", tags=["General"])
async def health_check(request: Request):
    """
    Checks the operational status of the API, including critical components
    like the embedding model and vector store connection.
    """
    # Check if the resources stored in app.state during startup are available.
    model_ok = hasattr(request.app.state, 'embedding_model') and request.app.state.embedding_model is not None
    db_ok = hasattr(request.app.state, 'vector_collection') and request.app.state.vector_collection is not None

    if model_ok and db_ok:
        # If resources are okay, return a success status.
        # Optionally add more checks, like trying a dummy query on the vector store.
        return {"status": "ok", "embedding_model_loaded": True, "vector_store_initialized": True}
    else:
        # If critical components failed to load, return a 503 Service Unavailable error.
        logger.error(f"Health check failed: Model OK={model_ok}, DB OK={db_ok}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "embedding_model_loaded": model_ok,
                "vector_store_initialized": db_ok,
                "message": "One or more critical components failed to initialize properly."
            }
        )

# --- Include API Routers ---
# Mount the router defined in app.api.endpoints.py onto the main application.
# The 'prefix' argument means all routes defined in api_router will start with '/api/v1'.
# The 'tags' argument helps group these endpoints in the API documentation.
app.include_router(api_router, prefix="/api/v1", tags=["RAG API"])

logger.info("FastAPI application configured. API router included under /api/v1 prefix.")

# To run this application:
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000