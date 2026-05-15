# -*- coding: utf-8 -*-
"""
LLM Fine-tuning Script (QLoRA with Unsloth)
===========================================
Luyện nội suy mô hình Qwen2.5 trên tập dữ liệu VietIDP để trở thành 
chuyên gia trích xuất hành chính, ép trả về định dạng chuẩn JSON.

Sử dụng:
  python scripts/train_qlora.py              # Train từ đầu
  python scripts/train_qlora.py --resume     # Tiếp tục từ checkpoint gần nhất

Checkpoint được lưu mỗi 200 steps vào thư mục outputs/.
"""

import os
import sys
import glob
import argparse
import pathlib

# [HOTFIX] Khắc phục lỗi kinh điển của thư viện TRL trên Windows (Lỗi UnicodeDecodeError)
_original_read_text = pathlib.Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    return _original_read_text(self, encoding=encoding or "utf-8", errors=errors)
pathlib.Path.read_text = _utf8_read_text

# Fix python path for importing src from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# [QUAN TRỌNG] Phải import unsloth TRƯỚC KHI import transformers/trl để nó kích hoạt Ép xung VRAM
try:
    from unsloth import FastLanguageModel
except ImportError:
    pass

import torch
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
from src.config import Config

def train_llm(args):
    print("🚀 Khởi động Hệ thống Huấn luyện Siêu phân luồng (Unsloth QLoRA)...")
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("❌ Lỗi: Chưa cài đặt thư viện 'unsloth'. Hãy cài bằng pip install unsloth")
        return

    dataset_path = os.path.join(Config.LLM_TRAINING_DIR, "train.jsonl")
    if not os.path.exists(dataset_path):
        print(f"❌ Không tìm thấy Dataset tại {dataset_path}. Chạy scripts/build_qlora_dataset.py trước!")
        return

    # 1. Cấu hình Unsloth FastLanguageModel
    max_seq_length = Config.LLM_MAX_SEQ_LENGTH
    dtype = None # Auto detect (Bfloat16 for Ampere/Blackwell)
    load_in_4bit = True # Bắt buộc phải là INT4 để nhét vừa 8GB VRAM (RTX 5070)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = Config.LLM_BASE_MODEL,
        max_seq_length = max_seq_length,
        dtype = dtype,
        load_in_4bit = load_in_4bit,
    )

    # 2. Add LoRA Adapters
    # Dropout=0.0 → Unsloth sẽ Fast Patch TẤT CẢ layers (QKV + O + MLP)
    # → Tăng tốc training 10-50x so với dropout>0
    model = FastLanguageModel.get_peft_model(
        model,
        r = Config.LORA_R,
        target_modules = Config.LORA_TARGET_MODULES,
        lora_alpha = Config.LORA_ALPHA,
        lora_dropout = Config.LORA_DROPOUT,  # PHẢI = 0.0
        bias = "none",
        use_gradient_checkpointing = "unsloth",
        random_state = 3407,
    )

    # 3. Load & Format Dataset
    alpaca_prompt = """Dưới đây là một lệnh mô tả nhiệm vụ. Hãy viết một phản hồi hoàn thành xuất sắc yêu cầu đó.

### Lệnh (Instruction):
{}

### Đầu vào (Input OCR):
{}

### Phản hồi JSON (Response):
{}"""

    EOS_TOKEN = tokenizer.eos_token # Must add EOS_TOKEN

    def formatting_prompts_func(examples):
        instructions = examples["instruction"]
        inputs       = examples["input"]
        outputs      = examples["output"]
        texts = []
        for instruction, input, output in zip(instructions, inputs, outputs):
            # Tuân thủ chặt chẽ định dạng Alpaca/ShareGPT
            text = alpaca_prompt.format(instruction, input, output) + EOS_TOKEN
            texts.append(text)
        return { "text" : texts, }

    dataset = load_dataset("json", data_files=dataset_path, split="train")
    dataset = dataset.map(formatting_prompts_func, batched = True)
    
    print(f"📚 Đã tải và định dạng {len(dataset)} mẫu văn bản!")

    # 4. Thiết lập Trainer
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = dataset,
        dataset_text_field = "text",
        max_seq_length = max_seq_length,
        dataset_num_proc = 2,
        packing = False, # Can make training 5x faster for short sequences
        args = TrainingArguments(
            per_device_train_batch_size = Config.LLM_BATCH_SIZE,
            gradient_accumulation_steps = Config.LLM_GRADIENT_ACCUM,
            warmup_steps = 10,
            num_train_epochs = Config.LLM_NUM_EPOCHS,
            learning_rate = Config.LLM_LEARNING_RATE,
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 10,
            optim = "paged_adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "cosine",
            seed = 3407,
            output_dir = "outputs",
            save_strategy = "no",      # TẮT checkpoint giữa chừng để tránh BSOD (KMODE_EXCEPTION)
                                       # Model chỉ lưu 1 lần duy nhất khi train xong
        ),
    )

    # 5. Huấn luyện (Fire!)
    print("🔥 Đang mồi lửa kiến trúc Blackwell... Training started!")

    # [HOTFIX] Unsloth Fused CE Loss bị lỗi trên card 8GB VRAM (false OOM).
    # Ghi đè compute_loss để dùng PyTorch vanilla CE thay thế.
    # Forward pass VẪN được tăng tốc bởi Fast Patching (28 layers, dropout=0).
    import types
    def _patched_compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")
        # Causal LM shift: logits[:-1] dự đoán labels[1:]
        seq_len = min(logits.size(1), labels.size(1))
        shift_logits = logits[..., :seq_len-1, :].contiguous()
        shift_labels = labels[..., 1:seq_len].contiguous()
        loss = torch.nn.functional.cross_entropy(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1),
            ignore_index=-100,
        )
        return (loss, outputs) if return_outputs else loss
    trainer.compute_loss = types.MethodType(_patched_compute_loss, trainer)

    torch.cuda.empty_cache()

    # Kiểm tra resume từ checkpoint
    resume_from = None
    if args.resume:
        checkpoints = sorted(glob.glob(os.path.join("outputs", "checkpoint-*")), key=os.path.getmtime)
        if checkpoints:
            resume_from = checkpoints[-1]
            print(f"🔄 TIẾP TỤC TRAINING từ checkpoint: {resume_from}")
        else:
            print("⚠️ Không tìm thấy checkpoint nào trong outputs/. Bắt đầu từ đầu.")

    trainer_stats = trainer.train(resume_from_checkpoint=resume_from)
    
    # 6. Lưu file LoRA Weights (bản cuối cùng)
    adapter_path = Config.LLM_ADAPTER_PATH
    os.makedirs(adapter_path, exist_ok=True)
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    
    print(f"\n{'='*60}")
    print(f"✅ HOÀN TẤT QLoRA Fine-Tuning!")
    print(f"   Trọng số LoRA adapter: {adapter_path}")
    print(f"   Training time: {trainer_stats.metrics['train_runtime']:.0f}s")
    print(f"   Final loss: {trainer_stats.metrics['train_loss']:.4f}")
    print(f"{'='*60}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QLoRA Fine-tuning for VietIDP")
    parser.add_argument("--resume", action="store_true",
                        help="Tiếp tục training từ checkpoint gần nhất trong outputs/")
    args = parser.parse_args()
    train_llm(args)
