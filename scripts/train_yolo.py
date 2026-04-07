import os
from ultralytics import YOLO

# Sử dụng paths tương đối từ project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOLO_BASE_MODEL = os.path.join(BASE_DIR, "yolov8n.pt")
DATASET_DIR = os.path.join(BASE_DIR, "data", "yolo_dataset")
MODEL_OUTPUT_DIR = os.path.join(BASE_DIR, "ai", "models")

model = YOLO(YOLO_BASE_MODEL)

data_path = os.path.join(DATASET_DIR, "data.yaml")

if __name__ == '__main__':
    if not os.path.exists(data_path):
        print(f"❌ data.yaml không tìm thấy tại: {data_path}")
        print(f"   Hãy chạy generate_dataset.py trước để tạo dataset")
        exit(1)

    print("🚀 Bắt đầu huấn luyện mô hình YOLOv8 nhận diện CON DẤU")
    results = model.train(
        data=data_path,
        epochs=30,
        imgsz=640,
        batch=8,
        name='stamp_model',
        project=MODEL_OUTPUT_DIR
    )
    print("✅ Huấn luyện hoàn tất! Model lưu trong thư mục ai/models/stamp_model/weights/")
