# retrieval_service.py
# Retrieval pipeline:
# Question → embed with all-MiniLM-L6-v2 → search ChromaDB → return chunks

import logging
from app.models.schemas import RetrievedChunk, RetrievalResult
from app.services.embedding_service import get_embeddings_model
from app.services import chromadb_service
from app.core.config import settings

logger = logging.getLogger(__name__)


def retrieve_relevant_chunks(
    question: str,
    k: int = None
) -> list[RetrievedChunk]:
    """
    Embeds the question and finds the top-K most relevant chunks.
    Uses the same all-MiniLM-L6-v2 model used for storing.
    """
    if k is None:
        k = settings.RETRIEVER_K

    logger.info(
        f"Searching for top {k} chunks: '{question[:60]}'"
    )

    # Use the same model that embedded the stored chunks
    model = get_embeddings_model()

    raw_results = chromadb_service.search_similar_chunks(
        query=question,
        embeddings=model,
        k=k
    )

    chunks = []
    for r in raw_results:
        meta = r.get("metadata", {})
        chunks.append(RetrievedChunk(
            text=r["text"],
            source=meta.get("source", "unknown"),
            page_number=meta.get("page_number", 0),
            score=r.get("score", 0.0),
            chunk_index=meta.get("chunk_index", 0)
        ))

    if chunks:
        logger.info(
            f"Retrieved {len(chunks)} chunks. "
            f"Best score: {chunks[0].score:.4f} "
            f"(lower = more relevant)"
        )

    return chunks


def build_context(chunks: list[RetrievedChunk]) -> str:
    """
    Formats retrieved chunks into a single context block.
    Each chunk is labelled with its source and page number.
    This context block is sent to Gemini as background information.
    """
    if not chunks:
        return ""

    parts = []
    for chunk in chunks:
        header = (
            f"[Source: {chunk.source} | "
            f"Page: {chunk.page_number} | "
            f"Relevance: {chunk.score:.4f}]"
        )
        parts.append(f"{header}\n{chunk.text}")

    return "\n\n".join(parts)


def retrieve(question: str, k: int = None) -> RetrievalResult:
    """
    Master retrieval function.
    Returns RetrievalResult with context, chunks, and sources.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    question = question.strip()
    logger.info(f"Retrieval for: '{question[:80]}'")

    chunks = retrieve_relevant_chunks(question=question, k=k)

    if not chunks:
        return RetrievalResult(
            question=question,
            context="",
            chunks=[],
            total_chunks=0,
            sources=[]
        )

    context = build_context(chunks)
    sources = list(dict.fromkeys(c.source for c in chunks))

    logger.info(
        f"Retrieval complete. "
        f"{len(chunks)} chunks from: {sources}"
    )

    return RetrievalResult(
        question=question,
        context=context,
        chunks=chunks,
        total_chunks=len(chunks),
        sources=sources
    )