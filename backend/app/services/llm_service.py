# llm_service.py
# Answer generation using Gemini 2.5 Flash.

import logging
import time
import google.generativeai as genai
from app.core.config import settings
from app.models.schemas import AnswerResponse, SourceCitation, RetrievedChunk
from app.services.retrieval_service import retrieve

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a precise and helpful document assistant.

Answer the user's question using ONLY the context provided below.

STRICT RULES:
1. Answer ONLY using information present in the context.
2. If the answer cannot be found, respond with exactly:
   "I could not find relevant information in the provided documents to answer this question."
3. NEVER make up facts not in the context.
4. Be clear and well-structured.
5. Reference the source page when helpful (e.g. "According to page 3...").
6. Do not repeat the question in your answer.

Context from uploaded documents:
═══════════════════════════════════════════════════════
{context}
═══════════════════════════════════════════════════════

Question: {question}

Answer:"""

NO_ANSWER_PHRASES = [
    "could not find relevant information",
    "not found in the provided documents",
    "no information available",
    "cannot answer this question",
    "not mentioned in the context",
    "the document does not contain",
]


def call_gemini_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Calls Gemini 2.5 Flash with automatic retry on rate limits."""
    api_key = settings.GEMINI_API_KEY.strip()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is empty. "
            "Open backend/.env and add: GEMINI_API_KEY=your_key_here"
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=settings.LLM_MODEL,
        generation_config={
            "temperature": 0.1,
            "max_output_tokens": 1024,
        }
    )

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Gemini call attempt {attempt}/{max_retries}...")
            response = model.generate_content(prompt)
            if response.text:
                logger.info("Gemini responded successfully.")
                return response.text.strip()
            else:
                raise ValueError("Gemini returned empty response.")

        except Exception as e:
            error_str = str(e).lower()

            if any(t in error_str for t in ["429", "quota", "rate", "resource_exhausted", "too many requests"]):
                if attempt < max_retries:
                    wait = 20 * attempt
                    logger.warning(f"Rate limit hit. Waiting {wait}s before retry {attempt+1}...")
                    time.sleep(wait)
                    continue
                else:
                    raise ValueError("Rate limit reached. Wait 1 minute and try again.")

            elif any(t in error_str for t in ["api key not valid", "invalid api key", "permission_denied", "unauthenticated"]):
                raise ValueError(
                    "API key not valid. Check GEMINI_API_KEY in backend/.env"
                )
            else:
                logger.error(f"Gemini error: {e}")
                raise

    raise ValueError("Gemini failed after all retries.")


def validate_answer(answer: str) -> bool:
    if not answer or not answer.strip():
        return False
    return not any(p in answer.lower() for p in NO_ANSWER_PHRASES)


def build_citations(chunks: list[RetrievedChunk]) -> list[SourceCitation]:
    seen = {}
    for chunk in chunks:
        key = (chunk.source, chunk.page_number)
        if key not in seen or chunk.score < seen[key].score:
            seen[key] = SourceCitation(
                filename=chunk.source,
                page_number=chunk.page_number,
                excerpt=chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text,
                score=chunk.score
            )
    return sorted(seen.values(), key=lambda x: x.score)


def generate_answer(question: str, k: int = None) -> AnswerResponse:
    """Full RAG pipeline: retrieve → prompt → Gemini → answer."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    question = question.strip()
    logger.info(f"Question: '{question[:80]}'")

    # Step 1 — Retrieve chunks from ChromaDB
    result = retrieve(question=question, k=k)

    if not result.chunks:
        return AnswerResponse(
            answer="No documents found. Please upload a PDF first.",
            sources=[],
            question=question,
            model_used=settings.LLM_MODEL,
            chunks_used=0,
            answer_found=False
        )

    # Step 2 — Build prompt with retrieved context
    prompt = PROMPT_TEMPLATE.format(
        context=result.context,
        question=question
    )
    logger.info(f"Prompt built. Context: {len(result.context)} chars from {result.sources}")

    # Step 3 — Call Gemini
    raw_answer = call_gemini_with_retry(prompt)

    # Step 4 — Return answer with citations
    return AnswerResponse(
        answer=raw_answer,
        sources=build_citations(result.chunks),
        question=question,
        model_used=settings.LLM_MODEL,
        chunks_used=result.total_chunks,
        answer_found=validate_answer(raw_answer)
    )