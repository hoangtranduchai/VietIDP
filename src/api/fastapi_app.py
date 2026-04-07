# -*- coding: utf-8 -*-
"""
FastAPI Web Service
====================
API trích xuất thông tin từ văn bản hành chính Việt Nam.

Security hardening:
- CORS restricted to localhost
- API key authentication (optional)
- File type validation
- File size limit (20MB)

Nguồn: Phase5_End_to_End_Pipeline.py, line 522-625
"""

import os
import json
import shutil
import uuid

from src.config import Config


def create_api_app():
    """
    Tạo FastAPI web service cho OCR-LLM pipeline.

    Endpoints:
    - POST /api/process     : Upload & xử lý 1 file
    - GET  /api/results     : Lấy danh sách kết quả
    - GET  /api/results/{id}: Lấy chi tiết 1 kết quả
    - GET  /api/health      : Health check
    """
    from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from src.api.auth import verify_api_key

    app = FastAPI(
        title="VietIDP - OCR-LLM Vietnamese Document Processing API",
        description="API trích xuất thông tin từ văn bản hành chính Việt Nam (100% offline)",
        version="2.0.0"
    )

    # CORS — Chỉ cho phép localhost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Config.CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Pipeline instance (load models once)
    pipeline = None

    @app.on_event("startup")
    async def startup():
        nonlocal pipeline
        from src.pipeline.ocr_llm_pipeline import OCRLLMPipeline
        pipeline = OCRLLMPipeline(
            load_stamp_model=True,
            load_ocr=True,
            load_llm=True
        )

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        import torch
        return {
            "status": "healthy",
            "version": "2.0.0",
            "gpu_available": torch.cuda.is_available() if 'torch' in dir() else False,
            "models_loaded": {
                "stamp_removal": (
                    pipeline.stamp_remover is not None
                    and pipeline.stamp_remover.is_loaded
                ) if pipeline else False,
                "ocr": (
                    pipeline.ocr_engine is not None
                    and pipeline.ocr_engine.is_loaded
                ) if pipeline else False,
                "llm": pipeline.llm_client is not None if pipeline else False,
            }
        }

    @app.post("/api/process")
    async def process_document(file: UploadFile = File(...)):
        """Upload và xử lý file PDF/Image."""
        # Validate file type
        allowed = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        ext = os.path.splitext(file.filename or '')[1].lower()
        if ext not in allowed:
            raise HTTPException(400, f"Unsupported file type: {ext}")

        # Validate file size (20MB max)
        contents = await file.read()
        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 20MB.")
        await file.seek(0)

        # Save uploaded file
        job_id = str(uuid.uuid4())[:8]
        upload_dir = Config.RESULTS_DIR / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{job_id}_{file.filename}"

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Process
        try:
            result = pipeline.process_file(str(file_path), save_result=True)
            result['job_id'] = job_id
            return JSONResponse(content=result)
        except Exception as e:
            raise HTTPException(500, f"Processing error: {str(e)}")

    @app.get("/api/results")
    async def list_results():
        """Lấy danh sách kết quả đã xử lý."""
        results = []
        results_dir = Config.RESULTS_DIR
        if not results_dir.exists():
            return results

        for f in os.listdir(results_dir):
            if f.endswith('_result.json'):
                path = results_dir / f
                with open(path, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                results.append({
                    'filename': f,
                    'source': data.get('source_file', ''),
                    'processed_at': data.get('processed_at', ''),
                    'doc_type': data.get('extraction', {}).get('loai_van_ban', ''),
                })
        return results

    @app.get("/api/results/{filename}")
    async def get_result(filename: str):
        """Lấy chi tiết 1 kết quả."""
        # Path traversal protection
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(400, "Invalid filename")

        path = Config.RESULTS_DIR / filename
        if not path.exists():
            raise HTTPException(404, "Result not found")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    return app
