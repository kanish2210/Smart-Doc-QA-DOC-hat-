from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "models/embedding-001"
    VECTORSTORE_DIR: str = "vectorstore"
    RETRIEVER_K: int = 4
    UPLOAD_DIR: str = "uploads"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

def validate_config(s: Settings) -> None:
    if not s.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set!")
    else:
        logger.info(f"GEMINI_API_KEY loaded. Model: {s.LLM_MODEL}")

settings = Settings()