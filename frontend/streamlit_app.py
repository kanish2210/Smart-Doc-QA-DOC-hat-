# streamlit_app.py
# Complete Streamlit chat interface for Smart Document Q&A.

import streamlit as st
import requests
import time

BACKEND_URL = "https://smart-doc-qa-backend.onrender.com"

# Page config — must be first Streamlit command
st.set_page_config(
    page_title="Smart Document Q&A",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for chat bubbles and citations
st.markdown("""
<style>
.user-message {
    background-color: #DCF8C6;
    padding: 12px 16px;
    border-radius: 12px 12px 2px 12px;
    margin: 8px 0;
    margin-left: 20%;
    color: #000000;
    font-size: 15px;
}
.assistant-message {
    background-color: #F0F0F0;
    padding: 12px 16px;
    border-radius: 12px 12px 12px 2px;
    margin: 8px 0;
    margin-right: 20%;
    color: #000000;
    font-size: 15px;
}
.citation-box {
    background-color: #FFFBF0;
    border-left: 3px solid #FFA500;
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 4px;
    font-size: 13px;
    color: #333333;
}
.timestamp {
    font-size: 11px;
    color: #888888;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API Helper Functions
# ---------------------------------------------------------------------------

def check_backend() -> bool:
    """Returns True if FastAPI backend is reachable."""
    try:
        r = requests.get(
            f"{BACKEND_URL}/api/health",
            timeout=3
        )
        return r.status_code == 200
    except Exception:
        return False


def upload_pdf(file) -> dict:
    """Uploads PDF to backend. Returns response dict."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/upload",
            files={
                "file": (
                    file.name,
                    file.getvalue(),
                    "application/pdf"
                )
            },
            timeout=180
            # 3 minutes — large PDFs take time to embed
        )
        if r.status_code == 200:
            return r.json()
        return {"error": r.json().get("detail", "Upload failed.")}

    except requests.exceptions.Timeout:
        return {"error": "Timed out. Try a smaller PDF."}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach backend."}
    except Exception as e:
        return {"error": str(e)}


def ask_question(question: str, k: int = 4) -> dict:
    """Sends question to backend. Returns answer dict."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/ask",
            json={"question": question, "k": k},
            timeout=60
        )
        if r.status_code == 200:
            return r.json()
        return {"error": r.json().get("detail", "Request failed.")}

    except requests.exceptions.Timeout:
        return {"error": "Timed out. Try again."}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach backend."}
    except Exception as e:
        return {"error": str(e)}


def get_chat_history() -> list:
    """Fetches conversation history from backend."""
    try:
        r = requests.get(
            f"{BACKEND_URL}/api/chat-history",
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("messages", [])
        return []
    except Exception:
        return []


def clear_history() -> bool:
    """Clears chat history on backend."""
    try:
        r = requests.delete(
            f"{BACKEND_URL}/api/chat-history",
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


def get_documents() -> list:
    """Gets list of stored document filenames."""
    try:
        r = requests.get(
            f"{BACKEND_URL}/api/documents",
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("documents", [])
        return []
    except Exception:
        return []


def delete_document(filename: str) -> bool:
    """Deletes a document from ChromaDB."""
    try:
        r = requests.delete(
            f"{BACKEND_URL}/api/documents/{filename}",
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Render Functions
# ---------------------------------------------------------------------------

def render_message(message: dict):
    """Renders one chat message as styled HTML."""
    role = message.get("role", "user")
    content = message.get("content", "")
    timestamp = message.get("timestamp", "")
    sources = message.get("sources") or []

    # Format timestamp
    display_time = ""
    if timestamp:
        try:
            display_time = timestamp.split("T")[1].split(".")[0]
        except Exception:
            pass

    if role == "user":
        st.markdown(
            f'<div class="user-message">'
            f'🧑 {content}'
            f'<div class="timestamp">{display_time}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="assistant-message">'
            f'🤖 {content}'
            f'<div class="timestamp">{display_time}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        # Show citations if available
        if sources:
            render_citations(sources)


def render_citations(sources: list):
    """Renders source citations in an expandable section."""
    with st.expander(
        f"📚 View Sources ({len(sources)} reference(s))",
        expanded=False
    ):
        for source in sources:
            filename = source.get("filename", "unknown")
            page = source.get("page_number", 0)
            excerpt = source.get("excerpt", "")
            score = source.get("score", 0.0)

            # Colour-coded relevance label
            if score < 0.5:
                relevance = "🟢 High relevance"
            elif score < 1.0:
                relevance = "🟡 Medium relevance"
            else:
                relevance = "🔴 Low relevance"

            st.markdown(
                f'<div class="citation-box">'
                f'<strong>📄 {filename}</strong> — '
                f'Page {page} &nbsp;|&nbsp; '
                f'{relevance} (score: {score:.3f})<br><br>'
                f'<em>"{excerpt}"</em>'
                f'</div>',
                unsafe_allow_html=True
            )


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "documents" not in st.session_state:
    st.session_state.documents = []

if "last_question" not in st.session_state:
    st.session_state.last_question = ""


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("📄 Smart Doc Q&A")
    st.caption(
        "all-MiniLM-L6-v2 Embeddings + "
        "Gemini 2.0 Flash"
    )
    st.divider()

    # Backend status
    st.subheader("🔌 Backend Status")
    backend_ok = check_backend()

    if backend_ok:
        st.success("✅ Connected")
    else:
        st.error("❌ Disconnected")
        st.caption(
            "Start backend:\n"
            "`uvicorn app.main:app --reload`"
        )

    st.divider()

    # PDF Upload
    st.subheader("📁 Upload PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload a PDF to ask questions about it."
    )

    if uploaded_file:
        size_kb = len(uploaded_file.getvalue()) / 1024
        st.caption(
            f"📄 {uploaded_file.name} ({size_kb:.1f} KB)"
        )

        if st.button(
            "🚀 Upload & Process",
            type="primary",
            use_container_width=True,
            disabled=not backend_ok
        ):
            with st.spinner(
                "Processing PDF... "
                "This may take a few minutes."
            ):
                result = upload_pdf(uploaded_file)

            if "error" in result:
                st.error(f"❌ {result['error']}")
            else:
                st.success(
                    f"✅ Done!\n\n"
                    f"📄 Pages: {result.get('total_pages')}\n\n"
                    f"🧩 Chunks: {result.get('chunks')}"
                )
                st.session_state.documents = get_documents()
                time.sleep(1)
                st.rerun()

    st.divider()

    # Stored documents
    st.subheader("📚 Stored Documents")
    st.session_state.documents = get_documents()

    if not st.session_state.documents:
        st.caption("No documents uploaded yet.")
    else:
        for doc in st.session_state.documents:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"📄 `{doc}`")
            with col2:
                if st.button(
                    "🗑️",
                    key=f"del_{doc}",
                    help=f"Delete {doc}"
                ):
                    with st.spinner(f"Deleting {doc}..."):
                        success = delete_document(doc)
                    if success:
                        st.session_state.documents = get_documents()
                        st.rerun()
                    else:
                        st.error("Delete failed.")

    st.divider()

    # Chat controls
    st.subheader("💬 Chat Controls")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.messages = get_chat_history()
            st.rerun()

    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            with st.spinner("Clearing..."):
                success = clear_history()
            if success:
                st.session_state.messages = []
                st.rerun()

    st.divider()

    # Settings
    st.subheader("⚙️ Settings")
    k_value = st.slider(
        "Chunks to retrieve (K)",
        min_value=1,
        max_value=10,
        value=4,
        help=(
            "Higher K = more context for Gemini "
            "but slightly slower responses."
        )
    )


# ---------------------------------------------------------------------------
# MAIN AREA
# ---------------------------------------------------------------------------

st.title("💬 Smart Document Q&A")
st.caption(
    "Upload a PDF in the sidebar, "
    "then ask questions about its content."
)

# Stop if backend is offline
if not backend_ok:
    st.warning(
        "⚠️ Backend is offline. "
        "Start the FastAPI server first:\n\n"
        "`uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`"
    )
    st.stop()

# Show info if no documents uploaded
if not st.session_state.documents:
    st.info(
        "👈 Upload a PDF from the sidebar to get started. "
        "Once uploaded, ask any question about its content."
    )

st.divider()

# ---------------------------------------------------------------------------
# CHAT HISTORY
# ---------------------------------------------------------------------------

# Load history from backend on first load
if not st.session_state.messages:
    st.session_state.messages = get_chat_history()

# Render all messages
if st.session_state.messages:
    st.subheader("🗨️ Conversation")
    for msg in st.session_state.messages:
        render_message(msg)
    st.divider()
else:
    if st.session_state.documents:
        st.markdown(
            "<div style='text-align:center;"
            "color:#888888;padding:40px 0'>"
            "<h3>💡 No questions yet</h3>"
            "<p>Type your first question below!</p>"
            "</div>",
            unsafe_allow_html=True
        )

# ---------------------------------------------------------------------------
# QUESTION INPUT
# ---------------------------------------------------------------------------

st.subheader("❓ Ask a Question")

if not st.session_state.documents:
    st.warning(
        "⚠️ Please upload a PDF document "
        "before asking questions."
    )

question = st.text_area(
    "Your question",
    placeholder=(
        "e.g. What is this document about?\n"
        "e.g. What are the key findings?\n"
        "e.g. Summarize the main points."
    ),
    height=100,
    disabled=not st.session_state.documents,
    label_visibility="collapsed"
)

# Centered Ask button
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    ask_btn = st.button(
        "🔍 Ask",
        type="primary",
        use_container_width=True,
        disabled=(
            not st.session_state.documents
            or not question.strip()
        )
    )

# ---------------------------------------------------------------------------
# HANDLE SUBMISSION
# ---------------------------------------------------------------------------

if ask_btn and question.strip():

    # Prevent duplicate submissions
    if question.strip() == st.session_state.last_question:
        st.warning("You already asked this. Try a new question.")
        st.stop()

    st.session_state.last_question = question.strip()

    # Show user message immediately
    render_message({
        "role": "user",
        "content": question.strip(),
        "timestamp": "",
        "sources": None
    })

    # Call backend
    with st.spinner(
        "🤔 Searching documents and generating answer..."
    ):
        result = ask_question(
            question=question.strip(),
            k=k_value
        )

    if "error" in result:
        st.error(f"❌ Error: {result['error']}")

    else:
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        answer_found = result.get("answer_found", True)
        model = result.get("model_used", "gemini-2.0-flash")
        chunks = result.get("chunks_used", 0)

        # Show answer
        render_message({
            "role": "assistant",
            "content": answer,
            "timestamp": "",
            "sources": sources
        })

        # Show metadata
        st.caption(
            f"Model: {model} · "
            f"Chunks used: {chunks} · "
            f"K setting: {k_value} · "
            f"Answer found: {answer_found}"
        )

        # Sync with backend history
        st.session_state.messages = get_chat_history()
        time.sleep(0.5)
        st.rerun()