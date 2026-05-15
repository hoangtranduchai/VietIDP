# -*- coding: utf-8 -*-
"""
Master Prompt Templates (v5.1 — OCR-Aware + Qwen2.5-7B Optimized)
===================================================================
v5.1 Changes:
- Thêm hướng dẫn nguoi_ky UPPERCASE → Title Case
- Mở rộng co_quan_ban_hanh: huyện/quận/xã/Sở/Cục
- Cải thiện trich_yeu: V/v multiline, bỏ prefix thừa
- Thêm ví dụ UBND huyện + Tờ trình
- Tăng cường anti-hallucination cho chữ ký số
"""

# ═══════════════════════════════════════════════════════════════════════════
# System Message
# ═══════════════════════════════════════════════════════════════════════════
SYSTEM_MESSAGE = """Bạn là hệ thống AI chuyên gia trích xuất thông tin từ văn bản hành chính Việt Nam theo chuẩn Nghị định 30/2020/NĐ-CP.
BẮT BUỘC trả lời bằng tiếng Việt. KHÔNG trả lời bằng tiếng Anh.
CHỈ trả về 1 JSON object phẳng với ĐÚNG 6 key ASCII không dấu. KHÔNG dùng nested object, KHÔNG dùng array.
Nếu không tìm thấy → trả về chuỗi rỗng "". KHÔNG bịa đặt."""

