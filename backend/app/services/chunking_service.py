# chunking_service.py
# Splits extracted PDF pages into smaller text chunks.
# Uses chunk size 800 with 150 character overlap.

import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.models.schemas import PageContent
from app.core.config import settings

logger = logging.getLogger(__name__)


def create_text_splitter() -> RecursiveCharacterTextSplitter:
    """
    Creates the text splitter with settings from config.
    Tries to split on paragraphs first, then sentences, then words.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        # 800 characters per chunk

        chunk_overlap=settings.CHUNK_OVERLAP,
        # 150 characters overlap between chunks
        # Prevents losing context at chunk boundaries

        length_function=len,
        # Measures chunk size by character count

        separators=["\n\n", "\n", ". ", " ", ""]
        # Split order: paragraphs → lines → sentences → words → chars
    )


def chunk_pages(
    pages: list[PageContent],
    filename: str
) -> list[dict]:
    """
    Splits all pages into chunks with metadata.

    Each chunk dict contains:
    - text     : The chunk content
    - metadata : source filename, page number, chunk index
    """
    if not pages:
        raise ValueError("No pages provided for chunking.")

    splitter = create_text_splitter()
    all_chunks = []
    chunk_index = 0

    for page in pages:
        # Split this page's text into chunks
        page_chunks = splitter.split_text(page.text)

        for chunk_text in page_chunks:
            # Skip whitespace-only chunks
            if not chunk_text.strip():
                continue

            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": filename,
                    "page_number": page.page_number,
                    "chunk_index": chunk_index,
                    "total_chunks": 0
                    # total_chunks updated after all chunks created
                }
            })
            chunk_index += 1

    # Now we know the total — update every chunk
    total = len(all_chunks)
    for chunk in all_chunks:
        chunk["metadata"]["total_chunks"] = total

    if not all_chunks:
        raise ValueError("No chunks could be created from this PDF.")

    logger.info(
        f"Created {total} chunks from {len(pages)} pages. "
        f"Chunk size: {settings.CHUNK_SIZE}, "
        f"Overlap: {settings.CHUNK_OVERLAP}"
    )
    return all_chunks


def get_chunk_stats(chunks: list[dict]) -> dict:
    """Returns statistics about the created chunks."""
    if not chunks:
        return {
            "total": 0,
            "avg_length": 0,
            "min_length": 0,
            "max_length": 0
        }

    lengths = [len(c["text"]) for c in chunks]
    return {
        "total": len(chunks),
        "avg_length": int(sum(lengths) / len(lengths)),
        "min_length": min(lengths),
        "max_length": max(lengths)
    }