# -*- coding: utf-8 -*-
"""
Layout Region Classifier (NĐ 30/2020/NĐ-CP)
==============================================
Phân loại các dòng OCR vào 14 ô số thể thức văn bản hành chính
dựa trên quy tắc không gian chuẩn trên khổ A4 (210×297mm).

Phương pháp: Rule-based heuristic (không cần train model).
Tận dụng tính quy luật không gian (spatial regularity) của NĐ 30/2020.

Sơ đồ bố cục A4 (chuẩn hóa 0.0 → 1.0):
    ┌────────────────────────────────────────┐
    │  Ô2 (cơ quan)  │  Ô1 (quốc hiệu)     │  y: 0.00–0.12
    │  Ô10 (mật/khẩn)│                       │
    ├────────────────────────────────────────┤
    │  Ô3 (số hiệu)  │  Ô4 (địa danh, ngày) │  y: 0.10–0.18
    ├────────────────────────────────────────┤
    │         Ô5a,5b (tên loại + trích yếu)  │  y: 0.15–0.25
    ├────────────────────────────────────────┤
    │                                        │
    │         Ô6 (nội dung văn bản)          │  y: 0.22–0.78
    │                                        │
    ├────────────────────────────────────────┤
    │  Ô9 (nơi nhận)  │  Ô7 (chức vụ/ký)    │  y: 0.72–0.95
    │                  │  Ô8 (con dấu)       │
    │  Ô11-14 (phụ)   │                      │
    └────────────────────────────────────────┘
"""

import re
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# Region Definitions (NĐ 30/2020/NĐ-CP)
# ═══════════════════════════════════════════════════════════════════════════

