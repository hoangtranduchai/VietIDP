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
            → Layout Region Classification (NĐ 30/2020)
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
from src.llm.qlora_engine import QLoRAEngine
from src.pipeline.layout_regions import LayoutRegionClassifier


class VietIDPPipeline:
    """
    Pipeline đầu cuối cho xử lý văn bản hành chính Việt Nam.

    Quy trình 6 giai đoạn:
    1. Preprocessing: Deskew → Denoise
    2. Stamp Detection (YOLOv8l) → Stamp Removal (HybridStampMatting)
    3. OCR: EasyOCR detect + VietOCR recognize → raw text
    4. Layout Classification: Phân loại dòng OCR theo 14 ô số NĐ 30/2020
    5. LLM: QLoRA (GPU) hoặc Ollama → classification + extraction
    6. Validation: Kiểm tra format JSON → Structured Output

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
        self.layout_classifier = LayoutRegionClassifier()

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

        # ── 4. LLM Engine (QLoRA GPU hoặc Ollama) ─────────────────────────
        if load_llm:
            if Config.LLM_BACKEND == "qlora":
                print("[4/4] Khởi tạo QLoRA Engine (Qwen2.5-3B GPU)...")
                qlora = QLoRAEngine()
                qlora.load()
                if qlora.is_loaded:
                    self.llm_client = qlora
                else:
                    print("  → Fallback sang Ollama...")
                    self._ensure_ollama_running()
                    self.llm_client = OllamaClient()
                    print(f"  → Model: {Config.OLLAMA_MODEL}")
            else:
                print("[4/4] Khởi tạo Ollama LLM Client...")
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
            tuple: (clean_image, stamp_bboxes, detection_viz)
                   detection_viz: ảnh vẽ bounding box lên stamp (để giám sát)
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

        # Tạo ảnh giám sát Stage 1: vẽ bounding box lên stamp
        detection_viz = image.copy()
        for stamp in stamp_bboxes:
            x1, y1 = stamp['x1'], stamp['y1']
            x2, y2 = stamp['x2'], stamp['y2']
            cv2.rectangle(detection_viz, (x1, y1), (x2, y2), (0, 0, 255), 3)
            label = f"Stamp {stamp['confidence']:.2f}"
            cv2.putText(detection_viz, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

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

        return clean_img, stamp_bboxes, detection_viz

    # ═══════════════════════════════════════════════════════════════════
    # Stage 3: OCR
    # ═══════════════════════════════════════════════════════════════════
    def run_ocr(self, image: np.ndarray) -> tuple:
        """Nhận dạng text từ ảnh (VietOCR + EasyOCR)."""
        if self.ocr_engine is None or not self.ocr_engine.is_loaded:
            return "", []
        result = self.ocr_engine.process_image(image)
        return result.get('text', ''), result.get('lines', [])

    # ═══════════════════════════════════════════════════════════════════
    # Stage 4: LLM Extraction
    # ═══════════════════════════════════════════════════════════════════
    def extract_info(self, text: str) -> tuple:
        """Trích xuất thông tin từ text bằng Qwen2.5-7B."""
        if not text.strip():
            return {}, {}

        if self.llm_client is None:
            return self._regex_extraction(text), {}

        result, error = self.llm_client.extract_info(text)
        if error or result is None:
            print(f"  ⚠️ LLM error: {error}, falling back to regex")
            return self._regex_extraction(text), {"error": error}

        if isinstance(result, dict):
            return self._normalize_extraction_schema(result), result
        return self._regex_extraction(text), {"raw": result}

    def _normalize_extraction_schema(self, raw: dict) -> dict:
        """
        Chuẩn hóa kết quả LLM về đúng 6 trường NĐ30.
        Xử lý 3 trường hợp LLM trả sai:
        1. JSON lồng nhau: {người_ký: {tên: "X"}} → nguoi_ky: "X"
        2. Keys tiếng Việt có dấu: loại, số, ngày → loai_van_ban, so_hieu...
        3. List values: ["item1", "item2"] → "item1, item2"
        """
        # ─── Bước 1: Flatten JSON nested → dict phẳng ──────────────────
        flat = {}
        def _flatten(obj, prefix=''):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_key = f"{prefix}.{k}" if prefix else k
                    if isinstance(v, dict):
                        _flatten(v, new_key)
                    elif isinstance(v, list):
                        # List of strings → join
                        str_items = [str(i) for i in v if isinstance(i, (str, int, float))]
                        if str_items:
                            flat[new_key] = ', '.join(str_items)
                        # List of dicts → flatten each
                        for i, item in enumerate(v):
                            if isinstance(item, dict):
                                _flatten(item, f"{new_key}.{i}")
                    else:
                        flat[new_key] = v
        _flatten(raw)

        # ─── Bước 2: Bảng ánh xạ mở rộng (gồm nested keys + Vietnamese diacritics) ──
        FIELD_ALIASES = {
            # === loai_van_ban ===
            'loai_van_ban': 'loai_van_ban',
            'loai': 'loai_van_ban',
            'loại': 'loai_van_ban',
            'loại_văn_bản': 'loai_van_ban',
            'bản.loại': 'loai_van_ban',
            'type': 'loai_van_ban',
            'document_type': 'loai_van_ban',
            # === so_hieu ===
            'so_hieu': 'so_hieu',
            'so': 'so_hieu',
            'số': 'so_hieu',
            'số_hiệu': 'so_hieu',
            'bản.số': 'so_hieu',
            'number': 'so_hieu',
            'ma_so': 'so_hieu',
            # === ngay_ban_hanh ===
            'ngay_ban_hanh': 'ngay_ban_hanh',
            'ngay_cap': 'ngay_ban_hanh',
            'ngay_ky': 'ngay_ban_hanh',
            'ngay': 'ngay_ban_hanh',
            'ngày': 'ngay_ban_hanh',
            'ngày_ban_hành': 'ngay_ban_hanh',
            'bản.ngày': 'ngay_ban_hanh',
            'date': 'ngay_ban_hanh',
            'ngay_thang': 'ngay_ban_hanh',
            # === co_quan_ban_hanh ===
            'co_quan_ban_hanh': 'co_quan_ban_hanh',
            'noi_cap': 'co_quan_ban_hanh',
            'co_quan': 'co_quan_ban_hanh',
            'cơ_quan': 'co_quan_ban_hanh',
            'cơ_quan_ban_hành': 'co_quan_ban_hanh',
            'don_vi': 'co_quan_ban_hanh',
            'to_chuc': 'co_quan_ban_hanh',
            'issuing_authority': 'co_quan_ban_hanh',
            'organization': 'co_quan_ban_hanh',
            # === trich_yeu ===
            'trich_yeu': 'trich_yeu',
            'noi_dung': 'trich_yeu',
            'nội_dung': 'trich_yeu',
            'trích_yếu': 'trich_yeu',
            'tieu_de': 'trich_yeu',
            'tiêu_đề': 'trich_yeu',
            'mo_ta': 'trich_yeu',
            'subject': 'trich_yeu',
            'summary': 'trich_yeu',
            'content': 'trich_yeu',
            'bản.nội_dung': 'trich_yeu',
            # === nguoi_ky ===
            'nguoi_ky': 'nguoi_ky',
            'nguoi_ky_ten': 'nguoi_ky',
            'người_ký': 'nguoi_ky',
            'người_ký.tên': 'nguoi_ky',
            'người_ký.họ_tên': 'nguoi_ky',
            'signer': 'nguoi_ky',
            'ten_nguoi_ky': 'nguoi_ky',
            'signed_by': 'nguoi_ky',
        }

        REQUIRED_FIELDS = [
            'loai_van_ban', 'so_hieu', 'ngay_ban_hanh',
            'co_quan_ban_hanh', 'trich_yeu', 'nguoi_ky'
        ]

        normalized = {}

        # ─── Bước 3: Map flat keys → canonical fields ──────────────────
        for key, value in flat.items():
            if value is None or str(value).strip() == '':
                continue
            val_str = str(value).strip()

            # Exact match
            canonical = FIELD_ALIASES.get(key)

            # Nếu không exact match, thử fuzzy match (key chứa từ khóa)
            if not canonical:
                key_lower = key.lower().replace(' ', '_')
                canonical = FIELD_ALIASES.get(key_lower)

            # Nếu vẫn không, thử match phần cuối key (cho nested)
            if not canonical:
                parts = key.split('.')
                for part in reversed(parts):
                    canonical = FIELD_ALIASES.get(part)
                    if canonical:
                        break

            if canonical:
                # Ghi đè nếu chưa có hoặc giá trị mới dài hơn
                if canonical not in normalized or (
                    len(val_str) > len(str(normalized.get(canonical, '')))
                ):
                    normalized[canonical] = val_str

        # ─── Bước 4: Đảm bảo đủ 6 trường bắt buộc ────────────────────
        for field in REQUIRED_FIELDS:
            if field not in normalized:
                normalized[field] = ''

        # ─── Bước 5: Chuẩn hóa giá trị ───────────────────────────────
        # so_hieu: loại bỏ khoảng trắng thừa
        if normalized.get('so_hieu'):
            normalized['so_hieu'] = re.sub(r'\s+', '', normalized['so_hieu'])

        # ngay_ban_hanh: chuyển YYYY-MM-DD → DD/MM/YYYY
        if normalized.get('ngay_ban_hanh'):
            date_str = normalized['ngay_ban_hanh']
            iso_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
            if iso_match:
                y, m, d = iso_match.groups()
                normalized['ngay_ban_hanh'] = f"{d}/{m}/{y}"

        # Chỉ giữ lại 6 trường bắt buộc (loại bỏ trường thừa)
        return {k: normalized[k] for k in REQUIRED_FIELDS}

    # All 29 NĐ30 administrative types + 5 QPPL types
    VALID_DOCUMENT_TYPES = [
        # 29 loại theo NĐ 30/2020/NĐ-CP
        'Quyết định', 'Nghị quyết', 'Chỉ thị', 'Quy chế', 'Quy định',
        'Thông báo', 'Hướng dẫn', 'Chương trình', 'Kế hoạch', 'Phương án',
        'Đề án', 'Dự án', 'Báo cáo', 'Biên bản', 'Tờ trình',
        'Hợp đồng', 'Công văn', 'Công điện', 'Giấy mời', 'Giấy giới thiệu',
        'Giấy ủy quyền', 'Giấy nghỉ phép', 'Phiếu gửi', 'Phiếu chuyển',
        'Phiếu báo', 'Thư công', 'Bản ghi nhớ', 'Bản thỏa thuận', 'Giấy biên nhận',
        # Văn bản QPPL
        'Luật', 'Nghị định', 'Thông tư', 'Pháp lệnh', 'Lệnh',
        # Fallback
        'Khác',
    ]

    # Mapping UPPER CASE → Title Case cho loai_van_ban
    _LOAI_VB_UPPER_MAP = {
        t.upper(): t for t in VALID_DOCUMENT_TYPES if t != 'Khác'
    }

    # Mapping cho co_quan_ban_hanh (UPPER → mixed case)
    _CO_QUAN_DIRECT_MAP = {
        'THỦ TƯỚNG CHÍNH PHỦ': 'Thủ tướng Chính phủ',
        'CHÍNH PHỦ': 'Chính phủ',
        'VĂN PHÒNG CHÍNH PHỦ': 'Văn phòng Chính phủ',
        'VĂN PHÒNG QUỐC HỘI': 'Văn phòng Quốc hội',
        'QUỐC HỘI': 'Quốc hội',
        'NGÂN HÀNG NHÀ NƯỚC VIỆT NAM': 'Ngân hàng Nhà nước Việt Nam',
        'NGÂN HÀNG NHÀ NƯỚC': 'Ngân hàng Nhà nước Việt Nam',
        'KIỂM TOÁN NHÀ NƯỚC': 'Kiểm toán Nhà nước',
        'THANH TRA CHÍNH PHỦ': 'Thanh tra Chính phủ',
        'VIỆN KIỂM SÁT NHÂN DÂN TỐI CAO': 'Viện kiểm sát nhân dân tối cao',
        'TÒA ÁN NHÂN DÂN TỐI CAO': 'Tòa án nhân dân tối cao',
    }

    def _normalize_loai_van_ban(self, loai: str) -> str:
        """Chuẩn hóa loai_van_ban: UPPER CASE → Title Case, case-insensitive match."""
        if not loai or not loai.strip():
            return 'Khác'
        loai = loai.strip()

        # Exact match
        if loai in self.VALID_DOCUMENT_TYPES:
            return loai

        # UPPER CASE match
        upper = loai.upper()
        if upper in self._LOAI_VB_UPPER_MAP:
            return self._LOAI_VB_UPPER_MAP[upper]

        # Case-insensitive fuzzy match
        loai_lower = loai.lower()
        for valid_type in self.VALID_DOCUMENT_TYPES:
            if loai_lower == valid_type.lower():
                return valid_type

        return 'Khác'

    def _normalize_co_quan(self, name: str) -> str:
        """Chuẩn hóa co_quan_ban_hanh: UPPER CASE → mixed case."""
        if not name or not name.strip():
            return name
        name = name.strip()

        # Check direct mapping first
        name_upper = name.upper()
        if name_upper in self._CO_QUAN_DIRECT_MAP:
            return self._CO_QUAN_DIRECT_MAP[name_upper]

        # Check if already mixed case (not all upper)
        alpha_chars = [c for c in name if c.isalpha()]
        if alpha_chars:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if upper_ratio < 0.7:
                # Already mixed case, just normalize tỉnh/thành phố casing
                name = re.sub(r'\bTỉnh\b', 'tỉnh', name)
                name = re.sub(r'\bThành Phố\b', 'thành phố', name, flags=re.IGNORECASE)
                name = re.sub(r'\bThành phố\b', 'thành phố', name)
                return name

        # Full UPPER CASE → convert to proper case
        # Handle prefix "CHỦ TỊCH"
        prefix = ''
        if name_upper.startswith('CHỦ TỊCH '):
            prefix = 'Chủ tịch '
            name = name[len('CHỦ TỊCH '):]
            name_upper = name.upper()

        # Check direct mapping again after prefix removal
        if name_upper in self._CO_QUAN_DIRECT_MAP:
            return prefix + self._CO_QUAN_DIRECT_MAP[name_upper]

        result = name

        # BỘ ...
        bo_match = re.match(r'^BỘ\s+(.+)$', name, re.IGNORECASE)
        if bo_match:
            rest = bo_match.group(1)
            # Capitalize first word of ministry name
            words = rest.lower().split()
            if words:
                words[0] = words[0].capitalize()
            result = 'Bộ ' + ' '.join(words)
            return prefix + result

        # ỦY BAN NHÂN DÂN ...
        ubnd_match = re.match(r'^ỦY\s*BAN\s*NHÂN\s*DÂN\s+(.+)$', name, re.IGNORECASE)
        if ubnd_match:
            rest = ubnd_match.group(1).strip()
            # tỉnh/thành phố + tên riêng
            loc_match = re.match(r'^(TỈNH|THÀNH\s*PHỐ|HUYỆN|QUẬN|THỊ\s*XÃ|XÃ|PHƯỜNG|THỊ\s*TRẤN)\s+(.+)$', rest, re.IGNORECASE)
            if loc_match:
                admin_raw = loc_match.group(1).lower().strip()
                admin_map = {'tỉnh': 'tỉnh', 'huyện': 'huyện', 'quận': 'quận',
                             'xã': 'xã', 'phường': 'phường'}
                if 'thành' in admin_raw and 'phố' in admin_raw:
                    admin_unit = 'thành phố'
                elif 'thị' in admin_raw and 'xã' in admin_raw:
                    admin_unit = 'thị xã'
                elif 'thị' in admin_raw and 'trấn' in admin_raw:
                    admin_unit = 'thị trấn'
                else:
                    admin_unit = admin_map.get(admin_raw, admin_raw)
                place_words = loc_match.group(2).lower().split()
                place_name = ' '.join(w.capitalize() for w in place_words)
                result = f'Ủy ban nhân dân {admin_unit} {place_name}'
            else:
                result = 'Ủy ban nhân dân ' + rest.lower().capitalize()
            return prefix + result

        # HỘI ĐỒNG NHÂN DÂN ...
        hdnd_match = re.match(r'^HỘI\s*ĐỒNG\s*NHÂN\s*DÂN\s+(.+)$', name, re.IGNORECASE)
        if hdnd_match:
            rest = hdnd_match.group(1).strip()
            loc_match = re.match(r'^(TỈNH|THÀNH\s*PHỐ)\s+(.+)$', rest, re.IGNORECASE)
            if loc_match:
                admin_unit = 'thành phố' if 'thành' in loc_match.group(1).lower() else 'tỉnh'
                place_words = loc_match.group(2).lower().split()
                place_name = ' '.join(w.capitalize() for w in place_words)
                result = f'Hội đồng nhân dân {admin_unit} {place_name}'
            else:
                result = 'Hội đồng nhân dân ' + rest.lower().capitalize()
            return prefix + result

        # SỞ ...
        so_match = re.match(r'^SỞ\s+(.+)$', name, re.IGNORECASE)
        if so_match:
            rest_words = so_match.group(1).lower().split()
            if rest_words:
                rest_words[0] = rest_words[0].capitalize()
            return prefix + 'Sở ' + ' '.join(rest_words)

        # TỔNG CỤC ...
        tc_match = re.match(r'^TỔNG\s*CỤC\s+(.+)$', name, re.IGNORECASE)
        if tc_match:
            rest_words = tc_match.group(1).lower().split()
            if rest_words:
                rest_words[0] = rest_words[0].capitalize()
            return prefix + 'Tổng cục ' + ' '.join(rest_words)

        # CỤC ...
        cuc_match = re.match(r'^CỤC\s+(.+)$', name, re.IGNORECASE)
        if cuc_match:
            rest_words = cuc_match.group(1).lower().split()
            if rest_words:
                rest_words[0] = rest_words[0].capitalize()
            return prefix + 'Cục ' + ' '.join(rest_words)

        # Generic: just lowercase then capitalize first letter
        result = name.lower()
        if result:
            result = result[0].upper() + result[1:]
        return prefix + result

    def _regex_extraction(self, text: str) -> dict:
        """Fallback: trích xuất bằng regex khi LLM chưa sẵn sàng."""
        result = {
            "loai_van_ban": "", "so_hieu": "", "ngay_ban_hanh": "",
            "co_quan_ban_hanh": "", "trich_yeu": "", "nguoi_ky": ""
        }

        text_lower = text.lower()
        # Check against all valid types
        type_patterns = [
            ('quyết định', 'Quyết định'),
            ('nghị quyết', 'Nghị quyết'),
            ('chỉ thị', 'Chỉ thị'),
            ('nghị định', 'Nghị định'),
            ('thông tư', 'Thông tư'),
            ('thông báo', 'Thông báo'),
            ('công văn', 'Công văn'),
            ('công điện', 'Công điện'),
            ('luật', 'Luật'),
            ('hợp đồng', 'Hợp đồng'),
            ('tờ trình', 'Tờ trình'),
            ('báo cáo', 'Báo cáo'),
            ('biên bản', 'Biên bản'),
            ('kế hoạch', 'Kế hoạch'),
        ]
        for pattern, type_name in type_patterns:
            if pattern in text_lower:
                result['loai_van_ban'] = type_name
                break
        if not result['loai_van_ban']:
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
    # Stage 4.5: Layout Enrichment
    # ═══════════════════════════════════════════════════════════════════
    def _enrich_from_layout(self, extracted: dict, layout_fields: dict) -> dict:
        """
        Bổ sung dữ liệu từ layout_fields khi LLM trả thiếu.
        Layout classifier đọc trực tiếp từ OCR text theo vùng không gian,
        nên có trich_yeu đầy đủ hơn LLM (vốn dễ bị truncate).
        """
        if not layout_fields:
            return extracted

        enriched = dict(extracted)

        # ── trich_yeu: lấy từ ten_loai_text nếu LLM trả ngắn hơn ──
        ten_loai = layout_fields.get('ten_loai_text', '')
        if ten_loai:
            # Loại bỏ dòng đầu (tên loại VB) để lấy phần trích yếu
            lines = ten_loai.strip().split('\n')
            if len(lines) > 1:
                # Dòng đầu thường là "QUYẾT ĐỊNH", "THÔNG BÁO" → bỏ
                trich_yeu_from_layout = ' '.join(
                    line.strip() for line in lines[1:] if line.strip()
                )
                # Apply OCR post-correction (layout text chưa qua correction)
                trich_yeu_from_layout = self._ocr_post_correct(trich_yeu_from_layout)
                # Dùng layout nếu dài hơn LLM
                llm_trich_yeu = enriched.get('trich_yeu', '')
                if len(trich_yeu_from_layout) > len(llm_trich_yeu):
                    enriched['trich_yeu'] = trich_yeu_from_layout

        # ── co_quan_ban_hanh: lấy từ co_quan_text nếu LLM thiếu ──
        co_quan = layout_fields.get('co_quan_text', '')
        if co_quan and not enriched.get('co_quan_ban_hanh'):
            # Lấy phần đầu (bỏ số hiệu nếu nằm cùng vùng)
            co_quan_lines = co_quan.strip().split('\n')
            co_quan_name = ' '.join(
                line.strip() for line in co_quan_lines
                if not re.match(r'^\d+[\\/]', line.strip())  # bỏ dòng số hiệu
            )
            if co_quan_name:
                enriched['co_quan_ban_hanh'] = co_quan_name

        return enriched

    def _enrich_from_fulltext(self, extracted: dict, full_text: str) -> dict:
        """
        Regex enrichment: bổ sung so_hieu, ngay_ban_hanh, nguoi_ky, loai_van_ban, co_quan
        trực tiếp từ full_text khi LLM trả rỗng hoặc sai.
        """
        enriched = dict(extracted)
        corrected_text = self._ocr_post_correct(full_text)

        # ── so_hieu: regex mở rộng cho nhiều pattern ──
        if not enriched.get('so_hieu'):
            # Pattern 1: Số: XX/YYYY/QĐ-XX (có năm)
            match = re.search(
                r'[Ss]ố[:\s]+(\d+[\\/]\d{4}[\\/][A-ZĐa-zđ\d\-]+)',
                corrected_text
            )
            if not match:
                # Pattern 2: Số: XX/VBHN-XX hoặc XX/QĐ-XX (không có năm)
                match = re.search(
                    r'[Ss]ố[:\s]+(\d+[\\/][A-ZĐa-zđ\d\-]+[\\/]?[A-ZĐa-zđ\d\-]*)',
                    corrected_text
                )
            if match:
                enriched['so_hieu'] = match.group(1).replace('\\', '/')

        # ── ngay_ban_hanh: regex cho "ngày DD tháng MM năm YYYY" ──
        if not enriched.get('ngay_ban_hanh'):
            match = re.search(
                r'[Nn]gày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
                corrected_text
            )
            if match:
                d, m, y = match.groups()
                enriched['ngay_ban_hanh'] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"

        # ── nguoi_ky: regex cho vùng ký cuối văn bản ──
        if not enriched.get('nguoi_ky'):
            tail = corrected_text[-4000:] if len(corrected_text) > 4000 else corrected_text
            # Pattern 1: Title Case (Nguyễn Văn A)
            matches = re.findall(
                r'(?:^|\n)\s*([A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆ]'
                r'[a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+'
                r'(?:\s+[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬ][a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+){1,5})\s*(?:\n|$)',
                tail
            )
            if not matches:
                # Pattern 2: FULL UPPERCASE (NGUYỄN VĂN A) — phổ biến trong VB hành chính
                matches = re.findall(
                    r'(?:^|\n)\s*([A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ]{2,}'
                    r'(?:\s+[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ]+){1,4})\s*(?:\n|$)',
                    tail
                )
                if matches:
                    # Convert UPPERCASE → Title Case
                    matches = [m.strip().title() for m in matches]
            if not matches:
                # Pattern 3: Tên bị tách dòng (OCR tách từng từ trên dòng riêng)
                # Ví dụ: "nguyễn\nChí\nDũng" hoặc "Trần Duy\nĐông"
                tail_lines = tail.split('\n')
                # Tìm vùng ký: sau "KT.", "TM." hoặc "CHỦ TỊCH"
                sign_start_idx = 0
                for idx, ln in enumerate(tail_lines):
                    if re.search(r'KT\.|TM\.|CHỦ TỊCH|GIÁM ĐỐC|BỘ TRƯỜNG|THỦ TƯỚNG', ln, re.IGNORECASE):
                        if idx > len(tail_lines) * 0.3:
                            sign_start_idx = idx
                            break
                # Tìm "Nơi nhận" để giới hạn vùng ký
                noi_nhan_idx = len(tail_lines)
                for idx in range(sign_start_idx, len(tail_lines)):
                    if 'Nơi nhận' in tail_lines[idx] or 'nơi nhận' in tail_lines[idx].lower():
                        noi_nhan_idx = idx
                        break
                # Tìm các từ viết hoa đầu (hoặc tất cả thường nhưng đứng riêng) trong vùng ký
                name_word_re = re.compile(
                    r'^[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆa-zàáảãạăắằẳẵặâấầẩẫậ]'
                    r'[a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+$'
                )
                false_positives = {'Trung', 'Phục', 'Hành', 'Công', 'Tiếp', 'Theo',
                                   'Văn', 'Phòng', 'Ban', 'Viện', 'Sở', 'Cục', 'Vụ',
                                   'Lưu', 'Tỉnh', 'Nhu', 'Trên', 'Diện', 'Giấy'}
                candidate_parts = []
                for idx in range(sign_start_idx, min(noi_nhan_idx + 5, len(tail_lines))):
                    ln = tail_lines[idx].strip()
                    if name_word_re.match(ln) and len(ln) <= 12 and ln not in false_positives:
                        candidate_parts.append((idx, ln))
                # Ghép nhóm liên tiếp (khoảng cách <= 3 dòng)
                if len(candidate_parts) >= 2:
                    groups = [[candidate_parts[0]]]
                    for i in range(1, len(candidate_parts)):
                        if candidate_parts[i][0] - candidate_parts[i-1][0] <= 4:
                            groups[-1].append(candidate_parts[i])
                        else:
                            groups.append([candidate_parts[i]])
                    best = max(groups, key=len)
                    if 2 <= len(best) <= 5:
                        joined = ' '.join(p[1] for p in best)
                        # Title case nếu chữ đầu viết thường
                        joined = ' '.join(w.capitalize() if w[0].islower() else w for w in joined.split())
                        matches = [joined]
            if matches:
                enriched['nguoi_ky'] = matches[-1].strip()

        # ── loai_van_ban: regex fallback nếu LLM trả "Khác" hoặc rỗng ──
        if not enriched.get('loai_van_ban') or enriched.get('loai_van_ban') == 'Khác':
            text_upper = corrected_text[:3000].upper()
            type_patterns = [
                ('QUYẾT ĐỊNH', 'Quyết định'),
                ('NGHỊ QUYẾT', 'Nghị quyết'),
                ('CHỈ THỊ', 'Chỉ thị'),
                ('NGHỊ ĐỊNH', 'Nghị định'),
                ('THÔNG TƯ', 'Thông tư'),
                ('THÔNG BÁO', 'Thông báo'),
                ('CÔNG VĂN', 'Công văn'),
                ('CÔNG ĐIỆN', 'Công điện'),
                ('LUẬT', 'Luật'),
            ]
            for pattern, type_name in type_patterns:
                # Tìm pattern ở dạng dòng riêng (để tránh false positive)
                if re.search(r'(?:^|\n)\s*' + pattern + r'\s*(?:\n|$)', text_upper):
                    enriched['loai_van_ban'] = type_name
                    break

        # ── co_quan_ban_hanh: regex fallback ──
        if not enriched.get('co_quan_ban_hanh'):
            head = corrected_text[:2000].upper()
            # Pattern: tên cơ quan ở đầu trang — ưu tiên UBND/Bộ trước
            cq_patterns = [
                # UBND ưu tiên cao nhất (VB địa phương phổ biến)
                (r'ỦY\s*BAN\s*NHÂN\s*DÂN\s*\n\s*(TỈNH|THÀNH\s*PHỐ)\s+([A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ\s]+?)(?:\n|CỘNG)', None),
                # Bộ
                (r'(?:^|\n)\s*BỘ\s+([A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ\s]+?)(?:\n|CỘNG)', None),
                # Thủ tướng — trên dòng riêng
                (r'(?:^|\n)\s*THỦ\s*TƯỚNG\s*CHÍNH\s*PHỦ\s*(?:\n|$)', 'Thủ tướng Chính phủ'),
                (r'(?:^|\n)\s*VĂN\s*PHÒNG\s*CHÍNH\s*PHỦ\s*(?:\n|$)', 'Văn phòng Chính phủ'),
                (r'(?:^|\n)\s*VĂN\s*PHÒNG\s*QUỐC\s*HỘI\s*(?:\n|$)', 'Văn phòng Quốc hội'),
                (r'(?:^|\n)\s*CHÍNH\s*PHỦ\s*(?:\n|$)', 'Chính phủ'),
                (r'(?:^|\n)\s*QUỐC\s*HỘI\s*(?:\n|$)', 'Quốc hội'),
            ]
            for pat, direct_name in cq_patterns:
                match = re.search(pat, head)
                if match:
                    if direct_name:
                        enriched['co_quan_ban_hanh'] = direct_name
                    elif 'ỦY' in pat and 'BAN' in pat:
                        cap = match.group(1).strip()
                        ten = match.group(2).strip().title()
                        cap_lower = 'tỉnh' if 'TỈNH' in cap else 'thành phố'
                        enriched['co_quan_ban_hanh'] = f"Ủy ban nhân dân {cap_lower} {ten}"
                    elif 'BỘ' in pat:
                        enriched['co_quan_ban_hanh'] = f"Bộ {match.group(1).strip().title()}"
                    else:
                        enriched['co_quan_ban_hanh'] = match.group(0).strip()
                    break

        return enriched

    def _regex_header_override(self, extracted: dict, full_text: str) -> dict:
        """
        Regex Header Override: trích xuất trực tiếp từ HEADER (3000 ký tự đầu)
        và GHI ĐÈ kết quả LLM nếu regex có độ tin cậy cao.

        Đây là biện pháp chống lại việc LLM bị "lạc" vào phần phụ lục.
        CHỈ ghi đè nếu regex tìm thấy match rõ ràng trong header.
        """
        result = dict(extracted)
        header = full_text[:3000]  # Header chứa metadata VB chính
        corrected_header = self._ocr_post_correct(header)

        # ── loai_van_ban: override nếu LLM trả "Khác" hoặc không đúng pattern ──
        header_upper = corrected_header.upper()
        type_patterns = [
            ('QUYẾT ĐỊNH', 'Quyết định'),
            ('NGHỊ QUYẾT', 'Nghị quyết'),
            ('CHỈ THỊ', 'Chỉ thị'),
            ('NGHỊ ĐỊNH', 'Nghị định'),
            ('THÔNG TƯ', 'Thông tư'),
            ('THÔNG BÁO', 'Thông báo'),
            ('CÔNG VĂN', 'Công văn'),
            ('CÔNG ĐIỆN', 'Công điện'),
            ('LUẬT', 'Luật'),
        ]
        regex_loai = None
        for pattern, type_name in type_patterns:
            # Tìm pattern ở dạng dòng riêng biệt (tiêu đề chính)
            if re.search(r'(?:^|\n)\s*' + pattern + r'\s*(?:\n|$)', header_upper):
                regex_loai = type_name
                break
        if regex_loai and result.get('loai_van_ban') in ('Khác', '', None):
            print(f"  🔧 Header Override: loai_van_ban '{result.get('loai_van_ban')}' → '{regex_loai}'")
            result['loai_van_ban'] = regex_loai

        # ── ngay_ban_hanh: override bằng ngày ĐẦU TIÊN trong header ──
        # OCR thường tách ngày ra nhiều dòng → dùng giới hạn .{0,80} thay vì DOTALL vô hạn
        date_match = re.search(
            r'[Nn]gày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
            corrected_header, re.DOTALL
        )
        if not date_match:
            # Fallback 1: "ngày DD\n...tháng MM năm YYYY" (OCR tách dòng, max 80 chars)
            date_match = re.search(
                r'ngày\s+(\d{1,2}).{0,80}?tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
                corrected_header, re.IGNORECASE | re.DOTALL
            )
        if not date_match:
            # Fallback 2: tìm pattern "tháng MM\n...năm YYYY" + "ngày DD"
            # Khi OCR đảo thứ tự: "01 năm 2026\nHà Nội; ngày 08"
            month_year = re.search(r'(\d{1,2})\s+năm\s+(\d{4})', corrected_header)
            day_match = re.search(r'ngày\s+(\d{1,2})', corrected_header, re.IGNORECASE)
            if month_year and day_match:
                d = day_match.group(1)
                m = month_year.group(1)
                y = month_year.group(2)
                regex_date = f"{d.zfill(2)}/{m.zfill(2)}/{y}"
                if result.get('ngay_ban_hanh') != regex_date:
                    print(f"  🔧 Header Override: ngay_ban_hanh '{result.get('ngay_ban_hanh')}' → '{regex_date}'")
                    result['ngay_ban_hanh'] = regex_date
                date_match = True  # Flag để skip block bên dưới
        if date_match and date_match is not True:
            d, m, y = date_match.groups()
            regex_date = f"{d.zfill(2)}/{m.zfill(2)}/{y}"
            if result.get('ngay_ban_hanh') != regex_date:
                print(f"  🔧 Header Override: ngay_ban_hanh '{result.get('ngay_ban_hanh')}' → '{regex_date}'")
                result['ngay_ban_hanh'] = regex_date

        # ── so_hieu: override nếu LLM trả sai hoặc rỗng ──
        so_hieu_match = re.search(
            r'[Ss]ố[.:;\s]+(\d+[\\/]\d{4}[\\/][A-ZĐa-zđ\d\-]+)',
            corrected_header
        )
        if not so_hieu_match:
            so_hieu_match = re.search(
                r'[Ss]ố[.:;\s]+(\d+[\\/][A-ZĐa-zđ\d\-]+[\\/]?[A-ZĐa-zđ\d\-]*)',
                corrected_header
            )
        if so_hieu_match:
            regex_so = so_hieu_match.group(1).replace('\\', '/')
            if result.get('so_hieu') != regex_so:
                print(f"  🔧 Header Override: so_hieu '{result.get('so_hieu')}' → '{regex_so}'")
                result['so_hieu'] = regex_so

        # ── co_quan_ban_hanh: override CHỈ KHI LLM trả rỗng hoặc rõ ràng sai ──
        # KHÔNG ghi đè khi LLM đã có giá trị hợp lệ (tránh false positive)
        if not result.get('co_quan_ban_hanh') or result.get('co_quan_ban_hanh') == 'Khác':
            # Chỉ tìm khi LLM không trả được
            cq_patterns = [
                # Ưu tiên UBND (phổ biến trong VB địa phương)
                (r'ỦY\s*BAN\s*NHÂN\s*DÂN\s*\n\s*(TỈNH|THÀNH\s*PHỐ)\s+([A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ\s]+)', None),
                # Thủ tướng / Văn phòng / Quốc hội — phải trên dòng riêng
                (r'(?:^|\n)\s*THỦ\s*TƯỚNG\s*CHÍNH\s*PHỦ\s*(?:\n|$)', 'Thủ tướng Chính phủ'),
                (r'(?:^|\n)\s*VĂN\s*PHÒNG\s*CHÍNH\s*PHỦ\s*(?:\n|$)', 'Văn phòng Chính phủ'),
                (r'(?:^|\n)\s*VĂN\s*PHÒNG\s*QUỐC\s*HỘI\s*(?:\n|$)', 'Văn phòng Quốc hội'),
                # CHÍNH PHỦ đứng một mình trên dòng riêng (KHÔNG match "chính quyền")
                (r'(?:^|\n)\s*CHÍNH\s*PHỦ\s*(?:\n|$)', 'Chính phủ'),
                (r'(?:^|\n)\s*QUỐC\s*HỘI\s*(?:\n|$)', 'Quốc hội'),
                # Bộ + tên
                (r'(?:^|\n)\s*BỘ\s+([A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ\s]+?)(?:\n|CỘNG)', None),
            ]
            for pat, direct_name in cq_patterns:
                match = re.search(pat, corrected_header.upper())
                if match:
                    if direct_name:
                        cq_name = direct_name
                    elif 'ỦY BAN' in pat.upper() or 'ỦY\\s*BAN' in pat:
                        # Parse UBND pattern
                        cap = match.group(1).strip()  # TỈNH hoặc THÀNH PHỐ
                        ten = match.group(2).strip()
                        cap_lower = cap.lower().replace('thành phố', 'thành phố')
                        if 'TỈNH' in cap:
                            cap_lower = 'tỉnh'
                        elif 'THÀNH' in cap:
                            cap_lower = 'thành phố'
                        # Title case cho tên
                        ten_title = ten.title()
                        cq_name = f"Ủy ban nhân dân {cap_lower} {ten_title}"
                    else:
                        # Bộ pattern
                        ten_bo = match.group(1).strip().title()
                        cq_name = f"Bộ {ten_bo}"
                    print(f"  🔧 Header Override: co_quan_ban_hanh '' → '{cq_name}'")
                    result['co_quan_ban_hanh'] = cq_name
                    break

        # ── nguoi_ky: override nếu rỗng hoặc LLM trả chuỗi dài bất thường (>30 chars) ──
        need_nguoiky_override = (
            not result.get('nguoi_ky') or
            result.get('nguoi_ky', '').strip() == '' or
            len(result.get('nguoi_ky', '')) > 30
        )
        if need_nguoiky_override:
            # Tìm vùng ký: ưu tiên tìm bằng chức danh markers, fallback Nơi nhận
            sign_markers = ['KT\.', 'TM\.', 'TL\.', 'TUQ\.', 'CHỦ TỊCH', 'GIÁM ĐỐC',
                           'BỘ TRƯỞNG', 'THỦ TƯỚNG', 'XÁC THỰC VĂN BẢN', 'CHỦ NHIỆM']
            sign_zone_start = -1
            for marker in sign_markers:
                m = re.search(marker, full_text, re.IGNORECASE)
                if m and m.start() > len(full_text) * 0.4:
                    sign_zone_start = m.start()
                    break
            if sign_zone_start == -1:
                # Fallback: tìm "Nơi nhận:"
                noi_nhan_pos = full_text.find('Nơi nhận')
                if noi_nhan_pos > 0:
                    sign_zone_start = max(0, noi_nhan_pos - 3000)
                else:
                    # Last resort: 40-80% vị trí text (vùng ký thường ở đây)
                    sign_zone_start = int(len(full_text) * 0.4)
            sign_zone_end = min(len(full_text), sign_zone_start + 5000)
            sign_zone = full_text[sign_zone_start:sign_zone_end]

            # Pattern 1: Title Case (Nguyễn Văn A)
            name_matches = re.findall(
                r'(?:^|\n)\s*([A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆ]'
                r'[a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+'
                r'(?:\s+[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬ][a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+){1,4})\s*(?:\n|$)',
                sign_zone
            )
            if not name_matches:
                # Pattern 2: FULL UPPERCASE (NGUYỄN VĂN A)
                name_matches = re.findall(
                    r'(?:^|\n)\s*([A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ]{2,}'
                    r'(?:\s+[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ]+){1,4})\s*(?:\n|$)',
                    sign_zone
                )
                if name_matches:
                    name_matches = [m.strip().title() for m in name_matches]

            if not name_matches:
                # Pattern 3: Tên bị tách dòng + xen rác (ví dụ: "Trần Duy\n...\nĐông")
                # Tìm các từ viết hoa chữ đầu đứng một mình trên dòng, gần cuối sign_zone
                sign_lines = sign_zone.split('\n')
                # Tìm vị trí "Nơi nhận" trong sign_zone để giới hạn vùng tìm
                noi_nhan_line = -1
                for idx, ln in enumerate(sign_lines):
                    if 'Nơi nhận' in ln or 'nơi nhận' in ln.lower():
                        noi_nhan_line = idx
                        break
                # Vùng tìm: từ đầu sign_zone đến Nơi nhận (hoặc hết)
                search_end = noi_nhan_line if noi_nhan_line > 0 else len(sign_lines)
                # Lấy các từ viết hoa đầu, nằm trên dòng riêng/gần nhau
                name_word_pattern = re.compile(
                    r'^[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬ]'
                    r'[a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+'
                    r'$'
                )
                false_positives = {'Trung', 'Phục', 'Hành', 'Công', 'Tiếp', 'Theo',
                                   'Văn', 'Phòng', 'Ban', 'Viện', 'Sở', 'Cục', 'Vụ',
                                   'Lưu', 'Tỉnh', 'Nhu', 'Trên', 'Diện', 'Giấy'}
                candidate_parts = []
                for idx in range(max(0, search_end - 15), search_end):
                    ln = sign_lines[idx].strip()
                    if name_word_pattern.match(ln) and len(ln) <= 15 and ln not in false_positives:
                        candidate_parts.append((idx, ln))
                # Tìm nhóm liên tiếp (khoảng cách <= 3 dòng)
                if len(candidate_parts) >= 2:
                    groups = [[candidate_parts[0]]]
                    for i in range(1, len(candidate_parts)):
                        if candidate_parts[i][0] - candidate_parts[i-1][0] <= 4:
                            groups[-1].append(candidate_parts[i])
                        else:
                            groups.append([candidate_parts[i]])
                    # Lấy nhóm dài nhất (2-5 từ)
                    best = max(groups, key=len)
                    if 2 <= len(best) <= 5:
                        joined_name = ' '.join(p[1] for p in best)
                        name_matches = [joined_name]

            if name_matches:
                real_name = name_matches[-1].strip()
                print(f"  🔧 Header Override: nguoi_ky → '{real_name}'")
                result['nguoi_ky'] = real_name

        # ── trich_yeu: override nếu rỗng, lấy sai từ phụ lục, hoặc có dấu hiệu OCR rác ──
        need_trich_override = False
        current_trich = result.get('trich_yeu', '').strip()
        if not current_trich:
            need_trich_override = True
        else:
            # Kiểm tra dấu hiệu sai
            suspicious = False
            # Bắt đầu bằng chữ thường hoặc "này" → bị cắt từ giữa câu
            if current_trich and current_trich[0].islower():
                suspicious = True
            if current_trich.startswith('này ') or current_trich.startswith('Này '):
                suspicious = True
            # Chứa từ khóa phụ lục
            phuluc_keywords = ['Mẫu số', 'mẫu số', 'Văn bản đề nghị', 'ĐƠN ĐỀ NGHỊ',
                               'Đề nghị cấp lại', 'Đề nghị cấp', 'Đề nghị nhập khẩu']
            if any(kw in current_trich for kw in phuluc_keywords):
                suspicious = True
            if suspicious:
                need_trich_override = True

        if need_trich_override:
            # Tìm trích yếu thật từ header (giữa tên loại VB và "Căn cứ")
            trich_match = re.search(
                r'(?:QUYẾT ĐỊNH|NGHỊ ĐỊNH|LUẬT|THÔNG TƯ|CHỈ THỊ|NGHỊ QUYẾT|THÔNG BÁO|CÔNG VĂN|CÔNG ĐIỆN|TỜ TRÌNH|BÁO CÁO)\s*\n\s*(.+?)(?:\n\s*Căn cứ|\n\s*Theo|\n\s*Thực hiện|\n\s*Kính gửi)',
                corrected_header, re.DOTALL | re.IGNORECASE
            )
            if not trich_match:
                # Fallback: V/v multiline (Công văn)
                trich_match = re.search(
                    r'[Vv]\s*/\s*[Vv]\s*[:\s]+(.+?)(?:\n\s*\n|\n\s*Kính\s+gửi|$)',
                    corrected_header, re.DOTALL
                )
            if trich_match:
                real_trich = trich_match.group(1).strip()
                # Nối nhiều dòng thành 1 câu, loại bỏ ký tự rác
                real_trich = re.sub(r'\s*\n\s*', ' ', real_trich).strip()
                # Bỏ prefix thừa ("này", "V/v:", số trang...)
                real_trich = re.sub(r'^(này|Này)\s+', '', real_trich)
                real_trich = re.sub(r'^V\s*/\s*v\s*[:\s]+', '', real_trich, flags=re.IGNORECASE)
                # Viết hoa chữ đầu
                if real_trich and real_trich[0].islower():
                    real_trich = real_trich[0].upper() + real_trich[1:]
                if real_trich and len(real_trich) > 10:
                    print(f"  🔧 Header Override: trich_yeu → '{real_trich[:80]}...'")
                    result['trich_yeu'] = real_trich

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
            if not re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
                # Try DD/MM/YYYY or DD-MM-YYYY
                match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', date_str)
                if match:
                    d, m, y = match.groups()
                    validated['ngay_ban_hanh'] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"
                else:
                    # Try Vietnamese: "DD tháng MM năm YYYY" or "ngày DD tháng MM năm YYYY"
                    vi_match = re.search(
                        r'(?:ngày\s+)?(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
                        date_str, re.IGNORECASE
                    )
                    if vi_match:
                        d, m, y = vi_match.groups()
                        validated['ngay_ban_hanh'] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"
                    else:
                        # Try YYYY-MM-DD (ISO)
                        iso_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
                        if iso_match:
                            y, m, d = iso_match.groups()
                            validated['ngay_ban_hanh'] = f"{d}/{m}/{y}"
            # Sanity check: reject hallucinated default dates
            if validated.get('ngay_ban_hanh'):
                suspicious_dates = ['01/01/2023', '01/01/1970', '01/01/2000', '01/01/2024']
                if validated['ngay_ban_hanh'] in suspicious_dates:
                    print(f"  ⚠️ Date sanity: rejected suspicious '{validated['ngay_ban_hanh']}'")
                    validated['ngay_ban_hanh'] = ''  # Force enrichment to fill correct date

        # ── Normalize loai_van_ban: case-insensitive match against all valid types ──
        if validated.get('loai_van_ban'):
            validated['loai_van_ban'] = self._normalize_loai_van_ban(validated['loai_van_ban'])
        else:
            validated['loai_van_ban'] = 'Khác'

        # ── Normalize co_quan_ban_hanh: UPPER CASE → proper mixed case ──
        if validated.get('co_quan_ban_hanh'):
            validated['co_quan_ban_hanh'] = self._normalize_co_quan(validated['co_quan_ban_hanh'])

        # ── Cleanup trich_yeu: bỏ tên loại VB ở đầu ──
        if validated.get('trich_yeu'):
            trich = validated['trich_yeu']
            # Bỏ prefix cho tất cả loại văn bản (cả UPPER và Title Case)
            for vb_type in self.VALID_DOCUMENT_TYPES:
                if vb_type == 'Khác':
                    continue
                for variant in [vb_type, vb_type.upper()]:
                    if trich.startswith(variant):
                        trich = trich[len(variant):].lstrip(' :.\n')
                        break
            # Bỏ "V/v:" prefix nếu có
            trich = re.sub(r'^V\s*/\s*v\s*[:\s]+', '', trich, flags=re.IGNORECASE)
            # Bỏ "Về việc" prefix nếu trich_yeu bắt đầu bằng nó
            # (giữ nguyên nếu ground truth cũng có "Về việc")
            validated['trich_yeu'] = trich.strip()

        # ── Cleanup nguoi_ky: bỏ chức danh triệt để ──
        if validated.get('nguoi_ky'):
            name = validated['nguoi_ky']
            # Bỏ LLM placeholder patterns
            placeholder_patterns = [
                r'\[Chưa có thông tin\]', r'\[Không tìm thấy\]', r'\[Không rõ\]',
                r'\[Không xác định\]', r'Chưa có thông tin', r'Không tìm thấy',
                r'N/A', r'n/a', r'None', r'null', r'không rõ',
            ]
            for pp in placeholder_patterns:
                if re.fullmatch(pp, name.strip(), re.IGNORECASE):
                    print(f"  ⚠️ nguoi_ky cleanup: '{name}' is placeholder → cleared")
                    validated['nguoi_ky'] = ''
                    name = ''
                    break
            # Bỏ tất cả chức danh phổ biến (nhiều vòng để xử lý nested)
            title_patterns = [
                r'(?:KT\.\s*|TM\.\s*|TL\.\s*|TUQ\.\s*|Q\.\s*)',
                r'(?:CHỦ TỊCH|PHÓ CHỦ TỊCH)',
                r'(?:GIÁM ĐỐC|PHÓ GIÁM ĐỐC|TỔNG GIÁM ĐỐC)',
                r'(?:THỦ TƯỚNG|PHÓ THỦ TƯỚNG)',
                r'(?:BỘ TRƯỞNG|THỨ TRƯỞNG|PHÓ BỘ TRƯỞNG)',
                r'(?:CHÁNH VĂN PHÒNG|PHÓ CHÁNH VĂN PHÒNG)',
                r'(?:CHỦ NHIỆM|PHÓ CHỦ NHIỆM)',
                r'(?:ỦY BAN NHÂN DÂN|CHÍNH PHỦ|QUỐC HỘI)',
                r'(?:VĂN PHÒNG)',
                r'(?:BỘ TRƯỞNG,\s*CHỦ NHIỆM)',
            ]
            for pat in title_patterns:
                name = re.sub(r'^\s*' + pat + r'\s*', '', name, flags=re.IGNORECASE).strip()

            # Bỏ watermark chữ ký số
            name = re.sub(r'Ký bởi:.*', '', name, flags=re.IGNORECASE).strip()
            name = re.sub(r'Ngày ký:.*', '', name, flags=re.IGNORECASE).strip()
            name = re.sub(r'Ký số bởi.*', '', name, flags=re.IGNORECASE).strip()

            if name:
                # Kiểm tra xem sau cleanup, còn lại có giống tên người không
                # Tên người Việt: 2-5 từ, mỗi từ viết hoa chữ đầu
                # Nếu chứa tên cơ quan → LLM trả chức danh thay vì tên → clear
                org_keywords = ['UBND', 'ubnd', 'Bộ ', 'Sở ', 'tỉnh', 'thành phố',
                                'Chính phủ', 'Quốc hội', 'Văn phòng', 'Cục ',
                                'Tổng cục', 'Hội đồng', 'Ban ', 'Viện ']
                has_org = any(kw in name for kw in org_keywords)
                # Tên người: 2-5 từ, không chứa số, không quá dài
                words = name.split()
                is_name = (2 <= len(words) <= 6 and
                          len(name) <= 50 and
                          not any(c.isdigit() for c in name) and
                          not has_org)
                if is_name:
                    validated['nguoi_ky'] = name
                else:
                    # Không giống tên người → clear, để regex fallback xử lý
                    print(f"  ⚠️ nguoi_ky cleanup: '{name}' not a person name → cleared")
                    validated['nguoi_ky'] = ''
            else:
                # Title stripping xóa hết → LLM chỉ trả chức danh, không có tên
                print(f"  ⚠️ nguoi_ky cleanup: '{validated['nguoi_ky']}' is only title → cleared")
                validated['nguoi_ky'] = ''

        # ── Cleanup so_hieu: sửa dính số (32025/ → 3/2025/) ──
        if validated.get('so_hieu'):
            sh = validated['so_hieu']
            # Pattern: "32025/QĐ" → "3/2025/QĐ" (số 1-3 chữ số dính năm 4 chữ số)
            match = re.match(r'^(\d{1,3})(20\d{2})/(.+)$', sh)
            if match:
                num, year, suffix = match.groups()
                validated['so_hieu'] = f"{num}/{year}/{suffix}"

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
                # Loại bỏ numpy arrays (ảnh) trước khi lưu JSON
                _img_keys = {'processed_images', 'original_image', 'detection_image', 'clean_image'}
                save_data = {}
                for k, v in result.items():
                    if k in _img_keys:
                        continue
                    if k == 'pages' and isinstance(v, list):
                        save_data[k] = [
                            {pk: pv for pk, pv in page.items() if pk not in _img_keys}
                            for page in v
                        ]
                    else:
                        save_data[k] = v
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print(f"  💾 Kết quả: {output_path}")

        return result

    def _ocr_post_correct(self, text: str) -> str:
        """
        Sửa các lỗi OCR phổ biến trong văn bản hành chính tiếng Việt.
        Dùng regex context-aware để tránh false positive.
        """
        # ── 1. Sửa lỗi Đ→4 trong số hiệu (Q4-UBND → QĐ-UBND, Q4-TTg → QĐ-TTg) ──
        text = re.sub(r'Q4-', 'QĐ-', text)
        text = re.sub(r'N4-CP', 'NĐ-CP', text)

        # ── 2. Sửa lỗi l→I (chữ L thường bị nhầm thành I hoa giữa từ) ──
        # Các từ phổ biến trong văn bản hành chính bị nhầm I→l
        i_to_l_words = {
            'Iệ': 'lệ', 'Iê': 'lê', 'Iý': 'lý', 'Iả': 'lả',
            'Ià': 'là', 'Iá': 'lá', 'Iạ': 'lạ', 'Iự': 'lự',
            'Iầ': 'lầ', 'Iập': 'lập', 'Iuật': 'luật', 'Iưu': 'lưu',
            'Iực': 'lực', 'Iịch': 'lịch', 'Iương': 'lương',
            'Iệnh': 'lệnh', 'Iãnh': 'lãnh', 'Iợi': 'lợi',
        }
        for wrong, right in i_to_l_words.items():
            # Chỉ thay khi I xuất hiện ở giữa/cuối từ (sau khoảng trắng + chữ thường)
            text = re.sub(r'(?<=\s)' + re.escape(wrong), right, text)
            # Hoặc sau chữ thường (dính liền)
            text = re.sub(r'(?<=[a-zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ])' + re.escape(wrong), right, text)

        # ── 3. Dấu phụ tỉnh/tính ──
        text = re.sub(r'(?:tính|tinh)(\s+(?:Đắk|Phú|Bình|Quảng|Nghệ|Hà|Bắc|Nam|Lào|Gia|Kon|Đồng|Hưng|Thái|Thanh|Vĩnh|Yên|Tây|Ninh|Lâm|Khánh|An|Hải|Trà|Long|Sóc|Cà|Bến|Tiền|Kiên|Hậu))',
                      r'tỉnh\1', text)
        text = text.replace('địa bàn tính', 'địa bàn tỉnh')
        text = text.replace('địa bàn tinh', 'địa bàn tỉnh')

        # ── 4. Ký tự đặc biệt ──
        text = text.replace('(C%)', '(%)')

        # ── 5. (Removed: hardcoded single-file fixes — now fixed by OCR row-sort) ──

        # ── 6. Loại bỏ watermark chữ ký số ──
        text = self._filter_digital_signature_watermark(text)

        return text

    def _filter_digital_signature_watermark(self, text: str) -> str:
        """
        Loại bỏ watermark chữ ký số khỏi text.
        Các PDF từ Cổng thông tin điện tử Chính phủ thường chứa watermark:
        "Người ký: CỔNG THÔNG TIN ĐIỆN Tử CHÍNH PHỦ ... Thời gian ký: ..."
        """
        if not text:
            return text

        # Pattern 1: Watermark từ Cổng TTDT Chính phủ (dạng đầy đủ)
        text = re.sub(
            r'Người ký:\s*CỔNG THÔNG TIN ĐIỆN TỬ CHÍNH PHỦ.*?(?:Thời gian ký:[\d\s:\+\-]+|$)',
            '', text, flags=re.DOTALL | re.IGNORECASE
        )
        # Pattern 2: CHINHPHU.VN header dính liền (OCR đọc watermark trang 1)
        text = re.sub(
            r'CHINHPHU\.VN.*?(?:chinhphu\.\w+|\+07:00)',
            '', text, flags=re.DOTALL | re.IGNORECASE
        )
        # Pattern 3: VGP header block
        text = re.sub(
            r'VGP.*?(?:chinhphu\.\w+|Email:.*?\n)',
            '', text, flags=re.DOTALL
        )
        # Pattern 4: THỜI GIAN KÝ block (dạng OCR đọc)
        text = re.sub(
            r'THỜI GIAN K[YÝ]:\s*[\d\.:\s\+\-]+',
            '', text, flags=re.IGNORECASE
        )
        # Pattern 5: "Ký bởi:" digital signature
        text = re.sub(
            r'Ký bởi:.*?(?:Ngày ký:.*?(?:\n|$)|$)',
            '', text, flags=re.DOTALL | re.IGNORECASE
        )
        # Pattern 6: Người ký simpler
        text = re.sub(
            r'Người ký:\s*CỔNG THÔNG TIN.*?(?:\+07:00|$)',
            '', text, flags=re.DOTALL
        )
        # Pattern 7: CỔNG THÔNG TIN ĐIỆN TỬ standalone
        text = re.sub(
            r'CỔNG THÔNG TIN ĐIỆN TỬ CHÍNH PHỦ.*?(?:\n|$)',
            '', text, flags=re.IGNORECASE
        )
        # Pattern 8: DÒNG OCR rác "G?NG TH?NG TIN" (OCR bị lỗi font)
        text = re.sub(
            r'G[?.]NG TH[?.]NG TIN.*?(?:\n|$)',
            '', text, flags=re.IGNORECASE
        )
        # Pattern 9: "D?N GAY" / "ĐƯN GÀY" date watermark
        text = re.sub(
            r'(?:D\?N GAY|ĐƯN GÀY|D.N GAY)\s*[\d/]+',
            '', text, flags=re.IGNORECASE
        )

        return text.strip()

    def _is_page_born_digital(self, page) -> bool:
        """
        Kiểm tra 1 trang PDF có text layer thực (born-digital) hay là ảnh scan.

        Logic:
        1. Lấy text từ page
        2. Filter watermark chữ ký số
        3. Nếu text sau filter > 100 chars → born-digital
        4. Nếu ≤ 100 chars → scanned (cần OCR)

        Returns:
            True nếu trang có text layer thực (born-digital)
        """
        raw_text = page.get_text()
        clean_text = self._filter_digital_signature_watermark(raw_text)
        return len(clean_text.strip()) > 100

    def _process_pdf(self, pdf_path: str) -> dict:
        """
        Xử lý file PDF (multi-page).
        CHIẾN LƯỢC: Luôn chạy OCR cho TẤT CẢ trang.

        Lý do không dùng PyMuPDF text extraction:
        - PDF "searchable scan" có text layer ẩn từ scanner OCR, thường sai/thiếu
        - PDF có ảnh scan chèn giữa trang có text → text layer không phản ánh thực tế
        - OCR đọc NỘI DUNG TRỰC QUAN trên ảnh → đáng tin cậy hơn

        Pipeline mỗi trang:
        1. Render ảnh ở DPI 400
        2. Preprocess (deskew, denoise)
        3. Stamp detect + remove (YOLOv8)
        4. OCR (EasyOCR text detection + VietOCR recognition)
        5. OCR post-correction
        """
        import fitz

        doc = fitz.open(pdf_path)
        pages_results = []
        all_text = []
        all_stamps = []
        all_ocr_lines = []
        processed_images = []

        print(f"  📊 {len(doc)} trang — OCR full pipeline (DPI {Config.OCR_DPI})")

        for page_idx in range(len(doc)):
            page = doc[page_idx]

            # ── Render ảnh ở DPI cao cho OCR ──
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
            clean_img, stamps, detection_viz = self.detect_and_remove_stamps(img)
            for s in stamps:
                s['page'] = page_idx + 1

            # Stage 3: OCR (EasyOCR + VietOCR)
            text, raw_lines = self.run_ocr(clean_img)

            # Stage 3.5: OCR Post-correction
            text = self._ocr_post_correct(text)

            print(f"    Trang {page_idx+1}: 🔍 OCR → {len(text)} chars, "
                  f"{len(stamps)} stamps")

            # Build structured OCR lines
            ocr_lines = []
            for line in raw_lines:
                bbox = line.get('bbox', [])
                if bbox and len(bbox) == 4:
                    xs = [pt[0] for pt in bbox]
                    ys = [pt[1] for pt in bbox]
                    x1, y1 = int(min(xs)), int(min(ys))
                    x2, y2 = int(max(xs)), int(max(ys))
                else:
                    x1, y1, x2, y2 = 0, 0, 0, 0

                ocr_lines.append({
                    'text': line.get('text', ''),
                    'confidence': line.get('confidence', 0),
                    'bbox': [x1, y1, x2, y2],
                    'page': page_idx + 1,
                })

            # Collect results
            all_text.append(text)
            all_stamps.extend(stamps)
            all_ocr_lines.extend(ocr_lines)
            processed_images.append(img)

            pages_results.append({
                'page': page_idx + 1,
                'method': 'ocr',
                'text': text,
                'stamps': stamps,
                'ocr_lines': ocr_lines,
            })

        doc.close()
        full_text = '\n\n'.join(all_text)

        # Stage 4: Layout Region Classification (trang 1)
        layout_fields = {}
        page1_lines = [l for l in all_ocr_lines if l.get('page') == 1]
        if page1_lines and processed_images:
            h, w = processed_images[0].shape[:2]
            classified = self.layout_classifier.classify_page(
                page1_lines, w, h
            )
            layout_fields = self.layout_classifier.extract_fields_from_regions(
                classified
            )
            # Enrich ocr_lines page 1 with region info
            region_map = {id(orig): cl for orig, cl in zip(page1_lines, classified)}
            for i, line in enumerate(all_ocr_lines):
                if line.get('page') == 1:
                    cl = classified[page1_lines.index(line)] if line in page1_lines else None
                    if cl:
                        line['region'] = cl.get('region', '')
                        line['region_name'] = cl.get('region_name', '')

        # Stage 5+6: LLM + Validate (gọi 1 lần cho toàn bộ)
        extracted, llm_raw_output = self.extract_info(full_text)

        # Enrichment 1: bổ sung từ layout_fields nếu LLM trả thiếu
        extracted = self._enrich_from_layout(extracted, layout_fields)

        # Enrichment 2: regex fallback từ full_text cho so_hieu, ngay, nguoi_ky
        extracted = self._enrich_from_fulltext(extracted, full_text)

        # Stage 6: Validate + Normalize
        validated = self.validate_output(extracted)

        # Enrichment 3 (POST-VALIDATE): regex header override — sửa sai bằng regex header
        # Chạy SAU validate để catch các trường hợp LLM trả rác → validate normalize → Khác
        validated = self._regex_header_override(validated, full_text)

        # Lưu full text làm llm_input (KHÔNG cắt xén)
        llm_input_text = full_text

        return {
            'status': 'success',
            'num_pages': len(pages_results),
            'pages': pages_results,
            'total_stamps': len(all_stamps),
            'stamp_coordinates': all_stamps,
            'full_text': full_text,
            'llm_input_text': llm_input_text,
            'llm_raw_output': llm_raw_output,
            'extraction': validated,
            'layout_fields': layout_fields,
            'ocr_lines': all_ocr_lines,
            'processed_images': processed_images,
        }

    def _process_single_image(self, image: np.ndarray) -> dict:
        """Xử lý 1 ảnh đơn."""
        # Stage 1: Preprocess
        image = self.preprocess_image(image)
        original_img = image.copy()

        # Stage 2: Stamp detect + remove
        clean_img, stamps, detection_viz = self.detect_and_remove_stamps(image)
        for s in stamps:
            s['page'] = 1

        # Stage 3: OCR
        text, raw_lines = self.run_ocr(clean_img)
        
        ocr_lines = []
        for line in raw_lines:
            bbox = line.get('bbox', [])
            if bbox and len(bbox) == 4:
                xs = [pt[0] for pt in bbox]
                ys = [pt[1] for pt in bbox]
                x1, y1 = int(min(xs)), int(min(ys))
                x2, y2 = int(max(xs)), int(max(ys))
            else:
                x1, y1, x2, y2 = 0, 0, 0, 0
            
            ocr_lines.append({
                'text': line.get('text', ''),
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'page': 1
            })

        # Stage 4+5: LLM + Validate
        extracted, llm_raw_output = self.extract_info(text)
        validated = self.validate_output(extracted)

        pages_results = [{
            'page': 1,
            'text': text,
            'stamps': len(stamps),
            'original_image': original_img,
            'detection_image': detection_viz,
            'clean_image': clean_img,
        }]

        return {
            'status': 'success',
            'num_pages': 1,
            'pages': pages_results,
            'total_stamps': len(stamps),
            'stamp_coordinates': stamps,
            'full_text': text,
            'llm_input_text': text,
            'llm_raw_output': llm_raw_output,
            'extraction': validated,
            'ocr_lines': ocr_lines,
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
