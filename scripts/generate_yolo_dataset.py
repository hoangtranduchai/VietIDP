import os
import cv2
import numpy as np
import random
from pathlib import Path
import yaml
from tqdm import tqdm

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN MLOps
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
STAMPS_DIR = BASE_DIR / "data" / "interim" / "stamps_transparent"
BG_TEXT_DIR = BASE_DIR / "data" / "interim" / "document_crops"  # 2200 Ảnh A4 sạch
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "yolo_dataset"

# Số lượng dữ liệu YOLO cần sinh
NUM_IMAGES = 5000  

def create_yolo_structure():
    """Tạo kiến trúc thư mục chuẩn Ultralytics YOLOv8"""
    for folder in ['images/train', 'images/val', 'labels/train', 'labels/val']:
        (OUTPUT_DIR / folder).mkdir(parents=True, exist_ok=True)
        
    # Tạo file dataset.yaml định nghĩa đường dẫn cho YOLO
    yaml_config = {
        'path': str(OUTPUT_DIR.resolve()),
        'train': 'images/train',
        'val': 'images/val',
        'names': {0: 'stamp'}
    }
    with open(OUTPUT_DIR / 'dataset.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(yaml_config, f, sort_keys=False)
        
    print(f"✅ Đã tạo cấu trúc YOLO & file cấu hình tại: {OUTPUT_DIR}")

def augment_stamp(stamp, bg_width, bg_height):
    """
    Scale con dấu theo tỷ lệ trang A4 để bám sát thực tế.
    Một con dấu thật đường kính khoảng 3.5cm -> 4.5cm.
    Trang A4 ngang 21cm. Nghĩa là con dấu chiếm khoảng 16% - 22% chiều ngang trang giấy.
    """
    target_width_ratio = random.uniform(0.15, 0.25)
    target_w = int(bg_width * target_width_ratio)
    
    current_h, current_w = stamp.shape[:2]
    scale = target_w / max(current_w, 1)
    
    new_w = int(current_w * scale)
    new_h = int(current_h * scale)
    
    stamp_resized = cv2.resize(stamp, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Xoay ngẫu nhiên
    angle = random.uniform(-10, 10)
    center = (new_w // 2, new_h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    stamp_rotated = cv2.warpAffine(stamp_resized, M, (new_w, new_h), 
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    return stamp_rotated

def overlay_stamp_and_get_bbox(background, stamp):
    """
    Dán dấu lên nền A4 và BÁO LẠI tọa độ tạo chuẩn YOLO.
    Quy tắc đóng dấu: Thường đóng ở Nửa dưới (hoặc chữ ký), lệch sang phải.
    """
    bg_h, bg_w = background.shape[:2]
    st_h, st_w = stamp.shape[:2]

    # Vị trí ngẫu nhiên thiên về nửa dưới góc phải (như văn bản thật)
    # Tuy nhiên vẫn thi thoảng cho random khắp nơi để tăng tính Robust (chống Overfit)
    if random.random() < 0.7:  # 70% rơi trúng vị trí tiêu chuẩn chữ ký
        y_offset = random.randint(int(bg_h * 0.5), bg_h - st_h - 50)
        x_offset = random.randint(int(bg_w * 0.3), bg_w - st_w - 50)
    else:  # 30% dán bừa bãi hoặc chồng chéo lên góc
        y_offset = random.randint(50, bg_h - st_h - 50)
        x_offset = random.randint(50, bg_w - st_w - 50)

    # 1. Thực hiện dập hiệu ứng mực thấm
    opacity = random.uniform(0.7, 0.95)
    alpha_s = (stamp[:, :, 3] / 255.0) * opacity
    alpha_l = 1.0 - alpha_s

    result = background.copy()
    for c in range(0, 3):
        overlay_color = (stamp[:, :, c] * alpha_s)
        background_color = (result[y_offset:y_offset+st_h, x_offset:x_offset+st_w, c] * alpha_l)
        result[y_offset:y_offset+st_h, x_offset:x_offset+st_w, c] = overlay_color + background_color

    # 2. XÁC ĐỊNH Bounding Box cho YOLO (Định dạng x_center, y_center, width, height từ 0.0 -> 1.0)
    # Cắt bỏ những phần rìa hoàn toàn trong suốt (Alpha = 0) của ảnh stamp để bắt Box cực sát
    alpha_channel = stamp[:, :, 3]
    coords = cv2.findNonZero(alpha_channel)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        # Toạ độ thực sự của Box trên ảnh lớn
        real_x = x_offset + x
        real_y = y_offset + y
        real_w = w
        real_h = h
        
        # Chuyển về chuẩn Normalize của YOLO
        x_center = (real_x + real_w / 2) / bg_w
        y_center = (real_y + real_h / 2) / bg_h
        norm_w = real_w / bg_w
        norm_h = real_h / bg_h
        
        bbox = f"0 {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}"
        return result, bbox
    else:
        return background, None

def main():
    create_yolo_structure()
    
    stamp_files = list(STAMPS_DIR.glob("*.png"))
    bg_files = list(BG_TEXT_DIR.glob("*.*"))

    if not stamp_files or not bg_files:
        print("❌ LỖI: Không tìm thấy ảnh nền A4 hoặc con dấu.")
        return

    print(f"🚀 [YOLO Auto Labeling] Đang tự động dán và vẽ khung {NUM_IMAGES} mẫu...")

    success = 0
    for i in tqdm(range(NUM_IMAGES), desc="Generating YOLO Dataset"):
        split = 'train' if random.random() < 0.85 else 'val'
        
        bg_path = random.choice(bg_files)
        stamp_path = random.choice(stamp_files)
        
        bg_img = cv2.imread(str(bg_path))
        stamp_img = cv2.imread(str(stamp_path), cv2.IMREAD_UNCHANGED)
        
        if bg_img is None or stamp_img is None or stamp_img.shape[2] != 4:
            continue
            
        # 1. Kéo dãn con dấu cho vừa mắt văn bản
        stamp_aug = augment_stamp(stamp_img, bg_img.shape[1], bg_img.shape[0])
        
        # 2. Đóng dấu & Xoay Compa sinh Tọa độ
        result_img, yolo_bbox = overlay_stamp_and_get_bbox(bg_img, stamp_aug)
        
        if yolo_bbox:
            # Lưu ảnh
            out_name = f"doc_stamp_{i:06d}"
            img_out_path = OUTPUT_DIR / f"images/{split}/{out_name}.jpg"
            # Giảm chất lượng ảnh nén đôi chút để YOLO load đĩa nhanh hơn
            cv2.imwrite(str(img_out_path), result_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            
            # Lưu text nhãn
            txt_out_path = OUTPUT_DIR / f"labels/{split}/{out_name}.txt"
            with open(txt_out_path, 'w') as f:
                f.write(yolo_bbox)
                
            success += 1

    print(f"🎉 Hoàn thành! Đã sinh {success} Data Labeled hoàn hảo cho YOLOv8, sẵn sàng Train!")

if __name__ == "__main__":
    main()
