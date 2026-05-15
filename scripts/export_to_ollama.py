# -*- coding: utf-8 -*-
"""
Export QLoRA Model → Ollama
============================
Merge LoRA adapters vào base model → tạo Modelfile → import vào Ollama.

Ollama hỗ trợ import trực tiếp từ safetensors (không cần GGUF thủ công).

Sử dụng:
  python scripts/export_to_ollama.py

Sau đó chạy:
  cd models/ollama
  ollama create vietidp:latest -f Modelfile
"""

import os
import sys
import pathlib

# [HOTFIX] Windows UTF-8
_original_read_text = pathlib.Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    return _original_read_text(self, encoding=encoding or "utf-8", errors=errors)
pathlib.Path.read_text = _utf8_read_text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config


def main():
    print("=" * 60)
    print("🚀 Export QLoRA → Ollama (Safetensors)")
    print("=" * 60)

    output_dir = os.path.join("models", "ollama")
    merged_dir = os.path.join(output_dir, "vietidp-qwen2.5")

    # Kiểm tra xem đã merge chưa (từ lần chạy trước)
    merged_exists = os.path.exists(merged_dir) and any(
        f.endswith('.safetensors') for f in os.listdir(merged_dir)
    )

    if merged_exists:
        print(f"\n✅ Đã tìm thấy merged model tại: {merged_dir}")
        print("   (Bỏ qua bước merge, dùng kết quả từ lần chạy trước)")
    else:
        # ── Step 1: Merge LoRA → 16-bit safetensors ──
        try:
            from unsloth import FastLanguageModel
        except ImportError:
            print("❌ Chưa cài unsloth. Chạy: pip install unsloth")
            return

        adapter_path = str(Config.LLM_ADAPTER_PATH)
        if not os.path.exists(os.path.join(adapter_path, "adapter_model.safetensors")):
            print(f"❌ Không tìm thấy LoRA adapter tại {adapter_path}")
            return

        os.makedirs(output_dir, exist_ok=True)

        print("\n[1/2] Đang nạp base model + LoRA adapters...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=adapter_path,
            max_seq_length=Config.LLM_INFERENCE_SEQ_LENGTH,
            dtype=None,
            load_in_4bit=True,
        )
        print("  ✅ Model loaded")

        print("\n[2/2] Đang merge và lưu 16-bit safetensors...")
        model.save_pretrained_merged(
            merged_dir,
            tokenizer,
            save_method="merged_16bit",
        )
        print(f"  ✅ Merged model saved: {merged_dir}")

    # ── Tạo Modelfile ──
    print("\n📄 Đang tạo Modelfile...")

    modelfile_content = '''FROM ./vietidp-qwen2.5

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

SYSTEM """BẠN LÀ hệ thống AI chuyên gia pháp lý và lưu trữ dữ liệu hành chính Việt Nam. Nhiệm vụ: đọc văn bản OCR và trích xuất CHÍNH XÁC các trường thông tin hành chính theo cấu trúc Nghị định 30/2020/NĐ-CP.

CÁC TRƯỜNG CẦN TRÍCH XUẤT:
- loai_van_ban: Loại văn bản (Công văn / Hợp đồng / Quyết định / Tờ trình / Thông tư / Nghị định / Thông báo / Khác)
- so_hieu: Số ký hiệu văn bản (giữ nguyên dạng gốc)
- ngay_ban_hanh: Ngày ban hành theo định dạng DD/MM/YYYY
- co_quan_ban_hanh: Tên đầy đủ cơ quan ban hành (KHÔNG viết tắt)
- trich_yeu: Trích yếu nội dung
- nguoi_ky: Họ tên người ký (KHÔNG lấy chức danh, watermark, hoặc chữ ký số)

CHỈ trả về JSON thuần túy, KHÔNG giải thích. Nếu không tìm thấy, trả về chuỗi rỗng."""

PARAMETER temperature 0.1
PARAMETER num_predict 512
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
'''

    modelfile_path = os.path.join(output_dir, "Modelfile")
    with open(modelfile_path, 'w', encoding='utf-8') as f:
        f.write(modelfile_content)
    print(f"  ✅ Modelfile: {modelfile_path}")

    # ── Thống kê ──
    total_size = 0
    safetensor_files = []
    for f in os.listdir(merged_dir):
        fpath = os.path.join(merged_dir, f)
        if os.path.isfile(fpath):
            fsize = os.path.getsize(fpath)
            total_size += fsize
            if f.endswith('.safetensors'):
                safetensor_files.append(f"{f} ({fsize / (1024**3):.2f} GB)")

    abs_output = os.path.abspath(output_dir)

    print(f"\n{'=' * 60}")
    print("✅ EXPORT HOÀN TẤT!")
    print(f"{'=' * 60}")
    print(f"\n📦 Merged model: {merged_dir}")
    for sf in safetensor_files:
        print(f"   • {sf}")
    print(f"   Tổng: {total_size / (1024**3):.2f} GB")
    print(f"📄 Modelfile: {modelfile_path}")
    print(f"\n{'=' * 60}")
    print("🔧 BƯỚC TIẾP THEO — Chạy 2 lệnh trong PowerShell:")
    print(f"{'=' * 60}")
    print(f"\n   cd {abs_output}")
    print(f"   ollama create vietidp:latest -f Modelfile")
    print(f"\n   Rồi test:")
    print(f"   ollama run vietidp:latest \"Test\"")


if __name__ == "__main__":
    main()
