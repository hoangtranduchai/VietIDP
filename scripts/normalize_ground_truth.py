# -*- coding: utf-8 -*-
"""
Normalize ground_truth.json: Convert UPPER CASE fields to mixed case.
Option B: Chuẩn hóa ground truth về mixed case → giữ pipeline.
"""

import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GT_PATH = os.path.join("data", "benchmark", "ground_truth.json")

# ═══════════════════════════════════════════════════════════════════════════
# Mapping cho loai_van_ban (UPPER → Title Case)
# 29 loại theo NĐ 30/2020/NĐ-CP
# ═══════════════════════════════════════════════════════════════════════════
LOAI_VB_MAP = {
    "QUYẾT ĐỊNH": "Quyết định",
    "NGHỊ ĐỊNH": "Nghị định",
    "NGHỊ QUYẾT": "Nghị quyết",
    "THÔNG TƯ": "Thông tư",
    "THÔNG BÁO": "Thông báo",
    "CÔNG VĂN": "Công văn",
    "CHỈ THỊ": "Chỉ thị",
    "TỜ TRÌNH": "Tờ trình",
    "BÁO CÁO": "Báo cáo",
    "HỢP ĐỒNG": "Hợp đồng",
    "BIÊN BẢN": "Biên bản",
    "HƯỚNG DẪN": "Hướng dẫn",
    "CÔNG ĐIỆN": "Công điện",
    "KẾ HOẠCH": "Kế hoạch",
    "CHƯƠNG TRÌNH": "Chương trình",
    "PHƯƠNG ÁN": "Phương án",
    "ĐỀ ÁN": "Đề án",
    "DỰ ÁN": "Dự án",
    "QUY CHẾ": "Quy chế",
    "QUY ĐỊNH": "Quy định",
    "GIẤY MỜI": "Giấy mời",
    "GIẤY GIỚI THIỆU": "Giấy giới thiệu",
    "GIẤY ỦY QUYỀN": "Giấy ủy quyền",
    "GIẤY NGHỈ PHÉP": "Giấy nghỉ phép",
    "GIẤY BIÊN NHẬN": "Giấy biên nhận",
    "BẢN GHI NHỚ": "Bản ghi nhớ",
    "BẢN THỎA THUẬN": "Bản thỏa thuận",
    "PHIẾU GỬI": "Phiếu gửi",
    "PHIẾU CHUYỂN": "Phiếu chuyển",
    "PHIẾU BÁO": "Phiếu báo",
    "THƯ CÔNG": "Thư công",
    # Văn bản QPPL (cần phân biệt nhưng có thể xuất hiện)
    "LUẬT": "Luật",
    "PHÁP LỆNH": "Pháp lệnh",
    "LỆNH": "Lệnh",
}


def normalize_co_quan(name: str) -> str:
    """
    Chuẩn hóa tên cơ quan ban hành từ UPPER CASE sang Title Case.
    Xử lý đúng quy tắc tiếng Việt: viết hoa chữ đầu mỗi cụm nghĩa.
    """
    if not name or not name.strip():
        return name

    # Nếu đã là mixed case (không phải full UPPER), giữ nguyên
    upper_ratio = sum(1 for c in name if c.isupper()) / max(len(name.replace(" ", "")), 1)
    if upper_ratio < 0.7:
        return name.strip()

    # Mapping trực tiếp cho các cơ quan phổ biến
    DIRECT_MAP = {
        "THỦ TƯỚNG CHÍNH PHỦ": "Thủ tướng Chính phủ",
        "CHÍNH PHỦ": "Chính phủ",
        "VĂN PHÒNG CHÍNH PHỦ": "Văn phòng Chính phủ",
        "VĂN PHÒNG QUỐC HỘI": "Văn phòng Quốc hội",
        "QUỐC HỘI": "Quốc hội",
    }

    stripped = name.strip()
    if stripped in DIRECT_MAP:
        return DIRECT_MAP[stripped]

    # Pattern: "BỘ XÂY DỰNG" → "Bộ Xây dựng"
    # Pattern: "ỦY BAN NHÂN DÂN TỈNH ĐẮK LẮK" → "Ủy ban nhân dân tỉnh Đắk Lắk"
    # Pattern: "CHỦ TỊCH ỦY BAN NHÂN DÂN TỈNH PHÚ THỌ" → "Chủ tịch Ủy ban nhân dân tỉnh Phú Thọ"

    # Bước 1: Tách các phần có quy tắc riêng
    result = stripped

    # Xử lý prefix "CHỦ TỊCH" nếu có
    prefix = ""
    prefix_patterns = [
        ("CHỦ TỊCH ", "Chủ tịch "),
    ]
    for pat, repl in prefix_patterns:
        if result.startswith(pat):
            prefix = repl
            result = result[len(pat):]
            break

    # Mapping cho phần chính
    ORGAN_MAP = {
        "ỦY BAN NHÂN DÂN": "Ủy ban nhân dân",
        "HỘI ĐỒNG NHÂN DÂN": "Hội đồng nhân dân",
    }
    organ_part = ""
    for pat, repl in ORGAN_MAP.items():
        if result.startswith(pat):
            organ_part = repl
            result = result[len(pat):]
            break

    # Mapping cho "BỘ ..."
    if result.startswith("BỘ "):
        organ_part = "Bộ"
        result = result[3:]
        # Phần sau "BỘ" = tên bộ, viết hoa chữ đầu
        # "XÂY DỰNG" → "Xây dựng"
        # "Y TẾ" → "Y tế"
        result = " " + _smart_title(result)
    elif organ_part:
        # Phần sau organ: " TỈNH ĐẮK LẮK" hoặc " THÀNH PHỐ HẢI PHÒNG"
        result = " " + _smart_title(result.strip())
    else:
        # Trường hợp khác: title case thông thường
        result = _smart_title(result)
        organ_part = ""

    return prefix + organ_part + result


