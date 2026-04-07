# -*- coding: utf-8 -*-
"""
Phase 4: LLM Fine-tuning - Qwen-2.5-7B với QLoRA
==================================================
Notebook chạy trên Google Colab (CẦN GPU - T4/A100).

Module "The Brain": Tinh chỉnh mô hình ngôn ngữ lớn Qwen-2.5-7B-Instruct
để thực hiện:
1. Phân loại văn bản hành chính (5 loại)
2. Trích xuất thông tin (Key-Value → JSON)

Kỹ thuật: QLoRA (4-bit quantization + LoRA adapters)
VRAM yêu cầu: ~5.5 GB (chạy được trên T4 16GB / RTX 3060 8GB+)
"""

# ==============================================================================
# CELL 1: CÀI ĐẶT (Chạy 1 lần trên Colab)
# ==============================================================================
# !pip install -q torch torchvision torchaudio
# !pip install -q transformers>=4.40.0 datasets accelerate
# !pip install -q peft>=0.10.0 bitsandbytes>=0.43.0
# !pip install -q trl>=0.8.0      # Supervised Fine-Tuning Trainer
# !pip install -q wandb            # Optional: logging

import os
import json
import torch
from datetime import datetime

# ==============================================================================
# CELL 2: CẤU HÌNH
# ==============================================================================
# --- Google Colab ---
# from google.colab import drive
# drive.mount('/content/drive')
# BASE_DIR = "/content/drive/MyDrive/OCR-LLM_Research"

# --- Local ---
BASE_DIR = r"E:\OCR-LLM_Research"

LLM_TRAINING_DIR = os.path.join(BASE_DIR, "data/llm_training")
MODEL_OUTPUT_DIR = os.path.join(BASE_DIR, "models/qwen_finetuned")
os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)

# === HYPERPARAMETERS ===
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"  # Base model
MAX_SEQ_LENGTH = 2048       # Context window
BATCH_SIZE = 2              # Per-device batch size
GRADIENT_ACCUM = 8          # Effective batch = 2 * 8 = 16
NUM_EPOCHS = 3              # Số epoch (3-5 là đủ cho fine-tuning)
LEARNING_RATE = 2e-4        # Learning rate cho LoRA
WARMUP_RATIO = 0.03
WEIGHT_DECAY = 0.01

# LoRA Config
LORA_R = 16                 # LoRA rank
LORA_ALPHA = 32             # LoRA scaling
LORA_DROPOUT = 0.05
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj",
                  "gate_proj", "up_proj", "down_proj"]

# Quantization
LOAD_IN_4BIT = True         # QLoRA: 4-bit quantization

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"✅ Device: {DEVICE}")
if torch.cuda.is_available():
    print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
    mem = torch.cuda.get_device_properties(0).total_mem / 1e9
    print(f"✅ VRAM: {mem:.1f} GB")


# ==============================================================================
# CELL 3: LOAD & PREPARE DATASET
# ==============================================================================
from datasets import Dataset as HFDataset


def load_training_data(data_dir):
    """
    Load instruction dataset (Alpaca format) từ JSON files.

    Format mỗi sample:
    {
        "instruction": "...",
        "input": "<nội dung văn bản>",
        "output": "<kết_quả_JSON>"
    }
    """
    datasets = {}
    for split in ['train', 'val', 'test']:
        path = os.path.join(data_dir, f"{split}.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            datasets[split] = HFDataset.from_list(data)
            print(f"  📦 {split}: {len(data)} samples")
        else:
            print(f"  ⚠️ {split}.json not found!")

    return datasets


def format_prompt(sample, tokenizer):
    """
    Format prompt theo Qwen chat template.

    Qwen2.5-Instruct sử dụng ChatML format:
    <|im_start|>system
    You are a helpful assistant.<|im_end|>
    <|im_start|>user
    {instruction}\n{input}<|im_end|>
    <|im_start|>assistant
    {output}<|im_end|>
    """
    system_msg = (
        "Bạn là chuyên gia phân tích văn bản hành chính Việt Nam. "
        "Hãy thực hiện yêu cầu một cách chính xác và trả lời bằng tiếng Việt."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"{sample['instruction']}\n\n{sample['input']}"},
        {"role": "assistant", "content": sample['output']}
    ]

    # Sử dụng tokenizer.apply_chat_template
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False
    )

    return {"text": text}


