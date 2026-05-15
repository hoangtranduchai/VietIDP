# -*- coding: utf-8 -*-
"""
Vietnamese OCR Engine (VietOCR + EasyOCR) — v3.0
==================================================
Kiến trúc 2 tầng:
  - Tầng 1 (Text Detection): EasyOCR phát hiện vùng chữ (bounding boxes)
  - Tầng 2 (Text Recognition): VietOCR đọc chính xác tiếng Việt

v3.0: Full Coverage
  - Xử lý CẢ horizontal_list VÀ free_list (text nghiêng, bảng, biểu đồ)
  - VietOCR load config offline (tránh DNS failure)
  - EasyOCR readtext fallback khi detect+VietOCR trả ít kết quả
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

            # Thử load config — nếu DNS fail, dùng cached YAML
            try:
                config = Cfg.load_config_from_name(Config.VIETOCR_MODEL)
            except Exception as dns_err:
                print(f"  ⚠️ VietOCR config download failed: {dns_err}")
                print(f"  → Trying cached config files...")
                import tempfile, yaml
                import vietocr.tool.config as vcfg

                # Monkey-patch download_config để đọc từ cache
                _orig_download = vcfg.download_config
                def _cached_download(config_id):
                    cache_path = os.path.join(tempfile.gettempdir(), f'vietocr_{config_id}')
                    if os.path.exists(cache_path):
                        print(f"  → Loaded cached config: {cache_path}")
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            return yaml.safe_load(f)
                    # Nếu không có cache, thử download lại
                    return _orig_download(config_id)

                vcfg.download_config = _cached_download
                try:
                    config = Cfg.load_config_from_name(Config.VIETOCR_MODEL)
                except Exception:
                    # Last resort: tạo config cứng từ known-good values
                    print(f"  ⚠️ No cached config found. Creating hardcoded config...")
                    base_cfg = {
                        'vocab': 'aAàÀảẢãÃáÁạẠăĂằẰẳẲẵẴắẮặẶâÂầẦẩẨẫẪấẤậẬbBcCdDđĐeEèÈẻẺẽẼéÉẹẸêÊềỀểỂễỄếẾệỆfFgGhHiIìÌỉỈĩĨíÍịỊjJkKlLmMnNoOòÒỏỎõÕóÓọỌôÔồỒổỔỗỖốỐộỘơƠờỜởỞỡỠớỚợỢpPqQrRsStTuUùÙủỦũŨúÚụỤưƯừỪửỬữỮứỨựỰvVwWxXyYỳỲỷỶỹỸýÝỵỴzZ0123456789!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ ',
                        'device': Config.VIETOCR_DEVICE if use_gpu else 'cpu',
                        'predictor': {'beamsearch': False},
                        'dataset': {'image_height': 32, 'image_min_width': 32, 'image_max_width': 512},
                        'dataloader': {'num_workers': 0},
                        'trainer': {}, 'optimizer': {},
                        'backbone': 'vgg19_bn',
                        'cnn': {'hidden': 256, 'ks': [2, 2, 2, 2, 1], 'ss': [[2, 2], [2, 2], [2, 1], [2, 1], [1, 1]]},
                        'transformer': {
                            'd_model': 256, 'nhead': 8,
                            'num_encoder_layers': 6, 'num_decoder_layers': 6,
                            'dim_feedforward': 2048, 'max_seq_length': 1024,
                            'pos_dropout': 0.1, 'trans_dropout': 0.1,
                        },
                        'seq_modeling': 'transformer', 'weights': '',
                    }
                    config = Cfg(base_cfg)
                finally:
                    vcfg.download_config = _orig_download  # Restore

            config['device'] = Config.VIETOCR_DEVICE if use_gpu else 'cpu'

            # Kiểm tra model weight đã có trong temp
            import tempfile
            weight_path = os.path.join(tempfile.gettempdir(), 'vgg_transformer.pth')
            if os.path.exists(weight_path):
                config['weights'] = weight_path
                print(f"  → Found cached weights: {weight_path}")

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
        Nếu VietOCR không có, fallback sang EasyOCR readtext.

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

            # ── Xử lý horizontal bounding boxes ──
            h_bboxes = horizontal_list[0] if horizontal_list and len(horizontal_list[0]) > 0 else []

            for box in h_bboxes:
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

            # ── Xử lý free-form bounding boxes (text nghiêng, bảng...) ──
            f_bboxes = free_list[0] if free_list and len(free_list[0]) > 0 else []

            for poly in f_bboxes:
                # Free-form bbox là polygon [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                try:
                    pts = np.array(poly, dtype=np.float32)
                    x_min = max(0, int(pts[:, 0].min()))
                    y_min = max(0, int(pts[:, 1].min()))
                    x_max = min(image_bgr.shape[1], int(pts[:, 0].max()))
                    y_max = min(image_bgr.shape[0], int(pts[:, 1].max()))

                    if x_max <= x_min or y_max <= y_min:
                        continue

                    crop_bgr = image_bgr[y_min:y_max, x_min:x_max]
                    crop_pil = Image.fromarray(cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB))

                    text = self.vietocr_predictor.predict(crop_pil)
                    if text:
                        text = postprocess_vietnamese(text)
                        lines.append({
                            'bbox': [[x_min, y_min], [x_max, y_min],
                                     [x_max, y_max], [x_min, y_max]],
                            'text': text,
                            'confidence': 0.90,
                            'type': 'free_form'
                        })
                except Exception:
                    continue

            # ── Fallback: nếu detect+VietOCR trả quá ít, bổ sung bằng EasyOCR readtext ──
            if len(lines) < 3:
                easyocr_result = self._fallback_easyocr(image_bgr)
                if easyocr_result and len(easyocr_result.get('lines', [])) > len(lines):
                    return easyocr_result

            # Sắp xếp lines: group theo row (y gần nhau), sort trái→phải trong row
            if lines:
                # Tính chiều cao trung bình của các bbox
                heights = []
                for l in lines:
                    bb = l['bbox']
                    if bb and len(bb) >= 4:
                        h = abs(bb[2][1] - bb[0][1])
                        if h > 0:
                            heights.append(h)
                avg_height = np.mean(heights) if heights else 30

                # Sort theo y trước
                lines.sort(key=lambda x: x['bbox'][0][1] if x['bbox'] else 0)

                # Group lines thành rows: nếu y_center chênh < 50% avg_height → cùng row
                rows = []
                current_row = [lines[0]]
                for i in range(1, len(lines)):
                    prev_y = (current_row[-1]['bbox'][0][1] + current_row[-1]['bbox'][2][1]) / 2
                    curr_y = (lines[i]['bbox'][0][1] + lines[i]['bbox'][2][1]) / 2
                    if abs(curr_y - prev_y) < avg_height * 0.5:
                        current_row.append(lines[i])
                    else:
                        rows.append(current_row)
                        current_row = [lines[i]]
                rows.append(current_row)

                # Sort từng row theo x (trái → phải), rồi flatten
                sorted_lines = []
                for row in rows:
                    row.sort(key=lambda x: x['bbox'][0][0] if x['bbox'] else 0)
                    sorted_lines.extend(row)
                lines = sorted_lines

            full_text = '\n'.join([l['text'] for l in lines])
            avg_conf = float(np.mean([l['confidence'] for l in lines])) if lines else 0.0

            return {
                'text': full_text,
                'lines': lines,
                'confidence': avg_conf
            }

        except Exception as e:
            print(f"⚠️ OCR error: {e}")
            # Fallback sang EasyOCR readtext khi lỗi
            return self._fallback_easyocr(image_bgr)

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

            # Row-grouped sort (same as main path)
            if lines:
                heights = []
                for l in lines:
                    bb = l['bbox']
                    if bb and len(bb) >= 4:
                        h = abs(bb[2][1] - bb[0][1])
                        if h > 0:
                            heights.append(h)
                avg_height = np.mean(heights) if heights else 30

                lines.sort(key=lambda x: x['bbox'][0][1] if x['bbox'] else 0)

                rows = []
                current_row = [lines[0]]
                for i in range(1, len(lines)):
                    prev_y = (current_row[-1]['bbox'][0][1] + current_row[-1]['bbox'][2][1]) / 2
                    curr_y = (lines[i]['bbox'][0][1] + lines[i]['bbox'][2][1]) / 2
                    if abs(curr_y - prev_y) < avg_height * 0.5:
                        current_row.append(lines[i])
                    else:
                        rows.append(current_row)
                        current_row = [lines[i]]
                rows.append(current_row)

                sorted_lines = []
                for row in rows:
                    row.sort(key=lambda x: x['bbox'][0][0] if x['bbox'] else 0)
                    sorted_lines.extend(row)
                lines = sorted_lines

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
        OCR từ file PDF — LUÔN render ảnh và chạy OCR full.

        Chiến lược: Render TẤT CẢ trang ở DPI cao → OCR.
        KHÔNG dùng text layer vì text layer có thể sai/thiếu.

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

            # Luôn render → OCR (không dùng text layer)
            pix = page.get_pixmap(dpi=dpi)
            img_array = np.frombuffer(
                pix.samples, dtype=np.uint8
            ).reshape(pix.height, pix.width, pix.n).copy()

            if pix.n == 4:
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            elif pix.n == 1:
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
            else:
                img_bgr = img_array

            result = self.process_image(img_bgr)
            result['page'] = page_idx + 1
            result['method'] = 'ocr_full'
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
