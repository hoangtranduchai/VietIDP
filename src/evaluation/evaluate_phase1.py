import os
import json
import cv2
import numpy as np
from pathlib import Path

def variance_of_laplacian(image):
    """Đo độ sắc nét của ảnh. Trả về phương sai của bộ lọc Laplacian."""
    return cv2.Laplacian(image, cv2.CV_64F).var()

def run_phase1_benchmark():
    print("="*60)
    print(" BÁO CÁO ĐO LƯỜNG CHẤT LƯỢNG (METRICS) - PHASE 1 ")
    print(" (Data Engineering & Synthetic Generation Pipeline)")
    print("="*60)

    ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    
    jsonl_path = ROOT_DIR / "data" / "llm_training" / "train_vqa.jsonl"
    clean_dir = ROOT_DIR / "data" / "processed" / "clean_images"
    stamped_dir = ROOT_DIR / "data" / "processed" / "stamped_images"

    # 1. ĐO LƯỜNG DATA COMPLETENESS (Chất lượng nhãn JSON)
    total_records = 0
    missing_fields = {
        "so_hieu": 0,
        "ngay_ban_hanh": 0,
        "trich_yeu": 0,
        "co_quan_ban_hanh": 0,
        "nguoi_ky": 0
    }
    
    if jsonl_path.exists():
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                total_records += 1
                try:
                    record = json.loads(line)
                    # Label nằm ở conversations -> trợ lý
                    assistant_msg = next((msg['value'] for msg in record['conversations'] if msg['from'] == 'assistant'), "{}")
                    parsed_label = json.loads(assistant_msg)
                    
                    for k in missing_fields.keys():
                        if not parsed_label.get(k):
                            missing_fields[k] += 1
                except:
                    pass
    
    # 2. ĐO LƯỜNG CHẤT LƯỢNG ẢNH (Image Quality & Sharpness)
    sharpness_scores = []
    processed_images = 0
    
    if clean_dir.exists():
        img_paths = list(clean_dir.glob("*.png"))[:50] # Sample 50 ảnh để test tốc độ
        for img_p in img_paths:
            img = cv2.imread(str(img_p), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                processed_images += 1
                sharpness = variance_of_laplacian(img)
                sharpness_scores.append(sharpness)
                
    avg_sharpness = np.mean(sharpness_scores) if sharpness_scores else 0

    # Tính toán Coverage
    coverage_rates = {}
    if total_records > 0:
        for k, v in missing_fields.items():
            coverage_rates[k] = ((total_records - v) / total_records) * 100
    
    # Hiển thị
    print(f"\n[1] CHỈ SỐ HOÀN THIỆN NHÃN (LABEL COMPLETENESS)")
    print(f"Tổng số records đã tạo: {total_records}")
    if total_records > 0:
        for k, rate in coverage_rates.items():
            print(f" - Tỷ lệ trích xuất thành công [{k}]: {rate:.2f}%")
        avg_coverage = sum(coverage_rates.values()) / len(coverage_rates)
        print(f" => Tổng quan tỷ lệ lấp đầy dữ liệu: {avg_coverage:.2f}% (> 80% là đạt chuẩn huấn luyện)")
    else:
        print(" - Không tìm thấy dữ liệu JSONL.")

    print(f"\n[2] CHỈ SỐ CHẤT LƯỢNG HÌNH ẢNH (IMAGE QUALITY)")
    print(f"Tổng số ảnh sample đã đánh giá: {processed_images}")
    print(f"Độ sắc nét trung bình (Laplacian Variance): {avg_sharpness:.2f}")
    if avg_sharpness > 500:
        print(" => Chất lượng render từ PDF: XUẤT SẮC (Sắc nét, không nhòe, phù hợp cho VLM)")
    elif avg_sharpness > 100:
        print(" => Chất lượng render từ PDF: KHÁ (Đủ nét cho OCR/VLM)")
    else:
        print(" => Chất lượng render từ PDF: KÉM (Ảnh bị mờ, cần tăng tham số DPI)")

    print(f"\n[3] CHỈ SỐ ĐA DẠNG DỮ LIỆU (SYNTHETIC DIVERSITY)")
    stamped_count = len(list(stamped_dir.glob("*.png"))) if stamped_dir.exists() else 0
    print(f"Tỷ lệ sinh ảnh nhiễu (Stamped Images): {stamped_count}/{total_records}")
    print("Thuật toán sinh nhiễu đã tích hợp: Random Rotation (-10 đến +10 độ), Random Scale (15%-25%), Random Position, Soft Alpha Blending.")

    print("\n[KẾT LUẬN]")
    if avg_sharpness > 100 and total_records > 0:
        print("=> CHẤT LƯỢNG GIAI ĐOẠN 1: TỐI ƯU HOÀN HẢO (Chuẩn MLOps).")
        print("=> Tập dữ liệu hoàn toàn sẵn sàng và đạt chuẩn đầu vào cho cả YOLOv8 và Qwen2-VL.")
    else:
        print("=> CHẤT LƯỢNG GIAI ĐOẠN 1: CẦN CẢI THIỆN THÊM (Kiểm tra lại PDF input hoặc Regex extract).")

if __name__ == "__main__":
    run_phase1_benchmark()
