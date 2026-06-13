import logging
import json
import os
from datetime import datetime
from app.models.schemas import ChatMessage, SourceCitation

logger = logging.getLogger(__name__)

HISTORY_DIR = "chat_history"
os.makedirs(HISTORY_DIR, exist_ok=True)


def _history_path(filename: str) -> str:
    safe = filename.replace("/", "_").replace("\\", "_")
    return os.path.join(HISTORY_DIR, f"{safe}.json")


def _load(filename: str) -> list[dict]:
    path = _history_path(filename)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save(filename: str, messages: list[dict]):
    path = _history_path(filename)
    with open(path, "w") as f:
        json.dump(messages, f, indent=2)


def add_user_message(filename: str, question: str) -> ChatMessage:
    messages = _load(filename)
    msg = {
        "role": "user",
        "content": question,
        "timestamp": datetime.now().isoformat(),
        "sources": None
    }
    messages.append(msg)
    _save(filename, messages)
    return ChatMessage(**msg)


def add_assistant_message(
    filename: str,
    answer: str,
    sources: list[SourceCitation] = None
) -> ChatMessage:
    messages = _load(filename)
    msg = {
        "role": "assistant",
        "content": answer,
        "timestamp": datetime.now().isoformat(),
        "sources": [s.dict() for s in sources] if sources else []
    }
    messages.append(msg)
    _save(filename, messages)
    return ChatMessage(**msg)


def get_history(filename: str) -> list[ChatMessage]:
    messages = _load(filename)
    result = []
    for m in messages:
        sources = None
        if m.get("sources"):
            sources = [SourceCitation(**s) for s in m["sources"]]
        result.append(ChatMessage(
            role=m["role"],
            content=m["content"],
            timestamp=m.get("timestamp", ""),
            sources=sources
        ))
    return result


def clear_history(filename: str) -> int:
    messages = _load(filename)
    count = len(messages)
    _save(filename, [])
    return count


def get_all_files_with_history() -> list[str]:
    files = []
    for f in os.listdir(HISTORY_DIR):
        if f.endswith(".json"):
            original = f[:-5]
            data = _load(original)
            if data:
                files.append(original)
    return files