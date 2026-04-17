import os
import cv2
import numpy as np
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "data" / "interim" / "stamps_transparent"
TARGET_NUM_STAMPS = 2000  # Số lượng mục tiêu cần thiết

def augment_stamp_transparent(stamp):
    # 1. Resize ngẫu nhiên (60% đến 140% kích thước gốc)
    scale = random.uniform(0.6, 1.4)
    new_w, new_h = max(10, int(stamp.shape[1] * scale)), max(10, int(stamp.shape[0] * scale))
    stamp = cv2.resize(stamp, (new_w, new_h))
    
    # 2. Xoay ngẫu nhiên (-45 đến 45 độ)
    angle = random.uniform(-45, 45)
    center = (new_w // 2, new_h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    # Dùng borderValue trong suốt cho kênh alpha
    stamp = cv2.warpAffine(stamp, M, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    
    # 3. Simulate độ nhòe hoặc mờ (Gaussian Blur)
    if random.random() > 0.5:
        ksize = random.choice([3, 5])
        stamp = cv2.GaussianBlur(stamp, (ksize, ksize), 0)
        
    return stamp

def main():
    if not INPUT_DIR.exists():
        print(f"Không tìm thấy thư mục {INPUT_DIR}")
        return
        
    # Lấy các file gốc (không có prefix amplified_)
    stamp_files = [f for f in INPUT_DIR.glob("*.png") if not f.name.startswith("amplified_")]
    
    if not stamp_files:
        print("Không có ảnh trong suốt nào trong thư mục để phóng đại. Hãy chạy remove_bg_batch.py trước.")
        return
        
    print(f"Đang có {len(stamp_files)} ảnh gốc. Bắt đầu sinh số lượng lớn con dấu (Target: {TARGET_NUM_STAMPS})...")
    
    gen_count = 0
    to_generate = TARGET_NUM_STAMPS - len(stamp_files)
    if to_generate <= 0:
        print("Đã đủ hoặc vượt quá số lượng yêu cầu.")
        return

    for i in range(to_generate):
        stamp_path = random.choice(stamp_files)
        stamp_img = cv2.imread(str(stamp_path), cv2.IMREAD_UNCHANGED)
        
        if stamp_img is None or len(stamp_img.shape) != 3 or stamp_img.shape[2] != 4:
            continue
            
        aug_img = augment_stamp_transparent(stamp_img)
        
        out_name = f"amplified_{i:05d}_{stamp_path.name}"
        cv2.imwrite(str(INPUT_DIR / out_name), aug_img)
        
        gen_count += 1
        if gen_count % 200 == 0:
            print(f"Đã sinh {gen_count}/{to_generate} ảnh con dấu mới...")
            
    print(f"Hoàn tất. Đã bổ sung {gen_count} ảnh con dấu đa dạng về kích cỡ, góc nhìn vào {INPUT_DIR}.")

if __name__ == "__main__":
    main()