# ==============================================================================
# CELL 4: LOAD MODEL VỚI QUANTIZATION
# ==============================================================================
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


def load_model_and_tokenizer():
    """
    Load Qwen-2.5-7B-Instruct với 4-bit quantization (QLoRA).

    Kết quả:
    - Model ~5.5GB VRAM (thay vì ~14GB full precision)
    - LoRA adapters chỉ thêm ~20MB trainable parameters
    """
    print(f"🔄 Đang load {MODEL_NAME}...")

    # Quantization config (4-bit NF4)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=LOAD_IN_4BIT,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,  # Double quantization
    )

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        padding_side="right"
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )

    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(model)

    # LoRA config
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        target_modules=TARGET_MODULES,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # Apply LoRA
    model = get_peft_model(model, lora_config)

    # Print trainable parameters
    trainable, total = model.get_nb_trainable_parameters()
    print(f"✅ Model loaded!")
    print(f"   Total params: {total / 1e6:.1f}M")
    print(f"   Trainable params: {trainable / 1e6:.1f}M ({100 * trainable / total:.2f}%)")

    if torch.cuda.is_available():
        mem_used = torch.cuda.memory_allocated() / 1e9
        print(f"   VRAM used: {mem_used:.1f} GB")

    return model, tokenizer


# --- LOAD MODEL ---
# model, tokenizer = load_model_and_tokenizer()


# ==============================================================================
# CELL 5: TRAINING
# ==============================================================================
from trl import SFTTrainer


def train_llm(model, tokenizer, datasets):
    """
    Fine-tune Qwen-2.5-7B với SFTTrainer (Supervised Fine-Tuning).

    Quy trình:
    1. Format dữ liệu theo Qwen chat template
    2. Tokenize với max_seq_length
    3. Train với gradient accumulation
    4. Save LoRA adapters (chỉ ~20MB)
    """
    print("🏋️ Bắt đầu Fine-tuning LLM")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Epochs: {NUM_EPOCHS}")
    print(f"   Effective batch size: {BATCH_SIZE * GRADIENT_ACCUM}")
    print(f"   Learning rate: {LEARNING_RATE}")
    print()

    # Format dataset
    train_dataset = datasets['train'].map(
        lambda x: format_prompt(x, tokenizer),
        remove_columns=datasets['train'].column_names
    )

    val_dataset = None
    if 'val' in datasets:
        val_dataset = datasets['val'].map(
            lambda x: format_prompt(x, tokenizer),
            remove_columns=datasets['val'].column_names
        )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=MODEL_OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUM,
        learning_rate=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        warmup_ratio=WARMUP_RATIO,
        lr_scheduler_type="cosine",
        logging_steps=10,
        eval_strategy="steps" if val_dataset else "no",
        eval_steps=50 if val_dataset else None,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=3,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,  # Tiết kiệm VRAM
        optim="paged_adamw_8bit",     # Memory-efficient optimizer
        max_grad_norm=0.3,
        report_to="none",  # Đổi thành "wandb" nếu muốn log
        dataloader_num_workers=2,
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        args=training_args,
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_text_field="text",
        packing=True,  # Pack multiple samples vào 1 sequence
    )

    # Train
    print("🚀 Training...")
    trainer.train()

    # Save LoRA adapters
    adapter_path = os.path.join(MODEL_OUTPUT_DIR, "lora_adapters")
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    print(f"\n✅ Training hoàn tất!")
    print(f"   LoRA adapters saved: {adapter_path}")

    return trainer


# --- CHẠY TRAINING ---
# datasets = load_training_data(LLM_TRAINING_DIR)
# model, tokenizer = load_model_and_tokenizer()
# trainer = train_llm(model, tokenizer, datasets)


# ==============================================================================
# CELL 6: INFERENCE - TRÍCH XUẤT THÔNG TIN
# ==============================================================================
def load_finetuned_model(adapter_path=None):
    """Load model đã fine-tune (base model + LoRA adapters)."""
    from peft import PeftModel

    if adapter_path is None:
        adapter_path = os.path.join(MODEL_OUTPUT_DIR, "lora_adapters")

    print(f"🔄 Loading fine-tuned model...")

    # Load base model (quantized)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # Load LoRA adapters
    model = PeftModel.from_pretrained(base_model, adapter_path)
    tokenizer = AutoTokenizer.from_pretrained(adapter_path)

    model.eval()
    print("✅ Fine-tuned model loaded!")
    return model, tokenizer


