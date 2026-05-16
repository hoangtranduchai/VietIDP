# -*- coding: utf-8 -*-
"""
VietIDP — Gradio Demo App — Stage-by-Stage Inspector (v2.0)
=============================================================
Giao diện trình bày Pipeline trích xuất thông tin văn bản hành chính.
Thiết kế dành riêng cho bảo vệ trước Hội đồng.

Sử dụng:
  python demo_app.py
  Truy cập: http://localhost:7860
"""

import os
import sys
import pathlib
import time
import json
import traceback

# [HOTFIX] Windows UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

_original_read_text = pathlib.Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    return _original_read_text(self, encoding=encoding or "utf-8", errors=errors)
pathlib.Path.read_text = _utf8_read_text

import gradio as gr
import cv2
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

EXPORT_DIR = os.path.join("results", "demo_export")
os.makedirs(EXPORT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# CSS Premium Dark Theme
# ═══════════════════════════════════════════════════════════════
CUSTOM_CSS = """
/* === GLOBAL — Full-screen layout === */
.gradio-container {
    max-width: 100% !important;
    padding: 8px 20px !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}
/* === HEADER === */
.header-banner {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 16px;
    padding: 18px 30px;
    margin-bottom: 12px;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.header-banner h1 {
    background: linear-gradient(90deg, #f7971e, #ffd200);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.8rem !important;
    margin: 0 0 4px 0 !important;
    font-weight: 800 !important;
}
.header-banner p {
    color: #b8c0e0 !important;
    margin: 2px 0 !important;
    font-size: 0.88rem !important;
}
.header-banner .pipeline-flow {
    color: #7dd3fc !important;
    font-size: 0.9rem !important;
    font-weight: 600;
    margin-top: 8px !important;
    padding: 6px 12px;
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    display: inline-block;
    border: 1px solid rgba(125,211,252,0.15);
}
/* === BADGE === */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 700;
    margin-right: 6px;
}
.badge-gpu { background: #22c55e22; color: #4ade80; border: 1px solid #22c55e44; }
.badge-security { background: #ef444422; color: #f87171; border: 1px solid #ef444444; }
.badge-offline { background: #3b82f622; color: #60a5fa; border: 1px solid #3b82f644; }
/* === TABS === */
.tabs > .tab-nav > button {
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 10px 18px !important;
}
.tabs > .tab-nav > button.selected {
    border-bottom: 3px solid #f7971e !important;
    color: #fbbf24 !important;
}
/* === SUBMIT BTN === */
#submit-btn {
    background: linear-gradient(135deg, #f7971e, #ffd200) !important;
    color: #000 !important;
    font-weight: 700 !important;
    font-size: 1.1rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px !important;
    box-shadow: 0 4px 15px rgba(247,151,30,0.3) !important;
    transition: all 0.2s !important;
}
#submit-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(247,151,30,0.45) !important;
}
/* === METADATA === */
.metadata-box textarea {
    font-family: 'JetBrains Mono', 'Consolas', monospace !important;
    font-size: 0.85rem !important;
    line-height: 1.6 !important;
}
/* === GALLERY — Fill available vertical space === */
.gallery-full-height {
    min-height: calc(100vh - 360px) !important;
}
.gallery-full-height .grid-wrap,
.gallery-full-height .preview {
    min-height: calc(100vh - 400px) !important;
}
/* === COMPARISON — Side-by-side full height === */
.comparison-label {
    text-align: center;
    font-weight: 700;
    font-size: 0.95rem;
    padding: 6px;
    border-radius: 6px;
    margin-bottom: 4px;
}
.gallery-compare {
    min-height: calc(100vh - 400px) !important;
}
.gallery-compare .grid-wrap,
.gallery-compare .preview {
    min-height: calc(100vh - 440px) !important;
}
/* === OCR / JSON textboxes — fill height === */
.ocr-textbox textarea {
    min-height: calc(100vh - 400px) !important;
    font-size: 0.9rem !important;
    line-height: 1.7 !important;
}
.json-code-block {
    min-height: calc(100vh - 400px) !important;
}
.json-code-block .cm-editor {
    min-height: calc(100vh - 420px) !important;
}
/* === BENCHMARK === */
.benchmark-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border-radius: 12px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.06);
}
/* === FOOTER === */
.footer-banner {
    background: linear-gradient(135deg, #1a1a2e, #0f0c29);
    border-radius: 12px;
    padding: 12px 24px;
    margin-top: 8px;
    border: 1px solid rgba(255,255,255,0.06);
    text-align: center;
}
.footer-banner p {
    color: #6b7280 !important;
    font-size: 0.82rem !important;
    margin: 2px 0 !important;
}
/* === LEFT SIDEBAR === */
.left-sidebar {
    /* No scroll — all content visible at once */
}
"""

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def bgr2rgb(img):
    if img is not None:
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return None


def load_benchmark():
    """Load benchmark results từ file."""
    bench_path = os.path.join("results", "benchmark", "research_metrics.json")
    if not os.path.exists(bench_path):
        return "⚠️ Chưa có dữ liệu benchmark (chạy benchmark trước)."
    with open(bench_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    doc = data.get("document_level", {})
    fields = data.get("field_level", {})
    macro = data.get("macro_averages", {})
    timing = data.get("processing_time", {})

    field_names = {
        "loai_van_ban": "Loại văn bản",
        "so_hieu": "Số hiệu",
        "ngay_ban_hanh": "Ngày ban hành",
        "co_quan_ban_hanh": "Cơ quan ban hành",
        "trich_yeu": "Trích yếu",
        "nguoi_ky": "Người ký",
    }

    lines = []
    lines.append("# 📊 KẾT QUẢ BENCHMARK — 100 Văn bản Hành chính\n")
    lines.append(f"**Pipeline:** {meta.get('pipeline', 'N/A')}")
    lines.append(f"**OCR Engine:** {meta.get('ocr_engine', 'N/A')}")
    lines.append(f"**LLM Model:** {meta.get('llm_model', 'N/A')} (temp={meta.get('llm_temperature', 'N/A')})")
    lines.append(f"**Stamp Detection:** {meta.get('stamp_detector', 'N/A')} + {meta.get('stamp_matting', 'N/A')}")
    lines.append(f"**GPU:** {meta.get('gpu', 'N/A')} | **DPI:** {meta.get('ocr_dpi', 'N/A')}")
    lines.append(f"\n**Tổng số tài liệu:** {doc.get('total_documents', 0)}")
    lines.append(f"**Đạt 100% chính xác:** {doc.get('perfect_documents', 0)} tài liệu")
    lines.append("\n---\n")
    lines.append("## Accuracy theo từng trường\n")
    lines.append("| Trường | Exact Match | Token F1 | Char Similarity | Đúng | Sai |")
    lines.append("|--------|:-----------:|:--------:|:---------------:|:----:|:---:|")
    for key, name in field_names.items():
        f = fields.get(key, {})
        em = f.get("normalized_exact_match", 0)
        f1 = f.get("token_f1", 0)
        cs = f.get("character_similarity", 0)
        c = f.get("correct", 0)
        w = f.get("wrong", 0)
        lines.append(f"| {name} | **{em*100:.1f}%** | {f1*100:.1f}% | {cs*100:.1f}% | {c} | {w} |")
    lines.append(f"\n**Macro Average:** EM = **{macro.get('normalized_exact_match',0)*100:.1f}%** "
                 f"| Token F1 = **{macro.get('token_f1',0)*100:.1f}%** "
                 f"| Char Sim = **{macro.get('character_similarity',0)*100:.1f}%**")
    lines.append(f"\n**Thời gian xử lý:** Trung bình {timing.get('mean_seconds',0):.1f}s/file "
                 f"| Min {timing.get('min_seconds',0):.1f}s | Max {timing.get('max_seconds',0):.1f}s")
    return "\n".join(lines)


def export_stage_results(result, file_basename):
    """Xuất kết quả từng giai đoạn ra thư mục demo_export."""
    export_subdir = os.path.join(EXPORT_DIR, file_basename)
    os.makedirs(export_subdir, exist_ok=True)

    pages = result.get("pages", [])
    for page_data in pages:
        page_num = page_data.get("page", 1)
        prefix = f"page_{page_num:02d}"

        orig = page_data.get("original_image")
        if orig is not None:
            cv2.imwrite(os.path.join(export_subdir, f"{prefix}_stage0_original.png"), orig)

        det = page_data.get("detection_image")
        if det is not None:
            cv2.imwrite(os.path.join(export_subdir, f"{prefix}_stage1_stamp_detection.png"), det)

        clean = page_data.get("clean_image")
        if clean is not None:
            cv2.imwrite(os.path.join(export_subdir, f"{prefix}_stage2_stamp_removed.png"), clean)

    full_text = result.get("full_text", "")
    with open(os.path.join(export_subdir, "stage3_ocr_text.txt"), "w", encoding="utf-8") as f:
        f.write(full_text)

    extraction = result.get("extraction", {})
    with open(os.path.join(export_subdir, "stage4_extraction.json"), "w", encoding="utf-8") as f:
        json.dump(extraction, f, ensure_ascii=False, indent=2)

    metadata = {
        "source_file": result.get("source_file", ""),
        "num_pages": result.get("num_pages", 0),
        "total_stamps": result.get("total_stamps", 0),
        "processing_time_seconds": result.get("processing_time_seconds", 0),
        "llm_backend": Config.LLM_BACKEND,
        "processed_at": result.get("processed_at", ""),
        "stamp_coordinates": result.get("stamp_coordinates", []),
    }
    with open(os.path.join(export_subdir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return export_subdir


# ═══════════════════════════════════════════════════════════════
# Main Processing Function
# ═══════════════════════════════════════════════════════════════
def process_file_input(file_path, progress=gr.Progress()):
    """Xử lý file và trả kết quả cho tất cả tabs."""
    # 10 outputs total
    empty_gallery = []
    empty_return = (
        empty_gallery, empty_gallery, empty_gallery, empty_gallery,
        "⚠️ Vui lòng tải tệp lên.", "{}",
        "", ""
    )

    if file_path is None:
        return empty_return

    try:
        progress(0.05, desc="📄 Đang tiền xử lý tài liệu...")
        t_start = time.time()

        result = pipeline.process_file(file_path, save_result=True)

        progress(0.85, desc="📊 Đang format kết quả...")

        pages = result.get("pages", [])
        file_basename = os.path.splitext(os.path.basename(file_path))[0]

        # ── Stage 0: Ảnh gốc ──
        original_images = []
        for p in pages:
            orig = p.get("original_image")
            if orig is not None:
                original_images.append(bgr2rgb(orig))

        # ── Stage 1: YOLO Detection ──
        stage1_images = []
        for p in pages:
            det = p.get("detection_image")
            if det is not None:
                stage1_images.append(bgr2rgb(det))

        # ── Stage 2: Before (original) ──
        before_images = []
        for p in pages:
            orig = p.get("original_image")
            if orig is not None:
                before_images.append(bgr2rgb(orig))

        # ── Stage 2: After (clean) ──
        after_images = []
        for p in pages:
            clean = p.get("clean_image")
            if clean is not None:
                after_images.append(bgr2rgb(clean))

        # ── Stage 3: OCR Text ──
        raw_text = result.get("full_text", "")

        # ── Stage 4: Extraction JSON ──
        extraction = result.get("extraction", {})
        json_output = json.dumps(extraction, indent=4, ensure_ascii=False)

        # ── Metadata ──
        stamp_info = result.get("stamp_coordinates", [])
        stamp_details = ""
        for s in stamp_info:
            stamp_details += (f"  📍 Trang {s.get('page', '?')}: "
                              f"({s['x1']},{s['y1']})→({s['x2']},{s['y2']}) "
                              f"conf={s['confidence']}\n")

        proc_time = result.get('processing_time_seconds', 0)
        meta_lines = [
            "━" * 40,
            f"📄  File: {os.path.basename(file_path)}",
            f"📑  Số trang: {result.get('num_pages', '?')}",
            f"🔴  Con dấu phát hiện: {result.get('total_stamps', 0)}",
            stamp_details.rstrip() if stamp_details else "   (Không có con dấu)",
            "━" * 40,
            f"⏱️  Thời gian xử lý: {proc_time:.1f}s",
            f"🤖  LLM Backend: {Config.LLM_BACKEND.upper()} ({Config.OLLAMA_MODEL})",
            f"🖥️  OCR DPI: {Config.OCR_DPI}",
            f"📅  Thời điểm: {result.get('processed_at', '')}",
            "━" * 40,
        ]
        metadata = "\n".join(meta_lines)

        # ── Xuất file demo ──
        progress(0.95, desc="💾 Đang xuất file demo...")
        export_path = export_stage_results(result, file_basename)
        export_files = os.listdir(export_path)
        export_info = (f"✅ Đã xuất {len(export_files)} file vào:\n"
                       f"📂 {export_path}\n\n"
                       f"📁 Danh sách:\n")
        for f_name in sorted(export_files):
            size_kb = os.path.getsize(os.path.join(export_path, f_name)) / 1024
            export_info += f"  • {f_name}  ({size_kb:.1f} KB)\n"

        progress(1.0, desc="✅ Hoàn thành!")
        return (
            original_images, stage1_images, before_images, after_images,
            raw_text, json_output,
            metadata, export_info
        )

    except Exception as e:
        traceback.print_exc()
        err = f"❌ Lỗi: {str(e)}"
        return ([], [], [], [], err, "{}", "", "")


# ═══════════════════════════════════════════════════════════════
# Giao diện Web — Stage-by-Stage Inspector v2.0
# ═══════════════════════════════════════════════════════════════
THEME = gr.themes.Base(
    primary_hue="amber",
    secondary_hue="blue",
    neutral_hue="slate",
    font=[
        gr.themes.GoogleFont("Inter"),
        gr.themes.Font("Segoe UI"),
        gr.themes.Font("sans-serif"),
    ],
)

with gr.Blocks(
    title="VietIDP — Demo Bảo vệ Hội đồng",
) as demo:

    # ── HEADER ──
    gr.HTML("""
    <div class="header-banner">
        <h1>🇻🇳 VietIDP — Hệ thống Trích Xuất Văn Bản Hành Chính</h1>
        <p>
            <span class="badge badge-offline">🔒 100% OFFLINE</span>
            <span class="badge badge-gpu">⚡ RTX 5070 8GB</span>
            <span class="badge badge-security">🛡️ NĐ 13/2023/NĐ-CP</span>
        </p>
        <p class="pipeline-flow">
            📄 Input → ⚙️ Preprocess → 🔴 YOLOv8x (Stamp Detect)
            → 🧹 HybridStampMatting (Remove)
            → 📝 EasyOCR + VietOCR → 🤖 Qwen2.5-7B (Ollama) → 📋 JSON
        </p>
    </div>
    """)

    with gr.Row():
        # ══════════════════════════════════════
        # CỘT TRÁI: Upload + Metadata
        # ══════════════════════════════════════
        with gr.Column(scale=1, min_width=300):
            input_file = gr.File(
                label="📁 Tải lên Văn bản (PDF / JPG / PNG)",
                file_types=[".pdf", ".jpg", ".png", ".jpeg"],
            )
            submit_btn = gr.Button(
                "🚀  Phân tích & Trích xuất",
                variant="primary",
                size="lg",
                elem_id="submit-btn",
            )
            metadata_box = gr.Textbox(
                label="📊 Thông tin xử lý (Metadata)",
                lines=12,
                interactive=False,
                elem_classes=["metadata-box"],
            )
            export_box = gr.Textbox(
                label="💾 Kết quả xuất file Demo",
                lines=8,
                interactive=False,
            )

        # ══════════════════════════════════════
        # CỘT PHẢI: Kết quả Stage-by-Stage
        # ══════════════════════════════════════
        with gr.Column(scale=3):
            with gr.Tabs() as tabs:
                # ── Stage 0: Ảnh gốc ──
                with gr.Tab("📄 Stage 0 — Ảnh gốc"):
                    gr.Markdown("**Ảnh gốc sau tiền xử lý** (Deskew + Denoise) — "
                                "Đây là đầu vào cho pipeline xử lý con dấu.")
                    gallery_original = gr.Gallery(
                        label="Ảnh gốc (Preprocessed)",
                        preview=True, object_fit="contain", height=650,
                        columns=2,
                        elem_classes=["gallery-full-height"],
                    )

                # ── Stage 1: YOLO Detection ──
                with gr.Tab("🔴 Stage 1 — Phát hiện Con dấu (YOLO)"):
                    gr.Markdown("**YOLOv8x Stamp Detection** — Mô hình YOLO được tinh chỉnh "
                                "để khoanh vùng chính xác tọa độ Bounding Box của con dấu đỏ. "
                                "Hộp đỏ = vùng chứa con dấu.")
                    gallery_stage1 = gr.Gallery(
                        label="YOLO Bounding Boxes (đỏ = con dấu)",
                        preview=True, object_fit="contain", height=650,
                        columns=2,
                        elem_classes=["gallery-full-height"],
                    )

                # ── Stage 2: Before/After ──
                with gr.Tab("🧹 Stage 2 — Xóa Con dấu (Matting)"):
                    gr.Markdown("**HybridStampMatting** — Thuật toán kết hợp AI Segmentation (Rembg) "
                                "và Color Matting để bóc tách hoàn toàn dải màu đỏ con dấu, "
                                "**giữ nguyên nét mực đen** của chữ ký bên dưới.")
                    with gr.Row():
                        with gr.Column():
                            gr.HTML('<div class="comparison-label" style="background:#ef444433;color:#f87171;">⬅️ TRƯỚC — Ảnh gốc (có con dấu)</div>')
                            gallery_before = gr.Gallery(
                                label="Trước (có con dấu)",
                                preview=True, object_fit="contain", height=600,
                                elem_classes=["gallery-compare"],
                            )
                        with gr.Column():
                            gr.HTML('<div class="comparison-label" style="background:#22c55e33;color:#4ade80;">➡️ SAU — Đã xóa con dấu</div>')
                            gallery_after = gr.Gallery(
                                label="Sau (đã xóa dấu)",
                                preview=True, object_fit="contain", height=600,
                                elem_classes=["gallery-compare"],
                            )

                # ── Stage 3: OCR ──
                with gr.Tab("📝 Stage 3 — OCR (VietOCR)"):
                    gr.Markdown("**EasyOCR** (Text Detection) + **VietOCR VGG-Transformer** "
                                "(Text Recognition) — Kết quả OCR sau khi con dấu đã được xóa sạch.")
                    raw_text = gr.Textbox(
                        label="Kết quả OCR (Full Text)",
                        lines=28,
                        elem_classes=["ocr-textbox"],
                    )

                # ── Stage 4: LLM Extraction ──
                with gr.Tab("📋 Stage 4 — Trích xuất (LLM)"):
                    gr.Markdown("**Qwen2.5-7B** chạy cục bộ qua Ollama — Trích xuất 6 trường "
                                "thông tin theo chuẩn **NĐ 30/2020/NĐ-CP**: Loại VB, Số hiệu, "
                                "Ngày ban hành, Cơ quan ban hành, Trích yếu, Người ký.")
                    json_output = gr.Code(
                        label="Structured JSON Output",
                        language="json",
                        lines=28,
                        elem_classes=["json-code-block"],
                    )

                # ── Benchmark Tab ──
                with gr.Tab("📊 Benchmark (100 docs)"):
                    gr.Markdown("**Kết quả thực nghiệm** trên bộ test 100 văn bản hành chính "
                                "đa dạng loại (Quyết định, Nghị định, Thông tư, Công văn...).")
                    benchmark_md = gr.Markdown(
                        value=load_benchmark(),
                    )

    # ── Event Handler ──
    submit_btn.click(
        fn=process_file_input,
        inputs=[input_file],
        outputs=[
            gallery_original, gallery_stage1,
            gallery_before, gallery_after,
            raw_text, json_output,
            metadata_box, export_box,
        ],
    )

    # ── FOOTER ──
    gr.HTML("""
    <div class="footer-banner">
        <p><strong>VietIDP</strong> — Trích xuất thông tin từ Văn bản Hành chính tiếng Việt</p>
        <p>Chuẩn NĐ 30/2020/NĐ-CP | Bảo mật NĐ 13/2023/NĐ-CP | On-Premise RTX 5070 8GB</p>
        <p>📂 File demo tự động xuất vào <code>results/demo_export/</code></p>
    </div>
    """)


if __name__ == "__main__":
    print("🌐 Khởi động VietIDP Demo — http://localhost:7860")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        inbrowser=True,
        css=CUSTOM_CSS,
        theme=THEME,
    )
