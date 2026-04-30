# -*- coding: utf-8 -*-
"""
FastAPI Routes — VietIDP API v3.0
==================================
RESTful endpoints cho toàn bộ hệ thống IDP.
"""

import asyncio
import csv
import io
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from src.api.auth import verify_api_key
from src.api.database import Document, ExtractionResult, get_session
from src.config import Config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["VietIDP"])

# ── Upload directory ─────────────────────────────────────────────────
UPLOAD_DIR = Config.DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
UPLOAD_CHUNK_SIZE = 1024 * 1024
FILE_SIGNATURE_READ_SIZE = 1024
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
}
DECLARED_CONTENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg", "image/jpg"},
    ".jpeg": {"image/jpeg", "image/jpg"},
    ".tiff": {"image/tiff", "image/tif"},
    ".bmp": {"image/bmp"},
}


# ═══════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════

class ExtractionUpdate(BaseModel):
    loai_van_ban: Optional[str] = None
    so_hieu: Optional[str] = None
    ngay_ban_hanh: Optional[str] = None
    co_quan_ban_hanh: Optional[str] = None
    trich_yeu: Optional[str] = None
    nguoi_ky: Optional[str] = None


class ChatRequest(BaseModel):
    question: str
    document_id: Optional[int] = None
    context: Optional[str] = None


def detect_file_extension(content: bytes) -> Optional[str]:
    if content.startswith(b"%PDF-"):
        return ".pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith((b"II*\x00", b"MM\x00*")):
        return ".tiff"
    if content.startswith(b"BM"):
        return ".bmp"
    return None


def validate_upload_content(filename: str, content_type: Optional[str], content: bytes) -> tuple[str, str]:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")

    detected_ext = detect_file_extension(content)
    if detected_ext is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported or invalid file content")

    normalized_detected_ext = ".jpg" if detected_ext == ".jpeg" else detected_ext
    normalized_ext = ".jpg" if ext == ".jpeg" else ext
    if normalized_detected_ext != normalized_ext:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File content does not match extension")

    declared_type = (content_type or "").split(";", 1)[0].strip().lower()
    if declared_type and declared_type not in DECLARED_CONTENT_TYPES[ext] and declared_type != "application/octet-stream":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File content type is not allowed")

    return ext, MIME_TYPES[ext]


def build_storage_name(ext: str) -> str:
    return f"{uuid.uuid4().hex}{ext}"


def resolve_preview_path(doc: Document, extraction: Optional[ExtractionResult], page: int) -> Path:
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page must be greater than 0")

    page_names = []
    if extraction and isinstance(extraction.raw_json, dict):
        raw_pages = extraction.raw_json.get("pages")
        if isinstance(raw_pages, list):
            page_names = [str(item) for item in raw_pages if item]

    if page_names:
        if page > len(page_names):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview page not found")
        candidate = UPLOAD_DIR / page_names[page - 1]
    else:
        if page != 1:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview page not found")
        candidate = Path(doc.file_path or "")

    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview file not found") from exc

    upload_root = UPLOAD_DIR.resolve()
    if resolved != upload_root and upload_root not in resolved.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview file not found")

    return resolved


# ═══════════════════════════════════════════════════════════════════════
# Health & System
# ═══════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """Kiểm tra trạng thái hệ thống."""
    import requests

    tags_url = Config.OLLAMA_URL.replace("/api/generate", "/api/tags")
    ollama_ok = False
    try:
        r = await asyncio.to_thread(requests.get, tags_url, timeout=3)
        ollama_ok = r.status_code == 200
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "ollama": "active" if ollama_ok else "inactive",
            "database": "active",
            "model": Config.OLLAMA_MODEL,
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# Document Processing
# ═══════════════════════════════════════════════════════════════════════

