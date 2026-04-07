# -*- coding: utf-8 -*-
"""
Prompt Templates
================
Centralized prompt templates cho tất cả LLM tasks.

Tất cả prompts đều yêu cầu output tiếng Việt.
"""

PROMPTS = {
    # ── Summarize (tóm tắt văn bản hành chính) ──────────────────────────
    'summarize': """Bạn là chuyên gia phân tích văn bản hành chính Việt Nam. Hãy phân tích toàn diện văn bản sau và trả về JSON với cấu trúc chính xác như dưới đây:

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
    "Điểm nổi bật / quy định quan trọng số 3"
  ],
  "nghia_vu_va_quyen_han": ["Nghĩa vụ hoặc quyền hạn quan trọng"],
  "thoi_han_hieu_luc": "Ngày hiệu lực hoặc thời hạn hết hiệu lực nếu có",
  "van_ban_lien_quan": ["Số hiệu văn bản liên quan"],
  "tu_khoa": ["Từ khóa 1", "Từ khóa 2", "Từ khóa 3"],
  "muc_do_quan_trong": "Cao / Trung bình / Thấp",
  "linh_vuc": "Lĩnh vực chính (Giáo dục / Y tế / Kinh tế / An ninh / Môi trường / ...)"
}}

CHỈ TRẢ VỀ JSON, KHÔNG GIẢI THÍCH THÊM.

VĂN BẢN CẦN PHÂN TÍCH:
{text}""",

    # ── Extraction (trích xuất thông tin cấu trúc) ──────────────────────
    'extraction': """Bạn là chuyên gia trích xuất thông tin từ văn bản hành chính Việt Nam.
Hãy đọc văn bản sau và trích xuất các thông tin theo định dạng JSON:
{{
  "loai_van_ban": "<Công văn|Hợp đồng|Quy định|Tờ trình|Khác>",
  "so_hieu": "<số hiệu văn bản>",
  "ngay_ban_hanh": "<DD/MM/YYYY>",
  "co_quan_ban_hanh": "<tên cơ quan>",
  "trich_yeu": "<trích yếu nội dung>",
  "nguoi_ky": "<họ tên người ký>"
}}
Nếu không tìm thấy thông tin, để trống ("").

CHỈ TRẢ VỀ JSON, KHÔNG GIẢI THÍCH THÊM.

VĂN BẢN:
{text}""",

    # ── Classification (phân loại văn bản) ───────────────────────────────
    'classification': """Bạn là chuyên gia phân loại văn bản hành chính Việt Nam.
Hãy phân loại văn bản sau vào một trong các loại:
Công văn, Hợp đồng, Quy định, Tờ trình, Khác.

Chỉ trả lời tên loại văn bản, không giải thích thêm.

VĂN BẢN:
{text}""",

    # ── System message (cho Qwen ChatML) ─────────────────────────────────
    'system_message': """Bạn là chuyên gia phân tích văn bản hành chính Việt Nam.
Hãy thực hiện yêu cầu một cách chính xác và trả lời bằng tiếng Việt.""",
}
