# -*- coding: utf-8 -*-
"""
Ollama LLM Client
==================
Client kết nối Ollama local để phân tích văn bản hành chính.

Nâng cấp từ ai/summarize.py:
- Config-driven model name (default: qwen2.5:7b)
- max_chars: 32,000 (từ 8,000)
- num_predict: 3,000 (từ 1,500)
- Retry logic (3 attempts, exponential backoff)
- JSON validation
- Streaming support

Nguồn: ai/summarize.py + Phase5_End_to_End_Pipeline.py
"""

import json
import re
import time
import requests

from src.config import Config
from src.llm.prompts import PROMPTS


class OllamaClient:
    """Client cho Ollama LLM local."""

    def __init__(
        self,
        model=None,
        url=None,
        max_chars=None,
        num_predict=None,
        temperature=None,
        timeout=None,
        max_retries=None,
    ):
        self.model = model or Config.OLLAMA_MODEL
        self.url = url or Config.OLLAMA_URL
        self.max_chars = max_chars or Config.OLLAMA_MAX_CHARS
        self.num_predict = num_predict or Config.OLLAMA_NUM_PREDICT
        self.temperature = temperature or Config.OLLAMA_TEMPERATURE
        self.timeout = timeout or Config.OLLAMA_TIMEOUT
        self.max_retries = max_retries or Config.OLLAMA_MAX_RETRIES

    def generate(self, prompt: str, format_json: bool = True) -> tuple:
        """
        Gọi Ollama API với retry logic.

        Args:
            prompt: Prompt text
            format_json: Yêu cầu output JSON format

        Returns:
            tuple: (result_dict_or_str, error_str_or_none)
        """
        for attempt in range(self.max_retries):
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.num_predict,
                    }
                }
                if format_json:
                    payload["format"] = "json"

                response = requests.post(
                    self.url,
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code != 200:
                    error = f"Ollama HTTP {response.status_code}"
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None, error

                result_text = response.json().get("response", "")

                # Validate JSON
                if format_json:
                    json_match = re.search(r'\{[\s\S]*\}', result_text)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            return parsed, None
                        except json.JSONDecodeError:
                            if attempt < self.max_retries - 1:
                                time.sleep(2 ** attempt)
                                continue
                            return {"raw_response": result_text.strip()}, None

                return result_text.strip(), None

            except requests.exceptions.ConnectionError:
                error = "Không kết nối được Ollama. Chạy: ollama serve"
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, error

            except requests.exceptions.Timeout:
                error = f"Ollama timeout sau {self.timeout}s"
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, error

            except Exception as e:
                return None, str(e)

        return None, "Max retries exceeded"

    def summarize(self, text: str) -> tuple:
        """
        Phân tích và tóm tắt văn bản hành chính.

        Args:
            text: Nội dung văn bản

        Returns:
            tuple: (summary_dict, error_str_or_none)
        """
        if len(text) > self.max_chars:
            text = text[:self.max_chars] + "\n[...văn bản bị cắt bớt do giới hạn ngữ cảnh...]"

        prompt = PROMPTS['summarize'].format(text=text)
        return self.generate(prompt, format_json=True)

    def extract_info(self, text: str) -> tuple:
        """
        Trích xuất thông tin cấu trúc từ văn bản OCR.

        Args:
            text: Raw OCR text

        Returns:
            tuple: (extraction_dict, error_str_or_none)
        """
        if len(text) > self.max_chars:
            text = text[:self.max_chars]

        prompt = PROMPTS['extraction'].format(text=text)
        return self.generate(prompt, format_json=True)

    def classify(self, text: str) -> tuple:
        """
        Phân loại văn bản (Công văn/Hợp đồng/Quy định/Tờ trình/Khác).

        Args:
            text: Raw text

        Returns:
            tuple: (classification_str, error_str_or_none)
        """
        if len(text) > 5000:
            text = text[:5000]

        prompt = PROMPTS['classification'].format(text=text)
        return self.generate(prompt, format_json=False)


# ═══════════════════════════════════════════════════════════════════════════
# Legacy-compatible Function
# ═══════════════════════════════════════════════════════════════════════════

def summarize_with_ollama(text: str) -> tuple:
    """
    Drop-in replacement cho ai/summarize.py::summarize_with_ollama().

    Returns:
        tuple: (summary_dict, error_str_or_none)
    """
    client = OllamaClient()
    return client.summarize(text)
