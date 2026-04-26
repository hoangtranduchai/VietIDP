# -*- coding: utf-8 -*-
"""
VietIDP Unified Pipeline (v3.0)
================================
Pipeline đầu cuối duy nhất cho xử lý văn bản hành chính Việt Nam.
Hợp nhất từ end_to_end.py + ocr_llm_pipeline.py.

Kiến trúc:
  Image/PDF → Preprocess (Deskew + Denoise)
            → YOLO Stamp Detect → HybridStampMatting Remove
            → VietOCR + EasyOCR → Raw Text
            → Qwen2.5-7B (Ollama) → Structured JSON
            → Validation → Output
"""

import os
import re
import json
import time
import socket
import subprocess
import numpy as np
import cv2
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.preprocessing.deskew import auto_deskew
from src.preprocessing.denoise import denoise_image
from src.preprocessing.stamp_matting import HybridStampMatting
from src.ocr.engine import VietnameseOCREngine
from src.llm.ollama_client import OllamaClient


class VietIDPPipeline:
    """
    Pipeline đầu cuối cho xử lý văn bản hành chính Việt Nam.

    Quy trình 5 giai đoạn:
    1. Preprocessing: Deskew → Denoise
    2. Stamp Detection (YOLOv8x) → Stamp Removal (HybridStampMatting)
    3. OCR: EasyOCR detect + VietOCR recognize → raw text
    4. LLM: Qwen2.5-7B (Ollama) → classification + extraction
    5. Validation: Kiểm tra format JSON → Structured Output

    Tất cả model được load 1 lần và cache trong bộ nhớ.
    """

    def __init__(self, load_yolo=True, load_ocr=True, load_llm=True):
        print("=" * 60)
        print(" VIETIDP — Unified Pipeline v3.0")
        print("=" * 60)

        self.detector = None
        self.stamp_matter = None
        self.ocr_engine = None
        self.llm_client = None

        # ── 1. YOLO Stamp Detector ───────────────────────────────────────
        if load_yolo:
            print("[1/4] Khởi tạo YOLOv8x Stamp Detector...")
            try:
                from ultralytics import YOLO
                yolo_path = Config.STAMP_DETECTION_MODEL
                if yolo_path.exists():
                    self.detector = YOLO(str(yolo_path))
                    print(f"  → Loaded: {yolo_path.name}")
                else:
                    print(f"  → ⚠️ Không tìm thấy weights: {yolo_path}")
            except ImportError:
                print("  → ⚠️ ultralytics chưa cài đặt")

        # ── 2. HybridStampMatting (VRAM = 0) ─────────────────────────────
        print("[2/4] Khởi tạo HybridStampMatting (Color Matting + Rembg)...")
        try:
            self.stamp_matter = HybridStampMatting()
            print("  → Sẵn sàng (CPU-based, VRAM = 0MB)")
        except Exception as e:
            print(f"  → ⚠️ Lỗi: {e}")

        # ── 3. VietOCR + EasyOCR Engine ──────────────────────────────────
        if load_ocr:
            print("[3/4] Khởi tạo OCR Engine (VietOCR + EasyOCR)...")
            self.ocr_engine = VietnameseOCREngine()

        # ── 4. Ollama LLM Client (Qwen2.5-7B) ───────────────────────────
        if load_llm:
            print("[4/4] Khởi tạo Ollama LLM Client (Qwen2.5-7B)...")
            self._ensure_ollama_running()
            self.llm_client = OllamaClient()
            print(f"  → Model: {Config.OLLAMA_MODEL}")

        print("=" * 60)
        print("✅ Pipeline sẵn sàng!")
        print("=" * 60)

    # ═══════════════════════════════════════════════════════════════════
    # Stage 1: Preprocessing
    # ═══════════════════════════════════════════════════════════════════
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Tiền xử lý ảnh: deskew → denoise."""
        image = auto_deskew(image)
        image = denoise_image(image)
        return image

    # ═══════════════════════════════════════════════════════════════════
    # Stage 2: Stamp Detection + Removal
    # ═══════════════════════════════════════════════════════════════════
    def detect_and_remove_stamps(self, image: np.ndarray) -> tuple:
        """
        Phát hiện và xóa con dấu đỏ.

        Returns:
            tuple: (clean_image, stamp_bboxes)
        """
        stamp_bboxes = []

        # YOLO Detection
        if self.detector is not None:
            results = self.detector(image, conf=Config.YOLO_CONF_THRESHOLD, verbose=False)
            if len(results) > 0 and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    stamp_bboxes.append({
                        'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                        'confidence': round(conf, 4)
                    })

        # HybridStampMatting Removal (trên từng ROI)
        clean_img = image.copy()
        if self.stamp_matter is not None and stamp_bboxes:
            for stamp in stamp_bboxes:
                x1, y1, x2, y2 = stamp['x1'], stamp['y1'], stamp['x2'], stamp['y2']
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(clean_img.shape[1], x2), min(clean_img.shape[0], y2)

                roi = clean_img[y1:y2, x1:x2]
                if roi.size > 0:
                    clean_roi = self.stamp_matter.remove_stamp(roi)
                    if clean_roi is not None:
                        clean_img[y1:y2, x1:x2] = clean_roi

        return clean_img, stamp_bboxes

    # ═══════════════════════════════════════════════════════════════════
    # Stage 3: OCR
    # ═══════════════════════════════════════════════════════════════════
    def run_ocr(self, image: np.ndarray) -> str:
        """Nhận dạng text từ ảnh (VietOCR + EasyOCR)."""
        if self.ocr_engine is None or not self.ocr_engine.is_loaded:
            return ""
        result = self.ocr_engine.process_image(image)
        return result.get('text', '')

    # ═══════════════════════════════════════════════════════════════════
    # Stage 4: LLM Extraction
    # ═══════════════════════════════════════════════════════════════════
    def extract_info(self, text: str) -> dict:
        """Trích xuất thông tin từ text bằng Qwen2.5-7B."""
        if not text.strip():
            return {}

        if self.llm_client is None:
            return self._regex_extraction(text)

        result, error = self.llm_client.extract_info(text)
        if error or result is None:
            print(f"  ⚠️ LLM error: {error}, falling back to regex")
            return self._regex_extraction(text)

        if isinstance(result, dict):
            return result
        return self._regex_extraction(text)

    def _regex_extraction(self, text: str) -> dict:
        """Fallback: trích xuất bằng regex khi LLM chưa sẵn sàng."""
        result = {
            "loai_van_ban": "", "so_hieu": "", "ngay_ban_hanh": "",
            "co_quan_ban_hanh": "", "trich_yeu": "", "nguoi_ky": ""
        }

        text_lower = text.lower()
        if 'quyết định' in text_lower:
            result['loai_van_ban'] = 'Quyết định'
        elif 'công văn' in text_lower:
            result['loai_van_ban'] = 'Công văn'
        elif 'hợp đồng' in text_lower:
            result['loai_van_ban'] = 'Hợp đồng'
        elif 'tờ trình' in text_lower:
            result['loai_van_ban'] = 'Tờ trình'
        else:
            result['loai_van_ban'] = 'Khác'

        match = re.search(r'[Ss]ố[:\s]+(\d+[\/\-][A-ZĐa-zđ\d\/\-]+)', text)
        if match:
            result['so_hieu'] = match.group(1)

        match = re.search(
            r'[Nn]gày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', text
        )
        if match:
            d, m, y = match.groups()
            result['ngay_ban_hanh'] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"

        match = re.search(r'[Vv]\/[Vv][:\s]+(.+?)(?:\n|$)', text)
        if match:
            result['trich_yeu'] = match.group(1).strip()[:200]

        return result

    # ═══════════════════════════════════════════════════════════════════
    # Stage 5: Validation
    # ═══════════════════════════════════════════════════════════════════
    def validate_output(self, extracted: dict) -> dict:
        """Kiểm tra và chuẩn hóa dữ liệu đầu ra."""
        validated = dict(extracted)

        # Validate date format
        if validated.get('ngay_ban_hanh'):
            date_str = validated['ngay_ban_hanh']
            if not re.match(r'\d{2}/\d{2}/\d{4}', date_str):
                match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', date_str)
                if match:
                    d, m, y = match.groups()
                    validated['ngay_ban_hanh'] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"

        # Validate document type
        valid_types = ['Công văn', 'Hợp đồng', 'Quyết định', 'Tờ trình',
                       'Thông tư', 'Nghị định', 'Thông báo', 'Khác']
        if validated.get('loai_van_ban') not in valid_types:
            validated['loai_van_ban'] = 'Khác'

        return validated

    # ═══════════════════════════════════════════════════════════════════
    # Main Processing
    # ═══════════════════════════════════════════════════════════════════
    def process_file(self, file_path: str, save_result: bool = True) -> dict:
        """
        Xử lý 1 file PDF/Image đầu cuối.

        Args:
            file_path: Đường dẫn file
            save_result: Lưu JSON kết quả vào RESULTS_DIR

        Returns:
            dict: Kết quả trích xuất hoàn chỉnh
        """
        start_time = time.time()
        file_path = str(file_path)
        print(f"\n📄 Đang xử lý: {os.path.basename(file_path)}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.pdf':
            result = self._process_pdf(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            image = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("File ảnh bị hỏng hoặc định dạng không hỗ trợ.")
            result = self._process_single_image(image)
        else:
            raise ValueError(f"Unsupported format: {file_ext}")

        elapsed = time.time() - start_time
        result['processing_time_seconds'] = round(elapsed, 2)
        result['source_file'] = os.path.basename(file_path)
        result['processed_at'] = datetime.now().isoformat()

        print(f"  ⏱️ Thời gian: {elapsed:.2f}s")

        if save_result:
            Config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            output_name = os.path.splitext(os.path.basename(file_path))[0] + '_result.json'
            output_path = Config.RESULTS_DIR / output_name
            with open(output_path, 'w', encoding='utf-8') as f:
                # Loại bỏ processed_images trước khi lưu JSON
                save_data = {k: v for k, v in result.items() if k != 'processed_images'}
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print(f"  💾 Kết quả: {output_path}")

        return result

    def _process_pdf(self, pdf_path: str) -> dict:
        """Xử lý file PDF (multi-page)."""
        import fitz

        doc = fitz.open(pdf_path)
        pages_results = []
        all_text = []
        all_stamps = []
        processed_images = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=Config.OCR_DPI)
            img = np.frombuffer(
                pix.samples, dtype=np.uint8
            ).reshape(pix.height, pix.width, pix.n).copy()

            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif pix.n == 1:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            # Stage 1: Preprocess
            img = self.preprocess_image(img)

            # Stage 2: Stamp detect + remove
            clean_img, stamps = self.detect_and_remove_stamps(img)
            for s in stamps:
                s['page'] = page_idx + 1
            all_stamps.extend(stamps)

            # Stage 3: OCR
            text = self.run_ocr(clean_img)
            all_text.append(text)

            pages_results.append({
                'page': page_idx + 1,
                'text': text,
                'stamps': len(stamps)
            })
            processed_images.append(img)

            print(f"  📄 Trang {page_idx + 1}/{len(doc)} — "
                  f"{len(stamps)} stamps, {len(text)} chars")

        doc.close()
        full_text = '\n\n'.join(all_text)

        # Stage 4+5: LLM + Validate (gọi 1 lần cho toàn bộ)
        extracted = self.extract_info(full_text)
        validated = self.validate_output(extracted)

        return {
            'status': 'success',
            'num_pages': len(pages_results),
            'pages': pages_results,
            'total_stamps': len(all_stamps),
            'stamp_coordinates': all_stamps,
            'full_text': full_text,
            'extraction': validated,
            'processed_images': processed_images,
        }

    def _process_single_image(self, image: np.ndarray) -> dict:
        """Xử lý 1 ảnh đơn."""
        # Stage 1: Preprocess
        image = self.preprocess_image(image)

        # Stage 2: Stamp detect + remove
        clean_img, stamps = self.detect_and_remove_stamps(image)

        # Stage 3: OCR
        text = self.run_ocr(clean_img)

        # Stage 4+5: LLM + Validate
        extracted = self.extract_info(text)
        validated = self.validate_output(extracted)

        return {
            'status': 'success',
            'num_pages': 1,
            'total_stamps': len(stamps),
            'stamp_coordinates': stamps,
            'full_text': text,
            'extraction': validated,
            'processed_images': [image],
        }

    def batch_process(self, input_dir: str, limit: int = None) -> list:
        """Xử lý hàng loạt tất cả PDF/ảnh trong thư mục."""
        files = sorted([
            f for f in os.listdir(input_dir)
            if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))
        ])
        if limit:
            files = files[:limit]

        print(f"\n🔄 Batch processing {len(files)} files...")
        results = []

        for filename in files:
            file_path = os.path.join(input_dir, filename)
            try:
                result = self.process_file(file_path, save_result=True)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"  ⚠️ Error: {filename} — {e}")

        if results:
            avg_time = np.mean([r['processing_time_seconds'] for r in results])
            print(f"\n✅ Batch hoàn tất: {len(results)}/{len(files)} files")
            print(f"   Avg time/file: {avg_time:.2f}s")

        return results

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════
    def _ensure_ollama_running(self):
        """Tự động bật Ollama ngầm nếu chưa chạy."""
        def is_port_in_use(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0

        if not is_port_in_use(11434):
            print("  → Đang tự động kích hoạt Ollama...")
            try:
                import time as _time
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                )
                for _ in range(15):
                    _time.sleep(1)
                    if is_port_in_use(11434):
                        print("  → Ollama đã sẵn sàng!")
                        return
                print("  → ⚠️ Timeout khi khởi động Ollama")
            except FileNotFoundError:
                print("  → ⚠️ Chưa cài đặt Ollama (https://ollama.ai)")
        else:
            print("  → Ollama đang chạy tại port 11434")


# ═══════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    pipeline = VietIDPPipeline()

    if len(sys.argv) > 1:
        sample_path = sys.argv[1]
    else:
        sample_path = "data/raw/sample_test.jpg"

    if os.path.exists(sample_path):
        result = pipeline.process_file(sample_path)
        print("\n📝 KẾT QUẢ TRÍCH XUẤT:")
        safe_result = {k: v for k, v in result.items() if k != 'processed_images'}
        print(json.dumps(safe_result, indent=4, ensure_ascii=False))
    else:
        print(f"\n⚠️ Pipeline sẵn sàng. Để test: python -m src.pipeline.ocr_llm_pipeline <file>")
