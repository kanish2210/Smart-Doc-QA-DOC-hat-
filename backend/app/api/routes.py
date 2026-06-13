import logging
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import (
    UploadResponse, AskRequest, AnswerResponse, HealthResponse,
    CollectionStats, DocumentInfo, DeleteResponse, RetrievalResult,
    QuestionRequest, ChatHistory, ClearHistoryResponse,
)
from app.services.pdf_service import process_pdf
from app.services.chunking_service import chunk_pages, get_chunk_stats
from app.services.embedding_service import store_chunks_in_chromadb
from app.services import chromadb_service
from app.services import history_service
from app.services.llm_service import generate_answer
from app.core.config import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class AskRequestWithFile(BaseModel):
    question: str
    filename: str
    k: int = 4


class ClearFileHistory(BaseModel):
    filename: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        message="Smart Document Q&A backend is running."
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    logger.info(f"Upload request: {file.filename}")
    try:
        # Check if already exists
        exists = chromadb_service.document_exists(file.filename)

        pdf_result = process_pdf(file)
        chunks = chunk_pages(pages=pdf_result["pages"], filename=file.filename)
        stats = get_chunk_stats(chunks)

        # Delete old collection if re-uploading
        if exists:
            try:
                chromadb_service.delete_document(file.filename)
            except Exception:
                pass

        stored = store_chunks_in_chromadb(chunks, filename=file.filename)

        return UploadResponse(
            message=f"Successfully processed '{file.filename}'.",
            filename=file.filename,
            chunks=stored,
            total_pages=pdf_result["total_pages"],
            file_path=pdf_result["file_path"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/check/{filename}")
async def check_document_exists(filename: str):
    exists = chromadb_service.document_exists(filename)
    return {"exists": exists, "filename": filename}


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(request: AskRequestWithFile):
    logger.info(f"Question for '{request.filename}': '{request.question[:80]}'")
    try:
        history_service.add_user_message(request.filename, request.question)

        result = generate_answer(
            question=request.question,
            filename=request.filename,
            k=request.k
        )

        history_service.add_assistant_message(
            filename=request.filename,
            answer=result.answer,
            sources=result.sources
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-history/{filename}", response_model=ChatHistory)
async def get_chat_history(filename: str):
    messages = history_service.get_history(filename)
    return ChatHistory(
        messages=messages,
        total=len(messages),
        session_id=filename
    )


@router.delete("/chat-history/{filename}", response_model=ClearHistoryResponse)
async def clear_chat_history(filename: str):
    count = history_service.clear_history(filename)
    return ClearHistoryResponse(
        message=f"Chat history for '{filename}' cleared.",
        cleared=count,
        success=True
    )


@router.get("/documents")
async def list_documents():
    try:
        docs = chromadb_service.get_stored_documents()
        files_with_history = history_service.get_all_files_with_history()
        all_files = list(set(docs + files_with_history))
        return {"documents": all_files, "total": len(all_files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{filename}", response_model=DeleteResponse)
async def delete_document(filename: str):
    try:
        deleted = chromadb_service.delete_document(filename)
        history_service.clear_history(filename)
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