# -*- coding: utf-8 -*-
"""
LLM Training Dataset Builder
==============================
Tạo instruction-following dataset (Alpaca format) từ docx files.

Nguồn: Phase1_Data_Preparation.py, line 764-863
"""

import os
import json
import re
import random
import zipfile
import xml.etree.ElementTree as ET

from src.llm.prompts import PROMPTS


def docx_to_text(docx_path: str) -> str:
    """Đọc text từ file docx (dùng zipfile, không cần python-docx)."""
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        paragraphs = []
        for p in tree.findall(f'.//{{{ns}}}p'):
            texts = [t.text for t in p.findall(f'.//{{{ns}}}t') if t.text]
            line = ''.join(texts).strip()
            if line:
                paragraphs.append(line)
        return '\n'.join(paragraphs)
    except Exception as e:
        return f"ERROR: {e}"


def extract_metadata_from_docx(docx_path: str, category: str) -> dict:
    """
    Trích xuất metadata từ file docx bằng regex.

    Returns:
        dict chứa loai_van_ban, so_hieu, ngay_ban_hanh, trich_yeu, nguoi_ky, co_quan_ban_hanh
    """
    text = docx_to_text(docx_path)
    if text.startswith("ERROR"):
        return None

    category_map = {
        'CV': 'Công văn', 'HD': 'Hợp đồng',
        'QD': 'Quy định', 'TT': 'Tờ trình', 'K': 'Khác'
    }

    metadata = {
        "loai_van_ban": category_map.get(category, "Khác"),
        "so_hieu": "", "ngay_ban_hanh": "",
        "trich_yeu": "", "nguoi_ky": "", "co_quan_ban_hanh": "",
    }

    # Số hiệu
    for pattern in [r'[Ss]ố[:\s]+(\d+[\/\-][A-ZĐa-zđ\d\/\-]+)',
                    r'[Ss]ố[:\s]+(\d+\/\d+\/[A-ZĐ\-]+)']:
        match = re.search(pattern, text)
        if match:
            metadata["so_hieu"] = match.group(1).strip()
            break

    # Ngày ban hành
    for pattern in [r'[Nn]gày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
                    r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})']:
        match = re.search(pattern, text)
        if match and len(match.groups()) == 3:
            d, m, y = match.groups()
            metadata["ngay_ban_hanh"] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"
            break

    # Trích yếu
    for pattern in [r'[Vv]\/[Vv][:\s]+(.+?)(?:\n|$)',
                    r'[Tt]rích yếu[:\s]+(.+?)(?:\n|$)']:
        match = re.search(pattern, text)
        if match:
            metadata["trich_yeu"] = match.group(1).strip()[:200]
            break

    # Người ký
    lines = text.strip().split('\n')
    for line in reversed(lines[-10:]):
        line = line.strip()
        if line and len(line) < 50 and not any(c.isdigit() for c in line):
            words = line.split()
            if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w):
                metadata["nguoi_ky"] = line
                break

    return metadata


def build_llm_instruction_dataset(docx_dir: str, output_dir: str,
                                  limit: int = None) -> list:
    """
    Tạo instruction-following dataset cho LLM fine-tuning.

    Format Alpaca: {instruction, input, output}
    Split: 80% train / 10% val / 10% test

    Args:
        docx_dir: Thư mục chứa docx (tổ chức theo category)
        output_dir: Thư mục lưu train.json, val.json, test.json
        limit: Giới hạn số file

    Returns:
        list: Dataset đã tạo
    """
    os.makedirs(output_dir, exist_ok=True)
    dataset = []

    all_files = []
    if not os.path.exists(docx_dir):
        print(f"⚠️ Thư mục không tồn tại: {docx_dir}")
        return dataset

    for category in os.listdir(docx_dir):
        cat_dir = os.path.join(docx_dir, category)
        if os.path.isdir(cat_dir):
            for f in sorted(os.listdir(cat_dir)):
                if f.endswith('.docx'):
                    all_files.append((os.path.join(cat_dir, f), category))

    if limit:
        all_files = all_files[:limit]

    classification_instruction = PROMPTS['classification'].replace('{text}', '').strip()
    extraction_instruction = PROMPTS['extraction'].replace('{text}', '').strip()

    category_map = {
        'CV': 'Công văn', 'HD': 'Hợp đồng',
        'QD': 'Quy định', 'TT': 'Tờ trình', 'K': 'Khác'
    }

    for i, (docx_path, category) in enumerate(all_files):
        text = docx_to_text(docx_path)
        if text.startswith("ERROR") or len(text) < 30:
            continue

        if len(text) > 3000:
            text = text[:3000] + "\n[...văn bản bị cắt bớt...]"

        # Task 1: Classification
        dataset.append({
            "instruction": classification_instruction,
            "input": text,
            "output": category_map.get(category, "Khác")
        })

        # Task 2: Extraction
        metadata = extract_metadata_from_docx(docx_path, category)
        if metadata:
            dataset.append({
                "instruction": extraction_instruction,
                "input": text,
                "output": json.dumps(metadata, ensure_ascii=False, indent=2)
            })

        if (i + 1) % 200 == 0:
            print(f"  📊 Đã xử lý {i+1}/{len(all_files)} files")

    # Split
    random.shuffle(dataset)
    n = len(dataset)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)

    splits = {
        'train': dataset[:train_end],
        'val': dataset[train_end:val_end],
        'test': dataset[val_end:]
    }

    for split_name, split_data in splits.items():
        output_path = os.path.join(output_dir, f"{split_name}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(split_data, f, ensure_ascii=False, indent=2)
        print(f"  💾 {split_name}: {len(split_data)} samples → {output_path}")

    print(f"\n✅ Tổng cộng tạo {len(dataset)} training samples")
    return dataset
