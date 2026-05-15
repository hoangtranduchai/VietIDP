# -*- coding: utf-8 -*-
"""
Test QLoRA Fine-tuned Model
============================
Kiểm tra chất lượng trích xuất của model QLoRA đã train xong.

Sử dụng:
  python scripts/test_qlora.py                    # Test 5 mẫu ngẫu nhiên từ dataset
  python scripts/test_qlora.py --num_samples 10   # Test 10 mẫu
"""

import os
import sys
import json
import random
import argparse
import pathlib

# [HOTFIX] Windows UTF-8
_original_read_text = pathlib.Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    return _original_read_text(self, encoding=encoding or "utf-8", errors=errors)
pathlib.Path.read_text = _utf8_read_text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from unsloth import FastLanguageModel
except ImportError:
    pass

import torch
from src.config import Config

FIELDS = ["loai_van_ban", "so_hieu", "ngay_ban_hanh", "co_quan_ban_hanh", "trich_yeu", "nguoi_ky"]

ALPACA_PROMPT = """Dưới đây là một lệnh mô tả nhiệm vụ. Hãy viết một phản hồi hoàn thành xuất sắc yêu cầu đó.

### Lệnh (Instruction):
{}

### Đầu vào (Input OCR):
{}

### Phản hồi JSON (Response):
"""

def load_model():
    """Nạp base model + LoRA adapter đã train."""
    print("📥 Đang nạp model + LoRA adapter...")
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = str(Config.LLM_ADAPTER_PATH),
        max_seq_length = Config.LLM_MAX_SEQ_LENGTH,
        dtype = None,
        load_in_4bit = True,
    )
    FastLanguageModel.for_inference(model)  # Bật chế độ inference (nhanh 2x)
    print("✅ Model đã sẵn sàng!\n")
    return model, tokenizer

def extract(model, tokenizer, instruction, ocr_text):
    """Chạy inference trên 1 mẫu, trả về JSON string."""
    prompt = ALPACA_PROMPT.format(instruction, ocr_text)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.1,
            do_sample=False,
            use_cache=True,
        )

    # Decode chỉ phần response (bỏ phần prompt)
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return response.strip()

def parse_json_safe(text):
    """Cố parse JSON từ output, xử lý trường hợp model trả thêm text thừa."""
    # Tìm cặp {} đầu tiên
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None

def evaluate(predicted, expected):
    """So sánh từng trường, trả về dict kết quả."""
    results = {}
    for field in FIELDS:
        pred_val = predicted.get(field, "") if predicted else ""
        exp_val = expected.get(field, "")
        # Normalize: strip, lowercase cho so sánh
        match = str(pred_val).strip().lower() == str(exp_val).strip().lower()
        results[field] = {
            "expected": exp_val,
            "predicted": pred_val,
            "match": match,
        }
    return results

def main(args):
    # 1. Load test data
    dataset_path = os.path.join(Config.LLM_TRAINING_DIR, "train.jsonl")
    if not os.path.exists(dataset_path):
        print(f"❌ Không tìm thấy dataset tại {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        all_samples = [json.loads(line) for line in f]

    # Chọn mẫu ngẫu nhiên
    random.seed(42)
    samples = random.sample(all_samples, min(args.num_samples, len(all_samples)))
    print(f"📊 Test {len(samples)} mẫu ngẫu nhiên từ {len(all_samples)} mẫu\n")

    # 2. Load model
    model, tokenizer = load_model()

    # 3. Chạy test
    total_fields = 0
    correct_fields = 0
    exact_match = 0
    json_parse_ok = 0

    for i, sample in enumerate(samples):
        print(f"{'='*60}")
        print(f"📝 MẪU {i+1}/{len(samples)}")

        instruction = sample["instruction"]
        ocr_input = sample["input"]
        expected_output = json.loads(sample["output"])

        # Inference
        raw_output = extract(model, tokenizer, instruction, ocr_input)
        predicted = parse_json_safe(raw_output)

        if predicted is not None:
            json_parse_ok += 1

        # Evaluate
        results = evaluate(predicted, expected_output)

        sample_correct = 0
        for field, r in results.items():
            status = "✅" if r["match"] else "❌"
            total_fields += 1
            if r["match"]:
                correct_fields += 1
                sample_correct += 1
            print(f"  {status} {field}:")
            print(f"       Expected:  {r['expected']}")
            print(f"       Got:       {r['predicted']}")

        if sample_correct == len(FIELDS):
            exact_match += 1
            print(f"  🏆 EXACT MATCH!")
        print()

    # 4. Summary
    n = len(samples)
    field_accuracy = correct_fields / total_fields * 100 if total_fields > 0 else 0
    exact_match_rate = exact_match / n * 100 if n > 0 else 0
    json_rate = json_parse_ok / n * 100 if n > 0 else 0

    print(f"\n{'='*60}")
    print(f"📊 KẾT QUẢ TỔNG HỢP ({n} mẫu)")
    print(f"{'='*60}")
    print(f"  JSON hợp lệ:     {json_parse_ok}/{n} ({json_rate:.1f}%)")
    print(f"  Field Accuracy:   {correct_fields}/{total_fields} ({field_accuracy:.1f}%)")
    print(f"  Exact Match:      {exact_match}/{n} ({exact_match_rate:.1f}%)")
    print(f"{'='*60}")

    # Đánh giá
    if field_accuracy >= 90:
        print("  🏆 XUẤT SẮC — Model sẵn sàng tích hợp vào pipeline!")
    elif field_accuracy >= 75:
        print("  ✅ TỐT — Có thể dùng được, cần cải thiện thêm dataset.")
    elif field_accuracy >= 50:
        print("  ⚠️ TRUNG BÌNH — Cần train thêm hoặc bổ sung dữ liệu.")
    else:
        print("  ❌ YẾU — Cần kiểm tra lại pipeline training.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test QLoRA model extraction accuracy")
    parser.add_argument("--num_samples", type=int, default=5,
                        help="Số mẫu ngẫu nhiên để test (mặc định: 5)")
    args = parser.parse_args()
    main(args)
