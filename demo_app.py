# -*- coding: utf-8 -*-
"""
VietIDP — Gradio Demo App (QLoRA Backend) — Stage-by-Stage Inspector
=====================================================================
Giao diện trình bày Pipeline trích xuất thông tin văn bản hành chính.
Cho phép giám sát kết quả từng giai đoạn và xuất file demo.

Kiến trúc:
  Stage 1: YOLOv8l (Stamp Detection)
  Stage 2: HybridStampMatting (Stamp Removal)
  Stage 3: EasyOCR+VietOCR (OCR)
  Stage 4: Qwen2.5-7B Ollama (Extraction) → Structured JSON

Sử dụng:
  python demo_app.py
  Truy cập: http://localhost:7860
"""

import os
import sys
import pathlib
import time
import shutil

# [HOTFIX] Windows UTF-8 cho TRL/Transformers
_original_read_text = pathlib.Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    return _original_read_text(self, encoding=encoding or "utf-8", errors=errors)
pathlib.Path.read_text = _utf8_read_text

import gradio as gr
import cv2
import json
import numpy as np
from PIL import Image

from src.pipeline.ocr_llm_pipeline import VietIDPPipeline
from src.config import Config

# ═══════════════════════════════════════════════════════════════
# Khởi tạo Pipeline
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("🚀 VietIDP — Đang tải mô hình AI lên RTX 5070...")
print(f"   Backend LLM: {Config.LLM_BACKEND.upper()}")
print("=" * 60)
pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)

# Thư mục xuất file demo
EXPORT_DIR = os.path.join("results", "demo_export")
os.makedirs(EXPORT_DIR, exist_ok=True)


def bgr2rgb(img):
    """Chuyển BGR → RGB cho Gradio."""
    if img is not None:
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return None


