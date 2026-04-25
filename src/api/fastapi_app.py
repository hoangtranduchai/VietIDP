# -*- coding: utf-8 -*-
"""
FastAPI Application — VietIDP v3.0
====================================
Main application entry point. Tích hợp:
- Routes API (process, documents CRUD, chat, export)
- Database (SQLAlchemy + PostgreSQL/SQLite)
- CORS + Security middleware
- Static file serving cho uploaded images

Chạy: uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
"""

import os
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from src.config import Config
from src.api.routes import router as api_router
from src.api.database import init_db

# ═══════════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="VietIDP — Vietnamese Intelligent Document Processing",
    description="Hệ thống trích xuất thông tin tự động từ văn bản hành chính Việt Nam",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


# ── Startup Event ────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Khởi tạo database khi server start."""
    print("=" * 60)
    print(" VietIDP FastAPI Server v3.0")
    print(f" LLM Model: {Config.OLLAMA_MODEL}")
    print(f" Database: {Config.DATABASE_URL[:50]}...")
    print("=" * 60)
    init_db()


# ── Error Handlers ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "timestamp": datetime.utcnow().isoformat()}
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
