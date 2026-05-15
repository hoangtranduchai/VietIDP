# -*- coding: utf-8 -*-
"""
Ollama LLM Client (v4.0 — OCR-Optimized)
==========================================
v4.0 Changes:
- Fix temperature=0.0 bypass (use `is not None`)
- Cắt phụ lục trong structure markers (giảm noise cho LLM)
- Tăng num_predict cho extraction
- Retry với temperature tăng dần
- Merge ưu tiên chunk đầu tiên (chứa header)
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
        self.max_chars = max_chars if max_chars is not None else Config.OLLAMA_MAX_CHARS
        self.num_predict = num_predict if num_predict is not None else Config.OLLAMA_NUM_PREDICT
        self.temperature = temperature if temperature is not None else Config.OLLAMA_TEMPERATURE
        self.timeout = timeout if timeout is not None else Config.OLLAMA_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else Config.OLLAMA_MAX_RETRIES

    # ═══════════════════════════════════════════════════════════════════
    # JSON Schema cho extraction output (enforce đúng 6 fields)
    # ═══════════════════════════════════════════════════════════════════
    EXTRACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "loai_van_ban": {"type": "string"},
            "so_hieu": {"type": "string"},
            "ngay_ban_hanh": {"type": "string"},
            "co_quan_ban_hanh": {"type": "string"},
            "trich_yeu": {"type": "string"},
            "nguoi_ky": {"type": "string"},
        },
        "required": [
            "loai_van_ban", "so_hieu", "ngay_ban_hanh",
            "co_quan_ban_hanh", "trich_yeu", "nguoi_ky"
        ],
    }

    # ═══════════════════════════════════════════════════════════════════
    # Core API Call — /api/chat
    # ═══════════════════════════════════════════════════════════════════

    def generate(self, prompt: str, format_json: bool = True,
                 temperature: float = None, num_predict: int = None,
                 use_schema: bool = False) -> tuple:
        """
        Gọi Ollama /api/chat với retry logic.
        Retry lần 2+ sẽ tăng temperature nhẹ để tránh stuck.
        """
        _temp = temperature if temperature is not None else self.temperature
        _num = num_predict if num_predict is not None else self.num_predict

        # Build chat endpoint URL from generate URL
        chat_url = self.url.replace('/api/generate', '/api/chat')

        for attempt in range(self.max_retries):
            try:
                # Retry: tăng temperature nhẹ để tránh output lặp
                retry_temp = _temp + (attempt * 0.05) if attempt > 0 else _temp

                messages = [
                    {
                        "role": "system",
                        "content": PROMPTS.get('system_message', '')
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": retry_temp,
                        "num_predict": _num,
                    }
                }

                # JSON format enforcement
                if format_json:
                    if use_schema:
                        payload["format"] = self.EXTRACTION_SCHEMA
                    else:
                        payload["format"] = "json"

                response = requests.post(
                    chat_url,
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code != 200:
                    error = f"Ollama HTTP {response.status_code}"
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None, error

                # Parse response
                resp_json = response.json()
                result_text = resp_json.get("message", {}).get("content", "")

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
        """Chia văn bản dài thành các chunks có overlap."""
        if chunk_size is None:
            chunk_size = self.max_chars - 3000

        if len(text) <= chunk_size:
            return [text]

        paragraphs = text.split('\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 1 > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + '\n' + para
            else:
                current_chunk += '\n' + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _merge_extraction_results(self, results: list) -> dict:
        """
        Merge kết quả từ nhiều chunks.
        Ưu tiên chunk ĐẦU TIÊN (chứa header document).
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
                merged[key] = list(dict.fromkeys(all_items))
            elif key in ('tom_tat_day_du',):
                # Text dài: nối nếu khác nhau
                unique_vals = list(dict.fromkeys(values))
                merged[key] = ' '.join(unique_vals)
            elif key == 'trich_yeu':
                # Trích yếu: ưu tiên giá trị đầu tiên (từ chunk header)
                merged[key] = values[0]
            else:
                # Scalar fields: ưu tiên chunk đầu tiên (chứa header)
                merged[key] = values[0]

        return merged

    # ═══════════════════════════════════════════════════════════════════
    # Public Methods
    # ═══════════════════════════════════════════════════════════════════

    def summarize(self, text: str) -> tuple:
        """Phân tích và tóm tắt văn bản hành chính."""
        if len(text) <= self.max_chars:
            prompt = PROMPTS['summarize'].format(text=text)
            return self.generate(prompt, format_json=True)

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
        Trích xuất thông tin cấu trúc từ văn bản.
        Gửi TOÀN BỘ VB chính (cắt phụ lục) cho LLM.
        """
        # Thêm markers + cắt phụ lục (chỉ gửi VB chính)
        marked_text = self._add_structure_markers(text)

        if len(marked_text) <= self.max_chars:
            prompt = PROMPTS['extraction'].format(text=marked_text)
            return self.generate(prompt, format_json=True,
                                temperature=0.0, num_predict=1500,
                                use_schema=True)

        # Sliding Window cho văn bản cực dài (> 128K chars)
        print(f"  📄 Văn bản dài ({len(text)} chars), dùng Sliding Window...")
        chunks = self._split_text_into_chunks(marked_text)
        print(f"  📄 Chia thành {len(chunks)} chunks")

        results = []
        for i, chunk in enumerate(chunks):
            chunk_note = f"\n[Đoạn {i+1}/{len(chunks)} của văn bản]"
            prompt = PROMPTS['extraction'].format(text=chunk + chunk_note)
            result, error = self.generate(prompt, format_json=True,
                                          temperature=0.0, num_predict=1500,
                                          use_schema=True)
            if result and not error:
                results.append(result)

        if not results:
            return None, "Tất cả chunks đều thất bại"

        return self._merge_extraction_results(results), None

    def _add_structure_markers(self, text: str) -> str:
        """
        Thêm markers cấu trúc + CẮT PHỤ LỤC.
        Chỉ gửi VĂN BẢN CHÍNH cho LLM (giảm noise, tiết kiệm token).
        """
        import re

        # Tìm vị trí "Nơi nhận:" — đánh dấu kết thúc VB chính
        noi_nhan_matches = list(re.finditer(r'Nơi\s+nhận\s*:', text))

        # Tìm vị trí bắt đầu Phụ lục
        appendix_patterns = [
            r'\n\s*(?:PHỤ LỤC|Phụ lục)\b',
            r'\n\s*CÁC MẪU VĂN BẢN\b',
            r'\n\s*DANH MỤC\b',
        ]
        appendix_pos = len(text)
        for pat in appendix_patterns:
            match = re.search(pat, text)
            if match and match.start() > len(text) * 0.3:
                appendix_pos = min(appendix_pos, match.start())

        # Xác định ranh giới VB chính
        main_end = len(text)

        if noi_nhan_matches:
            for m in noi_nhan_matches:
                if m.start() < appendix_pos:
                    remaining = text[m.end():m.end() + 1000]
                    luu_match = re.search(r'Lưu\s*:', remaining)
                    if luu_match:
                        main_end = m.end() + luu_match.end() + 200
                    else:
                        main_end = m.end() + 500
                    main_end = min(main_end, appendix_pos)
                    break
        elif appendix_pos < len(text):
            main_end = appendix_pos

        # CẮT phụ lục — chỉ gửi VB chính cho LLM
        if main_end < len(text) - 200:
            main_text = text[:main_end].strip()
            return (
                f"[VĂN BẢN CHÍNH]\n"
                f"{main_text}\n"
                f"[KẾT THÚC VĂN BẢN CHÍNH]\n"
                f"(Phần phụ lục/mẫu đơn đính kèm đã được lược bỏ — KHÔNG trích xuất từ phần này)"
            )

        return text

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