@router.post("/process_document", dependencies=[Depends(verify_api_key)])
async def process_document(file: UploadFile = File(...), async_mode: bool = False):
    """
    Upload và xử lý văn bản qua full pipeline.

    - async_mode=False: Xử lý đồng bộ, trả kết quả ngay (mặc định)
    - async_mode=True: Đẩy vào Celery queue, trả task_id
    """
    first_chunk = await file.read(FILE_SIGNATURE_READ_SIZE)
    if len(first_chunk) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File rỗng (0 bytes)")

    ext, _media_type = validate_upload_content(file.filename or "", file.content_type, first_chunk)
    file_path = UPLOAD_DIR / build_storage_name(ext)
    file_size = len(first_chunk)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File quá lớn (>20MB)")

    with open(file_path, "wb") as f:
        f.write(first_chunk)
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                f.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File quá lớn (>20MB)")
            f.write(chunk)

    session = get_session()
    try:
        doc = Document(
            filename=file.filename or file_path.name,
            file_path=str(file_path),
            file_type=ext.lstrip("."),
            file_size=file_size,
            status="pending",
        )
        session.add(doc)
        session.commit()
        doc_id = doc.id

        if async_mode:
            from src.api.tasks import process_document_task

            task = process_document_task.delay(doc_id, str(file_path))
            return {
                "status": "queued",
                "document_id": doc_id,
                "task_id": task.id,
                "message": "Đã đưa vào hàng đợi xử lý",
            }

        doc.status = "processing"
        session.commit()

        from src.api.fastapi_app import get_pipeline

        pipeline = get_pipeline()
        start_time = time.time()
        result = pipeline.process_file(str(file_path), save_result=True)
        elapsed = time.time() - start_time

        extraction_data = result.get("extraction", {})

        extraction = ExtractionResult(
            document_id=doc_id,
            loai_van_ban=extraction_data.get("loai_van_ban", ""),
            so_hieu=extraction_data.get("so_hieu", ""),
            ngay_ban_hanh=extraction_data.get("ngay_ban_hanh", ""),
            co_quan_ban_hanh=extraction_data.get("co_quan_ban_hanh", ""),
            trich_yeu=extraction_data.get("trich_yeu", ""),
            nguoi_ky=extraction_data.get("nguoi_ky", ""),
            full_text=result.get("full_text", ""),
            raw_json=extraction_data,
            total_stamps=result.get("total_stamps", 0),
            processing_time=round(elapsed, 2),
        )
        session.add(extraction)
        doc.status = "completed"
        doc.num_pages = result.get("num_pages", 1)
        session.commit()

        return {
            "status": "completed",
            "document_id": doc_id,
            "processing_time": round(elapsed, 2),
            "num_pages": result.get("num_pages", 1),
            "total_stamps": result.get("total_stamps", 0),
            "extraction": extraction_data,
            "full_text": result.get("full_text", "")[:500],
        }

    except HTTPException:
        session.rollback()
        raise
    except Exception:
        logger.exception("Failed to process uploaded document")
        session.rollback()
        if "doc_id" in locals():
            doc_obj = session.query(Document).get(doc_id)
            if doc_obj:
                doc_obj.status = "failed"
                session.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Processing failed")
    finally:
        session.close()


@router.get("/task_status/{task_id}", dependencies=[Depends(verify_api_key)])
async def get_task_status(task_id: str):
    """Kiểm tra trạng thái Celery task."""
    from src.api.tasks import celery_app

    task = celery_app.AsyncResult(task_id)
    response = {"task_id": task_id, "status": task.status}

    if task.state == "PROGRESS":
        response["progress"] = task.info
    elif task.state == "SUCCESS":
        response["result"] = task.result
    elif task.state == "FAILURE":
        response["error"] = "Processing failed. Check server logs for details."

    return response


# ═══════════════════════════════════════════════════════════════════════
# Document CRUD
# ═══════════════════════════════════════════════════════════════════════

@router.get("/documents", dependencies=[Depends(verify_api_key)])
async def list_documents(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), status: Optional[str] = None):
    """Danh sách documents đã xử lý."""
    session = get_session()
    try:
        query = session.query(Document).order_by(Document.created_at.desc())
        if status:
            query = query.filter(Document.status == status)
        total = query.count()
        docs = query.offset(skip).limit(limit).all()
        return {"total": total, "documents": [d.to_dict() for d in docs]}
    finally:
        session.close()