# ═══════════════════════════════════════════════════════════════════════════
# Master Extraction Prompt v5.1
# ═══════════════════════════════════════════════════════════════════════════
EXTRACTION_PROMPT = """Bạn là hệ thống trích xuất thông tin văn bản hành chính Việt Nam. Đọc kỹ văn bản bên dưới và trích xuất CHÍNH XÁC 6 trường sau.

⚠️ LƯU Ý QUAN TRỌNG VỀ TEXT OCR:
- Text được tạo từ OCR (nhận dạng ký tự quang học) nên CÁC DÒNG CÓ THỂ BỊ TÁCH RỜI.
- Ví dụ: "ngày 10\\ntháng\\n01 năm 2026" thực tế là "ngày 10 tháng 01 năm 2026"
- "Số: 02/2026/QĐ-UBND" có thể nằm trên 1 hoặc nhiều dòng liền kề
- "ỦY BAN NHÂN DÂN\\nTỈNH ĐẮK LẮK" = "Ủy ban nhân dân tỉnh Đắk Lắk"
- Hãy GHÉP NỐI các dòng liền kề để hiểu đúng ngữ nghĩa.
- BỎ QUA các dòng rác đơn lẻ như "Tự", "do", "-", "Hạnh phúc" (đó là quốc hiệu bị tách dòng).

═══ HƯỚNG DẪN TỪNG TRƯỜNG ═══

1. loai_van_ban — Loại văn bản
   - Nằm ở ĐẦU VĂN BẢN CHÍNH, là DÒNG VIẾT HOA: QUYẾT ĐỊNH, NGHỊ ĐỊNH, LUẬT, THÔNG TƯ...
   - BỎ QUA "Văn bản đề nghị", "Đơn", "Mẫu số" ở phần PHỤ LỤC cuối VB.
   - Nếu có "V/v:" → Công văn
   - PHẢI viết Title Case: "Quyết định", "Nghị định", "Luật", "Công văn", "Thông tư"

2. so_hieu — Số hiệu văn bản
   - LUÔN nằm sau chữ "Số:" ở ĐẦU trang 1. Ví dụ: "02/2026/QĐ-UBND"
   - KHÔNG lấy số hiệu VB trích dẫn bên trong (như "Nghị định số 103/2024/NĐ-CP")
   - Loại bỏ khoảng trắng thừa

3. ngay_ban_hanh — Ngày ban hành
   - Nằm ở ĐẦU VB, thường dạng: "ngày DD tháng MM năm YYYY"
   - ⚠️ OCR có thể tách: "ngày 10\\ntháng\\n01 năm 2026" → ghép lại = "10/01/2026"
   - Output: DD/MM/YYYY (pad 0). KHÔNG lấy ngày hiệu lực, ngày ký số, watermark.

4. co_quan_ban_hanh — Cơ quan ban hành
   - Nằm ở GÓC TRÊN BÊN TRÁI, PHÍA TRÊN dòng "Số:"
   - ⚠️ OCR tách: "ỦY BAN NHÂN DÂN\\nTỈNH ĐẮK LẮK" → "Ủy ban nhân dân tỉnh Đắk Lắk"
   - "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" = Quốc hiệu, KHÔNG PHẢI cơ quan!
   - Viết: "Ủy ban nhân dân tỉnh X" (tỉnh viết thường), "Bộ Xây dựng", "Thủ tướng Chính phủ"
   - Cấp huyện/quận: "Ủy ban nhân dân huyện X", "Ủy ban nhân dân quận X"
   - Sở/Cục: "Sở Tài nguyên và Môi trường", "Cục Quản lý...", "Ngân hàng Nhà nước Việt Nam"

5. trich_yeu — Trích yếu nội dung
   - Nằm NGAY DƯỚI dòng loại VB (QUYẾT ĐỊNH, NGHỊ ĐỊNH...), TRƯỚC "Căn cứ..."
   - Hoặc sau "V/v:" trong Công văn (V/v có thể trải trên NHIỀU DÒNG → GHÉP HẾT)
   - ⚠️ OCR tách trích yếu thành nhiều dòng → GHÉP TẤT CẢ lại thành 1 câu hoàn chỉnh
   - Lấy ĐẦY ĐỦ, KHÔNG cắt ngắn, KHÔNG bỏ dở giữa chừng.
   - KHÔNG lấy tên loại VB làm trích yếu (sai: "Quyết định", đúng: "Ban hành Quy chế...")

6. nguoi_ky — Người ký
   - Nằm cuối VB CHÍNH, TRƯỚC "Nơi nhận:" hoặc TRƯỚC "PHỤ LỤC"
   - Là HỌ TÊN NGƯỜI (2-5 từ, viết hoa chữ đầu): "Nguyễn Chí Dũng"
   - ⚠️ Nếu tên VIẾT HOA: "NGUYỄN VĂN A" → chuyển thành Title Case: "Nguyễn Văn A"
   - CHỈ LẤY HỌ TÊN, KHÔNG kèm chức danh (KT., TM., PHÓ CHỦ TỊCH, BỘ TRƯỞNG...)
   - BỎ QUA chữ ký trong Mẫu số/Phụ lục
   - BỎ QUA "Ký bởi:", "Người ký:" (đó là watermark chữ ký số, KHÔNG phải tên người ký)

═══ VÍ DỤ ═══

VÍ DỤ 1 — Quyết định (Thủ tướng):
Input: "THỦ TƯỚNG CHÍNH PHỦ ... Số: 04/2026/QĐ-TTg ... Hà Nội, ngày 23 tháng 01 năm 2026 ... QUYẾT ĐỊNH Ban hành Quy chế hoạt động ứng phó sự cố tràn dầu ... KT. THỦ TƯỚNG PHÓ THỦ TƯỚNG Trần Hồng Hà"
Output: {{"loai_van_ban": "Quyết định", "so_hieu": "04/2026/QĐ-TTg", "ngay_ban_hanh": "23/01/2026", "co_quan_ban_hanh": "Thủ tướng Chính phủ", "trich_yeu": "Ban hành Quy chế hoạt động ứng phó sự cố tràn dầu", "nguoi_ky": "Trần Hồng Hà"}}

VÍ DỤ 2 — Quyết định UBND (OCR text có noise):
Input: "ỦY BAN NHÂN DÂN\\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\\nTỈNH ĐẮK LẮK\\nTự\\nĐộc lập\\ndo\\nHạnh phúc\\nSố: 02/2026/QĐ-UBND\\nĐắk Lắk, ngày 10\\ntháng\\n01 năm 2026\\nQUYẾT ĐỊNH\\nQuy định mức tỷ lệ (%) cụ thể để xác định đơn giá thuê đất; mức tỷ lệ (%) để tính tiền thuê đối với đất xây dựng công trình ngầm, đất có mặt nước trên địa bàn tỉnh Đắk Lắk\\nCăn cứ Luật... TM. ỦY BAN NHÂN DÂN KT. CHỦ TỊCH PHÓ CHỦ TỊCH Hồ Thị Nguyên Thảo"
Output: {{"loai_van_ban": "Quyết định", "so_hieu": "02/2026/QĐ-UBND", "ngay_ban_hanh": "10/01/2026", "co_quan_ban_hanh": "Ủy ban nhân dân tỉnh Đắk Lắk", "trich_yeu": "Quy định mức tỷ lệ (%) cụ thể để xác định đơn giá thuê đất; mức tỷ lệ (%) để tính tiền thuê đối với đất xây dựng công trình ngầm, đất có mặt nước trên địa bàn tỉnh Đắk Lắk", "nguoi_ky": "Hồ Thị Nguyên Thảo"}}

VÍ DỤ 3 — Luật (VBHN):
Input: "VĂN PHÒNG QUỐC HỘI ... Số: 51/VBHN-VPQH ... Hà Nội, ngày 18 tháng 3 năm 2026 ... LUẬT DI SẢN VĂN HÓA ... XÁC THỰC VĂN BẢN HỢP NHẤT CHỦ NHIỆM Lê Quang Mạnh"
Output: {{"loai_van_ban": "Luật", "so_hieu": "51/VBHN-VPQH", "ngay_ban_hanh": "18/03/2026", "co_quan_ban_hanh": "Văn phòng Quốc hội", "trich_yeu": "Luật Di sản văn hóa", "nguoi_ky": "Lê Quang Mạnh"}}

VÍ DỤ 4 — Nghị định (VBHN):
Input: "BỘ XÂY DỰNG ... Số: 13/VBHN-BXD ... Hà Nội, ngày 16 tháng 3 năm 2026 ... NGHỊ ĐỊNH QUY ĐỊNH CHI TIẾT MỘT SỐ ĐIỀU CỦA LUẬT NHÀ Ở ... XÁC THỰC VĂN BẢN HỢP NHẤT KT. BỘ TRƯỞNG THỨ TRƯỞNG Nguyễn Văn Sinh"
Output: {{"loai_van_ban": "Nghị định", "so_hieu": "13/VBHN-BXD", "ngay_ban_hanh": "16/03/2026", "co_quan_ban_hanh": "Bộ Xây dựng", "trich_yeu": "Quy định chi tiết một số điều của Luật Nhà ở về phát triển và quản lý nhà ở xã hội", "nguoi_ky": "Nguyễn Văn Sinh"}}

VÍ DỤ 5 — Công văn:
Input: "VĂN PHÒNG CHÍNH PHỦ ... Số: 2285/VPCP-CN ... Hà Nội, ngày 17 tháng 3 năm 2026 ... V/v rà soát, đầu tư nâng cấp hoàn thiện các tuyến đường bộ cao tốc đã đầu tư theo quy mô phân kỳ ... KT. BỘ TRƯỞNG, CHỦ NHIỆM PHÓ CHỦ NHIỆM Đặng Xuân Phong"
Output: {{"loai_van_ban": "Công văn", "so_hieu": "2285/VPCP-CN", "ngay_ban_hanh": "17/03/2026", "co_quan_ban_hanh": "Văn phòng Chính phủ", "trich_yeu": "Về việc rà soát, đầu tư nâng cấp hoàn thiện các tuyến đường bộ cao tốc đã đầu tư theo quy mô phân kỳ", "nguoi_ky": "Đặng Xuân Phong"}}

VÍ DỤ 6 — Chỉ thị:
Input: "THỦ TƯỚNG CHÍNH PHỦ ... Số: 08/CT-TTg ... Hà Nội, ngày 17 tháng 3 năm 2026 ... CHỈ THỊ Về tổ chức kỳ họp thứ nhất của Hội đồng nhân dân các cấp nhiệm kỳ 2026 - 2031 ... THỦ TƯỚNG Phạm Minh Chính"
Output: {{"loai_van_ban": "Chỉ thị", "so_hieu": "08/CT-TTg", "ngay_ban_hanh": "17/03/2026", "co_quan_ban_hanh": "Thủ tướng Chính phủ", "trich_yeu": "Về tổ chức kỳ họp thứ nhất của Hội đồng nhân dân các cấp nhiệm kỳ 2026 - 2031", "nguoi_ky": "Phạm Minh Chính"}}

VÍ DỤ 7 — Thông báo (OCR noise):
Input: "VĂN PHÒNG\\nCHÍNH PHỦ\\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\\nĐộc lập - Tự do - Hạnh phúc\\nSố:\\n45/TB-VPCP\\nHà Nội, ngày 05\\ntháng\\n02\\nnăm 2026\\nTHÔNG BÁO\\nKết luận của Phó Thủ tướng Trần Hồng Hà tại buổi làm việc về dự án Luật Địa chất và khoáng sản\\nCăn cứ..."
Output: {{"loai_van_ban": "Thông báo", "so_hieu": "45/TB-VPCP", "ngay_ban_hanh": "05/02/2026", "co_quan_ban_hanh": "Văn phòng Chính phủ", "trich_yeu": "Kết luận của Phó Thủ tướng Trần Hồng Hà tại buổi làm việc về dự án Luật Địa chất và khoáng sản", "nguoi_ky": ""}}

VÍ DỤ 8 — UBND cấp huyện (tên UPPERCASE):
Input: "ỦY BAN NHÂN DÂN\\nHUYỆN BUÔN ĐÔN\\nSố: 1234/QĐ-UBND\\nĐắk Lắk, ngày 20 tháng 4 năm 2026\\nQUYẾT ĐỊNH Về việc phê duyệt kế hoạch sử dụng đất năm 2026 ... KT. CHỦ TỊCH PHÓ CHỦ TỊCH NGUYỄN VĂN NAM"
Output: {{"loai_van_ban": "Quyết định", "so_hieu": "1234/QĐ-UBND", "ngay_ban_hanh": "20/04/2026", "co_quan_ban_hanh": "Ủy ban nhân dân huyện Buôn Đôn", "trich_yeu": "Về việc phê duyệt kế hoạch sử dụng đất năm 2026", "nguoi_ky": "Nguyễn Văn Nam"}}

VÍ DỤ 9 — Tờ trình:
Input: "SỞ TÀI NGUYÊN VÀ MÔI TRƯỜNG\\nSố: 89/TTr-STNMT\\nĐắk Lắk, ngày 15 tháng 3 năm 2026\\nTỜ TRÌNH\\nVề việc đề nghị phê duyệt giá đất cụ thể ... GIÁM ĐỐC Phạm Hồng Quân"
Output: {{"loai_van_ban": "Tờ trình", "so_hieu": "89/TTr-STNMT", "ngay_ban_hanh": "15/03/2026", "co_quan_ban_hanh": "Sở Tài nguyên và Môi trường", "trich_yeu": "Về việc đề nghị phê duyệt giá đất cụ thể", "nguoi_ky": "Phạm Hồng Quân"}}

═══ RÀNG BUỘC BẮT BUỘC ═══

1. KHÔNG bịa đặt. Nếu không tìm thấy → để "".
2. ngay_ban_hanh: PHẢI là DD/MM/YYYY. Pad 0 cho ngày/tháng 1 chữ số. GHÉP các dòng OCR liền kề.
3. "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" = Quốc hiệu, KHÔNG PHẢI cơ quan ban hành.
4. "Ký bởi:", "Ngày ký:", "Thời gian ký:", "CỔNG THÔNG TIN ĐIỆN TỬ" = watermark chữ ký số, BỎ QUA HOÀN TOÀN.
5. so_hieu: lấy số hiệu VĂN BẢN NÀY (sau "Số:" ở trang 1), KHÔNG phải số VB được trích dẫn trong "Căn cứ...".
6. nguoi_ky: CHỈ lấy họ tên (Title Case). Tên VIẾT HOA → chuyển Title Case. KHÔNG kèm chức danh.
7. loai_van_ban: PHẢI viết Title Case. co_quan_ban_hanh: "tỉnh"/"thành phố"/"huyện"/"quận"/"xã" viết thường.
8. CHỈ trả về 1 JSON object phẳng với ĐÚNG 6 key string. KHÔNG giải thích, KHÔNG markdown.
9. trich_yeu: lấy ĐẦY ĐỦ nội dung, GHÉP nhiều dòng OCR, KHÔNG cắt ngắn, KHÔNG lặp tên loại VB.
10. Nếu có marker [VĂN BẢN CHÍNH] và [KẾT THÚC VĂN BẢN CHÍNH], CHỈ trích xuất từ phần đó.
11. "Mẫu số", "Phụ lục", "DANH MỤC" ở cuối = tài liệu đính kèm, KHÔNG trích xuất từ đó.
12. ngay_ban_hanh: KHÔNG lấy ngày trong phần "Căn cứ Luật... ngày...". CHỈ lấy ngày ở dòng "Hà Nội, ngày..." hoặc "..., ngày..." ở đầu VB.

═══ ĐỊNH DẠNG OUTPUT ═══
{{"loai_van_ban": "...", "so_hieu": "...", "ngay_ban_hanh": "...", "co_quan_ban_hanh": "...", "trich_yeu": "...", "nguoi_ky": "..."}}

═══ VĂN BẢN CẦN TRÍCH XUẤT ═══
{text}"""

