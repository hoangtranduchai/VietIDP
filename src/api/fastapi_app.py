# -*- coding: utf-8 -*-
"""
FastAPI Web Service for Stamp Extraction
========================================
API kết nối Frontend với The Extractor (YOLOv8 + Hybrid Matting)
"""

import os
import json
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.config import Config

def create_api_app():
    """
    Khởi tạo FastAPI web service.

    Endpoints:
    - POST /api/extract_stamp : Upload PDF/Image, trả về Base64 Stamp Overlay
    - GET  /api/health       : Health check
    """
    app = FastAPI(
        title="VietIDP - Stamp Extraction API",
        description="API bóc tách và trích xuất nền con dấu trong suốt",
        version="3.0.0"
    )

    # CORS — Cho phép React Frontend kết nối
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Config.CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Cấu trúc Pipeline Tĩnh (Nạp vào RAM 1 lần duy nhất)
    pipeline = None

    @app.on_event("startup")
    async def startup():
        nonlocal pipeline
        from src.pipeline.stamp_pipeline import StampDetectorPipeline
        # Khởi tạo sẽ pre-load YOLOv8 và Rembg ONNX Session
        pipeline = StampDetectorPipeline()

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        import torch
        return {
            "status": "healthy",
            "version": "3.0.0",
            "gpu_available": torch.cuda.is_available() if hasattr(torch, "cuda") else False,
            "models_loaded": pipeline.is_loaded if pipeline else False
        }

    @app.post("/api/extract_stamp")
    async def extract_stamp(file: UploadFile = File(...)):
        """
        Nhận file Upload (PDF hoặc Image).
        Lưu ý: Hiện tại Test API hỗ trợ Image, với PDF cần thêm thư viện pdf2image
        chuyển trang đầu tiên thành ảnh trước khi đẩy vào pipeline.
        """
        allowed = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        ext = os.path.splitext(file.filename or '')[1].lower()
        if ext not in allowed:
            raise HTTPException(400, f"Unsupported file type: {ext}")

        contents = await file.read()
        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 20MB.")

        # Xử lý PDF (convert to image) -> Tương lai nếu upload PDF trực tiếp
        if ext == '.pdf':
            # Todo: Cần pdf2image ở đây nếu test trực tiếp file PDF
            raise HTTPException(400, "PDF not fully supported in simple Matting endpoint yet. Please upload an image.")

        try:
            # Truyền mảng byte trực tiếp vào Pipeline
            result = pipeline.process_image(contents)
            if not result.get("success"):
                raise HTTPException(500, result.get("error", "Failed to process image"))
                
            return JSONResponse(content=result)
        except Exception as e:
            raise HTTPException(500, f"Processing error: {str(e)}")

    return app