def extract_info(text, model, tokenizer, task="extraction"):
    """
    Trích xuất thông tin từ văn bản OCR.

    Args:
        text: Văn bản đầu vào (từ OCR)
        model: Fine-tuned Qwen model
        tokenizer: Tokenizer
        task: "classification" hoặc "extraction"
    Returns:
        str: Kết quả (tên loại hoặc JSON)
    """
    if task == "classification":
        instruction = (
            "Bạn là chuyên gia phân loại văn bản hành chính Việt Nam. "
            "Hãy phân loại văn bản sau vào một trong các loại: "
            "Công văn, Hợp đồng, Quy định, Tờ trình, Khác. "
            "Chỉ trả lời tên loại văn bản, không giải thích thêm."
        )
    else:  # extraction
        instruction = (
            "Bạn là chuyên gia trích xuất thông tin từ văn bản hành chính Việt Nam. "
            "Hãy đọc văn bản sau và trích xuất các thông tin theo định dạng JSON:\n"
            "{\n"
            '  "loai_van_ban": "<Công văn|Hợp đồng|Quy định|Tờ trình|Khác>",\n'
            '  "so_hieu": "<số hiệu văn bản>",\n'
            '  "ngay_ban_hanh": "<DD/MM/YYYY>",\n'
            '  "co_quan_ban_hanh": "<tên cơ quan>",\n'
            '  "trich_yeu": "<trích yếu nội dung>",\n'
            '  "nguoi_ky": "<họ tên người ký>"\n'
            "}\n"
            "Nếu không tìm thấy thông tin, để trống (\"\")."
        )

    system_msg = (
        "Bạn là chuyên gia phân tích văn bản hành chính Việt Nam. "
        "Hãy thực hiện yêu cầu một cách chính xác và trả lời bằng tiếng Việt."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"{instruction}\n\n{text}"}
    ]

    # Tokenize
    input_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,      # Low temperature = deterministic
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.pad_token_id,
        )

    # Decode only the generated part
    generated = outputs[0][inputs['input_ids'].shape[1]:]
    result = tokenizer.decode(generated, skip_special_tokens=True)

    return result.strip()


