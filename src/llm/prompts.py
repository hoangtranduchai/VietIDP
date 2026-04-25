# -*- coding: utf-8 -*-
"""
Prompt Templates (v3.0 — Optimized for Qwen2.5-7B)
====================================================
Centralized prompt templates cho tất cả LLM tasks.
Bổ sung few-shot examples để tăng độ chính xác trích xuất.
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

VÍ DỤ:
---
VĂN BẢN: "ỦY BAN NHÂN DÂN TỈNH BÌNH DƯƠNG ... Số: 456/QĐ-UBND ... Bình Dương, ngày 20 tháng 03 năm 2026 ... QUYẾT ĐỊNH Về việc phê duyệt kế hoạch cải cách hành chính ... CHỦ TỊCH ... Nguyễn Văn B"
KẾT QUẢ:
{{
  "loai_van_ban": "Quyết định",
  "so_hieu": "456/QĐ-UBND",
  "ngay_ban_hanh": "20/03/2026",
  "co_quan_ban_hanh": "Ủy ban nhân dân tỉnh Bình Dương",
  "trich_yeu": "Về việc phê duyệt kế hoạch cải cách hành chính",
  "nguoi_ky": "Nguyễn Văn B"
}}
---

Hãy đọc văn bản sau và trích xuất các thông tin theo định dạng JSON:
{{
  "loai_van_ban": "<Công văn|Hợp đồng|Quyết định|Tờ trình|Thông tư|Nghị định|Thông báo|Khác>",
  "so_hieu": "<số hiệu văn bản>",
  "ngay_ban_hanh": "<DD/MM/YYYY>",
  "co_quan_ban_hanh": "<tên cơ quan>",
  "trich_yeu": "<trích yếu nội dung>",
  "nguoi_ky": "<họ tên người ký>"
}}

QUY TẮC:
1. Nếu không tìm thấy thông tin, để trống ("").
2. Ngày tháng phải theo định dạng DD/MM/YYYY.
3. Số hiệu giữ nguyên dạng gốc (VD: "123/QĐ-UBND").
4. Tên cơ quan viết đầy đủ, không viết tắt.

CHỈ TRẢ VỀ JSON, KHÔNG GIẢI THÍCH THÊM.

VĂN BẢN:
{text}""",

    # ── Classification (phân loại văn bản) ───────────────────────────────
    'classification': """Bạn là chuyên gia phân loại văn bản hành chính Việt Nam.
Hãy phân loại văn bản sau vào MỘT trong các loại:
- Công văn
- Hợp đồng
- Quyết định
- Tờ trình
- Thông tư
- Nghị định
- Thông báo
- Khác

VÍ DỤ:
- "QUYẾT ĐỊNH Về việc phê duyệt..." → Quyết định
- "V/v: Báo cáo tình hình thực hiện..." → Công văn
- "HỢP ĐỒNG KINH TẾ Số: 01/HĐKT..." → Hợp đồng

Chỉ trả lời TÊN LOẠI VĂN BẢN, không giải thích thêm.

VĂN BẢN:
{text}""",

    # ── Chat (hỏi đáp trên tài liệu) ────────────────────────────────────
    'chat': """Bạn là chuyên gia phân tích văn bản hành chính Việt Nam.
Hãy đọc kỹ tài liệu được cung cấp và trả lời câu hỏi của người dùng.

QUY TẮC:
1. Trả lời TRỰC TIẾP dựa trên nội dung văn bản, KHÔNG suy đoán.
2. Trích xuất đầy đủ và chính xác (ngày tháng, số hiệu, nội dung).
3. Trả lời ngắn gọn bằng tiếng Việt.
4. Nếu không tìm thấy trong văn bản, nói: "Tôi không tìm thấy thông tin này trong văn bản."

TÀI LIỆU:
{context}

CÂU HỎI:
{question}""",

    # ── System message (cho Qwen ChatML) ─────────────────────────────────
    'system_message': """Bạn là chuyên gia phân tích văn bản hành chính Việt Nam.
Hãy thực hiện yêu cầu một cách chính xác và trả lời bằng tiếng Việt.
Luôn trả về kết quả theo định dạng được yêu cầu.""",
}
