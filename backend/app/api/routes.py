# routes.py
# Updated: uses SQLite history_service.
# Added /sessions and /sessions/{id} endpoints.
# Upload wipes ChromaDB first + links document to session.

import logging
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import (
    UploadResponse, AskRequest, AnswerResponse, HealthResponse,
    CollectionStats, DocumentInfo, DeleteResponse, RetrievalResult,
    QuestionRequest, ProcessRequest, ProcessResponse,
    ChatHistory, ClearHistoryResponse,
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
    return HealthResponse(
        status="ok",
        message="Smart Document Q&A backend is running."
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    POST /api/upload
    1. Wipes ChromaDB — only current doc answers questions.
    2. Extracts, chunks, embeds, stores.
    3. Links document name to current SQLite session.
    """
    logger.info(f"Upload request: {file.filename}")
    try:
        # Step 1 — Process PDF
        pdf_result = process_pdf(file)
        logger.info(f"PDF processed: {pdf_result['total_pages']} pages.")

        # Step 2 — Wipe ALL previous docs from ChromaDB
        try:
            wiped = chromadb_service.delete_all_documents()
            if wiped > 0:
                logger.info(f"Cleared {wiped} old chunks from ChromaDB.")
        except Exception as e:
            logger.warning(f"ChromaDB wipe skipped: {e}")

        # Step 3 — Chunk
        chunks = chunk_pages(pages=pdf_result["pages"], filename=file.filename)
        stats = get_chunk_stats(chunks)
        logger.info(f"Chunks: {stats['total']} (avg {stats['avg_length']} chars)")

        # Step 4 — Embed and store
        stored = store_chunks_in_chromadb(chunks)
        logger.info(f"Stored {stored} chunks for '{file.filename}'.")

        # Step 5 — Link document to current session in SQLite
        history_service.update_session_document(file.filename)

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


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(request: AskRequest):
    logger.info(f"Question: '{request.question[:80]}'")
    try:
        history_service.add_user_message(request.question)
        result = generate_answer(question=request.question, k=request.k)
        history_service.add_assistant_message(
            answer=result.answer,
            sources=result.sources
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-history", response_model=ChatHistory)
async def get_chat_history():
    messages = history_service.get_history()
    return ChatHistory(
        messages=messages,
        total=len(messages),
        session_id=history_service.SESSION_ID
    )


@router.delete("/chat-history", response_model=ClearHistoryResponse)
async def clear_chat_history():
    count = history_service.clear_history()
    return ClearHistoryResponse(
        message="Chat history cleared.",
        cleared=count,
        success=True
    )


# ── Session history endpoints ─────────────────────────────────────

@router.get("/sessions")
async def get_all_sessions():
    """
    GET /api/sessions
    Returns all past sessions with document name, date,
    message count, and first question preview.
    Used by Streamlit sidebar to populate the history list.
    """
    try:
        sessions = history_service.get_all_sessions()
        return {"sessions": sessions, "total": len(sessions)}
    except Exception as e:
        logger.error(f"Sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=ChatHistory)
async def get_session_history(session_id: str):
    """
    GET /api/sessions/{session_id}
    Returns all messages for one specific past session.
    Called when user clicks a session card in the sidebar.
    """
    try:
        messages = history_service.get_session_messages(session_id)
        if not messages:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{session_id}' not found."
            )
        return ChatHistory(
            messages=messages,
            total=len(messages),
            session_id=session_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Document endpoints ────────────────────────────────────────────

@router.get("/documents")
async def list_documents():
    try:
        docs = chromadb_service.get_stored_documents()
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection/stats", response_model=CollectionStats)
async def get_collection_stats():
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
    try:
        return retrieve(question=request.question)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{filename}", response_model=DeleteResponse)
async def delete_document(filename: str):
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


@router.post("/process-document", response_model=ProcessResponse)
async def process_document(request: ProcessRequest):
    file_path = os.path.join(settings.UPLOAD_DIR, request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"'{request.filename}' not found in uploads."
        )
    try:
        pages = extract_text_from_pdf(file_path)
        chunks = chunk_pages(pages=pages, filename=request.filename)
        try:
            chromadb_service.delete_all_documents()
        except Exception:
            pass
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