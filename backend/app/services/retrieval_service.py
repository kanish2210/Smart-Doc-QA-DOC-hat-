import logging
from app.models.schemas import RetrievedChunk, RetrievalResult
from app.services.embedding_service import get_embeddings_model
from app.services import chromadb_service
from app.core.config import settings

logger = logging.getLogger(__name__)


def retrieve_relevant_chunks(
    question: str,
    filename: str,
    k: int = None
) -> list[RetrievedChunk]:
    if k is None:
        k = settings.RETRIEVER_K

    model = get_embeddings_model()

    raw_results = chromadb_service.search_similar_chunks(
        query=question,
        embeddings=model,
        filename=filename,
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

    return chunks


def build_context(chunks: list[RetrievedChunk]) -> str:
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


def retrieve(question: str, filename: str, k: int = None) -> RetrievalResult:
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    question = question.strip()
    chunks = retrieve_relevant_chunks(question=question, filename=filename, k=k)

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

    return RetrievalResult(
        question=question,
        context=context,
        chunks=chunks,
        total_chunks=len(chunks),
        sources=sources
    )