def _smart_title(text: str) -> str:
    """
    Chuyển UPPER CASE thành Title Case thông minh cho tiếng Việt.
    Quy tắc: Viết hoa chữ đầu mỗi cụm danh từ riêng.
    """
    if not text or not text.strip():
        return text

    text = text.strip()

    # Các từ nên viết thường (trừ khi ở đầu cụm)
    LOWER_WORDS = {
        "VÀ", "CỦA", "TRONG", "NGOÀI", "TẠI", "THEO", "VỀ",
        "CHO", "ĐỐI VỚI", "TRÊN", "THUỘC", "TRỰC THUỘC",
    }

    # Tên riêng tỉnh/thành phải viết hoa: ĐẮK LẮK, PHÚ THỌ, etc.
    # Phát hiện "TỈNH X" hoặc "THÀNH PHỐ X"
    location_match = re.match(
        r'^(TỈNH|THÀNH PHỐ|HUYỆN|QUẬN|THỊ XÃ|PHƯỜNG|XÃ)\s+(.+)$',
        text, re.IGNORECASE
    )
    if location_match:
        admin_unit = location_match.group(1).lower().capitalize()
        # Tên riêng địa danh: viết hoa chữ đầu mỗi từ
        place_name = " ".join(
            w.capitalize() if len(w) > 1 else w.upper()
            for w in location_match.group(2).lower().split()
        )
        return f"{admin_unit} {place_name}"

    # Default: lowercase rồi capitalize từ đầu
    words = text.lower().split()
    if not words:
        return text

    # Capitalize từ đầu tiên luôn
    result = [words[0].capitalize()]
    for w in words[1:]:
        if w.upper() in LOWER_WORDS:
            result.append(w)
        else:
            result.append(w)  # giữ lowercase cho các từ không phải tên riêng

    return " ".join(result)


def main():
    with open(GT_PATH, 'r', encoding='utf-8') as f:
        gt = json.load(f)

    changes = {"loai_van_ban": 0, "co_quan_ban_hanh": 0}

    for filename, fields in gt.items():
        # Normalize loai_van_ban
        old_loai = fields.get("loai_van_ban", "")
        if old_loai.upper() in LOAI_VB_MAP:
            new_loai = LOAI_VB_MAP[old_loai.upper()]
            if old_loai != new_loai:
                fields["loai_van_ban"] = new_loai
                changes["loai_van_ban"] += 1

        # Normalize co_quan_ban_hanh
        old_cq = fields.get("co_quan_ban_hanh", "")
        new_cq = normalize_co_quan(old_cq)
        if old_cq != new_cq:
            fields["co_quan_ban_hanh"] = new_cq
            changes["co_quan_ban_hanh"] += 1

    # Save
    with open(GT_PATH, 'w', encoding='utf-8') as f:
        json.dump(gt, f, ensure_ascii=False, indent=2)

    print(f"✅ Normalized ground_truth.json:")
    print(f"   loai_van_ban: {changes['loai_van_ban']} changes")
    print(f"   co_quan_ban_hanh: {changes['co_quan_ban_hanh']} changes")

    # Print sample
    print("\n📋 Sample (first 5):")
    for i, (fn, fields) in enumerate(gt.items()):
        if i >= 5:
            break
        print(f"  {fn}:")
        print(f"    loai_van_ban: {fields['loai_van_ban']}")
        print(f"    co_quan_ban_hanh: {fields['co_quan_ban_hanh']}")


if __name__ == "__main__":
    main()
