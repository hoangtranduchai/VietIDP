# -*- coding: utf-8 -*-
"""
Celery Task Queue
==================
Xử lý văn bản bất đồng bộ bằng Celery + Redis.

Chạy worker: celery -A src.api.tasks worker --loglevel=info --pool=solo
"""

import os
import time
import json
from datetime import datetime
from celery import Celery

from src.config import Config

# ═══════════════════════════════════════════════════════════════════════
# Celery App
# ═══════════════════════════════════════════════════════════════════════

celery_app = Celery(
    "vietidp",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Ho_Chi_Minh',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # 1 task tại 1 thời điểm (GPU bottleneck)
)


# ═══════════════════════════════════════════════════════════════════════
# Tasks
# ═══════════════════════════════════════════════════════════════════════

@celery_app.task(bind=True, name="process_document")
def process_document_task(self, document_id: int, file_path: str):
    """
    Task xử lý 1 văn bản qua pipeline VietIDP.
    Cập nhật progress qua Celery state.
    """
    from src.api.database import get_session, Document, ExtractionResult, ProcessingLog

    session = get_session()

    try:
        # Update status
        doc = session.query(Document).get(document_id)
        if not doc:
            return {"error": f"Document {document_id} not found"}

        doc.status = "processing"
        session.commit()

        # ── Stage 1: Load Pipeline ───────────────────────────────────
        self.update_state(state='PROGRESS', meta={
            'stage': 'initializing', 'progress': 5,
            'message': 'Đang khởi tạo AI Pipeline...'
        })

        from src.pipeline.ocr_llm_pipeline import VietIDPPipeline
        pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)

        # ── Stage 2: Process ─────────────────────────────────────────
        self.update_state(state='PROGRESS', meta={
            'stage': 'processing', 'progress': 20,
            'message': 'Đang xử lý văn bản...'
        })

        start_time = time.time()
        result = pipeline.process_file(file_path, save_result=True)
        elapsed = time.time() - start_time

        # ── Stage 3: Save to Database ────────────────────────────────
        self.update_state(state='PROGRESS', meta={
            'stage': 'saving', 'progress': 90,
            'message': 'Đang lưu kết quả...'
        })

        extraction_data = result.get('extraction', {})

        extraction = ExtractionResult(
            document_id=document_id,
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

        # Log
        log = ProcessingLog(
            document_id=document_id,
            stage="pipeline_complete",
            status="completed",
            message=f"Processed in {elapsed:.2f}s, {result.get('num_pages', 1)} pages",
            duration=elapsed
        )
        session.add(log)
        session.commit()

        return {
            "status": "completed",
            "document_id": document_id,
            "processing_time": round(elapsed, 2),
            "extraction": extraction_data,
        }

    except Exception as e:
        # Update status to failed
        try:
            doc = session.query(Document).get(document_id)
            if doc:
                doc.status = "failed"
                session.commit()

            log = ProcessingLog(
                document_id=document_id,
                stage="pipeline_error",
                status="failed",
                message=str(e)
            )
            session.add(log)
            session.commit()
        except Exception:
            pass

        return {"status": "failed", "error": str(e)}

    finally:
        session.close()


@celery_app.task(bind=True, name="batch_process")
def batch_process_task(self, file_paths: list):
    """Task xử lý hàng loạt nhiều files."""
    results = []
    total = len(file_paths)

    for i, fp in enumerate(file_paths):
        self.update_state(state='PROGRESS', meta={
            'stage': 'batch', 'progress': int((i / total) * 100),
            'message': f'Processing file {i+1}/{total}'
        })

        result = process_document_task.delay(fp['document_id'], fp['file_path'])
        results.append({
            'file': fp['file_path'],
            'task_id': result.id
        })

    return {"total": total, "tasks": results}
