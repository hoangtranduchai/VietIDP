# -*- coding: utf-8 -*-
"""
Native Task Queue (Replaces Celery)
=====================================
Xử lý văn bản bất đồng bộ bằng threading / background tasks.
Không yêu cầu Redis hay Celery worker.
"""

import os
import time
import uuid
import threading
from datetime import datetime

from src.config import Config

# ═══════════════════════════════════════════════════════════════════════
# Simple Task Manager
# ═══════════════════════════════════════════════════════════════════════

class TaskState:
    PENDING = 'PENDING'
    PROGRESS = 'PROGRESS'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'

class NativeTaskManager:
    def __init__(self):
        self.tasks = {}

    def get_task(self, task_id):
        return self.tasks.get(task_id, {"status": TaskState.PENDING, "info": {}, "result": None, "state": TaskState.PENDING})

    def update_state(self, task_id, state, meta=None):
        if task_id in self.tasks:
            self.tasks[task_id]["state"] = state
            self.tasks[task_id]["status"] = state
            if meta:
                self.tasks[task_id]["info"] = meta

    def set_result(self, task_id, result):
        if task_id in self.tasks:
            self.tasks[task_id]["state"] = TaskState.SUCCESS
            self.tasks[task_id]["status"] = TaskState.SUCCESS
            self.tasks[task_id]["result"] = result

    def set_error(self, task_id, error_msg):
        if task_id in self.tasks:
            self.tasks[task_id]["state"] = TaskState.FAILURE
            self.tasks[task_id]["status"] = TaskState.FAILURE
            self.tasks[task_id]["info"] = error_msg

# Global instance
task_manager = NativeTaskManager()

class NativeAsyncResult:
    def __init__(self, task_id):
        self.task_id = task_id
        task_data = task_manager.get_task(task_id)
        self.status = task_data["status"]
        self.state = task_data["state"]
        self.info = task_data.get("info", {})
        self.result = task_data.get("result", None)

class NativeApp:
    def AsyncResult(self, task_id):
        return NativeAsyncResult(task_id)

celery_app = NativeApp()

# ═══════════════════════════════════════════════════════════════════════
# Tasks
# ═══════════════════════════════════════════════════════════════════════

def _process_document_worker(task_id: str, document_id: int, file_path: str):
    """Worker process thực sự (chạy trong thread)."""
    from src.api.database import get_session, Document, ExtractionResult, ProcessingLog

    session = get_session()

    try:
        # Update status
        doc = session.query(Document).get(document_id)
        if not doc:
            task_manager.set_error(task_id, f"Document {document_id} not found")
            return

        doc.status = "processing"
        session.commit()

        # ── Stage 1: Load Pipeline ───────────────────────────────────
        task_manager.update_state(task_id, TaskState.PROGRESS, meta={
            'stage': 'initializing', 'progress': 5,
            'message': 'Đang khởi tạo AI Pipeline...'
        })

        from src.pipeline.ocr_llm_pipeline import VietIDPPipeline
        pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)

        # ── Stage 2: Process ─────────────────────────────────────────
        task_manager.update_state(task_id, TaskState.PROGRESS, meta={
            'stage': 'processing', 'progress': 20,
            'message': 'Đang xử lý văn bản...'
        })

        start_time = time.time()
        result = pipeline.process_file(file_path, save_result=True)
        elapsed = time.time() - start_time

        # ── Stage 3: Save to Database ────────────────────────────────
        task_manager.update_state(task_id, TaskState.PROGRESS, meta={
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
            stamp_coordinates=result.get('stamp_coordinates', []),
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

        task_result = {
            "status": "completed",
            "document_id": document_id,
            "processing_time": round(elapsed, 2),
            "extraction": extraction_data,
        }
        task_manager.set_result(task_id, task_result)

    except Exception as e:
        session.rollback()  # Clear aborted transaction state
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

        task_manager.set_error(task_id, str(e))

    finally:
        session.close()


class NativeTaskDispatcher:
    def delay(self, document_id: int, file_path: str):
        task_id = str(uuid.uuid4())
        task_manager.tasks[task_id] = {
            "status": TaskState.PENDING,
            "state": TaskState.PENDING,
            "info": {},
            "result": None
        }
        # Start worker thread
        thread = threading.Thread(
            target=_process_document_worker,
            args=(task_id, document_id, file_path)
        )
        thread.daemon = True
        thread.start()
        
        class TaskRef:
            def __init__(self, tid):
                self.id = tid
        return TaskRef(task_id)

process_document_task = NativeTaskDispatcher()

class NativeBatchDispatcher:
    def delay(self, file_paths: list):
        pass # Optional: implement batch processing if needed

batch_process_task = NativeBatchDispatcher()
