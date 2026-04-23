# -*- coding: utf-8 -*-
"""
LLM Dataset Builder
===================
Trích xuất thông tin (Metadata) từ các file `.docx` mẫu và chuyển đổi thành
tập dữ liệu (Dataset) chuẩn JSONL để huấn luyện mô hình ngôn ngữ lớn (LLM).
"""

import os
import sys
import json
import glob

# Fix python path for importing src from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from docx import Document
from tqdm import tqdm

from src.config import Config

class DatasetBuilder:
    def __init__(self, data_dir=Config.RAW_DOCX_DIR, output_dir=Config.LLM_TRAINING_DIR):
        self.data_dir = data_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def extract_text_from_docx(self, docx_path):
        """Đọc toàn bộ text từ file Word."""
        try:
            doc = Document(docx_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            full_text.append(f"[TABLE] {cell.text.strip()}")
            return '\n'.join(full_text)
        except Exception as e:
            print(f"Error reading {docx_path}: {e}")
            return None

    def construct_synthetic_json_label(self, text):
        """
        Nội suy nhãn JSON từ văn bản (.docx) sạch.
        Vì đây là data tổng hợp mô phỏng, ta dùng regex tĩnh để sinh Ground Truth.
        """
        # Logic bóc xuất trường thông tin đơn giản cho mẫu LLM
        so_hieu = ""
        ngay_ban_hanh = ""
        trich_yeu = ""
        nguoi_ky = ""
        
        lines = text.split('\n')
        for i, line in enumerate(lines[:15]): # Tìm trong 15 dòng đầu
            if "Số:" in line or "Số /" in line:
                so_hieu = line.strip()
            if "Ngày" in line and "tháng" in line and "năm" in line:
                ngay_ban_hanh = line.strip()
            if "V/v" in line or "Về việc" in line:
                trich_yeu = line.strip()
                
        # Tìm chữ ký ở 10 dòng cuối
        for line in lines[-10:]:
            if line.isupper() and len(line) < 30 and " " in line:
                nguoi_ky = line.strip()

        return json.dumps({
            "so_hieu": so_hieu,
            "ngay_ban_hanh": ngay_ban_hanh,
            "trich_yeu": trich_yeu,
            "nguoi_ky": nguoi_ky
        }, ensure_ascii=False)

    def build_qlora_dataset(self):
        """Build file train.jsonl cho Unsloth SFTTrainer."""
        docx_files = glob.glob(os.path.join(self.data_dir, "**/*.docx"), recursive=True)
        if not docx_files:
            print(f"⚠️ Không tìm thấy file docx tại {self.data_dir}. Sinh data giả lập để test script.")
            # Mock data để script train không bị rỗng
            docx_files = ["mock1.docx", "mock2.docx"]
            
        output_file = os.path.join(self.output_dir, "train.jsonl")
        
        system_prompt = "Bạn là chuyên viên văn thư. Hãy trích xuất các thông tin hành chính từ văn bản OCR sau và trả về định dạng JSON nghiêm ngặt."
        
        records_created = 0
        with open(output_file, 'w', encoding='utf-8') as f:
            for file_path in tqdm(docx_files, desc="Parsing Docx to LLM JSONL"):
                if "mock" in file_path:
                    # Mock logic
                    text = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n\nSố: 123/QĐ-UBND\nNgày 01 tháng 01 năm 2026\n\nQUYẾT ĐỊNH\nVề việc nâng cấp hệ thống AI\n\nCHỦ TỊCH\nNGUYỄN VĂN A"
                else:
                    text = self.extract_text_from_docx(file_path)
                    
                if not text:
                    continue
                    
                json_label = self.construct_synthetic_json_label(text)
                
                # Định dạng sharegpt/alpaca cho Unsloth
                record = {
                    "instruction": system_prompt,
                    "input": text,
                    "output": json_label
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                records_created += 1
                
        print(f"✅ Đã tạo thành công {records_created} mẫu huấn luyện tại {output_file}")

if __name__ == "__main__":
    builder = DatasetBuilder()
    builder.build_qlora_dataset()
