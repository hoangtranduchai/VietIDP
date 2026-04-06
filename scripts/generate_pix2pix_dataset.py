import os
import cv2
import numpy as np
import random
from pathlib import Path

# Cấu hình Path theo dự án
BASE_DIR = Path(__file__).resolve().parent.parent
STAMPS_DIR = BASE_DIR / "data" / "interim" / "stamps_transparent" # Dùng ảnh đã xóa nền
BG_TEXT_DIR = BASE_DIR / "data" / "document_crops"      # Thư mục chứa các ảnh crop văn bản sạch (Không dấu)
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "pix2pix_dataset"

# Cấu hình Sinh Dữ Liệu
NUM_IMAGES = 1000  # Số lượng ảnh muốn sinh
TARGET_SIZE = 512  # Kích thước chuẩn cho Pix2Pix (thường dùng 256x256 hoặc 512x512)

def create_dirs():
    """Tạo cấu trúc thư mục A/B/Paired cho Pix2Pix"""
    for split in ['train', 'val']:
        (OUTPUT_DIR / split).mkdir(parents=True, exist_ok=True)
    print(f"✅ Đã khởi tạo thư mục Dataset tại: {OUTPUT_DIR}")

def augment_stamp(stamp):
    """Augmentation con dấu: Xoay nhẹ, bôi mờ, thay đổi kích thước để mô phỏng thực tế."""
    # 1. Resize ngẫu nhiên
    scale = random.uniform(0.6, 1.2)
    new_w, new_h = int(stamp.shape[1] * scale), int(stamp.shape[0] * scale)
    stamp = cv2.resize(stamp, (new_w, new_h))
    
    # 2. Xoay ngẫu nhiên (-15 đến 15 độ)
    angle = random.uniform(-15, 15)
    center = (new_w // 2, new_h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    stamp = cv2.warpAffine(stamp, M, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    
    # 3. Simulate mực mờ/nhòe (Gaussian Blur ngẫu nhiên)
    if random.random() > 0.5:
        stamp = cv2.GaussianBlur(stamp, (3, 3), 0)
        
    return stamp

def overlay_stamp_with_alpha(background, stamp):
    """
    Hòa trộn con dấu (RGBA) lên background (RGB)
    Dùng phép tính Alpha Blending để mô phỏng mực dấu chìm đè lên mực in.
    """
    bg_h, bg_w = background.shape[:2]
    st_h, st_w = stamp.shape[:2]

    # Nếu nhỏ hơn không chèn được
    if bg_h < st_h or bg_w < st_w:
        return background

    # Random vị trí dán
    y_offset = random.randint(0, bg_h - st_h)
    x_offset = random.randint(0, bg_w - st_w)

    # Tính toán alpha mask từ kênh 4 (Opacity) của ảnh dấu png
    alpha_s = stamp[:, :, 3] / 255.0
    alpha_l = 1.0 - alpha_s

    # Tạo bản copy của background để Overlay
    result = background.copy()

    for c in range(0, 3): # Trộn 3 kênh R, G, B
        # Phép Blend = (Màu con dấu * Alpha của dấu) + (Màu nền văn bản * (1 - Alpha))
        # Mô phỏng hiệu ứng Multiply để mực đỏ giống mực in thấm vào giấy
        overlay_color = (stamp[:, :, c] * alpha_s)
        background_color = (result[y_offset:y_offset+st_h, x_offset:x_offset+st_w, c] * alpha_l)
        
        result[y_offset:y_offset+st_h, x_offset:x_offset+st_w, c] = overlay_color + background_color

    return result

def crop_random_background(bg_image, size):
    """Crop ngẫu nhiên một vùng văn bản kích thước Size x Size để làm nền."""
    h, w = bg_image.shape[:2]
    if h <= size or w <= size:
        return cv2.resize(bg_image, (size, size))
    y = random.randint(0, h - size)
    x = random.randint(0, w - size)
    return bg_image[y:y+size, x:x+size]

def main():
    create_dirs()
    
    # Đọc list files
    stamp_files = list(STAMPS_DIR.glob("*.png"))
    bg_files = list(BG_TEXT_DIR.glob("*.*"))

    if not stamp_files or not bg_files:
        print("❌ Thiếu dữ liệu đầu vào. Vui lòng kiểm tra thư mục 'stamps' và 'document_crops'.")
        return

    print(f"🔄 Đang sinh {NUM_IMAGES} samples cho mô hình Pix2Pix GAN...")

    for i in range(NUM_IMAGES):
        split = 'train' if random.random() < 0.85 else 'val'
        
        # 1. Chọn ngẫu nhiên nền sạch và con dấu đỏ
        bg_path = random.choice(bg_files)
        stamp_path = random.choice(stamp_files)
        
        bg_img = cv2.imread(str(bg_path))
        stamp_img = cv2.imread(str(stamp_path), cv2.IMREAD_UNCHANGED) # RGBA

        if bg_img is None or stamp_img is None or stamp_img.shape[2] != 4:
            continue
            
        # 2. Xử lý logic Background & Stamp
        bg_crop = crop_random_background(bg_img, TARGET_SIZE)
        stamp_aug = augment_stamp(stamp_img)
        
        # 3. Tạo Target B (Sạch - Không có dấu)
        img_B = bg_crop.copy() 
        
        # 4. Tạo Input A (Dơ - Đã áp con dấu vô)
        img_A = overlay_stamp_with_alpha(bg_crop, stamp_aug)

        # 5. Gộp lại tạo Paired Image [A | B] - Yêu cầu thiết yếu của Pix2Pix format
        paired_img = np.concatenate([img_A, img_B], axis=1) # Width là 512*2 = 1024
        
        # 6. Lưu kết quả
        out_name = f"sample_{i:05d}.jpg"
        cv2.imwrite(str(OUTPUT_DIR / split / out_name), paired_img)

        if (i+1) % 100 == 0:
            print(f"✅ Xong {i+1}/{NUM_IMAGES} ảnh...")

    print("🎉 Hoàn thành sinh dữ liệu (Paired Dataset) của Pix2Pix!")

if __name__ == "__main__":
    main()
