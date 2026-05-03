# -*- coding: utf-8 -*-
"""
API Request/Response Schemas — VietIDP
=======================================
Pydantic models for API input validation and response serialization.
Separate from ORM models in database.py.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# Extraction Fields
# ═══════════════════════════════════════════════════════════════════════


class ExtractionFields(BaseModel):
    """Core extraction fields for Vietnamese administrative documents."""
    loai_van_ban: Optional[str] = Field(None, description="Loại văn bản (Quyết định, Thông báo, etc.)")
    so_hieu: Optional[str] = Field(None, description="Số hiệu văn bản")
    ngay_ban_hanh: Optional[str] = Field(None, description="Ngày ban hành (dd/mm/yyyy)")
    co_quan_ban_hanh: Optional[str] = Field(None, description="Cơ quan ban hành")
    trich_yeu: Optional[str] = Field(None, description="Trích yếu nội dung")
    nguoi_ky: Optional[str] = Field(None, description="Người ký")


class ExtractionUpdate(ExtractionFields):
    """Request body for updating extraction results."""
    pass


# ═══════════════════════════════════════════════════════════════════════
# Chat
# ═══════════════════════════════════════════════════════════════════════


class ChatRequest(BaseModel):
    """Request body for document Q&A."""
    question: str = Field(..., min_length=1, max_length=2000, description="Câu hỏi về tài liệu")
    document_id: Optional[int] = Field(None, description="ID tài liệu để hỏi đáp")
    context: Optional[str] = Field(None, description="Context text (nếu không dùng document_id)")


class ChatResponse(BaseModel):
    """Response for document Q&A."""
    answer: str
    question: str


# ═══════════════════════════════════════════════════════════════════════
# Document Responses
# ═══════════════════════════════════════════════════════════════════════


class ExtractionResponse(BaseModel):
    """Extraction result in API responses."""
    id: int
    document_id: int
    loai_van_ban: Optional[str] = None
    so_hieu: Optional[str] = None
    ngay_ban_hanh: Optional[str] = None
    co_quan_ban_hanh: Optional[str] = None
    trich_yeu: Optional[str] = None
    nguoi_ky: Optional[str] = None
    ocr_confidence: Optional[float] = None
    llm_confidence: Optional[float] = None
    total_stamps: int = 0
    stamp_coordinates: Optional[List[Any]] = None
    processing_time: Optional[float] = None
    verified_by_user: bool = False
    raw_json: Optional[Dict[str, Any]] = None
    edited_json: Optional[Dict[str, Any]] = None
    full_text: Optional[str] = None


class DocumentResponse(BaseModel):
    """Single document in API responses."""
    id: int
    filename: str
    storage_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    num_pages: int = 1
    status: str = "pending"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    extraction: Optional[ExtractionResponse] = None


class DocumentListResponse(BaseModel):
    """Paginated document list."""
    total: int
    documents: List[DocumentResponse]


# ═══════════════════════════════════════════════════════════════════════
# Processing Responses
# ═══════════════════════════════════════════════════════════════════════


class ProcessingResult(BaseModel):
    """Response after document processing completes."""
    status: str
    document_id: int
    processing_time: Optional[float] = None
    num_pages: int = 1
    total_stamps: int = 0
    extraction: Optional[Dict[str, Any]] = None
    full_text: Optional[str] = None


class TaskQueuedResponse(BaseModel):
    """Response when document is queued for async processing."""
    status: str = "queued"
    document_id: int
    task_id: str
    message: str = "Đã đưa vào hàng đợi xử lý"


# ═══════════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════════


class ServiceStatus(BaseModel):
    """Individual service status."""
    ollama: str = "inactive"
    database: str = "active"
    model: str = ""


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "3.0.0"
    timestamp: str
    services: ServiceStatus
