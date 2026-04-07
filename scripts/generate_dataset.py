import cv2
import os
import numpy as np
import random
from pathlib import Path

# Paths tương đối từ project root
BASE_DIR = Path(__file__).resolve().parent.parent
STAMPS_DIR = BASE_DIR / "data" / "stamps" / "extracted"
DATASET_DIR = BASE_DIR / "data" / "yolo_dataset"

NUM_IMAGES = 200


def create_yolo_dataset_structure():
    """Tạo cấu trúc thư mục YOLOv8 chuẩn."""
    dirs = [
        DATASET_DIR / "images" / "train",
        DATASET_DIR / "images" / "val",
        DATASET_DIR / "labels" / "train",
        DATASET_DIR / "labels" / "val",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print(f"✅ Đã tạo cấu trúc YOLO tại {DATASET_DIR}")


def generate_synthetic_document(width=800, height=1200):
    """Tạo background trắng/ngà giống tờ giấy scan."""
    base_color = random.randint(230, 255)
    img = np.full((height, width, 3), base_color, dtype=np.uint8)
    for y in range(100, height - 200, 30):
        if random.random() > 0.3:
            random_length = random.randint(300, 600)
            cv2.line(img, (100, y), (100 + random_length, y),
                     (100, 100, 100), random.randint(1, 3))
    return img


def overlay_stamp(bg_img, stamp_path):
    """Dán con dấu lên nền văn bản, trả về ảnh mới và tọa độ YOLO."""
    stamp = cv2.imread(str(stamp_path), cv2.IMREAD_UNCHANGED)
    if stamp is None:
        return None, None

    new_h = random.randint(100, 250)
    aspect_ratio = stamp.shape[1] / stamp.shape[0]
    new_w = int(new_h * aspect_ratio)
    stamp = cv2.resize(stamp, (new_w, new_h))

    bg_h, bg_w = bg_img.shape[:2]

    if random.random() > 0.2:
        max_y_start = int(bg_h * 0.5)
        y_offset = random.randint(max_y_start, max(max_y_start + 1, bg_h - new_h - 20))
    else:
        y_offset = random.randint(20, max(21, int(bg_h * 0.5)))

    x_offset = random.randint(20, max(21, bg_w - new_w - 20))

    if len(stamp.shape) == 3 and stamp.shape[2] == 3:
        roi = bg_img[y_offset:y_offset + new_h, x_offset:x_offset + new_w]
        gray = cv2.cvtColor(stamp, cv2.COLOR_BGR2GRAY)
        ret, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        mask_inv = cv2.bitwise_not(mask)
        bg_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)
        stamp_fg = cv2.bitwise_and(stamp, stamp, mask=mask)
        dst = cv2.add(bg_bg, stamp_fg)
        bg_img[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = dst
    elif len(stamp.shape) == 3 and stamp.shape[2] == 4:
        alpha_s = stamp[:, :, 3] / 255.0
        alpha_l = 1.0 - alpha_s
        for c in range(0, 3):
            bg_img[y_offset:y_offset + new_h, x_offset:x_offset + new_w, c] = (
                alpha_s * stamp[:, :, c] +
                alpha_l * bg_img[y_offset:y_offset + new_h, x_offset:x_offset + new_w, c]
            )

    x_c = (x_offset + new_w / 2.0) / bg_w
    y_c = (y_offset + new_h / 2.0) / bg_h
    w_pct = new_w / bg_w
    h_pct = new_h / bg_h

    bbox = f"0 {x_c:.6f} {y_c:.6f} {w_pct:.6f} {h_pct:.6f}"
    return bg_img, bbox


def main():
    create_yolo_dataset_structure()

    stamp_files = [
        f for f in os.listdir(STAMPS_DIR)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ][:200] if STAMPS_DIR.exists() else []

    if not stamp_files:
        print("❌ Không tìm thấy ảnh con dấu trong", STAMPS_DIR)
        return

    print(f"🔄 Bắt đầu sinh {NUM_IMAGES} ảnh giả lập từ {len(stamp_files)} con dấu...")

    for i in range(NUM_IMAGES):
        split = "train" if random.random() < 0.8 else "val"
        bg = generate_synthetic_document()
        stamp_f = random.choice(stamp_files)
        stamp_path = STAMPS_DIR / stamp_f
        result_img, yolo_label = overlay_stamp(bg, stamp_path)

        if result_img is not None:
            img_name = f"doc_{i:04d}.jpg"
            lbl_name = f"doc_{i:04d}.txt"
            img_path = DATASET_DIR / "images" / split / img_name
            cv2.imwrite(str(img_path), result_img)
            lbl_path = DATASET_DIR / "labels" / split / lbl_name
            with open(lbl_path, "w") as f:
                f.write(yolo_label)

        if (i + 1) % 50 == 0:
            print(f"  Đã sinh {i + 1}/{NUM_IMAGES} ảnh...")

    yaml_content = f"""train: {DATASET_DIR}/images/train
val: {DATASET_DIR}/images/val

nc: 1
names: ['stamp']
"""
    with open(DATASET_DIR / "data.yaml", "w") as f:
        f.write(yaml_content)

    print("\n✅ HOÀN TẤT SINH DATASET!")


if __name__ == "__main__":
    main()