def batch_extract(ocr_results_dir, model, tokenizer, output_dir, limit=None):
    """
    Trích xuất thông tin hàng loạt từ kết quả OCR.

    Input: Thư mục chứa OCR JSON files
    Output: Thư mục chứa extraction results
    """
    os.makedirs(output_dir, exist_ok=True)

    ocr_files = sorted([f for f in os.listdir(ocr_results_dir) if f.endswith('_ocr.json')])
    if limit:
        ocr_files = ocr_files[:limit]

    print(f"🧠 Đang trích xuất thông tin từ {len(ocr_files)} files...")
    results = []

    for i, ocr_file in enumerate(ocr_files):
        with open(os.path.join(ocr_results_dir, ocr_file), 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)

        ocr_text = ocr_data.get('full_text', '')
        if not ocr_text:
            continue

        # Truncate if too long
        if len(ocr_text) > 3000:
            ocr_text = ocr_text[:3000]

        # Classification
        doc_type = extract_info(ocr_text, model, tokenizer, task="classification")

        # Extraction
        extraction = extract_info(ocr_text, model, tokenizer, task="extraction")

        result = {
            'source_file': ocr_data.get('source_pdf', ocr_file),
            'classification': doc_type,
            'extraction_raw': extraction,
        }

        # Try parse JSON
        try:
            result['extraction_json'] = json.loads(extraction)
        except json.JSONDecodeError:
            result['extraction_json'] = None

        results.append(result)

        # Save individual result
        out_name = ocr_file.replace('_ocr.json', '_extracted.json')
        with open(os.path.join(output_dir, out_name), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        if (i + 1) % 10 == 0:
            print(f"  📄 {i+1}/{len(ocr_files)}")

    print(f"\n✅ Trích xuất hoàn tất: {len(results)} files")
    return results


# --- CHẠY INFERENCE ---
# model, tokenizer = load_finetuned_model()
# result = extract_info("Số: 123/QĐ-UBND\nNgày 15/03/2024...", model, tokenizer)
# print(result)


# ==============================================================================
# CELL 7: ĐÁNH GIÁ LLM (Precision/Recall/F1)
# ==============================================================================
def evaluate_extraction(predictions_dir, ground_truth_path, limit=None):
    """
    Đánh giá độ chính xác trích xuất thông tin.

    Metrics:
    - Classification Accuracy
    - Per-field Precision/Recall/F1 (so_hieu, ngay_ban_hanh, trich_yeu, nguoi_ky)
    - Overall F1-Score
    """
    # Load ground truth
    with open(ground_truth_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)

    fields = ['loai_van_ban', 'so_hieu', 'ngay_ban_hanh', 'co_quan_ban_hanh',
              'trich_yeu', 'nguoi_ky']

    field_scores = {f: {'tp': 0, 'fp': 0, 'fn': 0} for f in fields}
    classification_correct = 0
    total = 0

    pred_files = sorted([f for f in os.listdir(predictions_dir)
                         if f.endswith('_extracted.json')])
    if limit:
        pred_files = pred_files[:limit]

    for pred_file in pred_files:
        with open(os.path.join(predictions_dir, pred_file), 'r', encoding='utf-8') as f:
            pred = json.load(f)

        if pred.get('extraction_json') is None:
            continue

        # Tìm ground truth tương ứng
        source = pred.get('source_file', '')
        gt_match = None
        for gt in gt_data:
            if gt.get('source', '') == source or gt.get('filename', '') == source:
                gt_match = gt
                break

        if gt_match is None:
            continue

        total += 1
        pred_json = pred['extraction_json']

        # Classification accuracy
        if pred.get('classification', '').strip() == gt_match.get('loai_van_ban', '').strip():
            classification_correct += 1

        # Per-field matching
        for field in fields:
            pred_val = str(pred_json.get(field, '')).strip()
            gt_val = str(gt_match.get(field, '')).strip()

            if pred_val and gt_val:
                if pred_val.lower() == gt_val.lower():
                    field_scores[field]['tp'] += 1
                else:
                    field_scores[field]['fp'] += 1
                    field_scores[field]['fn'] += 1
            elif pred_val and not gt_val:
                field_scores[field]['fp'] += 1
            elif not pred_val and gt_val:
                field_scores[field]['fn'] += 1

    # Calculate metrics
    print("=" * 60)
    print("🧠 LLM EXTRACTION EVALUATION")
    print("=" * 60)

    if total > 0:
        print(f"\n📊 Classification Accuracy: {classification_correct}/{total} "
              f"({classification_correct/total:.2%})")

    print(f"\n{'Field':<20} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("-" * 52)

    overall_tp = 0
    overall_fp = 0
    overall_fn = 0

    for field in fields:
        tp = field_scores[field]['tp']
        fp = field_scores[field]['fp']
        fn = field_scores[field]['fn']

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        print(f"  {field:<20} {precision:>9.2%} {recall:>9.2%} {f1:>9.2%}")

        overall_tp += tp
        overall_fp += fp
        overall_fn += fn

    overall_p = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) > 0 else 0
    overall_r = overall_tp / (overall_tp + overall_fn) if (overall_tp + overall_fn) > 0 else 0
    overall_f1 = 2 * overall_p * overall_r / (overall_p + overall_r) if (overall_p + overall_r) > 0 else 0

    print("-" * 52)
    print(f"  {'OVERALL':<20} {overall_p:>9.2%} {overall_r:>9.2%} {overall_f1:>9.2%}")
    print("=" * 60)

    return {
        'classification_accuracy': classification_correct / max(total, 1),
        'overall_f1': overall_f1,
        'per_field': field_scores
    }


if __name__ == '__main__':
    print("🧠 Phase 4: LLM Fine-tuning (The Brain)")
    print("Chạy trên Google Colab với GPU T4/A100")
    print()
    print("Thứ tự chạy:")
    print("  1. Load training data (Cell 3)")
    print("  2. Load model + QLoRA (Cell 4)")
    print("  3. Train (Cell 5)")
    print("  4. Inference test (Cell 6)")
    print("  5. Evaluate (Cell 7)")
