# streamlit_app.py
# Complete Streamlit chat interface for Smart Document Q&A.

import streamlit as st
import requests
import time

BACKEND_URL = "https://kanish22-smart-doc-qa-backend.hf.space"

# Page config — must be first Streamlit command
st.set_page_config(
    page_title="DOC'hat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_ebar_state="expanded"
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
    try:
        r = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def upload_pdf(file) -> dict:
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/upload",
            files={"file": (file.name, file.getvalue(), "application/pdf")},
            timeout=180
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
    try:
        r = requests.get(f"{BACKEND_URL}/api/chat-history", timeout=10)
        if r.status_code == 200:
            return r.json().get("messages", [])
        return []
    except Exception:
        return []


def clear_history() -> bool:
    try:
        r = requests.delete(f"{BACKEND_URL}/api/chat-history", timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def get_documents() -> list:
    try:
        r = requests.get(f"{BACKEND_URL}/api/documents", timeout=10)
        if r.status_code == 200:
            return r.json().get("documents", [])
        return []
    except Exception:
        return []


def delete_document(filename: str) -> bool:
    try:
        r = requests.delete(f"{BACKEND_URL}/api/documents/{filename}", timeout=10)
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Render Functions
# ---------------------------------------------------------------------------

def render_message(message: dict):
    role = message.get("role", "user")
    content = message.get("content", "")
    timestamp = message.get("timestamp", "")
    sources = message.get("sources") or []

    display_time = ""
    if timestamp:
        try:
            display_time = timestamp.split("T")[1].split(".")[0]
        except Exception:
            pass

    if role == "user":
        st.markdown(
            f'<div class="user-message">🧑 {content}'
            f'<div class="timestamp">{display_time}</div></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="assistant-message">🤖 {content}'
            f'<div class="timestamp">{display_time}</div></div>',
            unsafe_allow_html=True
        )
        if sources:
            render_citations(sources)


def render_citations(sources: list):
    with st.expander(f"📚 View Sources ({len(sources)} reference(s))", expanded=False):
        for source in sources:
            filename = source.get("filename", "unknown")
            page = source.get("page_number", 0)
            excerpt = source.get("excerpt", "")
            score = source.get("score", 0.0)

            if score < 0.5:
                relevance = "🟢 High relevance"
            elif score < 1.0:
                relevance = "🟡 Medium relevance"
            else:
                relevance = "🔴 Low relevance"

            st.markdown(
                f'<div class="citation-box">'
                f'<strong>📄 {filename}</strong> — '
                f'Page {page} &nbsp;|&nbsp; {relevance} (score: {score:.3f})<br><br>'
                f'<em>"{excerpt}"</em></div>',
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

if "input_key" not in st.session_state:
    st.session_state.input_key = 0


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("💬 DOC'hat")
    st.caption("Ask anything about your PDF documents.")
    st.divider()

    # Backend status
    st.subheader("🔌 Backend Status")
    backend_ok = check_backend()
    if backend_ok:
        st.success("✅ Connected")
    else:
        st.error("❌ Disconnected")

    st.divider()

    # PDF Upload
    st.subheader("📁 Upload Document")
    st.info("📌 Please upload files in **PDF format only**.")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Only PDF files are supported."
    )

    if uploaded_file:
        size_kb = len(uploaded_file.getvalue()) / 1024
        st.caption(f"📄 {uploaded_file.name} ({size_kb:.1f} KB)")

        if st.button(
            "🚀 Upload & Process",
            type="primary",
            use_container_width=True,
            disabled=not backend_ok
        ):
            with st.spinner("Processing PDF... This may take a few minutes."):
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
                if st.button("🗑️", key=f"del_{doc}", help=f"Delete {doc}"):
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
        help="Higher K = more context but slightly slower."
    )


# ---------------------------------------------------------------------------
# MAIN AREA
# ---------------------------------------------------------------------------

st.title("💬 DOC'hat")
st.caption("Upload a PDF in the sidebar, then ask questions about its content.")

if not backend_ok:
    st.warning("⚠️ Backend is offline. Please try again in a moment.")
    st.stop()

if not st.session_state.documents:
    st.info("👈 Upload a PDF from the sidebar to get started. Only PDF format is supported.")

st.divider()

# ---------------------------------------------------------------------------
# CHAT HISTORY
# ---------------------------------------------------------------------------

if not st.session_state.messages:
    st.session_state.messages = get_chat_history()

if st.session_state.messages:
    st.subheader("🗨️ Conversation")
    for msg in st.session_state.messages:
        render_message(msg)
    st.divider()
else:
    if st.session_state.documents:
        st.markdown(
            "<div style='text-align:center;color:#888888;padding:40px 0'>"
            "<h3>💡 No questions yet</h3>"
            "<p>Type your first question below!</p></div>",
            unsafe_allow_html=True
        )

# ---------------------------------------------------------------------------
# QUESTION INPUT
# ---------------------------------------------------------------------------

st.subheader("❓ Ask a Question")

if not st.session_state.documents:
    st.warning("⚠️ Please upload a PDF document before asking questions.")

question = st.text_area(
    "Your question",
    placeholder=(
        "e.g. What is this document about?\n"
        "e.g. What are the key findings?\n"
        "e.g. Summarize the main points."
    ),
    height=100,
    disabled=not st.session_state.documents,
    label_visibility="collapsed",
    key=f"question_input_{st.session_state.input_key}"
)

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    ask_btn = st.button(
        "🔍 Ask",
        type="primary",
        use_container_width=True,
        disabled=(not st.session_state.documents or not question.strip())
    )

# ---------------------------------------------------------------------------
# HANDLE SUBMISSION
# ---------------------------------------------------------------------------

if ask_btn and question.strip():

    if question.strip() == st.session_state.last_question:
        st.warning("You already asked this. Try a new question.")
        st.stop()

    st.session_state.last_question = question.strip()

    render_message({
        "role": "user",
        "content": question.strip(),
        "timestamp": "",
        "sources": None
    })

    with st.spinner("🤔 Searching documents and generating answer..."):
        result = ask_question(question=question.strip(), k=k_value)

    if "error" in result:
        st.error(f"❌ Error: {result['error']}")
    else:
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        answer_found = result.get("answer_found", True)
        model = result.get("model_used", "gemini-2.5-flash")
        chunks = result.get("chunks_used", 0)

        # If no relevant info found
        if not answer_found or not answer.strip():
            answer = "⚠️ No relevant information found in the uploaded document for your question."

        render_message({
            "role": "assistant",
            "content": answer,
            "timestamp": "",
            "sources": sources
        })

        st.caption(
            f"Model: {model} · Chunks used: {chunks} · "
            f"K setting: {k_value} · Answer found: {answer_found}"
        )

        # Clear input box by incrementing key
        st.session_state.input_key += 1
        st.session_state.messages = get_chat_history()
        time.sleep(0.5)
        st.rerun()