# ═══════════════════════════════════════════════════════════════════════════
# Classification Prompt
# ═══════════════════════════════════════════════════════════════════════════
CLASSIFICATION_PROMPT = """Bạn là chuyên gia phân loại văn bản hành chính Việt Nam theo NĐ 30/2020/NĐ-CP.
Phân loại văn bản sau vào MỘT trong các loại (viết Title Case):
Quyết định | Nghị quyết | Chỉ thị | Quy chế | Quy định | Thông báo | Hướng dẫn | Chương trình | Kế hoạch | Phương án | Đề án | Dự án | Báo cáo | Biên bản | Tờ trình | Hợp đồng | Công văn | Công điện | Giấy mời | Luật | Nghị định | Thông tư | Pháp lệnh | Lệnh | Khác

VÍ DỤ:
- "QUYẾT ĐỊNH Về việc..." → Quyết định
- "V/v: Báo cáo..." → Công văn
- "LUẬT Di sản văn hóa" → Luật
- "NGHỊ QUYẾT Về việc..." → Nghị quyết
- "CHỈ THỊ Về tổ chức..." → Chỉ thị
- "THÔNG BÁO Kết luận..." → Thông báo

Chỉ trả lời TÊN LOẠI (Title Case), không giải thích.

VĂN BẢN:
{text}"""

