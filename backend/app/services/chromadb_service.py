# chromadb_service.py
# All ChromaDB vector database operations.
# Store, search, retrieve, and delete document embeddings.

import logging
import os
import shutil
from typing import Optional
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "smart_doc_qa"
# One collection for all documents in this app


def get_collection(
    embeddings: SentenceTransformerEmbeddings
) -> Chroma:
    """
    Opens or creates the ChromaDB collection.
    If collection exists it opens it.
    If not it creates a new empty one.
    """
    os.makedirs(settings.VECTORSTORE_DIR, exist_ok=True)

    return Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=settings.VECTORSTORE_DIR,
        embedding_function=embeddings
    )


def store_chunks(
    texts: list[str],
    metadatas: list[dict],
    ids: list[str],
    embeddings: SentenceTransformerEmbeddings
) -> int:
    """
    Stores a batch of text chunks with embeddings in ChromaDB.
    Uses unique IDs to prevent duplicates on re-upload.
    Returns number of chunks stored.
    """
    if not texts:
        raise ValueError("No texts provided.")

    Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        ids=ids,
        collection_name=COLLECTION_NAME,
        persist_directory=settings.VECTORSTORE_DIR
    )

    logger.debug(f"Stored {len(texts)} chunks in ChromaDB.")
    return len(texts)


def search_similar_chunks(
    query: str,
    embeddings: SentenceTransformerEmbeddings,
    k: Optional[int] = None
) -> list[dict]:
    """
    Searches ChromaDB for chunks most similar to the query.
    Returns list of dicts with text, metadata, and score.
    Lower score = more relevant.
    """
    if k is None:
        k = settings.RETRIEVER_K

    vectorstore = get_collection(embeddings)
    count = vectorstore._collection.count()

    if count == 0:
        raise ValueError(
            "ChromaDB is empty. Please upload a PDF first."
        )

    results = vectorstore.similarity_search_with_score(
        query=query,
        k=min(k, count)
    )

    return [
        {
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": round(float(score), 4)
        }
        for doc, score in results
    ]


def get_collection_stats() -> dict:
    """
    Returns statistics about stored documents and chunks.
    """
    empty_stats = {
        "total_chunks": 0,
        "total_documents": 0,
        "documents": [],
        "collection_name": COLLECTION_NAME,
        "persist_directory": settings.VECTORSTORE_DIR
    }

    if not os.path.exists(settings.VECTORSTORE_DIR):
        return empty_stats

    try:
        import chromadb
        client = chromadb.PersistentClient(
            path=settings.VECTORSTORE_DIR
        )

        try:
            collection = client.get_collection(name=COLLECTION_NAME)
        except Exception:
            return empty_stats

        total = collection.count()
        if total == 0:
            return empty_stats

        # Fetch all metadata to build per-document stats
        items = collection.get(include=["metadatas"])
        doc_stats = {}

        for meta in items["metadatas"]:
            if not meta:
                continue
            src = meta.get("source", "unknown")
            pg = meta.get("page_number", 0)

            if src not in doc_stats:
                doc_stats[src] = {
                    "chunk_count": 0,
                    "pages": set()
                }

            doc_stats[src]["chunk_count"] += 1
            doc_stats[src]["pages"].add(pg)

        documents = sorted([
            {
                "filename": src,
                "chunk_count": s["chunk_count"],
                "pages": sorted(list(s["pages"]))
            }
            for src, s in doc_stats.items()
        ], key=lambda x: x["filename"])

        return {
            "total_chunks": total,
            "total_documents": len(documents),
            "documents": documents,
            "collection_name": COLLECTION_NAME,
            "persist_directory": settings.VECTORSTORE_DIR
        }

    except Exception as e:
        logger.error(f"Stats error: {e}")
        return empty_stats


def get_stored_documents() -> list[str]:
    """Returns list of stored document filenames."""
    stats = get_collection_stats()
    return [d["filename"] for d in stats["documents"]]


def delete_document(filename: str) -> int:
    """
    Deletes all chunks for a specific document.
    Returns number of chunks deleted.
    """
    import chromadb
    client = chromadb.PersistentClient(
        path=settings.VECTORSTORE_DIR
    )

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        raise ValueError("ChromaDB collection does not exist.")

    results = collection.get(
        where={"source": filename},
        include=["metadatas"]
    )

    ids = results["ids"]
    if not ids:
        raise ValueError(
            f"Document '{filename}' not found in ChromaDB."
        )

    collection.delete(ids=ids)
    logger.info(f"Deleted {len(ids)} chunks for '{filename}'.")
    return len(ids)


def delete_all_documents() -> int:
    """
    Deletes entire ChromaDB vectorstore from disk.
    Returns total chunks deleted.
    """
    stats = get_collection_stats()
    total = stats["total_chunks"]

    if os.path.exists(settings.VECTORSTORE_DIR):
        shutil.rmtree(settings.VECTORSTORE_DIR)
        os.makedirs(settings.VECTORSTORE_DIR, exist_ok=True)

    logger.info(f"Deleted entire vectorstore ({total} chunks).")
    return total