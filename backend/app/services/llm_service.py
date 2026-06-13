import logging
import time
import google.generativeai as genai
from app.core.config import settings
from app.models.schemas import AnswerResponse, SourceCitation, RetrievedChunk
from app.services.retrieval_service import retrieve

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a precise document assistant.

Answer ONLY using the context below from the document '{filename}'.

STRICT RULES:
1. Answer ONLY using information from the context.
2. If the answer is not in the context, respond with exactly:
   "I could not find relevant information in the provided document to answer this question."
3. NEVER make up facts.
4. Reference page numbers when helpful.
5. Do not repeat the question.

Context from '{filename}':
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
    api_key = settings.GEMINI_API_KEY.strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is empty.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=settings.LLM_MODEL,
        generation_config={"temperature": 0.1, "max_output_tokens": 1024}
    )

    for attempt in range(1, max_retries + 1):
        try:
            response = model.generate_content(prompt)
            if response.text:
                return response.text.strip()
            raise ValueError("Gemini returned empty response.")
        except Exception as e:
            error_str = str(e).lower()
            if any(t in error_str for t in ["429", "quota", "rate", "resource_exhausted"]):
                if attempt < max_retries:
                    wait = 20 * attempt
                    logger.warning(f"Rate limit. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                raise ValueError("Rate limit reached. Wait 1 minute.")
            elif any(t in error_str for t in ["api key not valid", "invalid api key", "permission_denied"]):
                raise ValueError("API key not valid. Check GEMINI_API_KEY.")
            else:
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


def generate_answer(question: str, filename: str, k: int = None) -> AnswerResponse:
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    question = question.strip()
    result = retrieve(question=question, filename=filename, k=k)

    if not result.chunks:
        return AnswerResponse(
            answer="No documents found. Please upload a PDF first.",
            sources=[],
            question=question,
            model_used=settings.LLM_MODEL,
            chunks_used=0,
            answer_found=False
        )

    prompt = PROMPT_TEMPLATE.format(
        filename=filename,
        context=result.context,
        question=question
    )

    raw_answer = call_gemini_with_retry(prompt)

    return AnswerResponse(
        answer=raw_answer,
        sources=build_citations(result.chunks),
        question=question,
        model_used=settings.LLM_MODEL,
        chunks_used=result.total_chunks,
        answer_found=validate_answer(raw_answer)
    )