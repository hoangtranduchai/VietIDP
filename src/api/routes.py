# -*- coding: utf-8 -*-
"""
FastAPI Routes — VietIDP API v3.0
==================================
RESTful endpoints cho toàn bộ hệ thống IDP.
"""

import os
import io
import csv
import time
import shutil
import tempfile
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from src.config import Config
from src.api.database import get_session, Document, ExtractionResult, ProcessingLog
from src.api.auth import verify_api_key

router = APIRouter(prefix="/api", tags=["VietIDP"])

# ── Upload directory ─────────────────────────────────────────────────
UPLOAD_DIR = Config.DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


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


# ═══════════════════════════════════════════════════════════════════════
# Health & System
# ═══════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """Kiểm tra trạng thái hệ thống."""
    import requests
    ollama_ok = False
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        ollama_ok = r.status_code == 200
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "ollama": "active" if ollama_ok else "inactive",
            "database": "active",
            "model": Config.OLLAMA_MODEL,
        }
    }


# ═══════════════════════════════════════════════════════════════════════
# Document Processing
# ═══════════════════════════════════════════════════════════════════════

@router.post("/process_document")
async def process_document(file: UploadFile = File(...), async_mode: bool = False):
    """
    Upload và xử lý văn bản qua full pipeline.

    - async_mode=False: Xử lý đồng bộ, trả kết quả ngay (mặc định)
    - async_mode=True: Đẩy vào Celery queue, trả task_id
    """
    # Validate file
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type not allowed: {ext}")

    # Save file
    timestamp = int(time.time() * 1000)
    safe_name = f"{timestamp}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, "File rỗng (0 bytes)")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File quá lớn (>20MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    # Save to database
    session = get_session()
    try:
        doc = Document(
            filename=file.filename,
            file_path=str(file_path),
            file_type=ext.lstrip('.'),
            file_size=len(content),
            status="pending"
        )
        session.add(doc)
        session.commit()
        doc_id = doc.id

        if async_mode:
            # Celery async
            from src.api.tasks import process_document_task
            task = process_document_task.delay(doc_id, str(file_path))
            return {
                "status": "queued",
                "document_id": doc_id,
                "task_id": task.id,
                "message": "Đã đưa vào hàng đợi xử lý"
            }
        else:
            # Synchronous processing
            doc.status = "processing"
            session.commit()

            from src.pipeline.ocr_llm_pipeline import VietIDPPipeline
            pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)

            start_time = time.time()
            result = pipeline.process_file(str(file_path), save_result=True)
            elapsed = time.time() - start_time

            extraction_data = result.get('extraction', {})

            extraction = ExtractionResult(
                document_id=doc_id,
                loai_van_ban=extraction_data.get('loai_van_ban', ''),
                so_hieu=extraction_data.get('so_hieu', ''),
                ngay_ban_hanh=extraction_data.get('ngay_ban_hanh', ''),
                co_quan_ban_hanh=extraction_data.get('co_quan_ban_hanh', ''),
                trich_yeu=extraction_data.get('trich_yeu', ''),
                nguoi_ky=extraction_data.get('nguoi_ky', ''),
                full_text=result.get('full_text', ''),
                raw_json=extraction_data,
                total_stamps=result.get('total_stamps', 0),
                processing_time=round(elapsed, 2),
            )
            session.add(extraction)
            doc.status = "completed"
            doc.num_pages = result.get('num_pages', 1)
            session.commit()

            return {
                "status": "completed",
                "document_id": doc_id,
                "processing_time": round(elapsed, 2),
                "num_pages": result.get('num_pages', 1),
                "total_stamps": result.get('total_stamps', 0),
                "extraction": extraction_data,
                "full_text": result.get('full_text', '')[:500],
            }

    except Exception as e:
        session.rollback()
        if 'doc_id' in locals():
            doc_obj = session.query(Document).get(doc_id)
            if doc_obj:
                doc_obj.status = "failed"
                session.commit()
        raise HTTPException(500, f"Processing error: {str(e)}")
    finally:
        session.close()


