import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.models.schemas import PageContent
from app.core.config import settings

logger = logging.getLogger(__name__)


def create_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )


def chunk_pages(
    pages: list[PageContent],
    filename: str
) -> list[dict]:
    if not pages:
        raise ValueError("No pages provided for chunking.")

    splitter = create_text_splitter()
    all_chunks = []
    chunk_index = 0

    for page in pages:
        page_chunks = splitter.split_text(page.text)
        for chunk_text in page_chunks:
            if not chunk_text.strip():
                continue
            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": filename,
                    "page_number": page.page_number,
                    "chunk_index": chunk_index,
                    "total_chunks": 0
                }
            })
            chunk_index += 1

    total = len(all_chunks)
    for chunk in all_chunks:
        chunk["metadata"]["total_chunks"] = total

    if not all_chunks:
        raise ValueError("No chunks could be created from this file.")

    logger.info(f"Created {total} chunks from {len(pages)} pages.")
    return all_chunks


def get_chunk_stats(chunks: list[dict]) -> dict:
    if not chunks:
        return {"total": 0, "avg_length": 0, "min_length": 0, "max_length": 0}

    lengths = [len(c["text"]) for c in chunks]
    return {
        "total": len(chunks),
        "avg_length": int(sum(lengths) / len(lengths)),
        "min_length": min(lengths),
        "max_length": max(lengths)
    }