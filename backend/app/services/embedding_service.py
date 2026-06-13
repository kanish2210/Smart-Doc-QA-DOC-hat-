import logging
import time
from langchain_community.embeddings import SentenceTransformerEmbeddings
from app.core.config import settings
from app.services import chromadb_service

logger = logging.getLogger(__name__)


def get_embeddings_model() -> SentenceTransformerEmbeddings:
    return SentenceTransformerEmbeddings(model_name=settings.EMBEDDING_MODEL)


def store_chunks_in_chromadb(chunks: list[dict], filename: str) -> int:
    if not chunks:
        raise ValueError("No chunks provided.")

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
                embeddings=model,
                filename=filename
            )
            total_stored += stored
        except Exception as err:
            logger.error(f"Batch {i+1} failed: {err}")
            raise

    elapsed = time.time() - start_time
    logger.info(f"Done. {total_stored}/{len(chunks)} chunks in {elapsed:.2f}s.")
    return total_stored