@router.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    """Kiểm tra trạng thái Celery task."""
    from src.api.tasks import celery_app
    task = celery_app.AsyncResult(task_id)
    response = {"task_id": task_id, "status": task.status}

    if task.state == 'PROGRESS':
        response["progress"] = task.info
    elif task.state == 'SUCCESS':
        response["result"] = task.result
    elif task.state == 'FAILURE':
        response["error"] = str(task.info)

    return response


# ═══════════════════════════════════════════════════════════════════════
# Document CRUD
# ═══════════════════════════════════════════════════════════════════════

@router.get("/documents")
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None
):
    """Danh sách documents đã xử lý."""
    session = get_session()
    try:
        query = session.query(Document).order_by(Document.created_at.desc())
        if status:
            query = query.filter(Document.status == status)
        total = query.count()
        docs = query.offset(skip).limit(limit).all()
        return {
            "total": total,
            "documents": [d.to_dict() for d in docs]
        }
    finally:
        session.close()


@router.get("/documents/{doc_id}")
async def get_document(doc_id: int):
    """Chi tiết 1 document và kết quả trích xuất."""
    session = get_session()
    try:
        doc = session.query(Document).get(doc_id)
        if not doc:
            raise HTTPException(404, "Document not found")
        return doc.to_dict()
    finally:
        session.close()


@router.put("/documents/{doc_id}")
async def update_extraction(doc_id: int, data: ExtractionUpdate):
    """Cập nhật kết quả trích xuất (user chỉnh sửa)."""
    session = get_session()
    try:
        extraction = session.query(ExtractionResult).filter_by(document_id=doc_id).first()
        if not extraction:
            raise HTTPException(404, "Extraction result not found")

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


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int):
    """Xóa document và kết quả."""
    session = get_session()
    try:
        doc = session.query(Document).get(doc_id)
        if not doc:
            raise HTTPException(404, "Document not found")

        # Delete uploaded file
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError:
                pass # Ignore file lock errors on Windows, proceed with DB delete

        session.delete(doc)
        session.commit()
        return {"status": "deleted", "document_id": doc_id}
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════

@router.get("/export/{doc_id}")
async def export_document(doc_id: int, format: str = Query("json", pattern="^(json|csv)$")):
    """Export kết quả trích xuất ra JSON hoặc CSV."""
    session = get_session()
    try:
        extraction = session.query(ExtractionResult).filter_by(document_id=doc_id).first()
        if not extraction:
            raise HTTPException(404, "Extraction result not found")

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
                headers={"Content-Disposition": f"attachment; filename=doc_{doc_id}.csv"}
            )
        else:
            return JSONResponse(content=data)
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════
# Chat (Document Q&A)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/chat")
async def chat_with_document(req: ChatRequest):
    """Hỏi đáp trên tài liệu đã xử lý."""
    context = req.context

    # Nếu có document_id, lấy text từ database
    if req.document_id and not context:
        session = get_session()
        try:
            extraction = session.query(ExtractionResult).filter_by(
                document_id=req.document_id
            ).first()
            if extraction and extraction.full_text:
                context = extraction.full_text
        finally:
            session.close()

    if not context:
        raise HTTPException(400, "Không có context. Cung cấp document_id hoặc context text.")

    from src.llm.ollama_client import OllamaClient
    from src.llm.prompts import PROMPTS

    # Lỗi 5: Safe truncation (Cắt chuỗi an toàn ở cuối từ/câu thay vì cắt ngang)
    max_chars = Config.OLLAMA_MAX_CHARS
    if len(context) > max_chars:
        truncated = context[:max_chars]
        cut_point = max(truncated.rfind(' '), truncated.rfind('\n'))
        if cut_point > 0:
            context = truncated[:cut_point] + "..."
        else:
            context = truncated + "..."

    prompt = PROMPTS['chat'].format(context=context, question=req.question)
    client = OllamaClient()
    result, error = client.generate(prompt, format_json=False)

    if error:
        raise HTTPException(500, f"LLM error: {error}")

    return {"answer": result, "question": req.question}
