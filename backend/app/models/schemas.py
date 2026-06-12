# schemas.py
# Defines data shapes for all API requests and responses.
# FastAPI uses these to validate inputs and format outputs.

from pydantic import BaseModel
from typing import Optional


class PageContent(BaseModel):
    """One page of extracted PDF text."""
    page_number: int
    text: str


class RetrievedChunk(BaseModel):
    """One chunk returned from ChromaDB search."""
    text: str
    source: str
    page_number: int
    score: float
    chunk_index: int


class RetrievalResult(BaseModel):
    """Full result from the retrieval pipeline."""
    question: str
    context: str
    chunks: list[RetrievedChunk]
    total_chunks: int
    sources: list[str]


class SourceCitation(BaseModel):
    """One source citation attached to an answer."""
    filename: str
    page_number: int
    excerpt: str
    score: float


class DocumentInfo(BaseModel):
    """Info about one stored document."""
    filename: str
    chunk_count: int
    pages: list[int]


class CollectionStats(BaseModel):
    """ChromaDB collection statistics."""
    total_chunks: int
    total_documents: int
    documents: list[DocumentInfo]
    collection_name: str
    persist_directory: str


class DeleteResponse(BaseModel):
    """Response after deleting a document."""
    message: str
    filename: str
    chunks_deleted: int
    success: bool


class UploadResponse(BaseModel):
    """Response after uploading and processing a PDF."""
    message: str
    filename: str
    chunks: int
    total_pages: int
    file_path: str


class AskRequest(BaseModel):
    """Request body for /ask endpoint."""
    question: str
    k: Optional[int] = None


class AnswerResponse(BaseModel):
    """Full response from the /ask endpoint."""
    answer: str
    sources: list[SourceCitation]
    question: str
    model_used: str
    chunks_used: int
    answer_found: bool


class QuestionRequest(BaseModel):
    """Simple question request."""
    question: str


class HealthResponse(BaseModel):
    """Response from /health endpoint."""
    status: str
    message: str


class ProcessRequest(BaseModel):
    """Request to reprocess an existing PDF."""
    filename: str


class ProcessResponse(BaseModel):
    """Response after reprocessing a document."""
    message: str
    filename: str
    chunks: int
    total_pages: int
    success: bool


class ChatMessage(BaseModel):
    """One message in conversation history."""
    role: str
    content: str
    timestamp: str
    sources: Optional[list[SourceCitation]] = None


class ChatHistory(BaseModel):
    """Full conversation history."""
    messages: list[ChatMessage]
    total: int
    session_id: str


class ClearHistoryResponse(BaseModel):
    """Response after clearing chat history."""
    message: str
    cleared: int
    success: bool