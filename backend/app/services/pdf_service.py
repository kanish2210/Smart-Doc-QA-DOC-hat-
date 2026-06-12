# pdf_service.py
# Handles PDF validation, saving to disk, and text extraction.
# Uses PyMuPDF (fitz) to read PDF pages.

import fitz  # PyMuPDF
import os
import shutil
import logging
from fastapi import UploadFile
from app.models.schemas import PageContent
from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_pdf_file(file: UploadFile) -> None:
    """
    Checks the uploaded file is actually a PDF.
    Raises ValueError if not.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise ValueError(
            f"Only PDF files are accepted. Got: {file.filename}"
        )
    if file.content_type not in [
        "application/pdf",
        "application/octet-stream"
    ]:
        raise ValueError(
            f"Invalid content type: {file.content_type}"
        )


def save_uploaded_file(file: UploadFile) -> str:
    """
    Saves the uploaded PDF to the uploads folder.
    Returns the full file path.
    """
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logger.info(f"Saved PDF: {file_path}")
    return file_path


def extract_text_from_pdf(file_path: str) -> list[PageContent]:
    """
    Extracts text from every page of a PDF.
    Skips blank pages automatically.
    Returns list of PageContent objects.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    pages = []

    with fitz.open(file_path) as pdf:
        if pdf.page_count == 0:
            raise ValueError("PDF has no pages.")

        for i in range(pdf.page_count):
            # Extract plain text from this page
            text = pdf[i].get_text("text").strip()

            # Skip pages with no text (blank or image-only pages)
            if not text:
                continue

            pages.append(PageContent(
                page_number=i + 1,
                text=text
            ))

    if not pages:
        raise ValueError(
            "No text could be extracted. "
            "This PDF may be a scanned image. "
            "Please use a PDF with selectable text."
        )

    logger.info(f"Extracted text from {len(pages)} pages.")
    return pages


def process_pdf(file: UploadFile) -> dict:
    """
    Master function — validates, saves, and extracts text.
    Called by the upload endpoint.
    """
    validate_pdf_file(file)
    file_path = save_uploaded_file(file)
    pages = extract_text_from_pdf(file_path)

    return {
        "file_path": file_path,
        "pages": pages,
        "total_pages": len(pages),
        "pages_with_text": len(pages)
    }