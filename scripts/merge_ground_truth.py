"""Merge all ground truth parts into final ground_truth.json"""
import json, os

BASE = r"e:\OCR-LLM_Research\OCR-LLM_Research\data\benchmark"

# Original 12 entries
original = {
  "pdf_test_1.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"02/2026/QĐ-TTg","ngay_ban_hanh":"07/01/2026","co_quan_ban_hanh":"THỦ TƯỚNG CHÍNH PHỦ","trich_yeu":"Sửa đổi, bổ sung một số điều của các Quyết định để cắt giảm, đơn giản hóa thủ tục hành chính liên quan đến hoạt động sản xuất, kinh doanh thuộc phạm vi quản lý nhà nước của Bộ Khoa học và Công nghệ","nguoi_ky":"Nguyễn Chí Dũng"},
  "pdf_test_2.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"02/2026/QĐ-UBND","ngay_ban_hanh":"10/01/2026","co_quan_ban_hanh":"ỦY BAN NHÂN DÂN TỈNH ĐẮK LẮK","trich_yeu":"Quy định mức tỷ lệ (%) cụ thể để xác định đơn giá thuê đất; mức tỷ lệ (%) để tính tiền thuê đối với đất xây dựng công trình ngầm, đất có mặt nước trên địa bàn tỉnh Đắk Lắk","nguoi_ky":"Hồ Thị Nguyên Thảo"},
  "pdf_test_3.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"3/2025/QĐ-UBND","ngay_ban_hanh":"01/07/2025","co_quan_ban_hanh":"ỦY BAN NHÂN DÂN TỈNH PHÚ THỌ","trich_yeu":"Quy định chức năng, nhiệm vụ, quyền hạn và cơ cấu tổ chức của Sở Công Thương tỉnh Phú Thọ","nguoi_ky":"Trần Duy Đông"},
  "pdf_test_4.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"03/2026/QĐ-TTg","ngay_ban_hanh":"20/01/2026","co_quan_ban_hanh":"THỦ TƯỚNG CHÍNH PHỦ","trich_yeu":"Sửa đổi, bổ sung một số điều của Quy chế xây dựng, quản lý, thực hiện Chương trình Thương hiệu quốc gia Việt Nam ban hành kèm theo Quyết định số 30/2019/QĐ-TTg ngày 08 tháng 10 năm 2019 của Thủ tướng Chính phủ","nguoi_ky":"Bùi Thanh Sơn"},
  "pdf_test_5.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"04/2026/QĐ-TTg","ngay_ban_hanh":"23/01/2026","co_quan_ban_hanh":"THỦ TƯỚNG CHÍNH PHỦ","trich_yeu":"Ban hành Quy chế hoạt động ứng phó sự cố tràn dầu","nguoi_ky":"Trần Hồng Hà"},
  "pdf_test_6.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"05/2026/QĐ-TTg","ngay_ban_hanh":"27/01/2026","co_quan_ban_hanh":"THỦ TƯỚNG CHÍNH PHỦ","trich_yeu":"Quy định nguyên tắc, tiêu chí, định mức phân bổ vốn ngân sách trung ương thực hiện Chương trình mục tiêu quốc gia phòng, chống ma túy đến năm 2030","nguoi_ky":"Hồ Đức Phớc"},
  "pdf_test_7.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"056/2025/QĐ-UBND","ngay_ban_hanh":"31/12/2025","co_quan_ban_hanh":"Ủy ban nhân dân tỉnh Đắk Lắk","trich_yeu":"Bảng giá tính thuế tài nguyên đối với nhóm, loại tài nguyên có tính chất lý, hóa giống nhau trên địa bàn tỉnh Đắk Lắk","nguoi_ky":"Hồ Thị Nguyên Thảo"},
  "pdf_test_8.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"06/2026/QĐ-TTg","ngay_ban_hanh":"27/01/2026","co_quan_ban_hanh":"THỦ TƯỚNG CHÍNH PHỦ","trich_yeu":"Về tổ chức, hoạt động, nguồn kinh phí và việc sử dụng nguồn kinh phí cho hoạt động bộ máy của Quỹ Dịch vụ viễn thông công ích Việt Nam","nguoi_ky":"Hồ Đức Phớc"},
  "pdf_test_9.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"07/2026/QĐ-TTg","ngay_ban_hanh":"27/01/2026","co_quan_ban_hanh":"THỦ TƯỚNG CHÍNH PHỦ","trich_yeu":"Về việc thành lập, quản lý và sử dụng Quỹ phòng, chống tội phạm","nguoi_ky":"Hồ Đức Phớc"},
  "pdf_test_10.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"10/2025/QĐ-TTg","ngay_ban_hanh":"19/04/2025","co_quan_ban_hanh":"THỦ TƯỚNG CHÍNH PHỦ","trich_yeu":"Quy định về việc thành lập, tổ chức, hoạt động của trung tâm giáo dục quốc phòng và an ninh","nguoi_ky":"Lê Thành Long"},
  "pdf_test_11.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"102/2025/QĐ-UBND","ngay_ban_hanh":"10/09/2025","co_quan_ban_hanh":"ỦY BAN NHÂN DÂN TỈNH NINH BÌNH","trich_yeu":"Ban hành Quy định chức năng, nhiệm vụ, quyền hạn và cơ cấu tổ chức của Trung tâm Y tế Kim Bảng thuộc Sở Y tế tỉnh Ninh Bình","nguoi_ky":"Phạm Quang Ngọc"},
  "pdf_test_12.pdf": {"loai_van_ban":"QUYẾT ĐỊNH","so_hieu":"103/2025/QĐ-UBND","ngay_ban_hanh":"10/09/2025","co_quan_ban_hanh":"ỦY BAN NHÂN DÂN TỈNH NINH BÌNH","trich_yeu":"Ban hành Quy định chức năng, nhiệm vụ, quyền hạn và cơ cấu tổ chức của Trung tâm Y tế Hoa Lư thuộc Sở Y tế tỉnh Ninh Bình","nguoi_ky":"Phạm Quang Ngọc"}
}

# Load parts
merged = dict(original)
for part in ["gt_part1.json","gt_part2.json","gt_part3.json","gt_part4.json"]:
    path = os.path.join(BASE, part)
    if os.path.exists(path):
        with open(path,"r",encoding="utf-8") as f:
            merged.update(json.load(f))
        print(f"Loaded {part}")

# Sort by number
def sort_key(k):
    num = k.replace("pdf_test_","").replace(".pdf","")
    return int(num)

sorted_data = dict(sorted(merged.items(), key=lambda x: sort_key(x[0])))

# Write final
out = os.path.join(BASE, "ground_truth.json")
with open(out,"w",encoding="utf-8") as f:
    json.dump(sorted_data,f,ensure_ascii=False,indent=2)

print(f"\nTotal entries: {len(sorted_data)}")
print(f"Saved to: {out}")
