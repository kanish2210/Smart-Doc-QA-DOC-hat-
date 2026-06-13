# streamlit_app.py
# Smart Document Q&A — DO'C'hAT
# Backend: https://kanish22-smart-doc-qa-backend.hf.space

import streamlit as st
import requests
import time

BACKEND_URL = "https://kanish22-smart-doc-qa-backend.hf.space"

st.set_page_config(
    page_title="DO'C'hAT",
    page_icon="📄",
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
.timestamp {
    font-size: 11px;
    color: #888888;
    margin-top: 4px;
}
.history-banner {
    background-color: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 14px;
    color: #3730A3;
    margin-bottom: 16px;
}
.doc-session-banner {
    background-color: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 14px;
    color: #166534;
    margin-bottom: 16px;
}
.session-card {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 13px;
    color: #334155;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API Helpers
# ---------------------------------------------------------------------------

def check_backend() -> bool:
    try:
        r = requests.get(f"{BACKEND_URL}/api/health", timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def upload_pdf(file) -> dict:
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/upload",
            files={"file": (file.name, file.getvalue(), "application/pdf")},
            timeout=300
        )
        return r.json() if r.status_code == 200 else {"error": r.json().get("detail", "Upload failed.")}
    except requests.exceptions.Timeout:
        return {"error": "Timed out. Try a smaller PDF."}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach backend. Check HuggingFace Space is running."}
    except Exception as e:
        return {"error": str(e)}


def ask_question(question: str, k: int = 4) -> dict:
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/ask",
            json={"question": question, "k": k},
            timeout=120
        )
        return r.json() if r.status_code == 200 else {"error": r.json().get("detail", "Request failed.")}
    except requests.exceptions.Timeout:
        return {"error": "Timed out. Try again."}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach backend."}
    except Exception as e:
        return {"error": str(e)}


def get_current_history() -> list:
    try:
        r = requests.get(f"{BACKEND_URL}/api/chat-history", timeout=15)
        return r.json().get("messages", []) if r.status_code == 200 else []
    except Exception:
        return []


def get_all_sessions() -> list:
    try:
        r = requests.get(f"{BACKEND_URL}/api/sessions", timeout=15)
        return r.json().get("sessions", []) if r.status_code == 200 else []
    except Exception:
        return []


def get_session_messages(session_id: str) -> list:
    try:
        r = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}", timeout=15)
        return r.json().get("messages", []) if r.status_code == 200 else []
    except Exception:
        return []


def clear_history() -> bool:
    try:
        r = requests.delete(f"{BACKEND_URL}/api/chat-history", timeout=15)
        return r.status_code == 200
    except Exception:
        return False


def get_documents() -> list:
    try:
        r = requests.get(f"{BACKEND_URL}/api/documents", timeout=15)
        return r.json().get("documents", []) if r.status_code == 200 else []
    except Exception:
        return []


def delete_document(filename: str) -> bool:
    try:
        r = requests.delete(f"{BACKEND_URL}/api/documents/{filename}", timeout=15)
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def render_message(message):
    if not isinstance(message, dict):
        message = message.dict() if hasattr(message, "dict") else {}

    role    = message.get("role", "user")
    content = message.get("content", "")
    ts      = message.get("timestamp", "")
    sources = message.get("sources") or []

    display_time = ""
    if ts:
        try:
            display_time = ts.split("T")[1].split(".")[0]
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
    with st.expander(f"📚 Sources ({len(sources)})", expanded=False):
        for s in sources:
            filename  = s.get("filename", "unknown")
            page      = s.get("page_number", 0)
            excerpt   = s.get("excerpt", "")
            score     = s.get("score", 0.0)
            relevance = "🟢 High" if score < 0.5 else ("🟡 Medium" if score < 1.0 else "🔴 Low")
            st.markdown(
                f'<div class="citation-box">'
                f'<strong>📄 {filename}</strong> — Page {page} | {relevance} (score: {score:.3f})<br><br>'
                f'<em>"{excerpt}"</em></div>',
                unsafe_allow_html=True
            )


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

