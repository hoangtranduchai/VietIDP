# -*- coding: utf-8 -*-
"""
QLoRA Training Dataset Builder
================================
Đọc tất cả file DOCX từ data/raw_word_files/ và sinh training data
cho QLoRA fine-tune Qwen2.5-7B theo format Alpaca (instruction/input/output).

Sử dụng:
  $env:PYTHONIOENCODING = "utf-8"
  python scripts/build_qlora_dataset.py

Output:
  data/llm_training/train.jsonl  (cho scripts/train_qlora.py)
"""

import os
import sys
import json
import re
import random
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import Config

try:
    from docx import Document
except ImportError:
    print("❌ Cần cài python-docx: pip install python-docx")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# Mapping thư mục → loại văn bản
# ═══════════════════════════════════════════════════════════════════════════

DIR_TO_LOAI = {
    "CV": "Công văn",
    "HD": "Hợp đồng",
    "K": "Khác",
    "QD": "Quyết định",
    "TT": "Thông tư",
}

# ═══════════════════════════════════════════════════════════════════════════
# Cơ quan ban hành mẫu (đa dạng)
# ═══════════════════════════════════════════════════════════════════════════

CO_QUAN_SAMPLES = [
    "Ủy ban nhân dân tỉnh Bình Dương",
    "Bộ Giáo dục và Đào tạo",
    "Bộ Y tế",
    "Bộ Tài chính",
    "Bộ Công an",
    "Bộ Quốc phòng",
    "Bộ Ngoại giao",
    "Bộ Nông nghiệp và Phát triển nông thôn",
    "Bộ Công Thương",
    "Bộ Giao thông vận tải",
    "Bộ Xây dựng",
    "Bộ Tư pháp",
    "Bộ Lao động - Thương binh và Xã hội",
    "Bộ Khoa học và Công nghệ",
    "Bộ Tài nguyên và Môi trường",
    "Bộ Thông tin và Truyền thông",
    "Bộ Văn hóa, Thể thao và Du lịch",
    "Bộ Kế hoạch và Đầu tư",
    "Bộ Nội vụ",
    "Thủ tướng Chính phủ",
    "Văn phòng Chính phủ",
    "Ủy ban nhân dân thành phố Hà Nội",
    "Ủy ban nhân dân thành phố Hồ Chí Minh",
    "Ủy ban nhân dân thành phố Đà Nẵng",
    "Ủy ban nhân dân tỉnh Nghệ An",
    "Ủy ban nhân dân tỉnh Thanh Hóa",
    "Sở Giáo dục và Đào tạo tỉnh Bình Dương",
    "Sở Y tế thành phố Hồ Chí Minh",
    "Sở Kế hoạch và Đầu tư thành phố Hà Nội",
    "Trường Đại học Bách khoa Hà Nội",
    "Trường Đại học Quốc gia Hà Nội",
    "Trường Đại học Quốc gia Thành phố Hồ Chí Minh",
    "Ngân hàng Nhà nước Việt Nam",
    "Tổng cục Thuế",
    "Tổng cục Hải quan",
    "Thanh tra Chính phủ",
    "Kiểm toán Nhà nước",
]

CHUC_VU_SAMPLES = [
    "CHỦ TỊCH", "PHÓ CHỦ TỊCH",
    "GIÁM ĐỐC", "PHÓ GIÁM ĐỐC",
    "BỘ TRƯỞNG", "THỨ TRƯỞNG",
    "TỔNG GIÁM ĐỐC", "PHÓ TỔNG GIÁM ĐỐC",
    "HIỆU TRƯỞNG", "PHÓ HIỆU TRƯỞNG",
    "TRƯỞNG PHÒNG", "PHÓ TRƯỞNG PHÒNG",
    "CHÁNH VĂN PHÒNG", "PHÓ CHÁNH VĂN PHÒNG",
]

HO_TEN_SAMPLES = [
    "Nguyễn Văn An", "Trần Thị Bình", "Lê Hoàng Cường",
    "Phạm Minh Đức", "Hoàng Thị Hương", "Vũ Đức Khoa",
    "Đặng Ngọc Linh", "Bùi Quang Minh", "Ngô Thị Ngọc",
    "Đỗ Hữu Phước", "Trịnh Xuân Quân", "Lý Thanh Sơn",
    "Cao Thị Thảo", "Đinh Văn Uy", "Hà Anh Vinh",
    "Mai Thị Xuân", "Phan Đình Yên", "Dương Bảo Châu",
    "Lương Thế Dũng", "Tạ Quốc Hùng", "Nguyễn Thị Kim",
    "Trần Đại Long", "Phạm Thị Mỹ", "Lê Văn Nam",
    "Hoàng Hữu Ân", "Vũ Thị Bích", "Đặng Quốc Cảnh",
    "Bùi Thị Diệp", "Ngô Xuân Em", "Đỗ Thị Pha",
]

