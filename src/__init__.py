# -*- coding: utf-8 -*-
"""
VietIDP - Vietnamese Intelligent Document Processing
=====================================================
Hệ thống xử lý văn bản hành chính Việt Nam sử dụng OCR + LLM.

Modules:
    - preprocessing: Deskew, denoise, stamp removal
    - ocr: PaddleOCR Vietnamese engine
    - llm: Ollama LLM client + prompts
    - pipeline: End-to-end OCR-LLM pipeline
    - api: FastAPI web service
    - evaluation: CER/WER/F1 metrics
    - data: Data preparation utilities
"""

__version__ = "1.0.0"
__author__ = "VietIDP Research Team"
