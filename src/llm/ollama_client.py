# -*- coding: utf-8 -*-
"""
Ollama LLM Client (v3.0 — Sliding Window)
===========================================
Client kết nối Ollama local Qwen2.5-7B để phân tích văn bản hành chính.

Nâng cấp v3.0:
- Sliding Window chunking cho văn bản > max_chars
- Smart merge kết quả từ nhiều chunks
- Retry logic (3 attempts, exponential backoff)
- JSON validation chặt chẽ
"""

import json
import re
import time
import requests

from src.config import Config
from src.llm.prompts import PROMPTS


class OllamaClient:
    """Client cho Ollama LLM local (Qwen2.5-7B)."""

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

    # ═══════════════════════════════════════════════════════════════════
    # Core API Call
    # ═══════════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════════
    # Sliding Window Chunking
    # ═══════════════════════════════════════════════════════════════════

    def _split_text_into_chunks(self, text: str, chunk_size: int = None,
                                overlap: int = 2000) -> list:
        """
        Chia văn bản dài thành các chunks có overlap.

        Chia theo đoạn (paragraph boundary) để không cắt giữa câu.

        Args:
            text: Văn bản cần chia
            chunk_size: Kích thước mỗi chunk (mặc định = max_chars - 3000 cho prompt)
            overlap: Số ký tự overlap giữa các chunks

        Returns:
            list[str]: Danh sách chunks
        """
        if chunk_size is None:
            chunk_size = self.max_chars - 3000  # Trừ không gian cho prompt template

        if len(text) <= chunk_size:
            return [text]

        paragraphs = text.split('\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 1 > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Overlap: giữ lại phần cuối của chunk trước
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + '\n' + para
            else:
                current_chunk += '\n' + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _merge_extraction_results(self, results: list) -> dict:
        """
        Merge kết quả trích xuất từ nhiều chunks.

        Chiến lược: Ưu tiên giá trị non-empty đầu tiên cho mỗi field.
        Đặc biệt cho trường 'trich_yeu': nối tất cả nếu khác nhau.

        Args:
            results: List các dict kết quả

        Returns:
            dict: Kết quả đã merge
        """
        if not results:
            return {}
        if len(results) == 1:
            return results[0]

        merged = {}
        all_keys = set()
        for r in results:
            if isinstance(r, dict):
                all_keys.update(r.keys())

        for key in all_keys:
            values = []
            for r in results:
                if isinstance(r, dict):
                    v = r.get(key, "")
                    if v and str(v).strip():
                        values.append(str(v).strip())

            if not values:
                merged[key] = ""
            elif key in ('diem_chinh', 'tu_khoa', 'nghia_vu_va_quyen_han',
                         'van_ban_lien_quan'):
                # List fields: merge tất cả unique items
                all_items = []
                for v in values:
                    if isinstance(v, str):
                        try:
                            v = json.loads(v)
                        except (json.JSONDecodeError, TypeError):
                            all_items.append(v)
                            continue
                    if isinstance(v, list):
                        all_items.extend(v)
                    else:
                        all_items.append(v)
                merged[key] = list(dict.fromkeys(all_items))  # Unique, giữ thứ tự
            elif key in ('tom_tat_day_du', 'trich_yeu'):
                # Text dài: nối nếu khác nhau
                unique_vals = list(dict.fromkeys(values))
                merged[key] = ' '.join(unique_vals)
            else:
                # Scalar fields: lấy giá trị dài nhất (thường chính xác hơn)
                merged[key] = max(values, key=len)

        return merged

    # ═══════════════════════════════════════════════════════════════════
    # Public Methods
    # ═══════════════════════════════════════════════════════════════════

    def summarize(self, text: str) -> tuple:
        """Phân tích và tóm tắt văn bản hành chính."""
        if len(text) <= self.max_chars:
            prompt = PROMPTS['summarize'].format(text=text)
            return self.generate(prompt, format_json=True)

        # Sliding Window cho văn bản dài
        print(f"  📄 Văn bản dài ({len(text)} chars), dùng Sliding Window...")
        chunks = self._split_text_into_chunks(text)
        print(f"  📄 Chia thành {len(chunks)} chunks")

        results = []
        for i, chunk in enumerate(chunks):
            chunk_note = f"\n[Đoạn {i+1}/{len(chunks)} của văn bản]"
            prompt = PROMPTS['summarize'].format(text=chunk + chunk_note)
            result, error = self.generate(prompt, format_json=True)
            if result and not error:
                results.append(result)

        if not results:
            return None, "Tất cả chunks đều thất bại"

        return self._merge_extraction_results(results), None

    def extract_info(self, text: str) -> tuple:
        """
        Trích xuất thông tin cấu trúc từ văn bản OCR.
        Hỗ trợ Sliding Window cho văn bản dài.
        """
        if len(text) <= self.max_chars:
            prompt = PROMPTS['extraction'].format(text=text)
            return self.generate(prompt, format_json=True)

        # Sliding Window
        print(f"  📄 Văn bản dài ({len(text)} chars), dùng Sliding Window...")
        chunks = self._split_text_into_chunks(text)
        print(f"  📄 Chia thành {len(chunks)} chunks")

        results = []
        for i, chunk in enumerate(chunks):
            chunk_note = f"\n[Đoạn {i+1}/{len(chunks)} của văn bản]"
            prompt = PROMPTS['extraction'].format(text=chunk + chunk_note)
            result, error = self.generate(prompt, format_json=True)
            if result and not error:
                results.append(result)

        if not results:
            return None, "Tất cả chunks đều thất bại"

        return self._merge_extraction_results(results), None

    def classify(self, text: str) -> tuple:
        """Phân loại văn bản (chỉ dùng 5000 ký tự đầu)."""
        if len(text) > 5000:
            text = text[:5000]

        prompt = PROMPTS['classification'].format(text=text)
        return self.generate(prompt, format_json=False)


# ═══════════════════════════════════════════════════════════════════════════
# Legacy-compatible Function
# ═══════════════════════════════════════════════════════════════════════════

def summarize_with_ollama(text: str) -> tuple:
    """Drop-in replacement cho ai/summarize.py."""
    client = OllamaClient()
    return client.summarize(text)
