import os
from ultralytics import YOLO
from pathlib import Path

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN MLOps
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_YAML = BASE_DIR / "data" / "processed" / "yolo_dataset" / "dataset.yaml"
MODEL_OUTPUT_DIR = BASE_DIR / "models" / "finetuned"

if __name__ == '__main__':
    # Kiểm tra xem bạn đã sinh dữ liệu YOLO từ script trước chưa
    if not DATASET_YAML.exists():
        print(f"❌ Không tìm thấy cấu hình Dataset tại: {DATASET_YAML}")
        print("💡 Vui lòng chạy 'python scripts/generate_yolo_dataset.py' trước tiên.")
        exit(1)

    print("🚀 KHỞI ĐỘNG LÒ LUYỆN ĐAN: YOLOv8 MLOPS DETECTOR 🚀")
    
    # Nâng cấp phần cứng: Dùng YOLOv8x (Extra Large) mạnh nhất thế giới.
    model = YOLO('yolov8x.pt') 

    # Các thông số huấn luyện ép xung cho RTX 5070 8GB VRAM
    results = model.train(
        data=str(DATASET_YAML),
        epochs=50,             
        imgsz=1024,            # Bắt buộc 1024 để nhìn rõ con dấu trên A4
        batch=4,               # Hạ xuống 4 vì bản X cực kỳ nặng, batch=16 sẽ gây OOM trên 8GB VRAM
        name='stamp_detector',
        project=str(MODEL_OUTPUT_DIR),
        device=0,              # Buộc sử dụng Card Đồ Họa Cụm 0 (NVIDIA)
        patience=10,           # Ngừng ngay nếu 10 Epoch không khôn lên được
        workers=8              # Bật đa luồng CPU chuẩn bị ảnh cho GPU (Data Loader)
    )
    
    print(f"✅ Huấn luyện thành công rực rỡ!")
    print(f"📁 Trọng số suy luận trực tiếp (best.pt) đóng gói tại: {MODEL_OUTPUT_DIR}/stamp_detector/weights/best.pt")
