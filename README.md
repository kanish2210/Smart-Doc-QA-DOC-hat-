# 💬 DOC'hat — Smart Document Q&A

> Upload a PDF. Ask anything. Get instant AI-powered answers with source citations.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-red)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🌐 Live Demo

| Service | URL |
|---|---|
| **Frontend** | https://jjhbdw9tb3dskxohxhzbr3.streamlit.app |
| **Backend API** | https://kanish22-smart-doc-qa-backend.hf.space/api/health |
| **API Docs** | https://kanish22-smart-doc-qa-backend.hf.space/docs |

---

## ✨ Features

- 📄 Upload PDF documents and ask natural language questions
- 🤖 Powered by **Google Gemini 2.5 Flash** for accurate answers
- 🔍 Semantic search using **all-MiniLM-L6-v2** embeddings
- 📚 Source citations with page numbers and relevance scores
- 💬 Persistent chat history per session
- 🗑️ Delete documents and clear chat history
- ⚡ Fast and responsive UI built with Streamlit

---

## 🏗️ Architecture Overview

### High-Level Architecture
┌─────────────────────────────────────────────────────┐

│                      USER                           │

│              (Browser / Any Device)                 │

└─────────────────────┬───────────────────────────────┘

│

▼

┌─────────────────────────────────────────────────────┐

│              FRONTEND LAYER                         │

│         Streamlit Cloud (streamlit_app.py)          │

│                                                     │

│  • Upload PDF UI                                    │

│  • Chat Interface                                   │

│  • Source Citations Display                         │

│  • Document Manager                                 │

└─────────────────────┬───────────────────────────────┘

│ HTTP REST API calls

▼

┌─────────────────────────────────────────────────────┐

│              BACKEND LAYER                          │

│       Hugging Face Spaces (FastAPI + Uvicorn)       │

│                                                     │

│  POST /api/upload       → Process & embed PDF       │

│  POST /api/ask          → Answer question           │

│  GET  /api/documents    → List documents            │

│  GET  /api/health       → Health check              │

│  GET  /api/chat-history → Fetch history             │

│  DELETE /api/chat-history → Clear history           │

└──────┬──────────────────────────┬───────────────────┘

│                          │

▼                          ▼

┌─────────────┐          ┌────────────────────┐

│  VECTOR DB  │          │     LLM LAYER      │

│  ChromaDB   │          │  Google Gemini     │

│             │          │  2.5 Flash API     │

│ • Stores    │          │                    │

│   embeddings│          │ • Generates        │

│ • Semantic  │          │   answers from     │

│   search    │          │   context chunks   │

└─────────────┘          └────────────────────┘

▲

│

┌─────────────────────────────────────────────────────┐

│              EMBEDDING LAYER                        │

│         all-MiniLM-L6-v2 (sentence-transformers)    │

│                                                     │

│  • Converts text chunks → 384-dimensional vectors   │

│  • Runs locally on Hugging Face server              │

│  • No API key needed                                │

└─────────────────────────────────────────────────────┘

### 📄 PDF Upload Flow
User uploads PDF

│

▼

PyMuPDF extracts text

│

▼

LangChain splits into chunks

(chunk size: 800, overlap: 150)

│

▼

all-MiniLM-L6-v2 converts

chunks → embeddings (vectors)

│

▼

ChromaDB stores

embeddings + metadata

(filename, page number)

│

▼

✅ Ready to answer questions

### ❓ Question Answering Flow
User types question

│

▼

all-MiniLM-L6-v2 converts

question → query vector

│

▼

ChromaDB semantic search

finds top-K similar chunks

│

▼

Chunks + question sent

to Gemini 2.5 Flash

│

▼

Gemini generates answer

with source references

│

▼

Answer + citations

displayed in chat UI


## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Streamlit | Web UI |
| Backend | FastAPI + Uvicorn | REST API server |
| LLM | Google Gemini 2.5 Flash | Answer generation |
| Embeddings | all-MiniLM-L6-v2 | Semantic search vectors |
| Vector Store | ChromaDB | Store and search embeddings |
| PDF Parsing | PyMuPDF | Extract text from PDFs |
| Deployment (FE) | Streamlit Cloud | Host frontend |
| Deployment (BE) | Hugging Face Spaces | Host backend |

---

## 📦 Libraries Used

