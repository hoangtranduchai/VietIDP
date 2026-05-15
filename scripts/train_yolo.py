import os
from ultralytics import YOLO
from pathlib import Path

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN MLOps
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_YAML = BASE_DIR / "data" / "processed" / "yolo_dataset" / "dataset.yaml"
MODEL_OUTPUT_DIR = BASE_DIR / "models"
FINAL_WEIGHTS = BASE_DIR / "models" / "stamp_model" / "weights" / "best.pt"

if __name__ == '__main__':
    import shutil

    # Kiểm tra xem bạn đã sinh dữ liệu YOLO từ script trước chưa
    if not DATASET_YAML.exists():
        print(f"❌ Không tìm thấy cấu hình Dataset tại: {DATASET_YAML}")
        print("💡 Vui lòng chạy 'python scripts/generate_yolo_dataset.py' trước tiên.")
        exit(1)

    print("🚀 KHỞI ĐỘNG HUẤN LUYỆN: YOLOv8l STAMP DETECTOR 🚀")
    print("   Config: imgsz=640, batch=16, epochs=50, patience=15")
    print("   ETA: ~4-5 giờ trên RTX 5070 8GB VRAM")
    
    # ====================================================================
    # LỰA CHỌN MODEL: YOLOv8l (Large, 43M params)
    # ====================================================================
    # Lý do không dùng YOLOv8x (68M):
    #   - Thực đo: x + 1024 + batch=4 = 12s/batch → 6h/epoch (quá chậm)
    #   - Cho 1-class detection, l vs x chênh <1% mAP (Ultralytics benchmark)
    #   - l nhỏ hơn 37% params → nhanh hơn ~2x, ít overfit hơn
    # Lý do không dùng YOLOv8m (25M):
    #   - m nhanh hơn nữa nhưng feature extraction yếu hơn cho stamp nhỏ/mờ
    #   - l là sweet spot: đủ mạnh + đủ nhanh cho 8GB VRAM
    # ====================================================================
    model = YOLO('yolov8l.pt') 

    results = model.train(
        data=str(DATASET_YAML),

        # === Core Training ===
        # Tính toán: l + 640 + batch=8 sẽ giữ VRAM < 8.0GB, tránh tràn RAM (spillover)
        epochs=50,             # 50 epochs: 1-class converges nhanh, early stop bảo vệ
        imgsz=640,             # 640: native YOLO resolution, stamp vẫn ~80-120px (đủ detect)
        batch=8,               # batch=8: KHÔNG ĐƯỢC VƯỢT QUÁ 8GB VRAM vật lý của RTX 5070
        device=0,

        # === Learning Rate (chống overfit) ===
        lr0=0.01,              # Default YOLO, đã proven tốt
        lrf=0.01,              # Giảm LR 100x cuối training → fine-tune precision
        cos_lr=True,           # Cosine schedule: giảm mượt, không drop đột ngột
        warmup_epochs=3,       # 3 epochs warm-up: ổn định gradient trước khi train mạnh

        # === Early Stopping (chống overfit chính) ===
        patience=15,           # Stop nếu 15 epochs val mAP không tăng

        # === Augmentation (chống overfit - layer 2) ===
        # Dataset v2 ĐÃ CÓ augmentation riêng → giữ YOLO augment vừa phải
        mosaic=1.0,            # Mosaic ON: ghép 4 ảnh → tăng diversity
        mixup=0.15,            # MixUp 15%: blend ảnh → regularization
        close_mosaic=10,       # Tắt mosaic 10 epochs cuối → fine-tune bbox precision
        hsv_h=0.015,           # Hue jitter nhẹ
        hsv_s=0.5,             # Saturation jitter
        hsv_v=0.3,             # Brightness jitter
        degrees=5.0,           # Xoay nhẹ (dataset đã có ±15°)
        translate=0.1,         # Dịch 10%
        scale=0.5,             # Scale ±50%
        fliplr=0.5,            # Lật ngang 50%
        flipud=0.0,            # Không lật dọc (stamp có chữ)

        # === Performance ===
        amp=True,              # FP16 mixed precision → nhanh hơn + tiết kiệm VRAM
        workers=4,
        cache='ram',           # Cache 640px vào RAM (~8GB) → loại bỏ disk I/O bottleneck
        exist_ok=True,

        # === Output ===
        name='stamp_model',
        project=str(MODEL_OUTPUT_DIR),
        verbose=True,
    )
    
    # Copy best.pt vào đúng vị trí mà Config.STAMP_DETECTION_MODEL trỏ tới
    trained_best = MODEL_OUTPUT_DIR / "stamp_model" / "weights" / "best.pt"
    if trained_best.exists():
        FINAL_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
        if str(trained_best.resolve()) != str(FINAL_WEIGHTS.resolve()):
            shutil.copy2(str(trained_best), str(FINAL_WEIGHTS))
        print(f"✅ Huấn luyện thành công!")
        print(f"📁 Weights tại: {FINAL_WEIGHTS}")
    else:
        print(f"⚠️ Huấn luyện xong nhưng không tìm thấy best.pt tại {trained_best}")
        print(f"   Kiểm tra thư mục: {MODEL_OUTPUT_DIR / 'stamp_model'}")
