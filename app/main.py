# File: app/main.py

import logging
from contextlib import asynccontextmanager

# --- Impor Limiter dari file baru ---
from slowapi import _rate_limit_exceeded_handler # Handler tetap dibutuhkan
from slowapi.errors import RateLimitExceeded
from .dependencies import limiter # Impor dari dependencies.py
# --- Akhir Impor ---

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.endpoints import router as api_router
from app.config import settings
from app.core.model_loader import initialize_embedding_model
from app.core.vector_store_manager import initialize_vector_store
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Definisi Limiter sudah dipindahkan ke dependencies.py ---

class PersonaSettingsState(BaseModel):
    ai_name: str = "AI Assistant"
    ai_role: str = "Customer Service AI"
    ai_tone: str = "friendly, helpful, enthusiastic and engaging"
    company: str = "-"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === ON STARTUP ===
    logger.info("Application startup sequence initiated...")

    # --- Tetap tambahkan Limiter (yang diimpor) ke App State ---
    app.state.limiter = limiter
    # --- Akhir Penambahan Limiter ---

    # Initialize and store the Embedding Model
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
    embedding_model = initialize_embedding_model(settings.EMBEDDING_MODEL_NAME)
    if embedding_model is None:
        logger.error("CRITICAL FAILURE: Embedding model failed to initialize.")
    app.state.embedding_model = embedding_model

    # Initialize and store the Vector Store Collection
    logger.info(f"Initializing vector store at '{settings.VECTOR_STORE_PATH}' with collection '{settings.VECTOR_COLLECTION_NAME}'")
    vector_collection = initialize_vector_store(
        persist_directory=settings.VECTOR_STORE_PATH,
        collection_name=settings.VECTOR_COLLECTION_NAME
    )
    if vector_collection is None:
        logger.error("CRITICAL FAILURE: Vector store collection failed to initialize.")
    app.state.vector_collection = vector_collection

    app.state.persona_settings = PersonaSettingsState()
    logger.info(f"Default Persona Set: Name='{app.state.persona_settings.ai_name}', Role='{app.state.persona_settings.ai_role}', Tone='{app.state.persona_settings.ai_tone}', Company='{app.state.persona_settings.company}'")

    logger.info("Application startup sequence potentially completed (check logs for errors).")

    yield

    # === ON SHUTDOWN ===
    logger.info("Application shutdown sequence initiated...")
    app.state.embedding_model = None
    app.state.vector_collection = None
    logger.info("Shared resources cleaned up.")
    logger.info("Application shutdown sequence completed.")

# --- Create FastAPI App Instance ---
app = FastAPI(
    title="Be My Assistant API",
    description="API for RAG Chatbot Assistant with Frontend",
    version="0.1.0",
    lifespan=lifespan
)

# --- Tetap tambahkan Exception Handler ---
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# --- Akhir Penambahan Exception Handler ---

# --- Mount Static Files & Templates (Unchanged) ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Frontend Endpoint (Unchanged) ---
@app.get("/", tags=["Frontend", "General"], include_in_schema=False)
async def serve_index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- Health Check Endpoint (Unchanged) ---
@app.get("/health", tags=["Status"])
async def health_check(request: Request):
    emb_model_ok = hasattr(request.app.state, 'embedding_model') and request.app.state.embedding_model is not None
    db_ok = hasattr(request.app.state, 'vector_collection') and request.app.state.vector_collection is not None

    status_detail = {
        "status": "ok",
        "embedding_model_loaded": emb_model_ok,
        "vector_store_initialized": db_ok,
    }

    if emb_model_ok and db_ok:
        return status_detail
    else:
        status_detail["status"] = "error"
        error_messages = []
        if not emb_model_ok: error_messages.append("Embedding model failed to load.")
        if not db_ok: error_messages.append("Vector store failed to initialize.")
        status_detail["message"] = " ".join(error_messages)

        logger.error(f"Health check failed: {status_detail['message']}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=status_detail
        )

# --- Include API Routers (Unchanged) ---
app.include_router(api_router, prefix="/api/v1", tags=["RAG API Endpoints"])

logger.info("FastAPI application configured. Static/templates enabled. API router included.")

# --- Hapus __all__ atau sesuaikan jika ada ekspor lain ---
# __all__ = ["app"] # Jika hanya app yang perlu diekspor