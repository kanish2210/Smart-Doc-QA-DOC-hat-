# Smart Document Q&A Assistant

RAG chatbot — upload a PDF and ask questions about it.

## Tech Stack
- Embeddings: all-MiniLM-L6-v2 (local, free)
- LLM: Gemini 2.0 Flash (free tier)
- Vector DB: ChromaDB
- Backend: FastAPI
- Frontend: Streamlit

## Run
```
cd backend && venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

cd frontend && venv\Scripts\activate
streamlit run streamlit_app.py
```