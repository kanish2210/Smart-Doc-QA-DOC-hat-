import logging
import time
import google.generativeai as genai
from langchain.embeddings.base import Embeddings
from app.core.config import settings
from app.services import chromadb_service

logger = logging.getLogger(__name__)


class GeminiEmbeddings(Embeddings):
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = "models/embedding-001"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(result["embedding"])
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_query"
        )
        return result["embedding"]


def get_embeddings_model() -> GeminiEmbeddings:
    return GeminiEmbeddings()


def verify_embedding_model() -> bool:
    try:
        model = get_embeddings_model()
        result = model.embed_query("test")
        if result and len(result) > 0:
            logger.info(f"Gemini embeddings OK. Dimensions: {len(result)}")
            return True
        return False
    except Exception as e:
        logger.error(f"Gemini embedding error: {e}")
        return False


def store_chunks_in_chromadb(chunks: list[dict]) -> int:
    if not chunks:
        raise ValueError("No chunks provided.")

    if not verify_embedding_model():
        raise ValueError("Gemini embedding failed. Check GEMINI_API_KEY.")

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [
        f"{c['metadata']['source']}_chunk_{c['metadata']['chunk_index']}"
        for c in chunks
    ]

    batch_size = 50
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    model = get_embeddings_model()
    total_stored = 0
    start_time = time.time()

    for i in range(total_batches):
        s = i * batch_size
        e = min(s + batch_size, len(chunks))
        try:
            stored = chromadb_service.store_chunks(
                texts=texts[s:e],
                metadatas=metadatas[s:e],
                ids=ids[s:e],
                embeddings=model
            )
            total_stored += stored
        except Exception as err:
            logger.error(f"Batch {i+1} failed: {err}")
            raise

    elapsed = time.time() - start_time
    logger.info(f"Done. {total_stored}/{len(chunks)} chunks in {elapsed:.2f}s.")
    return total_stored