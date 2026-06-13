# history_service.py
# Persistent chat history using SQLite.
# Replaces the old in-memory version.
# History now survives backend restarts.

import sqlite3
import logging
import uuid
import json
import os
from datetime import datetime
from app.models.schemas import ChatMessage, SourceCitation

logger = logging.getLogger(__name__)

# SQLite file — created automatically inside backend/ folder
DB_PATH = "chat_history.db"

# New session ID every time the backend starts
SESSION_ID = str(uuid.uuid4())[:8]


# ---------------------------------------------------------------------------
# Database Setup — runs once on import
# ---------------------------------------------------------------------------

def init_db():
    """
    Creates SQLite tables if they don't exist yet.

    sessions table:
        session_id  — unique ID for each backend start
        created_at  — when session started
        document    — which PDF was uploaded in this session

    messages table:
        id          — auto increment
        session_id  — which session this belongs to
        role        — "user" or "assistant"
        content     — the question or answer text
        timestamp   — when it was sent
        sources     — citations stored as JSON string
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id  TEXT PRIMARY KEY,
            created_at  TEXT NOT NULL,
            document    TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            sources     TEXT DEFAULT '[]',
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info(f"SQLite DB ready: {os.path.abspath(DB_PATH)}")


def ensure_session_exists(session_id: str, document: str = ""):
    """Creates a session row if it doesn't exist yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO sessions (session_id, created_at, document) VALUES (?, ?, ?)",
        (session_id, datetime.now().isoformat(), document)
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Write Operations
# ---------------------------------------------------------------------------

def add_user_message(question: str, document: str = "") -> ChatMessage:
    """Saves a user question to SQLite."""
    ensure_session_exists(SESSION_ID, document)
    ts = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, timestamp, sources) VALUES (?, ?, ?, ?, ?)",
        (SESSION_ID, "user", question, ts, "[]")
    )
    conn.commit()
    conn.close()

    logger.debug(f"User message saved: '{question[:50]}'")
    return ChatMessage(role="user", content=question, timestamp=ts, sources=None)


def add_assistant_message(
    answer: str,
    sources: list[SourceCitation] = None
) -> ChatMessage:
    """Saves an AI answer + citations to SQLite."""
    ensure_session_exists(SESSION_ID)
    ts = datetime.now().isoformat()

    # Convert SourceCitation objects → plain dicts → JSON string
    sources_data = []
    if sources:
        for s in sources:
            if hasattr(s, "dict"):
                sources_data.append(s.dict())
            elif isinstance(s, dict):
                sources_data.append(s)
    sources_json = json.dumps(sources_data)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, timestamp, sources) VALUES (?, ?, ?, ?, ?)",
        (SESSION_ID, "assistant", answer, ts, sources_json)
    )
    conn.commit()
    conn.close()

    logger.debug("Assistant message saved.")
    return ChatMessage(role="assistant", content=answer, timestamp=ts, sources=sources or [])


def update_session_document(document: str):
    """
    Updates the document name for the current session.
    Called after a PDF is uploaded so we know which doc
    this session's questions relate to.
    """
    ensure_session_exists(SESSION_ID, document)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessions SET document = ? WHERE session_id = ?",
        (document, SESSION_ID)
    )
    conn.commit()
    conn.close()
    logger.info(f"Session {SESSION_ID} linked to document: {document}")


# ---------------------------------------------------------------------------
# Read Operations
# ---------------------------------------------------------------------------

def get_history(session_id: str = None) -> list[ChatMessage]:
    """
    Returns all messages for a session.
    If session_id is None, returns current session messages.
    """
    target = session_id or SESSION_ID

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, timestamp, sources FROM messages "
        "WHERE session_id = ? ORDER BY id ASC",
        (target,)
    )
    rows = cursor.fetchall()
    conn.close()

    messages = []
    for role, content, timestamp, sources_json in rows:
        try:
            sources_data = json.loads(sources_json) if sources_json else []
            sources = [SourceCitation(**s) for s in sources_data] if sources_data else []
        except Exception:
            sources = []

        messages.append(ChatMessage(
            role=role,
            content=content,
            timestamp=timestamp,
            sources=sources if sources else None
        ))

    return messages


def get_history_count() -> int:
    """Returns total message count for current session."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ?",
        (SESSION_ID,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def clear_history(session_id: str = None) -> int:
    """
    Clears messages for a session.
    Returns count of messages deleted.
    """
    target = session_id or SESSION_ID

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ?",
        (target,)
    )
    count = cursor.fetchone()[0]
    cursor.execute(
        "DELETE FROM messages WHERE session_id = ?",
        (target,)
    )
    conn.commit()
    conn.close()

    logger.info(f"Cleared {count} messages from session {target}.")
    return count


# ---------------------------------------------------------------------------
# Session List — used by sidebar history
# ---------------------------------------------------------------------------

def get_all_sessions() -> list[dict]:
    """
    Returns all past sessions grouped with metadata.
    Used by Streamlit sidebar to show clickable document history.

    Each dict contains:
        session_id    — unique session ID
        created_at    — ISO timestamp
        display_date  — human-readable "Jan 15, 10:30"
        document      — PDF filename for this session
        message_count — total messages in session
        preview       — first question asked (truncated)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            s.session_id,
            s.created_at,
            s.document,
            COUNT(m.id) AS message_count,
            MIN(CASE WHEN m.role = 'user' THEN m.content END) AS first_question
        FROM sessions s
        LEFT JOIN messages m ON s.session_id = m.session_id
        GROUP BY s.session_id
        HAVING message_count > 0
        ORDER BY s.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    sessions = []
    for session_id, created_at, document, message_count, first_question in rows:
        try:
            dt = datetime.fromisoformat(created_at)
            display_date = dt.strftime("%b %d, %H:%M")
        except Exception:
            display_date = created_at[:16]

        preview = first_question or "No questions"
        if len(preview) > 50:
            preview = preview[:50] + "..."

        sessions.append({
            "session_id":   session_id,
            "created_at":   created_at,
            "display_date": display_date,
            "document":     document or "Unknown",
            "message_count": message_count,
            "preview":      preview
        })

    return sessions


def get_session_messages(session_id: str) -> list[ChatMessage]:
    """Returns all messages for a specific past session."""
    return get_history(session_id=session_id)


# ---------------------------------------------------------------------------
# Initialize DB when this module is first imported
# ---------------------------------------------------------------------------
init_db()