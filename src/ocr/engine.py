# -*- coding: utf-8 -*-
"""
Vietnamese OCR Engine
=====================
PaddleOCR PP-OCRv4 với hỗ trợ tiếng Việt + 2-tier strategy.

Tier 1: PyMuPDF getText() ≥ threshold → dùng text layer (nhanh)
Tier 2: PyMuPDF trả về ít text → fallback PaddleOCR-vi (xử lý scan)

Nguồn: Phase3_OCR_Engine.py
"""

import os
import tempfile
import numpy as np
import cv2

from src.ocr.postprocess import postprocess_vietnamese


class VietnameseOCREngine:
    """
    OCR Engine tối ưu cho văn bản hành chính tiếng Việt.

    Sử dụng PaddleOCR (PP-OCRv4) với các tối ưu:
    - Language: vi (Vietnamese)
    - GPU acceleration (tự động detect)
    - Text detection + Recognition pipeline
    - Post-processing: sửa lỗi ký tự tiếng Việt
    """

    def __init__(self, use_gpu=None, lang='vi'):
        """
        Khởi tạo OCR engine.

        Args:
            use_gpu: True/False/None (None = auto detect)
            lang: Ngôn ngữ OCR (default: 'vi')
        """
        self.ocr = None
        self.lang = lang

        if use_gpu is None:
            try:
                import torch
                use_gpu = torch.cuda.is_available()
            except ImportError:
                use_gpu = False

        try:
            from paddleocr import PaddleOCR
            from src.config import Config

            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                use_gpu=use_gpu,
                show_log=False,
                det_db_thresh=Config.OCR_DET_DB_THRESH,
                det_db_box_thresh=Config.OCR_DET_DB_BOX_THRESH,
                rec_batch_num=Config.OCR_REC_BATCH_NUM,
                max_text_length=100,
            )
            print("✅ PaddleOCR initialized (Vietnamese)")
        except ImportError:
            print("⚠️ PaddleOCR not installed. Run: pip install paddlepaddle paddleocr")
        except Exception as e:
            print(f"⚠️ PaddleOCR initialization error: {e}")

    def process_image(self, image_input):
        """
        OCR từ file ảnh hoặc numpy array.

        Args:
            image_input: Đường dẫn ảnh (str) hoặc numpy array (BGR)

        Returns:
            dict: {
                'text': str (toàn bộ text),
                'lines': list[dict] (từng dòng với bbox và confidence),
                'confidence': float (trung bình)
            }
        """
        if self.ocr is None:
            return {'text': '', 'lines': [], 'confidence': 0.0}

        # Nếu input là numpy array → lưu temp file
        temp_path = None
        if isinstance(image_input, np.ndarray):
            temp_path = os.path.join(tempfile.gettempdir(), "vietidp_ocr_temp.png")
            cv2.imwrite(temp_path, image_input)
            image_path = temp_path
        else:
            image_path = image_input

        try:
            result = self.ocr.ocr(image_path, cls=True)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

        if not result or not result[0]:
            return {'text': '', 'lines': [], 'confidence': 0.0}

        lines = []
        all_text = []
        confidences = []

        for line in result[0]:
            bbox = line[0]
            text = line[1][0]
            conf = line[1][1]

            # Post-processing tiếng Việt
            text = postprocess_vietnamese(text)

            lines.append({
                'bbox': bbox,
                'text': text,
                'confidence': conf
            })
            all_text.append(text)
            confidences.append(conf)

        # Sắp xếp theo vị trí Y (trên → dưới)
        lines.sort(key=lambda x: x['bbox'][0][1])

        return {
            'text': '\n'.join([l['text'] for l in lines]),
            'lines': lines,
            'confidence': float(np.mean(confidences)) if confidences else 0.0
        }

    def process_pdf(self, pdf_path, dpi=None):
        """
        OCR từ file PDF (render từng trang → OCR).

        2-tier strategy:
        - Tier 1: PyMuPDF text layer (nhanh)
        - Tier 2: PaddleOCR cho scan PDFs (chậm nhưng chính xác)

        Args:
            pdf_path: Đường dẫn file PDF
            dpi: DPI khi render (default từ config)

        Returns:
            dict với pages, full_text, num_pages, avg_confidence
        """
        import fitz  # PyMuPDF
        from src.config import Config

        if dpi is None:
            dpi = Config.OCR_DPI

        doc = fitz.open(pdf_path)
        pages = []
        all_text = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]

            # Tier 1: Thử text layer trước
            text_layer = page.get_text().strip()

            if len(text_layer) >= Config.OCR_MIN_TEXT_THRESHOLD:
                # Text layer đủ tốt → dùng luôn
                pages.append({
                    'page': page_idx + 1,
                    'text': text_layer,
                    'confidence': 1.0,
                    'method': 'text_layer'
                })
                all_text.append(text_layer)
            else:
                # Tier 2: Render → PaddleOCR
                pix = page.get_pixmap(dpi=dpi)
                img_array = np.frombuffer(
                    pix.samples, dtype=np.uint8
                ).reshape(pix.height, pix.width, pix.n)

                if pix.n == 4:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
                else:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                # OCR via PaddleOCR
                result = self.process_image(img_bgr)
                result['page'] = page_idx + 1
                result['method'] = 'paddleocr'
                pages.append(result)
                all_text.append(result['text'])

        doc.close()

        avg_conf = float(np.mean(
            [p.get('confidence', 0) for p in pages]
        )) if pages else 0.0

        return {
            'pages': pages,
            'full_text': '\n\n'.join(all_text),
            'num_pages': len(pages),
            'avg_confidence': avg_conf
        }

    def batch_process_pdfs(self, pdf_dir, output_dir, limit=None):
        """OCR hàng loạt tất cả PDF trong thư mục."""
        import json

        os.makedirs(output_dir, exist_ok=True)
        pdf_files = sorted([
            f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')
        ])
        if limit:
            pdf_files = pdf_files[:limit]

        print(f"🔍 Đang OCR {len(pdf_files)} PDFs...")
        results_summary = []

        for i, pdf_file in enumerate(pdf_files):
            pdf_path = os.path.join(pdf_dir, pdf_file)
            try:
                result = self.process_pdf(pdf_path)
                output_name = os.path.splitext(pdf_file)[0] + '_ocr.json'
                output_path = os.path.join(output_dir, output_name)

                result_clean = {
                    'source_pdf': pdf_file,
                    'num_pages': result['num_pages'],
                    'avg_confidence': result['avg_confidence'],
                    'full_text': result['full_text'],
                    'pages': [{
                        'page': p.get('page', 0),
                        'text': p.get('text', ''),
                        'confidence': float(p.get('confidence', 0)),
                        'method': p.get('method', 'unknown'),
                    } for p in result['pages']]
                }

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result_clean, f, ensure_ascii=False, indent=2)

                results_summary.append({
                    'file': pdf_file,
                    'pages': result['num_pages'],
                    'confidence': result['avg_confidence'],
                    'chars': len(result['full_text'])
                })

                if (i + 1) % 10 == 0:
                    print(f"  📄 {i+1}/{len(pdf_files)}")

            except Exception as e:
                print(f"  ⚠️ Lỗi {pdf_file}: {e}")

        if results_summary:
            avg_conf = np.mean([r['confidence'] for r in results_summary])
            total_chars = sum(r['chars'] for r in results_summary)
            print(f"\n✅ OCR hoàn tất {len(results_summary)} PDFs")
            print(f"   Avg confidence: {avg_conf:.2%}")
            print(f"   Total characters: {total_chars:,}")

        return results_summary

    @property
    def is_loaded(self) -> bool:
        return self.ocr is not None
