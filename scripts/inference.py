import cv2
import os
import numpy as np
from ultralytics import YOLO

# Paths tương đối từ project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ai", "models", "stamp_model", "weights", "best.pt")

model = None


def init_model():
    global model
    if model is None and os.path.exists(MODEL_PATH):
        try:
            model = YOLO(MODEL_PATH)
            print(f"✅ AI Model loaded: {MODEL_PATH}")
        except Exception as e:
            print(f"❌ Error loading model: {e}")


def detect_stamps_on_image(image_bytes):
    """
    Nhận diện con dấu trên ảnh đầu vào, trả về danh sách bounding boxes.
    [ {'x_center':10,'y_center':10,'width':50,'height':50, 'confidence': 0.95}, ... ]
    """
    if model is None:
        init_model()

    if model is None:
        return []

    # Đọc ảnh từ bytes
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return []

    results = model.predict(source=img, conf=0.5, save=False)

    stamps = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x, y, w, h = box.xywh[0].tolist()
            conf = float(box.conf[0])
            stamps.append({
                "x_center": x,
                "y_center": y,
                "width": w,
                "height": h,
                "confidence": round(conf * 100, 2)
            })

    return stamps
