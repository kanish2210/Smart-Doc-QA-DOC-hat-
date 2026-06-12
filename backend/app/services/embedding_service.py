# embedding_service.py
# Generates embeddings using all-MiniLM-L6-v2 (runs locally, free).
# Stores embeddings in ChromaDB via chromadb_service.

import logging
import time
from langchain_community.embeddings import SentenceTransformerEmbeddings
# SentenceTransformerEmbeddings : LangChain wrapper for local models
# Downloads and runs all-MiniLM-L6-v2 on your machine
# No API key needed — completely free and private

from app.core.config import settings
from app.services import chromadb_service

logger = logging.getLogger(__name__)


def get_embeddings_model() -> SentenceTransformerEmbeddings:
    """
    Creates the all-MiniLM-L6-v2 embedding model.

    This model:
    - Runs completely locally on your machine
    - Requires no API key
    - Produces 384-dimensional vectors
    - Is fast and accurate for semantic search
    - Downloads automatically on first use (~90MB)
    """
    logger.debug(f"Loading embedding model: {settings.EMBEDDING_MODEL}")

    return SentenceTransformerEmbeddings(
        model_name=settings.EMBEDDING_MODEL
        # all-MiniLM-L6-v2 : Small, fast, high quality
        # Downloaded from HuggingFace on first run
        # Cached locally after first download
    )


def verify_embedding_model() -> bool:
    """
    Tests the embedding model by encoding a short string.
    Returns True if working correctly.
    """
    logger.info("Verifying embedding model...")

    try:
        model = get_embeddings_model()
        result = model.embed_query("test connection")

        if result and len(result) > 0:
            logger.info(
                f"Embedding model verified. "
                f"Dimensions: {len(result)}"
            )
            return True

        logger.error("Embedding model returned empty vector.")
        return False

    except Exception as e:
        logger.error(f"Embedding model error: {e}")
        return False


def store_chunks_in_chromadb(chunks: list[dict]) -> int:
    """
    Converts chunks to embeddings and stores in ChromaDB.
    Uses all-MiniLM-L6-v2 for local embedding generation.

    Processes in batches of 50 to manage memory efficiently.
    Returns total number of chunks stored.
    """
    if not chunks:
        raise ValueError("No chunks provided.")

    logger.info(f"Starting embedding for {len(chunks)} chunks...")

    # Verify model loads correctly before processing
    if not verify_embedding_model():
        raise ValueError(
            "Embedding model failed to load. "
            "Run: pip install sentence-transformers"
        )

    # Prepare data lists
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [
        f"{c['metadata']['source']}_chunk_{c['metadata']['chunk_index']}"
        for c in chunks
    ]

    # Process in batches
    batch_size = 50
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    model = get_embeddings_model()
    total_stored = 0
    start_time = time.time()

    logger.info(f"Processing {total_batches} batch(es)...")

    for i in range(total_batches):
        s = i * batch_size
        e = min(s + batch_size, len(chunks))

        logger.info(f"Batch {i+1}/{total_batches} (chunks {s+1}-{e})...")

        try:
            stored = chromadb_service.store_chunks(
                texts=texts[s:e],
                metadatas=metadatas[s:e],
                ids=ids[s:e],
                embeddings=model
            )
            total_stored += stored
            logger.info(f"Batch {i+1} done — {stored} chunks stored.")

        except Exception as err:
            logger.error(f"Batch {i+1} failed: {err}")
            raise

    elapsed = time.time() - start_time
    logger.info(
        f"Embedding complete. "
        f"{total_stored}/{len(chunks)} chunks stored "
        f"in {elapsed:.2f}s."
    )
    return total_stored