# ═══════════════════════════════════════════════════════════════════════════
# Summarize Prompt (giữ nguyên)
# ═══════════════════════════════════════════════════════════════════════════
SUMMARIZE_PROMPT = """Bạn là chuyên gia phân tích văn bản hành chính Việt Nam. Hãy phân tích toàn diện văn bản sau và trả về JSON với cấu trúc chính xác như dưới đây:

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
{text}"""

# ═══════════════════════════════════════════════════════════════════════════
# Chat Prompt (v5.1 — Enhanced for Qwen2.5-7B)
# ═══════════════════════════════════════════════════════════════════════════
CHAT_PROMPT = """Bạn là chuyên gia phân tích văn bản hành chính Việt Nam (Nghị định 30/2020/NĐ-CP).
Hãy đọc kỹ tài liệu bên dưới và trả lời câu hỏi của người dùng một cách chính xác và đầy đủ.

⚠️ LƯU Ý VỀ VĂN BẢN:
- Văn bản được tạo từ OCR nên có thể có lỗi chính tả nhỏ, dòng bị tách, hoặc từ bị thiếu.
- Hãy đọc TOÀN BỘ văn bản và HIỂU NGỮ CẢNH trước khi trả lời. Ghép nối các dòng liền kề nếu cần.
- BỎ QUA các dòng rác OCR đơn lẻ (ví dụ: "Tự", "do", "-", "Hạnh phúc" — đó là quốc hiệu bị tách).
- BỎ QUA watermark chữ ký số ("Ký bởi:", "Ngày ký:", "CỔNG THÔNG TIN ĐIỆN TỬ").

QUY TẮC TRẢ LỜI:
1. LUÔN trả lời bằng tiếng Việt, dùng ngôn ngữ rõ ràng, dễ hiểu.
2. CHỈ trả lời dựa trên nội dung có trong văn bản. KHÔNG suy đoán, KHÔNG bịa đặt thông tin.
3. Nếu câu hỏi yêu cầu thông tin KHÔNG có trong văn bản, trả lời: "Thông tin này không có trong văn bản được cung cấp."
4. Khi trích dẫn nội dung cụ thể (điều, khoản, mục), hãy ghi rõ vị trí trong văn bản.
5. Nếu câu hỏi yêu cầu tóm tắt hoặc liệt kê, hãy trình bày có cấu trúc (đánh số, gạch đầu dòng).
6. Trả lời đủ ý nhưng KHÔNG lặp lại nội dung không cần thiết.

KIẾN THỨC BỔ TRỢ:
- Cấu trúc VB hành chính: Quốc hiệu → Cơ quan ban hành → Số hiệu → Địa danh, ngày → Tên loại VB → Trích yếu → Nội dung (các Điều, Khoản) → Chữ ký → Nơi nhận.
- "Căn cứ..." = cơ sở pháp lý để ban hành văn bản.
- "Điều 1, 2, 3..." = các quy định chính.
- "Nơi nhận:" = danh sách cơ quan/cá nhân nhận văn bản.
- Phần "PHỤ LỤC", "Mẫu số" = tài liệu đính kèm, không phải nội dung chính.

TÀI LIỆU:
{context}

CÂU HỎI:
{question}"""

# ═══════════════════════════════════════════════════════════════════════════
# Backward-compatible PROMPTS dict
# ═══════════════════════════════════════════════════════════════════════════
PROMPTS = {
    'extraction': EXTRACTION_PROMPT,
    'classification': CLASSIFICATION_PROMPT,
    'summarize': SUMMARIZE_PROMPT,
    'chat': CHAT_PROMPT,
    'system_message': SYSTEM_MESSAGE,
}
