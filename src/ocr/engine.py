# -*- coding: utf-8 -*-
"""
Vietnamese OCR Engine (VietOCR + EasyOCR)
==========================================
Kiến trúc 2 tầng:
  - Tầng 1 (Text Detection): EasyOCR phát hiện vùng chữ (bounding boxes)
  - Tầng 2 (Text Recognition): VietOCR đọc chính xác tiếng Việt

Chiến lược PDF 2-tier:
  - Tier 1: PyMuPDF getText() ≥ threshold → dùng text layer (nhanh)
  - Tier 2: Text layer ít → render ảnh → OCR (chính xác cho scan)
"""

import os
import numpy as np
import cv2
from PIL import Image

from src.ocr.postprocess import postprocess_vietnamese
from src.config import Config


class VietnameseOCREngine:
    """
    OCR Engine tối ưu cho văn bản hành chính tiếng Việt.

    Sử dụng VietOCR (vgg_transformer) làm recognizer chính,
    kết hợp EasyOCR làm text line detector.
    """

    def __init__(self, use_gpu=None):
        """
        Khởi tạo OCR engine: EasyOCR (detector) + VietOCR (recognizer).

        Args:
            use_gpu: True/False/None (None = auto detect)
        """
        self.text_detector = None
        self.vietocr_predictor = None

        if use_gpu is None:
            try:
                import torch
                use_gpu = torch.cuda.is_available()
            except ImportError:
                use_gpu = False

        # ── Tầng 1: EasyOCR Text Detector ────────────────────────────────
        try:
            import easyocr
            self.text_detector = easyocr.Reader(
                Config.EASYOCR_LANGS,
                gpu=use_gpu and Config.EASYOCR_GPU,
                verbose=False
            )
            print("✅ EasyOCR Text Detector initialized (Vietnamese)")
        except ImportError:
            print("⚠️ EasyOCR not installed. Run: pip install easyocr")
        except Exception as e:
            print(f"⚠️ EasyOCR init error: {e}")

        # ── Tầng 2: VietOCR Text Recognizer ──────────────────────────────
        try:
            from vietocr.tool.predictor import Predictor
            from vietocr.tool.config import Cfg

            config = Cfg.load_config_from_name(Config.VIETOCR_MODEL)
            config['device'] = Config.VIETOCR_DEVICE if use_gpu else 'cpu'
            self.vietocr_predictor = Predictor(config)
            print(f"✅ VietOCR Recognizer initialized ({Config.VIETOCR_MODEL})")
        except ImportError:
            print("⚠️ VietOCR not installed. Run: pip install vietocr")
        except Exception as e:
            print(f"⚠️ VietOCR init error: {e}")

    def process_image(self, image_input) -> dict:
        """
        OCR từ numpy array (BGR) hoặc file path.

        Pipeline: EasyOCR detect → crop → VietOCR recognize → postprocess

        Args:
            image_input: Đường dẫn ảnh (str) hoặc numpy array (BGR)

        Returns:
            dict: {
                'text': str (toàn bộ text),
                'lines': list[dict] (từng dòng với bbox và confidence),
                'confidence': float (trung bình)
            }
        """
        # Load ảnh nếu là đường dẫn
        if isinstance(image_input, str):
            image_bgr = cv2.imread(image_input)
            if image_bgr is None:
                return {'text': '', 'lines': [], 'confidence': 0.0}
        else:
            image_bgr = image_input

        if image_bgr is None or image_bgr.size == 0:
            return {'text': '', 'lines': [], 'confidence': 0.0}

        # Nếu chưa có VietOCR, fallback toàn bộ sang EasyOCR
        if self.vietocr_predictor is None:
            return self._fallback_easyocr(image_bgr)

        # Nếu chưa có EasyOCR detector, fallback
        if self.text_detector is None:
            return {'text': '', 'lines': [], 'confidence': 0.0}

        try:
            lines = []

            # ── Tầng 1: EasyOCR phát hiện vùng chữ ──────────────────────
            horizontal_list, free_list = self.text_detector.detect(image_bgr)

            if not horizontal_list or len(horizontal_list[0]) == 0:
                return {'text': '', 'lines': [], 'confidence': 0.0}

            bboxes = horizontal_list[0]
            # Sắp xếp từ trên xuống dưới (theo y trung bình)
            bboxes.sort(key=lambda b: (b[2] + b[3]) / 2)

            # ── Tầng 2: VietOCR đọc từng dòng ───────────────────────────
            for box in bboxes:
                x_min, x_max, y_min, y_max = map(int, box)

                # Clamp tọa độ
                x_min = max(0, x_min)
                y_min = max(0, y_min)
                x_max = min(image_bgr.shape[1], x_max)
                y_max = min(image_bgr.shape[0], y_max)

                if x_max <= x_min or y_max <= y_min:
                    continue

                # Crop và chuyển sang PIL (VietOCR yêu cầu PIL RGB)
                crop_bgr = image_bgr[y_min:y_max, x_min:x_max]
                crop_pil = Image.fromarray(cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB))

                # VietOCR predict
                text = self.vietocr_predictor.predict(crop_pil)
                if text:
                    text = postprocess_vietnamese(text)
                    lines.append({
                        'bbox': [[x_min, y_min], [x_max, y_min],
                                 [x_max, y_max], [x_min, y_max]],
                        'text': text,
                        'confidence': 0.95,  # VietOCR không trả confidence
                        'type': 'text'
                    })

            full_text = '\n'.join([l['text'] for l in lines])
            avg_conf = float(np.mean([l['confidence'] for l in lines])) if lines else 0.0

            return {
                'text': full_text,
                'lines': lines,
                'confidence': avg_conf
            }

        except Exception as e:
            print(f"⚠️ OCR error: {e}")
            return {'text': '', 'lines': [], 'confidence': 0.0}

    def _fallback_easyocr(self, image_bgr) -> dict:
        """Fallback: dùng EasyOCR cả detect lẫn recognize nếu VietOCR chưa cài."""
        if self.text_detector is None:
            return {'text': '', 'lines': [], 'confidence': 0.0}

        try:
            result = self.text_detector.readtext(image_bgr, detail=1, paragraph=False)
            lines = []
            confidences = []

            for (bbox, text, conf) in result:
                text = postprocess_vietnamese(text)
                lines.append({'bbox': bbox, 'text': text, 'confidence': conf, 'type': 'text'})
                confidences.append(conf)

            lines.sort(key=lambda x: x['bbox'][0][1] if x['bbox'] else 0)

            return {
                'text': '\n'.join([l['text'] for l in lines]),
                'lines': lines,
                'confidence': float(np.mean(confidences)) if confidences else 0.0
            }
        except Exception as e:
            print(f"⚠️ EasyOCR fallback error: {e}")
            return {'text': '', 'lines': [], 'confidence': 0.0}

    def process_pdf(self, pdf_path, dpi=None):
        """
        OCR từ file PDF (2-tier strategy).

        Tier 1: PyMuPDF text layer (nhanh)
        Tier 2: Render → VietOCR+EasyOCR (chính xác cho scan)

        Args:
            pdf_path: Đường dẫn file PDF
            dpi: DPI khi render (default từ config)

        Returns:
            dict với pages, full_text, num_pages, avg_confidence
        """
        import fitz  # PyMuPDF

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
                pages.append({
                    'page': page_idx + 1,
                    'text': text_layer,
                    'confidence': 1.0,
                    'method': 'text_layer'
                })
                all_text.append(text_layer)
            else:
                # Tier 2: Render → OCR
                pix = page.get_pixmap(dpi=dpi)
                img_array = np.frombuffer(
                    pix.samples, dtype=np.uint8
                ).reshape(pix.height, pix.width, pix.n)

                if pix.n == 4:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
                else:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                result = self.process_image(img_bgr)
                result['page'] = page_idx + 1
                result['method'] = 'vietocr'
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

    @property
    def is_loaded(self) -> bool:
        """True nếu ít nhất 1 engine OCR sẵn sàng."""
        return self.text_detector is not None or self.vietocr_predictor is not None
