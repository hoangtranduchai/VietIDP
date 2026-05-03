# ⚠️ ARCHIVED — Legacy Express Backend

**Status:** Quarantined (2026-05-03)

This Express.js backend has been **retired** in favor of the canonical **FastAPI** backend.

## Why archived?

- FastAPI (`src/api/`) is the canonical backend for all VietIDP operations
- This Express server was an early prototype and is no longer maintained
- Running `node index.js` will intentionally exit with an error message

## Canonical Stack

| Component | Technology | Location |
|-----------|-----------|----------|
| Backend | **FastAPI** | `src/api/fastapi_app.py` |
| Frontend | **React/Vite** | `apps/frontend/` |
| Database | **PostgreSQL** (prod) / SQLite (dev) | `src/api/database.py` |
| LLM Runtime | **Ollama** (local) | `src/llm/ollama_client.py` |
| Pipeline | **VietIDPPipeline** | `src/pipeline/ocr_llm_pipeline.py` |

## How to run the system

```bash
# Backend
uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000

# Frontend
cd apps/frontend && npm run dev
```

See root `README.md` for full setup instructions.
