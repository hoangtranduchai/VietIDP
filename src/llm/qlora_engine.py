# -*- coding: utf-8 -*-
"""
QLoRA Engine — Local GPU Inference
====================================
Nạp model Qwen2.5-3B + LoRA adapter đã fine-tune, chạy inference
trực tiếp trên GPU. Thay thế OllamaClient trong pipeline.

Ưu điểm:
  - Không cần Ollama server
  - Nhanh hơn (inference trực tiếp trên GPU)
  - Chính xác hơn (model đã fine-tune chuyên biệt)
"""

import json
import os
import pathlib

# [HOTFIX] Windows UTF-8 cho TRL/Transformers
_original_read_text = pathlib.Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    return _original_read_text(self, encoding=encoding or "utf-8", errors=errors)
pathlib.Path.read_text = _utf8_read_text

import torch
from src.config import Config

# Alpaca prompt template — PHẢI KHỚP CHÍNH XÁC với format training
ALPACA_PROMPT = """Dưới đây là một lệnh mô tả nhiệm vụ. Hãy viết một phản hồi hoàn thành xuất sắc yêu cầu đó.

### Lệnh (Instruction):
{}

### Đầu vào (Input OCR):
{}

### Phản hồi JSON (Response):
"""

EXTRACTION_INSTRUCTION = (
    "Bạn là hệ thống AI chuyên gia trích xuất thông tin từ văn bản hành chính "
    "Việt Nam theo Nghị định 30/2020/NĐ-CP. Đọc văn bản OCR sau và trích xuất "
    "chính xác 6 trường: loai_van_ban, so_hieu, ngay_ban_hanh, co_quan_ban_hanh, "
    "trich_yeu, nguoi_ky. Trả về JSON duy nhất, không giải thích."
)

EMPTY_RESULT = {
    "loai_van_ban": "", "so_hieu": "", "ngay_ban_hanh": "",
    "co_quan_ban_hanh": "", "trich_yeu": "", "nguoi_ky": ""
}


class QLoRAEngine:
    """
    Engine inference cho model QLoRA fine-tuned.
    Load 1 lần, cache trong bộ nhớ GPU.
    """

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self):
        """Nạp base model + LoRA adapter lên GPU."""
        if self._loaded:
            return

        adapter_path = str(Config.LLM_ADAPTER_PATH)
        if not os.path.exists(adapter_path):
            print(f"  → ⚠️ Không tìm thấy LoRA adapter: {adapter_path}")
            return

        try:
            from unsloth import FastLanguageModel
        except ImportError:
            print("  → ⚠️ Chưa cài đặt unsloth. pip install unsloth")
            return

        print(f"  → Đang nạp QLoRA adapter từ {adapter_path}...")
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=adapter_path,
            max_seq_length=Config.LLM_INFERENCE_SEQ_LENGTH,
            dtype=None,
            load_in_4bit=True,
        )
        FastLanguageModel.for_inference(self.model)
        self._loaded = True
        print("  → ✅ QLoRA Engine sẵn sàng (GPU inference)")

    def extract_info(self, text: str) -> tuple:
        """
        Trích xuất thông tin từ văn bản OCR.

        Args:
            text: Văn bản OCR cần trích xuất

        Returns:
            tuple: (result_dict, error_str_or_none)
                   Tương thích interface với OllamaClient.extract_info()
        """
        if not self._loaded:
            return None, "QLoRA model chưa được nạp"

        if not text or not text.strip():
            return dict(EMPTY_RESULT), None

        try:
            # Smart truncation: giữ header + footer trong budget token
            # 4096 tokens - ~200 (prompt) - 256 (output) = ~3640 tokens ≈ 8000 chars
            text = self._smart_truncate(text, max_chars=8000)

            prompt = ALPACA_PROMPT.format(EXTRACTION_INSTRUCTION, text)
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.1,
                    do_sample=False,
                    use_cache=True,
                )

            # Decode chỉ phần response (bỏ prompt)
            response = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True
            ).strip()

            # Parse JSON
            result = self._parse_json(response)
            if result is not None:
                return result, None
            else:
                return None, f"Không parse được JSON từ output: {response[:100]}"

        except Exception as e:
            return None, f"QLoRA inference error: {str(e)}"

    def _smart_truncate(self, text: str, max_chars: int = 1500) -> str:
        """
        Cắt thông minh: giữ phần đầu (header NĐ30) + phần cuối (người ký).

        Theo NĐ 30/2020/NĐ-CP:
        - Ô 1-5 (header): Quốc hiệu, cơ quan, số hiệu, ngày, loại VB, trích yếu
        - Ô 7 (footer): Chức vụ, họ tên người ký
        """
        if len(text) <= max_chars:
            return text

        # Header: lấy 2/3 budget (chứa hầu hết thông tin cần trích xuất)
        header_budget = int(max_chars * 2 / 3)
        # Footer: lấy 1/3 budget (chứa người ký)
        footer_budget = max_chars - header_budget

        header = text[:header_budget]
        footer = text[-footer_budget:]

        return header + "\n...\n" + footer

    def _parse_json(self, text: str) -> dict:
        """Parse JSON từ model output, xử lý text thừa."""
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            return None