@router.get("/documents/{doc_id}", dependencies=[Depends(verify_api_key)])
async def get_document(doc_id: int):
    """Chi tiết 1 document và kết quả trích xuất."""
    session = get_session()
    try:
        doc = session.query(Document).get(doc_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return doc.to_dict()
    finally:
        session.close()


@router.get("/documents/{doc_id}/preview", dependencies=[Depends(verify_api_key)])
async def preview_document(doc_id: int, page: int = Query(1, ge=1)):
    """Authenticated inline preview for uploaded documents/pages."""
    session = get_session()
    try:
        doc = session.query(Document).get(doc_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        extraction = session.query(ExtractionResult).filter_by(document_id=doc_id).first()
        preview_path = resolve_preview_path(doc, extraction, page)
        suffix = preview_path.suffix.lower()

        return FileResponse(
            path=str(preview_path),
            media_type=MIME_TYPES.get(suffix, "application/octet-stream"),
            filename=preview_path.name,
            headers={"Content-Disposition": f'inline; filename="{preview_path.name}"'},
        )
    finally:
        session.close()


@router.put("/documents/{doc_id}", dependencies=[Depends(verify_api_key)])
async def update_extraction(doc_id: int, data: ExtractionUpdate):
    """Cập nhật kết quả trích xuất (user chỉnh sửa)."""
    session = get_session()
    try:
        extraction = session.query(ExtractionResult).filter_by(document_id=doc_id).first()
        if not extraction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction result not found")

        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(extraction, key, value)

        extraction.edited_json = update_data
        extraction.verified_by_user = True
        session.commit()

        return {"status": "updated", "document_id": doc_id}
    finally:
        session.close()


@router.delete("/documents/{doc_id}", dependencies=[Depends(verify_api_key)])
async def delete_document(doc_id: int):
    """Xóa document và kết quả."""
    session = get_session()
    try:
        doc = session.query(Document).get(doc_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        extraction = session.query(ExtractionResult).filter_by(document_id=doc_id).first()
        preview_files = []
        if extraction and isinstance(extraction.raw_json, dict):
            raw_pages = extraction.raw_json.get("pages")
            if isinstance(raw_pages, list):
                preview_files = [UPLOAD_DIR / str(item) for item in raw_pages if item]

        file_candidates = [Path(doc.file_path)] if doc.file_path else []
        file_candidates.extend(preview_files)
        for candidate in file_candidates:
            try:
                resolved = candidate.resolve(strict=True)
            except FileNotFoundError:
                continue
            upload_root = UPLOAD_DIR.resolve()
            if resolved == upload_root or upload_root in resolved.parents:
                try:
                    os.remove(resolved)
                except OSError:
                    pass

        session.delete(doc)
        session.commit()
        return {"status": "deleted", "document_id": doc_id}
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════

@router.get("/export/{doc_id}", dependencies=[Depends(verify_api_key)])
async def export_document(doc_id: int, format: str = Query("json", pattern="^(json|csv)$")):
    """Export kết quả trích xuất ra JSON hoặc CSV."""
    session = get_session()
    try:
        extraction = session.query(ExtractionResult).filter_by(document_id=doc_id).first()
        if not extraction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction result not found")

        data = extraction.edited_json or extraction.raw_json or extraction.to_dict()

        if format == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow({k: str(v) for k, v in data.items()})
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=doc_{doc_id}.csv"},
            )

        return JSONResponse(content=data)
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════
# Chat (Document Q&A)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/chat", dependencies=[Depends(verify_api_key)])
async def chat_with_document(req: ChatRequest):
    """Hỏi đáp trên tài liệu đã xử lý."""
    context = req.context

    if req.document_id and not context:
        session = get_session()
        try:
            extraction = session.query(ExtractionResult).filter_by(document_id=req.document_id).first()
            if extraction and extraction.full_text:
                context = extraction.full_text
        finally:
            session.close()

    if not context:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Không có context. Cung cấp document_id hoặc context text.")

    from src.llm.ollama_client import OllamaClient
    from src.llm.prompts import PROMPTS

    max_chars = Config.OLLAMA_MAX_CHARS
    if len(context) > max_chars:
        truncated = context[:max_chars]
        cut_point = max(truncated.rfind(" "), truncated.rfind("\n"))
        if cut_point > 0:
            context = truncated[:cut_point] + "..."
        else:
            context = truncated + "..."

    prompt = PROMPTS["chat"].format(context=context, question=req.question)
    client = OllamaClient()
    result, error = client.generate(prompt, format_json=False)

    if error:
        logger.error("LLM error while answering chat request: %s", error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to generate a response right now")

    return {"answer": result, "question": req.question}
