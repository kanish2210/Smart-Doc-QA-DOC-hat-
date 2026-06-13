import logging
import os
import shutil
from typing import Optional
from langchain_community.vectorstores import Chroma
from app.core.config import settings

logger = logging.getLogger(__name__)


def _collection_name(filename: str) -> str:
    import re
    # Remove file extension
    name = filename.rsplit(".", 1)[0]
    # Replace any invalid character with underscore
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Strip leading/trailing underscores
    name = name.strip('_')
    # Ensure starts and ends with alphanumeric
    if not name[0].isalnum():
        name = 'doc' + name
    if not name[-1].isalnum():
        name = name + '0'
    # Prefix and trim to 63 chars
    name = f"doc_{name}"[:63]
    # Ensure ends with alphanumeric after trim
    while name and not name[-1].isalnum():
        name = name[:-1]
    return name


def _get_collection(filename: str, embeddings) -> Chroma:
    os.makedirs(settings.VECTORSTORE_DIR, exist_ok=True)
    return Chroma(
        collection_name=_collection_name(filename),
        persist_directory=settings.VECTORSTORE_DIR,
        embedding_function=embeddings
    )


def store_chunks(
    texts: list[str],
    metadatas: list[dict],
    ids: list[str],
    embeddings,
    filename: str
) -> int:
    if not texts:
        raise ValueError("No texts provided.")

    Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        ids=ids,
        collection_name=_collection_name(filename),
        persist_directory=settings.VECTORSTORE_DIR
    )

    logger.debug(f"Stored {len(texts)} chunks for '{filename}'.")
    return len(texts)


def search_similar_chunks(
    query: str,
    embeddings,
    filename: str,
    k: Optional[int] = None
) -> list[dict]:
    if k is None:
        k = settings.RETRIEVER_K

    vectorstore = _get_collection(filename, embeddings)
    count = vectorstore._collection.count()

    if count == 0:
        raise ValueError(
            f"No chunks found for '{filename}'. Please upload the PDF first."
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


def get_stored_documents() -> list[str]:
    if not os.path.exists(settings.VECTORSTORE_DIR):
        return []
    try:
        import chromadb
        client = chromadb.PersistentClient(path=settings.VECTORSTORE_DIR)
        collections = client.list_collections()
        docs = []
        for col in collections:
            if col.name.startswith("doc_"):
                name = col.name[4:].replace("_", ".")
                original = name
                for ext in [".pdf", ".PDF"]:
                    if original.endswith(ext.replace(".", "_")):
                        original = original[:-len(ext)] + ext
                docs.append(col.name[4:])
        return docs
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return []


def document_exists(filename: str) -> bool:
    if not os.path.exists(settings.VECTORSTORE_DIR):
        return False
    try:
        import chromadb
        client = chromadb.PersistentClient(path=settings.VECTORSTORE_DIR)
        try:
            client.get_collection(_collection_name(filename))
            return True
        except Exception:
            return False
    except Exception:
        return False


def delete_document(filename: str) -> int:
    import chromadb
    client = chromadb.PersistentClient(path=settings.VECTORSTORE_DIR)
    col_name = _collection_name(filename)
    try:
        collection = client.get_collection(col_name)
        count = collection.count()
        client.delete_collection(col_name)
        logger.info(f"Deleted collection '{col_name}' ({count} chunks).")
        return count
    except Exception:
        raise ValueError(f"Document '{filename}' not found.")


def delete_all_documents() -> int:
    total = 0
    if os.path.exists(settings.VECTORSTORE_DIR):
        shutil.rmtree(settings.VECTORSTORE_DIR)
        os.makedirs(settings.VECTORSTORE_DIR, exist_ok=True)
    return total


def get_collection_stats() -> dict:
    if not os.path.exists(settings.VECTORSTORE_DIR):
        return {"total_chunks": 0, "total_documents": 0, "documents": [],
                "collection_name": "per_file", "persist_directory": settings.VECTORSTORE_DIR}
    try:
        import chromadb
        client = chromadb.PersistentClient(path=settings.VECTORSTORE_DIR)
        collections = client.list_collections()
        docs = []
        total = 0
        for col in collections:
            if col.name.startswith("doc_"):
                c = client.get_collection(col.name)
                count = c.count()
                total += count
                docs.append({
                    "filename": col.name[4:],
                    "chunk_count": count,
                    "pages": []
                })
        return {
            "total_chunks": total,
            "total_documents": len(docs),
            "documents": docs,
            "collection_name": "per_file",
            "persist_directory": settings.VECTORSTORE_DIR
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total_chunks": 0, "total_documents": 0, "documents": [],
                "collection_name": "per_file", "persist_directory": settings.VECTORSTORE_DIR}