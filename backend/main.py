# main.py
# FastAPI application entry point.
# Creates app, adds middleware, registers routes, handles startup.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings, validate_config
import os
import logging

# Configure logging for entire application
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Smart Document Q&A API",
    description=(
        "RAG chatbot: upload PDFs and ask questions. "
        "Uses all-MiniLM-L6-v2 embeddings + Gemini 2.0 Flash."
    ),
    version="1.0.0",
)

# CORS — allows Streamlit (port 8501) to call FastAPI (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routes with /api prefix
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Runs once when server starts."""

    # Create data folders if missing
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.VECTORSTORE_DIR, exist_ok=True)

    # Validate configuration
    try:
        validate_config(settings)
    except ValueError as e:
        logger.error(f"Config error: {e}")

    # Print startup summary
    logger.info("=" * 50)
    logger.info("   Smart Document Q&A — STARTED")
    logger.info("=" * 50)
    logger.info(f"  API Docs  : http://127.0.0.1:8000/docs")
    logger.info(f"  Health    : http://127.0.0.1:8000/api/health")
    logger.info(f"  LLM       : {settings.LLM_MODEL}")
    logger.info(f"  Embeddings: {settings.EMBEDDING_MODEL}")
    logger.info(f"  Chunk size: {settings.CHUNK_SIZE}")
    logger.info(f"  Overlap   : {settings.CHUNK_OVERLAP}")
    logger.info(
        f"  Gemini Key: "
        f"{'SET' if settings.GEMINI_API_KEY else 'MISSING — check .env'}"
    )
    logger.info("=" * 50)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Smart Document Q&A API is running.",
        "docs": "http://127.0.0.1:8000/docs",
        "health": "http://127.0.0.1:8000/api/health"
    }