REGION_DEFINITIONS = {
    "quoc_hieu": {
        "id": 1,
        "name": "Quốc hiệu và Tiêu ngữ",
        "description": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM — Độc lập - Tự do - Hạnh phúc",
    },
    "co_quan": {
        "id": 2,
        "name": "Tên cơ quan, tổ chức ban hành",
        "description": "Cơ quan chủ quản + cơ quan ban hành",
    },
    "so_hieu": {
        "id": 3,
        "name": "Số, ký hiệu văn bản",
        "description": "Số: .../...-...",
    },
    "ngay_ban_hanh": {
        "id": 4,
        "name": "Địa danh và thời gian ban hành",
        "description": "..., ngày ... tháng ... năm ...",
    },
    "ten_loai": {
        "id": "5a",
        "name": "Tên loại văn bản",
        "description": "QUYẾT ĐỊNH, THÔNG TƯ, NGHỊ ĐỊNH, ...",
    },
    "trich_yeu": {
        "id": "5b",
        "name": "Trích yếu nội dung",
        "description": "V/v: ...",
    },
    "noi_dung": {
        "id": 6,
        "name": "Nội dung văn bản",
        "description": "Phần thân văn bản chính",
    },
    "nguoi_ky": {
        "id": "7a-c",
        "name": "Chức vụ, chữ ký, họ tên người ký",
        "description": "KT./TM./TL. + Chức vụ + Họ tên",
    },
    "con_dau": {
        "id": 8,
        "name": "Dấu cơ quan, tổ chức",
        "description": "Con dấu mộc đỏ",
    },
    "noi_nhan": {
        "id": "9a-b",
        "name": "Nơi nhận",
        "description": "Nơi nhận: - Như trên; - Lưu: VT, ...",
    },
    "do_mat_khan": {
        "id": "10a-b",
        "name": "Dấu chỉ độ mật, độ khẩn",
        "description": "HỎA TỐC, THƯỢNG KHẨN, MẬT, ...",
    },
    "phu_tro": {
        "id": "11-14",
        "name": "Thông tin phụ trợ hành chính",
        "description": "Chỉ dẫn lưu hành, ký hiệu người soạn thảo, ...",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Keyword Patterns for Content-based Classification
# ═══════════════════════════════════════════════════════════════════════════

# Patterns cho nhận diện nội dung (bổ sung cho spatial rules)
_QUOC_HIEU_KW = re.compile(
    r"CỘNG\s*H[OÒ]A\s*X[AÃ]\s*H[OỘ]I|Độc\s*lập|Tự\s*do|Hạnh\s*phúc",
    re.IGNORECASE,
)
_SO_HIEU_KW = re.compile(
    r"^Số\s*[:：]|^\d+\s*/\s*[A-ZĐ]",
    re.IGNORECASE,
)
_NGAY_KW = re.compile(
    r"ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}",
    re.IGNORECASE,
)
_TEN_LOAI_KW = re.compile(
    r"^(QUYẾT\s*ĐỊNH|NGHỊ\s*ĐỊNH|THÔNG\s*TƯ|THÔNG\s*BÁO|CÔNG\s*VĂN|"
    r"TỜ\s*TRÌNH|BÁO\s*CÁO|HỢP\s*ĐỒNG|BIÊN\s*BẢN|CHỈ\s*THỊ)\b",
    re.IGNORECASE,
)
_TRICH_YEU_KW = re.compile(
    r"^V\s*/\s*[Vv]\s*[:：]|^Về\s+việc\b",
    re.IGNORECASE,
)
_NOI_NHAN_KW = re.compile(
    r"^Nơi\s*nhận\s*[:：]|^-\s*Như\s*trên|^-\s*Lưu\s*[:：]",
    re.IGNORECASE,
)
_NGUOI_KY_KW = re.compile(
    r"^(KT\.|TM\.|TL\.|TUQ\.)|^(CHỦ\s*TỊCH|GIÁM\s*ĐỐC|BỘ\s*TRƯỞNG|"
    r"THỦ\s*TƯỚNG|PHÓ)",
    re.IGNORECASE,
)
_DO_MAT_KW = re.compile(
    r"^(HỎA\s*TỐC|THƯỢNG\s*KHẨN|KHẨN|MẬT|TUYỆT\s*MẬT|TỐI\s*MẬT)$",
    re.IGNORECASE,
)


class LayoutRegionClassifier:
    """
    Phân loại dòng OCR vào các ô số NĐ 30/2020/NĐ-CP.

    Chiến lược kết hợp:
    1. Spatial rules (vị trí tương đối trên trang A4)
    2. Keyword matching (nội dung đặc trưng của từng ô số)
    3. Left/right split (ô 2,3,9 bên trái — ô 1,4,7 bên phải)
    """

    def classify_line(
        self,
        text: str,
        x1: int, y1: int, x2: int, y2: int,
        page_width: int, page_height: int,
    ) -> str:
        """
        Phân loại 1 dòng OCR vào region tương ứng.

        Args:
            text: Nội dung dòng
            x1, y1, x2, y2: Bounding box (pixel)
            page_width, page_height: Kích thước trang (pixel)

        Returns:
            str: Region key (ví dụ "quoc_hieu", "so_hieu", "noi_dung", ...)
        """
        if not text or not text.strip():
            return "noi_dung"

        text_clean = text.strip()

        # Normalize tọa độ → 0.0 ~ 1.0
        cx = (x1 + x2) / 2 / max(page_width, 1)   # center x
        cy = (y1 + y2) / 2 / max(page_height, 1)   # center y
        nx1 = x1 / max(page_width, 1)
        nx2 = x2 / max(page_width, 1)

        is_left = cx < 0.45
        is_right = cx > 0.55

        # ── 1. Keyword-first: các pattern rất đặc trưng ──────────────────
        if _DO_MAT_KW.match(text_clean):
            return "do_mat_khan"

        if _QUOC_HIEU_KW.search(text_clean) and cy < 0.15:
            return "quoc_hieu"

        if _SO_HIEU_KW.match(text_clean) and cy < 0.22:
            return "so_hieu"

        if _NGAY_KW.search(text_clean) and cy < 0.22:
            return "ngay_ban_hanh"

        if _TEN_LOAI_KW.match(text_clean) and cy < 0.30:
            return "ten_loai"

        if _TRICH_YEU_KW.match(text_clean) and cy < 0.35:
            return "trich_yeu"

        if _NOI_NHAN_KW.match(text_clean) and cy > 0.65:
            return "noi_nhan"

        if _NGUOI_KY_KW.match(text_clean) and cy > 0.65:
            return "nguoi_ky"

        # ── 2. Spatial-only fallback ─────────────────────────────────────

        # Header zone (top 15%)
        if cy < 0.15:
            if is_right or cx > 0.40:
                return "quoc_hieu"
            else:
                return "co_quan"

        # Số hiệu / ngày ban hành zone (10%–20%)
        if 0.10 <= cy < 0.20:
            if is_left:
                return "so_hieu"
            else:
                return "ngay_ban_hanh"

        # Tên loại + trích yếu zone (15%–28%)
        if 0.18 <= cy < 0.28:
            return "ten_loai"

        # Bottom zone (>72%)
        if cy > 0.72:
            if is_left:
                return "noi_nhan"
            elif is_right:
                return "nguoi_ky"
            else:
                # Centered bottom — check content
                if _NOI_NHAN_KW.match(text_clean):
                    return "noi_nhan"
                return "nguoi_ky"

        # Everything else → nội dung chính
        return "noi_dung"

    def classify_page(
        self,
        ocr_lines: list[dict],
        page_width: int,
        page_height: int,
    ) -> list[dict]:
        """
        Phân loại tất cả dòng OCR trên 1 trang.

        Args:
            ocr_lines: List[dict] — mỗi dict chứa 'text', 'x1', 'y1', 'x2', 'y2'
            page_width, page_height: Kích thước trang (pixel)

        Returns:
            list[dict]: Mỗi dict gốc + thêm key 'region' và 'region_name'
        """
        results = []
        for line in ocr_lines:
            text = line.get("text", "")
            x1 = line.get("x1", 0)
            y1 = line.get("y1", 0)
            x2 = line.get("x2", 0)
            y2 = line.get("y2", 0)

            region = self.classify_line(
                text, x1, y1, x2, y2, page_width, page_height
            )
            region_info = REGION_DEFINITIONS.get(region, {})

            enriched = dict(line)
            enriched["region"] = region
            enriched["region_id"] = region_info.get("id", "?")
            enriched["region_name"] = region_info.get("name", region)
            results.append(enriched)

        return results

    def group_by_region(
        self,
        classified_lines: list[dict],
    ) -> dict[str, list[dict]]:
        """
        Nhóm các dòng đã phân loại theo region.

        Returns:
            dict: {region_key: [list of lines]}
        """
        groups: dict[str, list[dict]] = {}
        for line in classified_lines:
            region = line.get("region", "noi_dung")
            groups.setdefault(region, []).append(line)
        return groups

    def extract_fields_from_regions(
        self,
        classified_lines: list[dict],
    ) -> dict:
        """
        Trích xuất các trường hành chính từ các dòng đã phân loại.

        Đây là bước tiền xử lý TRƯỚC KHI đưa vào LLM —
        giúp LLM tập trung vào đúng vùng text, tăng accuracy.

        Returns:
            dict: {
                "co_quan_text": "...",
                "so_hieu_text": "...",
                "ngay_ban_hanh_text": "...",
                "ten_loai_text": "...",
                "trich_yeu_text": "...",
                "nguoi_ky_text": "...",
                "noi_dung_text": "...",
                "noi_nhan_text": "...",
            }
        """
        groups = self.group_by_region(classified_lines)

        def _join(region_key: str) -> str:
            lines = groups.get(region_key, [])
            return "\n".join(l.get("text", "") for l in lines).strip()

        return {
            "quoc_hieu_text": _join("quoc_hieu"),
            "co_quan_text": _join("co_quan"),
            "so_hieu_text": _join("so_hieu"),
            "ngay_ban_hanh_text": _join("ngay_ban_hanh"),
            "ten_loai_text": _join("ten_loai"),
            "trich_yeu_text": _join("trich_yeu"),
            "noi_dung_text": _join("noi_dung"),
            "nguoi_ky_text": _join("nguoi_ky"),
            "noi_nhan_text": _join("noi_nhan"),
        }
