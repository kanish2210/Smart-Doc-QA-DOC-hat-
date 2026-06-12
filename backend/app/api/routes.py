# routes.py
# All FastAPI API endpoints.

import logging
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import (
    UploadResponse,
    AskRequest,
    AnswerResponse,
    HealthResponse,
    CollectionStats,
    DocumentInfo,
    DeleteResponse,
    RetrievalResult,
    QuestionRequest,
    ProcessRequest,
    ProcessResponse,
    ChatHistory,
    ClearHistoryResponse,
)
from app.services.pdf_service import process_pdf, extract_text_from_pdf
from app.services.chunking_service import chunk_pages, get_chunk_stats
from app.services.embedding_service import store_chunks_in_chromadb
from app.services import chromadb_service
from app.services.retrieval_service import retrieve
from app.services.llm_service import generate_answer
from app.services import history_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """GET /api/health — confirms server is running."""
    return HealthResponse(
        status="ok",
        message="Smart Document Q&A backend is running."
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    POST /api/upload
    Full pipeline: validate → save → extract → chunk → embed → store.
    """
    logger.info(f"Upload request: {file.filename}")

    try:
        # Step 1 — Process PDF
        pdf_result = process_pdf(file)
        logger.info(
            f"PDF processed: {pdf_result['total_pages']} pages."
        )

        # Step 2 — Chunk
        chunks = chunk_pages(
            pages=pdf_result["pages"],
            filename=file.filename
        )
        stats = get_chunk_stats(chunks)
        logger.info(
            f"Chunks created: {stats['total']} "
            f"(avg {stats['avg_length']} chars)"
        )

        # Step 3 — Embed and store
        stored = store_chunks_in_chromadb(chunks)
        logger.info(f"Stored {stored} chunks in ChromaDB.")

        return UploadResponse(
            message=(
                f"Successfully processed '{file.filename}'. "
                f"Extracted {pdf_result['total_pages']} pages, "
                f"stored {stored} chunks."
            ),
            filename=file.filename,
            chunks=stored,
            total_pages=pdf_result["total_pages"],
            file_path=pdf_result["file_path"]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-document", response_model=ProcessResponse)
async def process_document(request: ProcessRequest):
    """
    POST /api/process-document
    Reprocess a PDF already saved in the uploads folder.
    """
    file_path = os.path.join(settings.UPLOAD_DIR, request.filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{request.filename}' not found in uploads. "
                "Upload it first."
            )
        )

    try:
        pages = extract_text_from_pdf(file_path)
        chunks = chunk_pages(
            pages=pages,
            filename=request.filename
        )

        # Remove old chunks before re-storing
        try:
            chromadb_service.delete_document(request.filename)
            logger.info("Old chunks removed.")
        except ValueError:
            pass  # Document wasn't stored yet — that's fine

        stored = store_chunks_in_chromadb(chunks)

        return ProcessResponse(
            message=f"'{request.filename}' reprocessed successfully.",
            filename=request.filename,
            chunks=stored,
            total_pages=len(pages),
            success=True
        )

    except Exception as e:
        logger.error(f"Reprocess error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(request: AskRequest):
    """
    POST /api/ask
    Full RAG pipeline: retrieve → prompt Gemini → return answer.
    """
    logger.info(f"Question: '{request.question[:80]}'")

    try:
        # Save question to history
        history_service.add_user_message(request.question)

        # Generate answer
        result = generate_answer(
            question=request.question,
            k=request.k
        )

        # Save answer to history
        history_service.add_assistant_message(
            answer=result.answer,
            sources=result.sources
        )

        logger.info(
            f"Answer generated. "
            f"found={result.answer_found}, "
            f"chunks={result.chunks_used}"
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-history", response_model=ChatHistory)
async def get_chat_history():
    """GET /api/chat-history — returns conversation history."""
    messages = history_service.get_history()
    return ChatHistory(
        messages=messages,
        total=len(messages),
        session_id=history_service.SESSION_ID
    )


@router.delete("/chat-history", response_model=ClearHistoryResponse)
async def clear_chat_history():
    """DELETE /api/chat-history — clears all history."""
    count = history_service.clear_history()
    return ClearHistoryResponse(
        message="Chat history cleared.",
        cleared=count,
        success=True
    )


@router.get("/documents")
async def list_documents():
    """GET /api/documents — lists all stored documents."""
    try:
        docs = chromadb_service.get_stored_documents()
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection/stats", response_model=CollectionStats)
async def get_collection_stats():
    """GET /api/collection/stats — ChromaDB statistics."""
    try:
        raw = chromadb_service.get_collection_stats()
        return CollectionStats(
            total_chunks=raw["total_chunks"],
            total_documents=raw["total_documents"],
            documents=[
                DocumentInfo(
                    filename=d["filename"],
                    chunk_count=d["chunk_count"],
                    pages=d["pages"]
                )
                for d in raw["documents"]
            ],
            collection_name=raw["collection_name"],
            persist_directory=raw["persist_directory"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve", response_model=RetrievalResult)
async def retrieve_chunks(request: QuestionRequest):
    """POST /api/retrieve — debug retrieval without LLM."""
    try:
        return retrieve(question=request.question)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{filename}", response_model=DeleteResponse)
async def delete_document(filename: str):
    """DELETE /api/documents/{filename} — delete one document."""
    try:
        deleted = chromadb_service.delete_document(filename)
        return DeleteResponse(
            message=f"'{filename}' deleted successfully.",
            filename=filename,
            chunks_deleted=deleted,
            success=True
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents", response_model=DeleteResponse)
async def delete_all_documents():
    """DELETE /api/documents — delete entire ChromaDB."""
    try:
        deleted = chromadb_service.delete_all_documents()
        return DeleteResponse(
            message="All documents deleted successfully.",
            filename="ALL",
            chunks_deleted=deleted,
            success=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))