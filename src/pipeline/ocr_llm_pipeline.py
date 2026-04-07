# -*- coding: utf-8 -*-
"""
OCR-LLM Pipeline
=================
Pipeline đầu cuối: Image → Preprocess → OCR → LLM → JSON.

Nguồn: Phase5_End_to_End_Pipeline.py
"""

import os
import re
import json
import time
import numpy as np
import cv2
from datetime import datetime

from src.config import Config
from src.preprocessing.deskew import auto_deskew
from src.preprocessing.denoise import denoise_image
from src.preprocessing.stamp_removal import StampRemover
from src.ocr.engine import VietnameseOCREngine
from src.llm.ollama_client import OllamaClient


class OCRLLMPipeline:
    """
    Pipeline đầu cuối cho xử lý văn bản hành chính Việt Nam.

    Quy trình 5 giai đoạn:
    1. Preprocessing: Deskew, denoise, stamp removal (GAN)
    2. OCR: PaddleOCR → raw text (2-tier strategy)
    3. LLM: Ollama Qwen → classification + extraction
    4. Validation: Kiểm tra format JSON
    5. Output: Structured JSON

    Tất cả model được load 1 lần và cache trong bộ nhớ.
    """

    def __init__(self, load_stamp_model=True, load_ocr=True, load_llm=True):
        print("🚀 Khởi tạo OCR-LLM Pipeline...")

        self.stamp_remover = None
        self.ocr_engine = None
        self.llm_client = None

        # 1. Load Stamp Removal GAN
        if load_stamp_model:
            self.stamp_remover = StampRemover()

        # 2. Load OCR Engine
        if load_ocr:
            self.ocr_engine = VietnameseOCREngine()

        # 3. Load LLM Client
        if load_llm:
            self.llm_client = OllamaClient()

        print("✅ Pipeline sẵn sàng!")

    # ───────────────────────────────────────────────────────────────────────
    # Stage 1: Preprocessing
    # ───────────────────────────────────────────────────────────────────────
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Tiền xử lý ảnh: deskew → denoise → stamp removal."""
        image = auto_deskew(image)
        image = denoise_image(image)
        if self.stamp_remover and self.stamp_remover.is_loaded:
            image = self.stamp_remover.remove_stamp(image)
        return image

    # ───────────────────────────────────────────────────────────────────────
    # Stage 2: OCR
    # ───────────────────────────────────────────────────────────────────────
    def run_ocr(self, image: np.ndarray) -> str:
        """Nhận dạng text từ ảnh."""
        if self.ocr_engine is None or not self.ocr_engine.is_loaded:
            return ""
        result = self.ocr_engine.process_image(image)
        return result.get('text', '')

    # ───────────────────────────────────────────────────────────────────────
    # Stage 3: LLM Extraction
    # ───────────────────────────────────────────────────────────────────────
    def extract_info(self, text: str) -> dict:
        """Trích xuất thông tin từ text bằng LLM."""
        if self.llm_client is None:
            return self._regex_extraction(text)

        result, error = self.llm_client.extract_info(text)
        if error or result is None:
            return self._regex_extraction(text)

        if isinstance(result, dict):
            return result
        return self._regex_extraction(text)

    def _regex_extraction(self, text: str) -> dict:
        """Fallback: trích xuất bằng regex khi LLM chưa sẵn sàng."""
        result = {
            "loai_van_ban": "",
            "so_hieu": "",
            "ngay_ban_hanh": "",
            "co_quan_ban_hanh": "",
            "trich_yeu": "",
            "nguoi_ky": ""
        }

        text_lower = text.lower()
        if 'quyết định' in text_lower:
            result['loai_van_ban'] = 'Quy định'
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

    # ───────────────────────────────────────────────────────────────────────
    # Stage 4: Validation
    # ───────────────────────────────────────────────────────────────────────
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
        valid_types = ['Công văn', 'Hợp đồng', 'Quy định', 'Tờ trình', 'Khác']
        if validated.get('loai_van_ban') not in valid_types:
            validated['loai_van_ban'] = 'Khác'

        return validated

    # ───────────────────────────────────────────────────────────────────────
    # Main Processing
    # ───────────────────────────────────────────────────────────────────────
    def process_file(self, file_path: str, save_result: bool = True) -> dict:
        """
        Xử lý 1 file PDF/Image đầu cuối.

        Returns:
            dict: Kết quả trích xuất
        """
        start_time = time.time()
        print(f"\n📄 Đang xử lý: {os.path.basename(file_path)}")

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.pdf':
            results = self._process_pdf(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            image = cv2.imread(file_path)
            results = self._process_single_image(image)
        else:
            print(f"  ⚠️ Unsupported format: {file_ext}")
            return {}

        elapsed = time.time() - start_time
        results['processing_time_seconds'] = round(elapsed, 2)
        results['source_file'] = os.path.basename(file_path)
        results['processed_at'] = datetime.now().isoformat()

        print(f"  ⏱️ Thời gian: {elapsed:.2f}s")

        if save_result:
            Config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            output_name = os.path.splitext(os.path.basename(file_path))[0] + '_result.json'
            output_path = Config.RESULTS_DIR / output_name
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"  💾 Kết quả: {output_path}")

        return results

    def _process_pdf(self, pdf_path: str) -> dict:
        """Xử lý file PDF."""
        import fitz

        doc = fitz.open(pdf_path)
        pages_results = []
        all_text = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=Config.OCR_DPI)
            img = np.frombuffer(
                pix.samples, dtype=np.uint8
            ).reshape(pix.height, pix.width, pix.n)

            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            else:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            img = self.preprocess_image(img)
            text = self.run_ocr(img)
            all_text.append(text)

            pages_results.append({
                'page': page_idx + 1,
                'text': text
            })
            print(f"  📄 Trang {page_idx + 1}/{len(doc)}")

        doc.close()
        full_text = '\n'.join(all_text)

        extracted = self.extract_info(full_text)
        validated = self.validate_output(extracted)

        return {
            'num_pages': len(pages_results),
            'pages': pages_results,
            'full_text': full_text,
            'extraction': validated,
        }

    def _process_single_image(self, image: np.ndarray) -> dict:
        """Xử lý 1 ảnh đơn."""
        image = self.preprocess_image(image)
        text = self.run_ocr(image)
        extracted = self.extract_info(text)
        validated = self.validate_output(extracted)

        return {
            'num_pages': 1,
            'full_text': text,
            'extraction': validated,
        }

    def batch_process(self, input_dir: str, limit: int = None) -> list:
        """Xử lý hàng loạt tất cả PDF/ảnh trong thư mục."""
        files = sorted([
            f for f in os.listdir(input_dir)
            if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))
        ])
        if limit:
            files = files[:limit]

        print(f"🔄 Batch processing {len(files)} files...")
        results = []

        for filename in files:
            file_path = os.path.join(input_dir, filename)
            try:
                result = self.process_file(file_path, save_result=True)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"  ⚠️ Error: {filename} - {e}")

        if results:
            avg_time = np.mean([r['processing_time_seconds'] for r in results])
            print(f"\n✅ Batch hoàn tất: {len(results)}/{len(files)} files")
            print(f"   Avg time/file: {avg_time:.2f}s")

        return results