DIA_DANH_SAMPLES = [
    "Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng",
    "Cần Thơ", "Bình Dương", "Đồng Nai", "Nghệ An",
    "Thanh Hóa", "Quảng Ninh", "Thừa Thiên Huế", "Khánh Hòa",
]

KY_HIEU_MAP = {
    "Công văn": ["CV", "UBND", "VP", "SGDDT"],
    "Hợp đồng": ["HĐKT", "HĐLĐ", "HĐDV", "HĐ"],
    "Quyết định": ["QĐ-UBND", "QĐ-TTg", "QĐ-BGD", "QĐ-BYT"],
    "Thông tư": ["TT-BGD", "TT-BTC", "TT-BCA", "TT-BYT"],
    "Khác": ["TB", "BB", "BC", "TTr"],
}


def extract_text_from_docx(filepath: str) -> str:
    """Đọc nội dung text từ file DOCX."""
    try:
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return ""


def extract_trich_yeu(text: str, loai: str) -> str:
    """Trích xuất trích yếu từ text."""
    # Tìm dòng "V/v: ..."
    m = re.search(r'V\s*/\s*[Vv]\s*[:：]\s*(.+)', text)
    if m:
        return m.group(1).strip()[:200]

    # Tìm dòng "Về việc ..."
    m = re.search(r'Về\s+việc\s+(.+)', text)
    if m:
        return "Về việc " + m.group(1).strip()[:200]

    # Lấy dòng đầu tiên sau tên loại
    lines = text.strip().split('\n')
    for i, line in enumerate(lines):
        if loai.upper() in line.upper() and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and len(next_line) > 5:
                return next_line[:200]

    # Fallback: dòng có nội dung đầu tiên (>10 ký tự)
    for line in lines[:5]:
        line = line.strip()
        if len(line) > 10 and "CỘNG HÒA" not in line:
            return line[:200]

    return ""


def generate_so_hieu(loai: str, idx: int) -> str:
    """Tạo số hiệu văn bản ngẫu nhiên nhưng hợp lệ."""
    ky_hieu = random.choice(KY_HIEU_MAP.get(loai, ["VB"]))
    num = random.randint(1, 999)
    year = random.choice([2023, 2024, 2025, 2026])
    return f"{num}/{year}/{ky_hieu}"


def generate_ngay() -> str:
    """Tạo ngày ban hành ngẫu nhiên."""
    d = random.randint(1, 28)
    m = random.randint(1, 12)
    y = random.choice([2023, 2024, 2025, 2026])
    return f"{d:02d}/{m:02d}/{y}"


def add_ocr_noise(text: str, noise_rate: float = 0.05) -> str:
    """
    Mô phỏng lỗi OCR thực tế (dấu sai, ký tự thay thế).
    noise_rate: tỷ lệ ký tự bị thay đổi (0.0–0.2)
    """
    if noise_rate <= 0:
        return text

    # Các lỗi OCR thường gặp với tiếng Việt
    ocr_errors = {
        'ệ': ['ê', 'e'], 'ạ': ['a'], 'ả': ['a'], 'ã': ['a'],
        'ẻ': ['e'], 'ẽ': ['e'], 'ọ': ['o'], 'ỏ': ['o'],
        'ũ': ['u'], 'ụ': ['u'], 'ủ': ['u'], 'ừ': ['u'],
        'ỳ': ['y'], 'ỵ': ['y'], 'ỷ': ['y'],
        'ắ': ['a'], 'ằ': ['a'], 'ặ': ['a'],
        'ố': ['o'], 'ồ': ['o'], 'ổ': ['o'],
        'ứ': ['u'], 'ử': ['u'], 'ữ': ['u'],
        '0': ['O'], 'O': ['0'], 'l': ['1'], '1': ['l'],
    }

    chars = list(text)
    for i in range(len(chars)):
        if random.random() < noise_rate and chars[i] in ocr_errors:
            chars[i] = random.choice(ocr_errors[chars[i]])
    return ''.join(chars)


INSTRUCTION_TEMPLATE = (
    "Bạn là hệ thống AI chuyên gia trích xuất thông tin từ văn bản hành chính "
    "Việt Nam theo Nghị định 30/2020/NĐ-CP. Đọc văn bản OCR sau và trích xuất "
    "chính xác 6 trường: loai_van_ban, so_hieu, ngay_ban_hanh, co_quan_ban_hanh, "
    "trich_yeu, nguoi_ky. Trả về JSON duy nhất, không giải thích."
)


