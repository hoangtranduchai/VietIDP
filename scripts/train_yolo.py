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
    
    # Tải trọng số khởi tạo YOLOv8 hệ Nano (siêu nhẹ, siêu nhạy). 
    # Framework sẽ tự tải 'yolov8n.pt' từ Internet nếu chưa có trong thư mục.
    model = YOLO('yolov8n.pt') 

    # Các thông số huấn luyện (Hyper-parameters) tối ưu cho siêu máy tính Miniconda
    results = model.train(
        data=str(DATASET_YAML),
        epochs=50,             # Chạy 50 vòng hội tụ (có Early Stopping tự ngắt nếu loss không giảm)
        imgsz=1024,            # CỰC QUAN TRỌNG: A4 rất to, nâng imgsz lên 1024 để máy học nhìn ra con dấu nhỏ
        batch=16,              # Nhồi 16 ảnh A4 1 lúc (Yêu cầu khoảng 8-12GB VRAM GPU)
        name='stamp_detector', # Checkpoint name
        project=str(MODEL_OUTPUT_DIR),
        device=0,              # Buộc sử dụng Card Đồ Họa Cụm 0 (NVIDIA)
        patience=10,           # Ngừng ngay nếu 10 Epoch không khôn lên được
        workers=8              # Bật đa luồng CPU chuẩn bị ảnh cho GPU (Data Loader)
    )
    
    print(f"✅ Huấn luyện thành công rực rỡ!")
    print(f"📁 Trọng số suy luận trực tiếp (best.pt) đóng gói tại: {MODEL_OUTPUT_DIR}/stamp_detector/weights/best.pt")
