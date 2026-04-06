import sys
import json
import re
import time
import requests
import os

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# ═══════════════════════════════════════════════════════════════════════════
# Configuration — Có thể override bằng environment variables
# ═══════════════════════════════════════════════════════════════════════════
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
MAX_CHARS = int(os.environ.get("OLLAMA_MAX_CHARS", "32000"))
NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "3000"))
MAX_RETRIES = 3


def extract_text_from_docx(file_path):
    if not HAS_DOCX:
        return None, "python-docx chưa được cài. Chạy: pip install python-docx"
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs)
    return full_text, None


def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(), None


def summarize_with_ollama(text):
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n[...văn bản bị cắt bớt do giới hạn ngữ cảnh...]"

    prompt = f"""Bạn là chuyên gia phân tích văn bản hành chính Việt Nam. Hãy phân tích toàn diện văn bản sau và trả về JSON với cấu trúc chính xác như dưới đây:

{{
  "loai_van_ban": "Tên loại văn bản (Quyết định / Thông tư / Công văn / Hướng dẫn / Nghị định / Nghị quyết / ...)",
  "so_hieu": "Số hiệu văn bản, ví dụ: 123/QĐ-BCA",
  "ngay_ban_hanh": "DD/MM/YYYY hoặc để trống",
  "co_quan_ban_hanh": "Tên đầy đủ của cơ quan, bộ, ngành ban hành",
  "nguoi_ky": "Họ tên, chức vụ người ký",
  "tom_tat_ngan": "Tóm tắt 1 câu về nội dung chính của văn bản",
  "tom_tat_day_du": "Tóm tắt chi tiết 5-8 câu, bao gồm bối cảnh, mục tiêu, biện pháp và hiệu lực thi hành",
  "muc_dich_chinh": "Mục đích / lý do ban hành văn bản này",
  "doi_tuong_ap_dung": "Đối tượng áp dụng cụ thể (cơ quan, cá nhân, tổ chức)",
  "pham_vi_ap_dung": "Phạm vi áp dụng (địa phương, toàn quốc, lĩnh vực cụ thể)",
  "diem_chinh": [
    "Điểm nổi bật / quy định quan trọng số 1",
    "Điểm nổi bật / quy định quan trọng số 2",
    "Điểm nổi bật / quy định quan trọng số 3",
    "Điểm nổi bật / quy định quan trọng số 4",
    "Điểm nổi bật / quy định quan trọng số 5"
  ],
  "nghia_vu_va_quyen_han": ["Nghĩa vụ hoặc quyền hạn quan trọng 1", "Nghĩa vụ 2"],
  "thoi_han_hieu_luc": "Ngày hiệu lực hoặc thời hạn hết hiệu lực nếu có",
  "van_ban_lien_quan": ["Số hiệu văn bản liên quan 1", "Số hiệu văn bản liên quan 2"],
  "tu_khoa": ["Từ khóa 1", "Từ khóa 2", "Từ khóa 3", "Từ khóa 4", "Từ khóa 5"],
  "muc_do_quan_trong": "Cao / Trung bình / Thấp",
  "linh_vuc": "Lĩnh vực chính (Giáo dục / Y tế / Kinh tế / An ninh / Môi trường / ...)"
}}

CHỈ TRẢ VỀ JSON, KHÔNG GIẢI THÍCH THÊM.

VĂN BẢN CẦN PHÂN TÍCH:
{text}
"""

    # Retry logic
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": NUM_PREDICT
                }
            }, timeout=300)

            if response.status_code != 200:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, f"Lỗi Ollama: HTTP {response.status_code}"

            result_text = response.json().get("response", "")

            # Validate JSON response
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                try:
                    summary = json.loads(json_match.group())
                    return summary, None
                except json.JSONDecodeError:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return {"tom_tat_ngan": result_text.strip()}, None
            else:
                return {"tom_tat_ngan": result_text.strip()}, None

        except requests.exceptions.ConnectionError:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return None, "Không kết nối được Ollama. Hãy chắc chắn Ollama đang chạy (ollama serve)"
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return None, "Ollama timeout. Hãy thử lại."
        except json.JSONDecodeError:
            return {"tom_tat_ngan": result_text.strip()}, None
        except Exception as e:
            return None, str(e)

    return None, "Đã thử lại 3 lần nhưng không thành công"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Không có đường dẫn file"}))
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(json.dumps({"error": f"File không tồn tại: {file_path}"}))
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".docx":
        text, err = extract_text_from_docx(file_path)
    elif ext in [".txt", ".md"]:
        text, err = extract_text_from_txt(file_path)
    else:
        print(json.dumps({"error": f"Định dạng file chưa hỗ trợ: {ext}"}))
        sys.exit(1)

    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    if not text or len(text.strip()) < 20:
        print(json.dumps({"error": "File trống hoặc không đọc được nội dung"}))
        sys.exit(1)

    word_count = len(text.split())
    char_count = len(text)

    summary, err = summarize_with_ollama(text)
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    print(json.dumps({
        "success": True,
        "summary": summary,
        "stats": {
            "word_count": word_count,
            "char_count": char_count,
            "preview_text": text[:800]
        }
    }))


if __name__ == "__main__":
    main()
