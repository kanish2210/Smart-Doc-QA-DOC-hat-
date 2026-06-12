# history_service.py
# Stores conversation history in memory.
# History is lost when server restarts.

import logging
from datetime import datetime
from app.models.schemas import ChatMessage, SourceCitation

logger = logging.getLogger(__name__)

# In-memory storage
_history: list[ChatMessage] = []
SESSION_ID = "session_001"


def add_user_message(question: str) -> ChatMessage:
    """Adds a user question to history."""
    msg = ChatMessage(
        role="user",
        content=question,
        timestamp=datetime.now().isoformat(),
        sources=None
    )
    _history.append(msg)
    logger.debug(f"User message added. Total: {len(_history)}")
    return msg


def add_assistant_message(
    answer: str,
    sources: list[SourceCitation] = None
) -> ChatMessage:
    """Adds an assistant answer to history."""
    msg = ChatMessage(
        role="assistant",
        content=answer,
        timestamp=datetime.now().isoformat(),
        sources=sources or []
    )
    _history.append(msg)
    logger.debug(f"Assistant message added. Total: {len(_history)}")
    return msg


def get_history() -> list[ChatMessage]:
    """Returns all messages in order."""
    return _history.copy()


def get_history_count() -> int:
    """Returns total message count."""
    return len(_history)


def clear_history() -> int:
    """Clears all history. Returns count cleared."""
    global _history
    count = len(_history)
    _history = []
    logger.info(f"Cleared {count} messages from history.")
    return count