def build_one_sample(
    filepath: str,
    loai_dir: str,
    idx: int,
    noise_rate: float = 0.0,
) -> dict | None:
    """Tạo 1 mẫu training từ 1 file DOCX."""
    text = extract_text_from_docx(filepath)
    if not text or len(text) < 50:
        return None

    loai = DIR_TO_LOAI.get(loai_dir, "Khác")

    # Giới hạn text → max 3000 ký tự (1 trang)
    if len(text) > 3000:
        text = text[:3000]

    # Sinh metadata
    so_hieu = generate_so_hieu(loai, idx)
    ngay = generate_ngay()
    co_quan = random.choice(CO_QUAN_SAMPLES)
    chuc_vu = random.choice(CHUC_VU_SAMPLES)
    ho_ten = random.choice(HO_TEN_SAMPLES)
    nguoi_ky = f"{chuc_vu} {ho_ten}"
    dia_danh = random.choice(DIA_DANH_SAMPLES)
    trich_yeu = extract_trich_yeu(text, loai)

    if not trich_yeu:
        trich_yeu = f"Về việc triển khai công tác hành chính năm {random.choice([2024, 2025, 2026])}"

    # Tạo header giả lập OCR (chèn trước nội dung)
    ocr_header = (
        f"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
        f"Độc lập - Tự do - Hạnh phúc\n"
        f"────────────────\n"
        f"{co_quan.upper()}\n"
        f"Số: {so_hieu}\n"
        f"{dia_danh}, ngày {ngay[0:2]} tháng {ngay[3:5]} năm {ngay[6:]}\n\n"
        f"{loai.upper()}\n"
        f"{trich_yeu}\n\n"
    )

    ocr_footer = (
        f"\n\n{chuc_vu}\n"
        f"(Đã ký)\n"
        f"{ho_ten}\n\n"
        f"Nơi nhận:\n"
        f"- Như trên;\n"
        f"- Lưu: VT.\n"
    )

    # Tạo input giả lập OCR
    ocr_text = ocr_header + text + ocr_footer

    # Thêm noise OCR nếu cần
    if noise_rate > 0:
        ocr_text = add_ocr_noise(ocr_text, noise_rate)

    # Tạo output chuẩn (ground truth)
    output_json = {
        "loai_van_ban": loai,
        "so_hieu": so_hieu,
        "ngay_ban_hanh": ngay,
        "co_quan_ban_hanh": co_quan,
        "trich_yeu": trich_yeu,
        "nguoi_ky": nguoi_ky,
    }

    return {
        "instruction": INSTRUCTION_TEMPLATE,
        "input": ocr_text,
        "output": json.dumps(output_json, ensure_ascii=False),
    }


def main():
    print("🚀 BẮT ĐẦU SINH TRAINING DATA CHO QLoRA")
    print("=" * 60)

    raw_dir = Config.RAW_DOCX_DIR
    output_dir = Config.LLM_TRAINING_DIR
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "train.jsonl")

    samples = []
    stats = {}

    for loai_dir in sorted(os.listdir(raw_dir)):
        loai_path = os.path.join(raw_dir, loai_dir)
        if not os.path.isdir(loai_path):
            continue

        files = sorted([
            f for f in os.listdir(loai_path)
            if f.endswith('.docx') and not f.startswith('~')
        ])

        print(f"\n📁 {loai_dir} ({DIR_TO_LOAI.get(loai_dir, '?')}): {len(files)} files")
        count = 0

        for idx, fname in enumerate(files):
            fpath = os.path.join(loai_path, fname)

            # ── Variant 1: Clean OCR (noise_rate=0) ──────────────
            sample = build_one_sample(fpath, loai_dir, idx, noise_rate=0.0)
            if sample:
                samples.append(sample)
                count += 1

            # ── Variant 2: Noisy OCR (noise_rate=0.03) ───────────
            sample_noisy = build_one_sample(fpath, loai_dir, idx, noise_rate=0.03)
            if sample_noisy:
                samples.append(sample_noisy)
                count += 1

            # ── Variant 3: Missing fields (10% chance) ───────────
            if random.random() < 0.10:
                sample_missing = build_one_sample(fpath, loai_dir, idx, noise_rate=0.0)
                if sample_missing:
                    # Randomly remove 1-2 fields
                    output = json.loads(sample_missing["output"])
                    removable = ["so_hieu", "ngay_ban_hanh", "nguoi_ky"]
                    for field in random.sample(removable, k=random.randint(1, 2)):
                        output[field] = ""
                    sample_missing["output"] = json.dumps(output, ensure_ascii=False)
                    samples.append(sample_missing)
                    count += 1

        stats[loai_dir] = count
        print(f"  ✅ Sinh {count} mẫu")

    # Shuffle
    random.seed(42)
    random.shuffle(samples)

    # Write JSONL
    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    print(f"\n{'=' * 60}")
    print(f"📊 TỔNG KẾT:")
    print(f"  Tổng samples: {len(samples)}")
    for k, v in stats.items():
        print(f"  - {k} ({DIR_TO_LOAI.get(k, '?')}): {v}")
    print(f"\n✅ Output: {output_path}")
    print(f"   Size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    print(f"\n🎯 Tiếp theo: chạy 'python scripts/train_qlora.py' để fine-tune!")


if __name__ == "__main__":
    main()
