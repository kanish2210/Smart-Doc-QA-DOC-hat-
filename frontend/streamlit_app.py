import streamlit as st
import requests
import time

BACKEND_URL = "https://kanish22-smart-doc-qa-backend.hf.space"

st.set_page_config(
    page_title="DOC'hat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
.timestamp { font-size: 11px; color: #888888; margin-top: 4px; }
.history-message-user {
    background-color: #DCF8C6;
    padding: 10px 14px;
    border-radius: 12px 12px 2px 12px;
    margin: 6px 0;
    margin-left: 20%;
    color: #000000;
    font-size: 14px;
}
.history-message-assistant {
    background-color: #F0F0F0;
    padding: 10px 14px;
    border-radius: 12px 12px 12px 2px;
    margin: 6px 0;
    margin-right: 20%;
    color: #000000;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API Helpers
# ---------------------------------------------------------------------------

def check_backend() -> bool:
    try:
        r = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def check_file_exists(filename: str) -> bool:
    try:
        r = requests.get(
            f"{BACKEND_URL}/api/documents/check/{requests.utils.quote(filename)}",
            timeout=5
        )
        if r.status_code == 200:
            return r.json().get("exists", False)
        return False
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
    except Exception as e:
        return {"error": str(e)}


def ask_question(question: str, filename: str, k: int = 4) -> dict:
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/ask",
            json={"question": question, "filename": filename, "k": k},
            timeout=60
        )
        if r.status_code == 200:
            return r.json()
        return {"error": r.json().get("detail", "Request failed.")}
    except requests.exceptions.Timeout:
        return {"error": "Timed out. Try again."}
    except Exception as e:
        return {"error": str(e)}


def get_chat_history(filename: str) -> list:
    try:
        r = requests.get(
            f"{BACKEND_URL}/api/chat-history/{requests.utils.quote(filename)}",
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("messages", [])
        return []
    except Exception:
        return []


def clear_history(filename: str) -> bool:
    try:
        r = requests.delete(
            f"{BACKEND_URL}/api/chat-history/{requests.utils.quote(filename)}",
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


def get_closed_documents() -> list:
    try:
        r = requests.get(f"{BACKEND_URL}/api/closed-documents", timeout=10)
        if r.status_code == 200:
            return r.json().get("documents", [])
        return []
    except Exception:
        return []


def close_document(filename: str) -> bool:
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/close-document",
            json={"filename": filename},
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


def delete_document(filename: str) -> bool:
    try:
        r = requests.delete(
            f"{BACKEND_URL}/api/documents/{requests.utils.quote(filename)}",
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Render helpers
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
            with st.expander(f"📚 Sources ({len(sources)})", expanded=False):
                for s in sources:
                    score = s.get("score", 0)
                    if score < 0.5:
                        relevance = "🟢 High relevance"
                    elif score < 1.0:
                        relevance = "🟡 Medium relevance"
                    else:
                        relevance = "🔴 Low relevance"
                    st.markdown(
                        f'<div class="citation-box">'
                        f'<strong>📄 {s.get("filename")}</strong> — '
                        f'Page {s.get("page_number")} | {relevance}<br><br>'
                        f'<em>"{s.get("excerpt")}"</em></div>',
                        unsafe_allow_html=True
                    )


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

if "active_file" not in st.session_state:
    st.session_state.active_file = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "closed_documents" not in st.session_state:
    st.session_state.closed_documents = []

if "input_key" not in st.session_state:
    st.session_state.input_key = 0

if "pending_upload" not in st.session_state:
    st.session_state.pending_upload = None

if "confirm_reupload" not in st.session_state:
    st.session_state.confirm_reupload = False

if "viewing_history" not in st.session_state:
    st.session_state.viewing_history = None

if "last_error" not in st.session_state:
    st.session_state.last_error = None

if "uploaded_file_data" not in st.session_state:
    st.session_state.uploaded_file_data = None


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("💬 DOC'hat")
    st.caption("Ask anything about your PDF documents.")
    st.divider()

    backend_ok = check_backend()
    if backend_ok:
        st.success("✅ Backend connected")
    else:
        st.error("❌ Backend offline")

    st.divider()

    # Upload section — only show when no active chat
    if not st.session_state.active_file:
        st.subheader("📁 Upload Document")
        st.info("📌 PDF format only.")

        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="Only PDF files are supported.",
            key="file_uploader"
        )

        if uploaded_file:
            size_kb = len(uploaded_file.getvalue()) / 1024
            st.caption(f"📄 {uploaded_file.name} ({size_kb:.1f} KB)")

            if st.button(
                "🚀 Upload & Start Chat",
                type="primary",
                use_container_width=True,
                disabled=not backend_ok
            ):
                already_exists = check_file_exists(uploaded_file.name)

                if already_exists and not st.session_state.confirm_reupload:
                    st.session_state.pending_upload = uploaded_file
                    st.session_state.confirm_reupload = True
                    st.rerun()
                else:
                    with st.spinner("Processing PDF..."):
                        result = upload_pdf(uploaded_file)

                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                    else:
                        st.session_state.active_file = uploaded_file.name
                        st.session_state.messages = []
                        st.session_state.viewing_history = None
                        st.session_state.confirm_reupload = False
                        st.session_state.pending_upload = None
                        st.session_state.last_error = None
                        st.rerun()

        if st.session_state.confirm_reupload and st.session_state.pending_upload:
            fname = st.session_state.pending_upload.name
            st.warning(f"⚠️ **'{fname}'** is already uploaded.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Re-upload", use_container_width=True):
                    with st.spinner("Re-uploading..."):
                        result = upload_pdf(st.session_state.pending_upload)
                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                    else:
                        st.session_state.active_file = fname
                        st.session_state.messages = []
                        st.session_state.viewing_history = None
                        st.session_state.confirm_reupload = False
                        st.session_state.pending_upload = None
                        st.rerun()
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.confirm_reupload = False
                    st.session_state.pending_upload = None
                    st.rerun()

    else:
        # Active chat controls
        st.subheader(f"💬 Active Chat")
        st.info(f"📄 {st.session_state.active_file}")

        if st.button("❌ Close Chat", use_container_width=True, type="primary"):
            # Save to closed documents
            close_document(st.session_state.active_file)
            st.session_state.closed_documents = get_closed_documents()
            st.session_state.active_file = None
            st.session_state.messages = []
            st.session_state.viewing_history = None
            st.session_state.last_error = None
            st.rerun()

        if st.button("🗑️ Clear Chat History", use_container_width=True):
            clear_history(st.session_state.active_file)
            st.session_state.messages = []
            st.rerun()

    st.divider()

    # Stored Documents — only closed chats
    st.subheader("📚 Stored Documents")
    st.session_state.closed_documents = get_closed_documents()

    if not st.session_state.closed_documents:
        st.caption("No closed chats yet.")
    else:
        for doc in st.session_state.closed_documents:
            col1, col2 = st.columns([4, 1])
            with col1:
                is_viewing = doc == st.session_state.viewing_history
                label = f"{'👁️ ' if is_viewing else '📄 '}{doc}"
                if st.button(label, key=f"view_{doc}",
                             use_container_width=True):
                    st.session_state.viewing_history = doc
                    st.session_state.active_file = None
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{doc}"):
                    delete_document(doc)
                    if st.session_state.viewing_history == doc:
                        st.session_state.viewing_history = None
                    st.session_state.closed_documents = get_closed_documents()
                    st.rerun()

    st.divider()
    st.subheader("⚙️ Settings")
    k_value = st.slider("Chunks to retrieve (K)", 1, 10, 4)


# ---------------------------------------------------------------------------
# MAIN AREA
# ---------------------------------------------------------------------------

st.title("💬 DOC'hat")

if not backend_ok:
    st.warning("⚠️ Backend is offline. Please try again in a moment.")
    st.stop()

# ---------------------------------------------------------------------------
# VIEWING HISTORY MODE
# ---------------------------------------------------------------------------

if st.session_state.viewing_history and not st.session_state.active_file:
    fname = st.session_state.viewing_history
    st.subheader(f"📄 Chat History — {fname}")
    st.caption("This is a read-only view of past conversations.")

    if st.button("← Back"):
        st.session_state.viewing_history = None
        st.rerun()

    st.divider()
    history = get_chat_history(fname)

    if not history:
        st.info("No chat history found for this document.")
    else:
        for msg in history:
            render_message(msg)

    st.stop()

# ---------------------------------------------------------------------------
# ACTIVE CHAT MODE
# ---------------------------------------------------------------------------

if not st.session_state.active_file:
    st.info(
        "👈 Upload a PDF from the sidebar to start a new chat, "
        "or click a document in Stored Documents to view its history."
    )
    st.stop()

st.subheader(f"📄 {st.session_state.active_file}")
st.caption("Answers are based only on this document.")
st.divider()

if not st.session_state.messages:
    st.session_state.messages = get_chat_history(st.session_state.active_file)

if st.session_state.messages:
    for msg in st.session_state.messages:
        render_message(msg)
    st.divider()
else:
    st.markdown(
        "<div style='text-align:center;color:#888;padding:40px 0'>"
        "<h3>💡 No questions yet</h3>"
        "<p>Type your question below and press Enter!</p></div>",
        unsafe_allow_html=True
    )

# Show last error if any
if st.session_state.last_error:
    st.error(f"❌ {st.session_state.last_error}")

# Question input with Enter to submit
st.subheader("❓ Ask a Question")

question = st.text_input(
    "Your question",
    placeholder="Type your question and press Enter...",
    label_visibility="collapsed",
    key=f"question_input_{st.session_state.input_key}"
)

if question.strip():
    render_message({
        "role": "user",
        "content": question.strip(),
        "timestamp": "",
        "sources": None
    })

    with st.spinner("🤔 Searching document and generating answer..."):
        result = ask_question(
            question=question.strip(),
            filename=st.session_state.active_file,
            k=k_value
        )

    if "error" in result:
        st.session_state.last_error = result["error"]
        st.session_state.input_key += 1
        st.rerun()
    else:
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        answer_found = result.get("answer_found", True)
        model = result.get("model_used", "gemini-2.5-flash")
        chunks = result.get("chunks_used", 0)

        if not answer_found or not answer.strip():
            answer = "⚠️ No relevant information found in this document for your question."

        render_message({
            "role": "assistant",
            "content": answer,
            "timestamp": "",
            "sources": sources
        })

        st.caption(f"Model: {model} · Chunks: {chunks} · K: {k_value}")
        st.session_state.last_error = None
        st.session_state.input_key += 1
        st.session_state.messages = get_chat_history(
            st.session_state.active_file
        )
        time.sleep(0.5)
        st.rerun()