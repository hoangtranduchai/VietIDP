# -*- coding: utf-8 -*-
"""
Vietnamese OCR Post-processing
================================
Sửa lỗi OCR thường gặp khi nhận dạng tiếng Việt.

Mở rộng từ 4 rules (Phase3) lên 25+ rules.
"""

import re


# ═══════════════════════════════════════════════════════════════════════════
# Correction Rules
# ═══════════════════════════════════════════════════════════════════════════

# Case-sensitive exact replacements
EXACT_CORRECTIONS = {
    # Cụm từ hành chính thường bị OCR sai
    'Cộng hòa xã hội chủ nghĩa Việt nam': 'Cộng hòa xã hội chủ nghĩa Việt Nam',
    'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAm': 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM',
    'ĐỘC LẬP - Tự DO - HẠNH PHÚC': 'ĐỘC LẬP - TỰ DO - HẠNH PHÚC',
    'QUYỂT ĐINH': 'QUYẾT ĐỊNH',
    'QUYỂT ĐỊNH': 'QUYẾT ĐỊNH',
    'QUYÉT ĐỊNH': 'QUYẾT ĐỊNH',
    'QUYÊT ĐỊNH': 'QUYẾT ĐỊNH',
    'THÔNG TU': 'THÔNG TƯ',
    'THONG TƯ': 'THÔNG TƯ',
    'NGHỊ ĐINH': 'NGHỊ ĐỊNH',
    'NGHI ĐỊNH': 'NGHỊ ĐỊNH',
    'CÔNG VĂN': 'CÔNG VĂN',
    'TỜ TRINH': 'TỜ TRÌNH',
    'TỜ TRÌNH': 'TỜ TRÌNH',
    'HỢP ĐÔNG': 'HỢP ĐỒNG',

    # Chức danh
    'Giám dốc': 'Giám đốc',
    'Phó Giám dốc': 'Phó Giám đốc',
    'Chủ tich': 'Chủ tịch',
    'Phó Chủ tich': 'Phó Chủ tịch',
    'Thứ truởng': 'Thứ trưởng',
    'Bộ truởng': 'Bộ trưởng',

    # Cơ quan
    'Uỷ ban nhân dân': 'Ủy ban nhân dân',
    'UỶ BAN NHÂN DÂN': 'ỦY BAN NHÂN DÂN',
}

# Regex-based patterns (case insensitive)
REGEX_CORRECTIONS = [
    # Sửa khoảng trắng thừa trong số hiệu
    (r'Số\s*:\s*', 'Số: '),
    # Chuẩn hóa "V/v:" và "V/V:"
    (r'[Vv]\s*/\s*[Vv]\s*:', 'V/v:'),
]


def postprocess_vietnamese(text: str) -> str:
    """
    Sửa lỗi OCR thường gặp khi nhận dạng tiếng Việt.

    Args:
        text: Raw OCR text

    Returns:
        str: Text đã sửa lỗi
    """
    if not text:
        return text

    # 1. Exact replacements
    for wrong, correct in EXACT_CORRECTIONS.items():
        text = text.replace(wrong, correct)

    # 2. Regex corrections
    for pattern, replacement in REGEX_CORRECTIONS:
        text = re.sub(pattern, replacement, text)

    # 3. Chuẩn hóa khoảng trắng
    text = re.sub(r'[ \t]+', ' ', text).strip()

    # 4. Sửa khoảng trắng sai trước dấu câu
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)

    return text
