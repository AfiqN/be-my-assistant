import logging
from contextlib import asynccontextmanager # Required for lifespan management
from fastapi import FastAPI, Request, HTTPException, status # Import Request, HTTPException, status
# Import StaticFiles for serving CSS/JS and Jinja2Templates for HTML
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# APIRouter might be needed if you move the HTML endpoint later
# from fastapi import APIRouter

# Import the API router from endpoints.py and the application settings
from app.api.endpoints import router as api_router
from app.config import settings

# Import the initializer functions from core modules
from app.core.vector_store_manager import initialize_embedding_model, initialize_vector_store

# Setup basic logging (configure as needed, e.g., using file handlers)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Lifespan Management for Shared Resources ---
# (Your existing lifespan code remains unchanged here)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === Code here runs ON STARTUP ===
    logger.info("Application startup sequence initiated...")

    # Initialize and store the Embedding Model
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
    embedding_model = initialize_embedding_model(settings.EMBEDDING_MODEL_NAME)
    if embedding_model is None:
        logger.error("CRITICAL FAILURE: Embedding model could not be initialized on startup.")
        raise RuntimeError("Could not initialize embedding model during application startup.")
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
    # Perform any cleanup if necessary
    app.state.embedding_model = None
    app.state.vector_collection = None
    logger.info("Shared resources cleaned up from application state.")
    logger.info("Application shutdown sequence completed.")


# --- Create FastAPI App Instance ---
# Register the 'lifespan' manager to handle startup/shutdown events.
app = FastAPI(
    title="Be My Assistant API",
    description="API for RAG Chatbot Assistant with Frontend", # Updated description
    version="0.1.0",
    lifespan=lifespan
)

# --- Mount Static Files Directory ---
# This line tells FastAPI: "Any request starting with '/static' should look for a corresponding file
# inside the directory named 'static' relative to where the app is running".
# The 'name="static"' allows generating URLs for static files if needed.
# Ensure the 'static/' directory exists at your project root (alongside 'app/').
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Setup Jinja2 Templates ---
# This tells FastAPI where to find HTML template files.
# Ensure the 'templates/' directory exists at your project root.
templates = Jinja2Templates(directory="templates")

# --- Frontend Endpoint (Serves index.html) ---
# We replace the old root endpoint with one that serves the HTML page.
@app.get("/", tags=["Frontend", "General"], include_in_schema=False) # Use GET for web pages, exclude from OpenAPI docs
async def serve_index_page(request: Request):
    """
    Serves the main index.html page for the chatbot frontend.
    """
    # 'request' object is required by Jinja2Templates for context.
    # It renders the 'index.html' file found in the 'templates' directory.
    return templates.TemplateResponse("index.html", {"request": request})

# --- Health Check Endpoint ---
# Keep the health check, maybe tag it differently for docs organization
@app.get("/health", tags=["Status"])
async def health_check(request: Request):
    """
    Checks the operational status of the API's critical components.
    """
    # (Your existing health check logic remains unchanged here)
    model_ok = hasattr(request.app.state, 'embedding_model') and request.app.state.embedding_model is not None
    db_ok = hasattr(request.app.state, 'vector_collection') and request.app.state.vector_collection is not None

    if model_ok and db_ok:
        return {"status": "ok", "embedding_model_loaded": True, "vector_store_initialized": True}
    else:
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
# Mount the API endpoints defined in app.api.endpoints.py (like /upload, /chat)
# These will be accessible under the '/api/v1' prefix.
app.include_router(api_router, prefix="/api/v1", tags=["RAG API Endpoints"])

logger.info("FastAPI application configured. Static files and templates enabled. API router included under /api/v1 prefix.")

# To run this application:
# uvicorn app.main:app --reload --port 8000
# Then access the frontend at http://localhost:8000/