defaults = {
    "messages":               [],
    "documents":              [],
    "last_question":          "",
    "view_mode":              "chat",       # "chat" | "doc_sessions" | "session_view"
    "viewing_doc":            None,
    "viewing_session_id":     None,
    "viewing_session_label":  "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("📄 DO'C'hAT")
    st.caption("all-MiniLM-L6-v2 · Gemini 2.5 Flash · HuggingFace")
    st.divider()

    # Backend status
    backend_ok = check_backend()
    if backend_ok:
        st.success("✅ Backend connected")
    else:
        st.error("❌ Backend offline")
        st.caption("Check your HuggingFace Space is running.")

    st.divider()

    # ── Upload ──────────────────────────────────────────────────
    st.subheader("📁 Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    if uploaded_file:
        size_kb = len(uploaded_file.getvalue()) / 1024
        st.caption(f"📄 {uploaded_file.name} ({size_kb:.1f} KB)")

        if st.button("🚀 Upload & Process", type="primary",
                     use_container_width=True, disabled=not backend_ok):
            with st.spinner("Uploading to HuggingFace & processing..."):
                result = upload_pdf(uploaded_file)
            if "error" in result:
                st.error(f"❌ {result['error']}")
            else:
                st.success(
                    f"✅ Done!\n\n"
                    f"📄 Pages: {result.get('total_pages')}  "
                    f"🧩 Chunks: {result.get('chunks')}"
                )
                st.session_state.documents = get_documents()
                st.session_state.view_mode = "chat"
                st.session_state.messages  = []
                time.sleep(0.8)
                st.rerun()

    st.divider()

    # ── Stored Documents ────────────────────────────────────────
    # Click document name → view all its chat sessions
    st.subheader("📚 Stored Documents")
    st.session_state.documents = get_documents()

    if not st.session_state.documents:
        st.caption("No documents uploaded yet.")
    else:
        for doc in st.session_state.documents:
            col1, col2 = st.columns([3, 1])
            with col1:
                is_active = (
                    st.session_state.view_mode in ("doc_sessions", "session_view")
                    and st.session_state.viewing_doc == doc
                )
                btn_label = f"{'▶ ' if is_active else ''}📄 {doc}"
                if st.button(
                    btn_label,
                    key=f"doc_{doc}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state.view_mode   = "doc_sessions"
                    st.session_state.viewing_doc = doc
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{doc}", help=f"Delete {doc}"):
                    with st.spinner("Deleting..."):
                        if delete_document(doc):
                            st.session_state.documents = get_documents()
                            if st.session_state.viewing_doc == doc:
                                st.session_state.view_mode   = "chat"
                                st.session_state.viewing_doc = None
                            st.rerun()
                        else:
                            st.error("Delete failed.")

    st.divider()

    # ── Chat Controls ───────────────────────────────────────────
    st.subheader("💬 Chat Controls")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.messages  = get_current_history()
            st.session_state.view_mode = "chat"
            st.rerun()
    with c2:
        if st.button("🗑️ Clear", use_container_width=True):
            with st.spinner("Clearing..."):
                if clear_history():
                    st.session_state.messages = []
                    st.rerun()

    st.divider()

    # ── Settings ────────────────────────────────────────────────
    st.subheader("⚙️ Settings")
    k_value = st.slider("Chunks to retrieve (K)", 1, 10, 4)


# ---------------------------------------------------------------------------
# MAIN AREA
# ---------------------------------------------------------------------------

st.title("💬 DO'C'hAT — Smart Document Q&A")
st.caption("Upload a PDF · Ask questions · Click stored documents to view chat history")

if not backend_ok:
    st.error(
        "⚠️ Backend is offline.\n\n"
        f"Check your HuggingFace Space: {BACKEND_URL}"
    )
    st.stop()

st.divider()

# ══════════════════════════════════════════════════════════════════
# MODE: doc_sessions
# User clicked a document → show all sessions for that doc
# ══════════════════════════════════════════════════════════════════
if st.session_state.view_mode == "doc_sessions":
    doc = st.session_state.viewing_doc

    st.markdown(
        f'<div class="doc-session-banner">'
        f'📄 Chat history for <strong>{doc}</strong><br>'
        f'<span style="font-size:12px">Click any session below to read the full conversation.</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    if st.button("← Back to current chat"):
        st.session_state.view_mode   = "chat"
        st.session_state.viewing_doc = None
        st.rerun()

    st.divider()

    # Filter sessions for this document only
    all_sessions = get_all_sessions()
    doc_sessions = [s for s in all_sessions if s.get("document") == doc]

    if not doc_sessions:
        st.info(
            f"No chat sessions found for **{doc}** yet.\n\n"
            "Upload this document and ask questions — "
            "all conversations will appear here."
        )
    else:
        st.subheader(f"📋 {len(doc_sessions)} session(s) for '{doc}'")
        st.caption("Each session = one upload + its full conversation.")
        st.markdown("")

        for sess in doc_sessions:
            sid       = sess["session_id"]
            date      = sess["display_date"]
            msg_count = sess["message_count"]
            preview   = sess["preview"]
            q_count   = msg_count // 2

            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f'<div class="session-card">'
                    f'🗓️ <strong>{date}</strong> &nbsp;·&nbsp; '
                    f'{msg_count} messages ({q_count} Q&A pairs)<br>'
                    f'<span style="color:#64748b;font-size:12px">First question: "{preview}"</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with col2:
                if st.button("👁 View", key=f"view_{sid}",
                             use_container_width=True, type="primary"):
                    st.session_state.view_mode            = "session_view"
                    st.session_state.viewing_session_id   = sid
                    st.session_state.viewing_session_label = f"{doc} — {date}"
                    st.rerun()

    st.stop()


# ══════════════════════════════════════════════════════════════════
# MODE: session_view
# User clicked "View" → show full conversation read-only
# ══════════════════════════════════════════════════════════════════
elif st.session_state.view_mode == "session_view":
    sid   = st.session_state.viewing_session_id
    label = st.session_state.viewing_session_label

    st.markdown(
        f'<div class="history-banner">'
        f'📖 Reading session: <strong>{label}</strong><br>'
        f'<span style="font-size:12px">Read-only view of a past conversation.</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    if st.button("← Back to sessions"):
        st.session_state.view_mode          = "doc_sessions"
        st.session_state.viewing_session_id = None
        st.rerun()

    st.divider()

    messages = get_session_messages(sid)
    if messages:
        st.subheader(f"🗨️ Conversation ({len(messages)} messages)")
        for msg in messages:
            render_message(msg if isinstance(msg, dict) else msg.dict())
    else:
        st.info("No messages found for this session.")

    st.stop()


# ══════════════════════════════════════════════════════════════════
# MODE: chat (default)
# ══════════════════════════════════════════════════════════════════
else:
    if not st.session_state.documents:
        st.info("👈 Upload a PDF from the sidebar to get started.")

    if not st.session_state.messages:
        st.session_state.messages = get_current_history()

    if st.session_state.messages:
        st.subheader("🗨️ Conversation")
        for msg in st.session_state.messages:
            render_message(msg if isinstance(msg, dict) else msg.dict())
        st.divider()
    else:
        if st.session_state.documents:
            st.markdown(
                "<div style='text-align:center;color:#888;padding:40px 0'>"
                "<h3>💡 No questions yet</h3>"
                "<p>Type your first question below!</p>"
                "</div>",
                unsafe_allow_html=True
            )

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
        label_visibility="collapsed"
    )

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        ask_btn = st.button(
            "🔍 Ask",
            type="primary",
            use_container_width=True,
            disabled=(not st.session_state.documents or not question.strip())
        )

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

        with st.spinner("🤔 Searching document and generating answer..."):
            result = ask_question(question=question.strip(), k=k_value)

        if "error" in result:
            st.error(f"❌ Error: {result['error']}")
        else:
            render_message({
                "role": "assistant",
                "content": result.get("answer", ""),
                "timestamp": "",
                "sources": result.get("sources", [])
            })
            st.caption(
                f"Model: {result.get('model_used','gemini-2.5-flash')} · "
                f"Chunks: {result.get('chunks_used',0)} · "
                f"K: {k_value} · "
                f"Found: {result.get('answer_found', True)}"
            )
            st.session_state.messages = get_current_history()
            time.sleep(0.5)
            st.rerun()