def export_stage_results(result, file_basename):
    """
    Xuất kết quả từng giai đoạn ra thư mục results/demo_export/<file_name>/
    để show cho người khác.
    """
    export_subdir = os.path.join(EXPORT_DIR, file_basename)
    os.makedirs(export_subdir, exist_ok=True)

    pages = result.get("pages", [])
    for page_data in pages:
        page_num = page_data.get("page", 1)
        prefix = f"page_{page_num:02d}"

        # Stage 1: Ảnh gốc sau preprocess
        orig = page_data.get("original_image")
        if orig is not None:
            cv2.imwrite(os.path.join(export_subdir, f"{prefix}_stage0_original.png"), orig)

        # Stage 1: YOLO detection visualization
        det = page_data.get("detection_image")
        if det is not None:
            cv2.imwrite(os.path.join(export_subdir, f"{prefix}_stage1_stamp_detection.png"), det)

        # Stage 2: Ảnh sau xóa con dấu
        clean = page_data.get("clean_image")
        if clean is not None:
            cv2.imwrite(os.path.join(export_subdir, f"{prefix}_stage2_stamp_removed.png"), clean)

    # Stage 3: OCR text output
    full_text = result.get("full_text", "")
    with open(os.path.join(export_subdir, "stage3_ocr_text.txt"), "w", encoding="utf-8") as f:
        f.write(full_text)

    # OCR lines with bounding boxes
    ocr_lines = result.get("ocr_lines", [])
    with open(os.path.join(export_subdir, "stage3_ocr_lines.json"), "w", encoding="utf-8") as f:
        json.dump(ocr_lines, f, ensure_ascii=False, indent=2)

    # Stage 4: Extraction JSON
    extraction = result.get("extraction", {})
    with open(os.path.join(export_subdir, "stage4_extraction.json"), "w", encoding="utf-8") as f:
        json.dump(extraction, f, ensure_ascii=False, indent=2)

    # Metadata tổng hợp
    metadata = {
        "source_file": result.get("source_file", ""),
        "num_pages": result.get("num_pages", 0),
        "total_stamps": result.get("total_stamps", 0),
        "processing_time_seconds": result.get("processing_time_seconds", 0),
        "llm_backend": Config.LLM_BACKEND,
        "processed_at": result.get("processed_at", ""),
        "stamp_coordinates": result.get("stamp_coordinates", []),
        "layout_fields": result.get("layout_fields", {}),
    }
    with open(os.path.join(export_subdir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return export_subdir


def process_file_input(file_path, progress=gr.Progress()):
    """Xử lý file và trả kết quả cho tất cả tabs."""
    if file_path is None:
        empty = None
        return (empty, empty, empty,                    # 3 galleries
                "⚠️ Vui lòng tải tệp lên.", "{}",      # OCR text + JSON
                "", "")                                  # metadata + export

    try:
        progress(0.05, desc="📄 Đang xử lý tài liệu...")

        result = pipeline.process_file(file_path, save_result=True)

        progress(0.85, desc="📊 Đang format kết quả...")

        pages = result.get("pages", [])
        file_basename = os.path.splitext(os.path.basename(file_path))[0]

        # ── Stage 1: Ảnh gốc + YOLO Detection ──
        stage1_images = []
        for p in pages:
            det = p.get("detection_image")
            if det is not None:
                stage1_images.append(bgr2rgb(det))

        # ── Stage 2: Ảnh sau xóa con dấu ──
        stage2_images = []
        for p in pages:
            clean = p.get("clean_image")
            if clean is not None:
                stage2_images.append(bgr2rgb(clean))

        # ── Stage 0: Ảnh gốc (original) ──
        original_images = []
        for p in pages:
            orig = p.get("original_image")
            if orig is not None:
                original_images.append(bgr2rgb(orig))

        # ── Stage 3: OCR Text ──
        raw_text = result.get("full_text", "")

        # ── Stage 4: Extraction JSON ──
        extraction = result.get("extraction", {})
        json_output = json.dumps(extraction, indent=4, ensure_ascii=False)

        # ── Metadata ──
        stamp_info = result.get("stamp_coordinates", [])
        stamp_details = ""
        for s in stamp_info:
            stamp_details += (f"  Trang {s.get('page', '?')}: "
                              f"({s['x1']},{s['y1']})→({s['x2']},{s['y2']}) "
                              f"conf={s['confidence']}\n")

        meta_lines = [
            f"📄 File: {os.path.basename(file_path)}",
            f"📑 Số trang: {result.get('num_pages', '?')}",
            f"🔴 Số con dấu phát hiện: {result.get('total_stamps', '?')}",
            stamp_details.rstrip() if stamp_details else "   (Không có con dấu)",
            f"⏱️ Thời gian xử lý: {result.get('processing_time_seconds', 0):.1f}s",
            f"🤖 Backend LLM: {Config.LLM_BACKEND.upper()}",
            f"📅 Thời điểm: {result.get('processed_at', '')}",
        ]
        metadata = "\n".join(meta_lines)

        # ── Xuất file demo ──
        progress(0.95, desc="💾 Đang xuất file demo...")
        export_path = export_stage_results(result, file_basename)

        # Đếm số file đã xuất
        export_files = os.listdir(export_path)
        export_info = (f"✅ Đã xuất {len(export_files)} file vào:\n"
                       f"📂 {export_path}\n\n"
                       f"📁 Danh sách file:\n")
        for f in sorted(export_files):
            size_kb = os.path.getsize(os.path.join(export_path, f)) / 1024
            export_info += f"  • {f}  ({size_kb:.1f} KB)\n"

        progress(1.0, desc="✅ Hoàn thành!")
        return (original_images, stage1_images, stage2_images,
                raw_text, json_output,
                metadata, export_info)

    except Exception as e:
        import traceback
        traceback.print_exc()
        err = f"❌ Lỗi: {str(e)}"
        return (None, None, None, err, "{}", "", "")


# ═══════════════════════════════════════════════════════════════
# Giao diện Web — Stage-by-Stage Inspector
# ═══════════════════════════════════════════════════════════════
with gr.Blocks(
    title="VietIDP — Trích Xuất Văn Bản Hành Chính",
) as demo:

    gr.Markdown(
        """
        # 🇻🇳 VietIDP — Hệ thống Trích Xuất Văn Bản Hành Chính

        **Pipeline 4 giai đoạn:** YOLOv8l → HybridStampMatting → EasyOCR+VietOCR → Qwen2.5-7B (Ollama)

        Chạy hoàn toàn **Offline (On-Premise)** trên RTX 5070 8GB | Tuân thủ **NĐ 13/2023/NĐ-CP**
        """
    )

    with gr.Row():
        # ── Cột trái: Upload + Metadata ──
        with gr.Column(scale=1):
            input_file = gr.File(
                label="📁 Tải lên Văn bản (PDF, JPG, PNG)",
                file_types=[".pdf", ".jpg", ".png", ".jpeg"]
            )
            submit_btn = gr.Button(
                "🚀 Phân tích & Trích xuất",
                variant="primary",
                size="lg"
            )
            metadata_box = gr.Textbox(
                label="📊 Thông tin xử lý",
                lines=8,
                interactive=False,
            )
            export_box = gr.Textbox(
                label="💾 Kết quả xuất file (cho Demo/Trình bày)",
                lines=8,
                interactive=False,
            )

        # ── Cột phải: Kết quả theo giai đoạn ──
        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.Tab("📄 Stage 0 — Ảnh gốc"):
                    gallery_original = gr.Gallery(
                        label="Ảnh gốc sau tiền xử lý (Deskew + Denoise)",
                        preview=True, object_fit="contain", height=450
                    )

                with gr.Tab("🔴 Stage 1 — Phát hiện Con dấu (YOLO)"):
                    gallery_stage1 = gr.Gallery(
                        label="YOLOv8l Stamp Detection — Bounding Boxes (đỏ = con dấu)",
                        preview=True, object_fit="contain", height=450
                    )

                with gr.Tab("🧹 Stage 2 — Xóa Con dấu (Matting)"):
                    gallery_stage2 = gr.Gallery(
                        label="HybridStampMatting — Ảnh sau khi xóa con dấu đỏ",
                        preview=True, object_fit="contain", height=450
                    )

                with gr.Tab("📝 Stage 3 — OCR (VietOCR)"):
                    raw_text = gr.Textbox(
                        label="EasyOCR (Detect) + VietOCR VGG-Transformer (Recognize)",
                        lines=20,
                    )

                with gr.Tab("📋 Stage 4 — Trích xuất (LLM)"):
                    json_output = gr.Code(
                        label="Qwen2.5-7B (Ollama) → Structured JSON",
                        language="json",
                        lines=20,
                    )

    submit_btn.click(
        fn=process_file_input,
        inputs=[input_file],
        outputs=[
            gallery_original, gallery_stage1, gallery_stage2,
            raw_text, json_output,
            metadata_box, export_box
        ]
    )

    gr.Markdown(
        """
        ---
        **Nghiên cứu:** Trích xuất thông tin từ VBHC tiếng Việt | **Chuẩn:** NĐ 30/2020/NĐ-CP
        | **Bảo mật:** NĐ 13/2023/NĐ-CP | **GPU:** RTX 5070 8GB VRAM
        | 📂 **File demo** được tự động xuất vào `results/demo_export/`
        """
    )

if __name__ == "__main__":
    print("🌐 Khởi động Gradio UI — http://localhost:7860")
    demo.launch(server_name="0.0.0.0", server_port=7860, inbrowser=True)
