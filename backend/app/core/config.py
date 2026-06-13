# config.py
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):

    # Gemini
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"

    # Embeddings (runs locally, no API needed)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # ChromaDB
    VECTORSTORE_DIR: str = "vectorstore"
    RETRIEVER_K: int = 4

    # File Upload
    UPLOAD_DIR: str = "uploads"

    # Chunking
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


def validate_config(s: Settings) -> None:
    """
    Validates critical settings on startup.
    Warns if GEMINI_API_KEY is missing but does not crash.
    """
    if not s.GEMINI_API_KEY:
        logger.warning(
            "GEMINI_API_KEY is not set! "
            "Add it to backend/.env — the app will not answer questions without it."
        )
    else:
        logger.info(f"GEMINI_API_KEY loaded. Model: {s.LLM_MODEL}")


settings = Settings()