### Backend

| Library | Version | Purpose |
|---|---|---|
| fastapi | 0.111.0 | Web framework for REST API |
| uvicorn | 0.30.1 | ASGI server |
| python-multipart | 0.0.9 | File upload handling |
| python-dotenv | 1.0.1 | Environment variable management |
| pydantic | 2.7.4 | Data validation |
| pydantic-settings | 2.3.4 | Settings from environment |
| pymupdf | 1.24.5 | PDF text extraction |
| langchain | 0.2.16 | RAG pipeline orchestration |
| langchain-core | 0.2.38 | Core abstractions |
| langchain-community | 0.2.16 | Community integrations |
| langchain-text-splitters | 0.2.4 | Document chunking |
| google-generativeai | 0.7.2 | Gemini LLM API |
| chromadb | 0.5.3 | Vector database |
| sentence-transformers | 2.7.0 | Local embedding model |

### Frontend

| Library | Purpose |
|---|---|
| streamlit | Web UI framework |
| requests | HTTP calls to backend |

---

## 📁 Project Structure
Smart-Doc-QA-DOC-hat-/

├── backend/

│   ├── main.py                    # FastAPI entry point

│   ├── requirements.txt           # Backend dependencies

│   ├── Dockerfile                 # Hugging Face deployment

│   └── app/

│       ├── api/

│       │   └── routes.py          # API endpoints

│       ├── core/

│       │   └── config.py          # App settings

│       └── services/

│           ├── embedding_service.py  # Embeddings + ChromaDB

│           ├── chromadb_service.py   # Vector DB operations

│           └── llm_service.py        # Gemini LLM calls

├── frontend/

│   ├── streamlit_app.py           # Streamlit UI

│   └── requirements.txt           # Frontend dependencies

└── README.md

---

## 🚀 Local Setup

### Prerequisites

- Python 3.11+
- Google Gemini API key → https://aistudio.google.com

### 1. Clone the Repository

```bash
git clone https://github.com/kanish2210/Smart-Doc-QA-DOC-hat-.git
cd Smart-Doc-QA-DOC-hat-
```

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo GEMINI_API_KEY=your_actual_api_key_here > .env

# Run backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend running at: **http://127.0.0.1:8000**
API Docs at: **http://127.0.0.1:8000/docs**

### 3. Setup Frontend

Open a new terminal:

```bash
cd frontend

# Install dependencies
pip install -r requirements.txt

# Update BACKEND_URL in streamlit_app.py line 6:
# BACKEND_URL = "http://127.0.0.1:8000"

# Run frontend
streamlit run streamlit_app.py
```

Frontend running at: **http://localhost:8501**

---

## ☁️ Cloud Deployment

### Backend — Hugging Face Spaces

1. Create a Space at https://huggingface.co/new-space
2. Select **Docker** SDK
3. Push backend files to the Space repo
4. Add `GEMINI_API_KEY` in Space **Settings → Repository Secrets**

### Frontend — Streamlit Cloud

1. Go to https://share.streamlit.io
2. Connect your GitHub repo
3. Set main file path to `frontend/streamlit_app.py`
4. Deploy

---

## 🔑 Environment Variables

| Variable | Where | Description |
|---|---|---|
| `GEMINI_API_KEY` | Backend `.env` / HF Secrets | Google Gemini API key |

---

## 🔑 Key Design Decisions

| Decision | Reason |
|---|---|
| FastAPI over Flask | Async support, auto docs, faster |
| ChromaDB over Pinecone | Free, runs locally, no API key |
| all-MiniLM-L6-v2 | Small, fast, high quality, free |
| Gemini over OpenAI | Free tier, generous limits |
| Streamlit over React | Rapid UI for ML apps |
| Hugging Face over Render | 16GB RAM vs 512MB, never sleeps |
| LangChain | Simplifies RAG pipeline |

---

## 📌 Notes

- Only **PDF format** is supported for upload
- Chat history is stored per session on the backend
- ChromaDB data resets if the Hugging Face Space restarts

---

## 👨‍💻 Author

**Kanish** — [GitHub](https://github.com/kanish2210)

---

## 📄 License

MIT License

---

## 🚀 Try It Live

👉 **[Open DOC'hat](https://jjhbdw9tb3dskxohxhzbr3.streamlit.app)**
