# -*- coding: utf-8 -*-
"""
Benchmark Pipeline — Ground Truth Labels cho 20 PDF
=====================================================
Tạo ground truth labels bằng cách đọc tên file + metadata từ PDF.
File PDF test đặt tên theo pattern: pdf_test_NNNN.pdf

Sử dụng: python scripts/create_ground_truth.py
Kết quả:  data/benchmark/ground_truth.json
"""

import os
import sys
import json
import re
import pathlib

# [HOTFIX] Windows UTF-8
_original_read_text = pathlib.Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    return _original_read_text(self, encoding=encoding or "utf-8", errors=errors)
pathlib.Path.read_text = _utf8_read_text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF


def extract_ground_truth_from_pdf(pdf_path: str) -> dict:
    """
    Trích xuất ground truth từ metadata + text trang 1 của PDF.
    Dùng regex chính xác (không qua OCR) để lấy thông tin chuẩn.
    """
    doc = fitz.open(pdf_path)
    
    # Lấy text trang 1 (text gốc trong PDF, không qua OCR)
    page1_text = doc[0].get_text() if len(doc) > 0 else ""
    # Lấy text trang cuối (chứa người ký)
    last_page_text = doc[-1].get_text() if len(doc) > 0 else ""
    full_text = "\n".join([doc[i].get_text() for i in range(len(doc))])
    
    doc.close()
    
    gt = {
        "loai_van_ban": "",
        "so_hieu": "",
        "ngay_ban_hanh": "",
        "co_quan_ban_hanh": "",
        "trich_yeu": "",
        "nguoi_ky": "",
    }
    
    # --- Loại văn bản ---
    for doc_type in ['QUYẾT ĐỊNH', 'CÔNG VĂN', 'THÔNG TƯ', 'NGHỊ ĐỊNH', 
                      'TỜ TRÌNH', 'HỢP ĐỒNG', 'THÔNG BÁO']:
        if doc_type in page1_text.upper():
            gt["loai_van_ban"] = doc_type.title()
            break
    if not gt["loai_van_ban"]:
        gt["loai_van_ban"] = "Khác"
    
    # --- Số hiệu ---
    match = re.search(r'[Ss]ố[:\s]+(\d+[\/_\-][A-ZĐa-zđ\d\/_\-]+)', page1_text)
    if match:
        gt["so_hieu"] = match.group(1).replace("_", "/")
    
    # --- Ngày ban hành ---
    match = re.search(
        r'[Nn]gày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', page1_text
    )
    if match:
        d, m, y = match.groups()
        gt["ngay_ban_hanh"] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    
    # --- Cơ quan ban hành ---
    # Thử tìm cơ quan từ header (thường ở dòng đầu, trước Quốc hiệu)
    lines = page1_text.strip().split('\n')
    for line in lines[:10]:
        line_upper = line.strip().upper()
        if any(kw in line_upper for kw in ['BỘ ', 'ỦY BAN', 'UBND', 'SỞ ', 'CHÍNH PHỦ', 
                                            'THỦ TƯỚNG', 'QUỐC HỘI', 'HỘI ĐỒNG']):
            if 'CỘNG HÒA' not in line_upper and 'ĐỘC LẬP' not in line_upper:
                gt["co_quan_ban_hanh"] = line.strip()
                break
    
    # --- Trích yếu ---
    # Tìm sau "V/v" hoặc sau tên loại văn bản
    match = re.search(r'[Vv]/[Vv][:\s]+(.+?)(?:\n|$)', page1_text)
    if match:
        gt["trich_yeu"] = match.group(1).strip()[:200]
    else:
        # Tìm dòng sau QUYẾT ĐỊNH, THÔNG TƯ, etc.
        for doc_type in ['QUYẾT ĐỊNH', 'CÔNG VĂN', 'THÔNG TƯ', 'NGHỊ ĐỊNH']:
            idx = page1_text.upper().find(doc_type)
            if idx >= 0:
                after = page1_text[idx + len(doc_type):].strip()
                first_line = after.split('\n')[0].strip()
                if first_line and len(first_line) > 10:
                    gt["trich_yeu"] = first_line[:200]
                    break
    
    # --- Người ký ---
    # Tìm từ cuối trang cuối: pattern TM., KT., Q., chức vụ + tên
    for pattern in [
        r'(?:TM\.|KT\.|TL\.|Q\.)\s*[A-ZĐ\s]+\n+([\w\s]+)',  # TM. CHỦ TỊCH\nNguyễn Văn A
        r'(?:CHỦ TỊCH|THỦ TƯỚNG|BỘ TRƯỞNG|GIÁM ĐỐC)\s*\n+\s*\n*([\w\s]+\w)',
    ]:
        match = re.search(pattern, last_page_text)
        if match:
            name = match.group(1).strip()
            if len(name) > 3 and len(name) < 50:
                gt["nguoi_ky"] = name
                break
    
    return gt


def main():
    pdf_dir = os.path.join("data", "raw", "pdf_test")
    output_dir = os.path.join("data", "benchmark")
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_files = sorted([
        f for f in os.listdir(pdf_dir) if f.endswith('.pdf')
    ])[:20]
    
    print(f"📊 Tạo Ground Truth cho {len(pdf_files)} PDF files...\n")
    
    ground_truth = {}
    for pdf_name in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_name)
        print(f"  📄 {pdf_name}...", end=" ")
        
        try:
            gt = extract_ground_truth_from_pdf(pdf_path)
            ground_truth[pdf_name] = gt
            
            filled = sum(1 for v in gt.values() if v)
            print(f"✅ {filled}/6 trường")
        except Exception as e:
            print(f"❌ {e}")
            ground_truth[pdf_name] = {
                "loai_van_ban": "", "so_hieu": "", "ngay_ban_hanh": "",
                "co_quan_ban_hanh": "", "trich_yeu": "", "nguoi_ky": ""
            }
    
    output_path = os.path.join(output_dir, "ground_truth.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved: {output_path}")
    print(f"📊 Total: {len(ground_truth)} files")
    
    # Thống kê
    total_fields = 0
    filled_fields = 0
    for gt in ground_truth.values():
        for v in gt.values():
            total_fields += 1
            if v:
                filled_fields += 1
    
    print(f"📈 Fields filled: {filled_fields}/{total_fields} ({filled_fields/total_fields*100:.1f}%)")


if __name__ == "__main__":
    main()
