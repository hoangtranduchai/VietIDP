# -*- coding: utf-8 -*-
"""
FastAPI Application — VietIDP v3.0
====================================
Main application entry point. Tich hop:
- Routes API (process, documents CRUD, chat, export)
- Database (SQLAlchemy + PostgreSQL/SQLite)
- CORS + Security middleware
- Static file serving cho uploaded images
- Pipeline singleton (load 1 lan khi startup)

Chay: uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import logging
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from src.config import Config
from src.api.routes import router as api_router
from src.api.database import init_db

# ── Logging Setup ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ── Logging Filter ───────────────────────────────────────────────────
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /api/health") == -1

logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


# ═══════════════════════════════════════════════════════════════════════
# Pipeline Singleton
# ═══════════════════════════════════════════════════════════════════════

_pipeline = None


def get_pipeline():
    """Get or create the singleton VietIDPPipeline instance."""
    global _pipeline
    if _pipeline is None:
        from src.pipeline.ocr_llm_pipeline import VietIDPPipeline
        _pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)
    return _pipeline


# ═══════════════════════════════════════════════════════════════════════
# Lifespan (replaces deprecated on_event)
# ═══════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────
    print("=" * 60)
    print(" VietIDP FastAPI Server v3.0")
    print(f" LLM Model: {Config.OLLAMA_MODEL}")
    print(f" Database: {Config.DATABASE_URL[:50]}...")
    print("=" * 60)
    init_db()

    yield  # App is running

    # ── Shutdown ─────────────────────────────────────────────────
    global _pipeline
    _pipeline = None
    print("VietIDP server stopped.")


# ═══════════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="VietIDP — Vietnamese Intelligent Document Processing",
    description="He thong trich xuat thong tin tu dong tu van ban hanh chinh Viet Nam",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (uploaded documents, images) ────────────────────────
upload_dir = Config.DATA_DIR / "uploads"
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# ── Routes ───────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Error Handlers ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
    )


# ── Root endpoint ────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "VietIDP API",
        "version": "3.0.0",
        "docs": "/docs",
        "status": "active"
    }
