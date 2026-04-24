import os
import cv2
import numpy as np
import random
from pathlib import Path
from tqdm import tqdm

# Cấu hình Path chuẩn MLOps
BASE_DIR = Path(__file__).resolve().parent.parent
STAMPS_DIR = BASE_DIR / "data" / "interim" / "stamps_transparent" # Dùng ảnh đã xóa nền
BG_TEXT_DIR = BASE_DIR / "data" / "interim" / "document_crops"      # Thư mục chứa các ảnh crop văn bản sạch (Không dấu)
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "pix2pix_dataset"

NUM_IMAGES = 10000  # Tạo dư dả 10.000 samples từ 2200 tờ A4 để Train model cứng cáp nhất
TARGET_SIZE = 512   # Vùng crop tiêu chuẩn cho Pix2Pix (Trải nghiệm thực tế tốt nhất)

def create_dirs():
    for split in ['train', 'val']:
        (OUTPUT_DIR / split).mkdir(parents=True, exist_ok=True)

def random_crop_patch(bg_image, target_size=512):
    """Cắt ngẫu nhiên 1 ô vuông nhỏ 512x512 từ trang A4 cực lớn."""
    h, w = bg_image.shape[:2]
    # Nếu ảnh xui xẻo nhỏ hơn 512, thì resize
    if h <= target_size or w <= target_size:
        return cv2.resize(bg_image, (target_size, target_size))
        
    y = random.randint(0, h - target_size)
    x = random.randint(0, w - target_size)
    return bg_image[y:y+target_size, x:x+target_size]

def augment_stamp_for_patch(stamp, patch_size=512):
    """Mô phỏng kích thước thật của con dấu dóng vào ô patch 512x512."""
    # Con dấu thật ngoài đời khi scan 300DPI sẽ tốn khoảng 300-450 pixel
    # Vì thế ta random scale nó ở khoảng 150px đến 350px để tạo tính đa dạng và zoom xa gần
    target_stamp_size = random.randint(150, 350)
    
    current_h, current_w = stamp.shape[:2]
    scale = target_stamp_size / max(current_h, current_w)
    
    new_w, new_h = int(current_w * scale), int(current_h * scale)
    stamp_resized = cv2.resize(stamp, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Xoay ngẫu nhiên
    angle = random.uniform(-10, 10)
    center = (new_w // 2, new_h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    stamp_rotated = cv2.warpAffine(stamp_resized, M, (new_w, new_h), borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    
    return stamp_rotated

def draw_synthetic_blue_signature(image):
    """
    Vẽ ngẫu nhiên các đường cong (Bezier/Polylines) màu XANH LAM giả lập chữ ký tay.
    Giải quyết triệt để lỗi Out-of-Distribution (OOD) khi GAN xóa mất chữ ký thật.
    """
    h, w = image.shape[:2]
    # Xác suất 60% sẽ vẽ chữ ký giả vào ảnh
    if random.random() > 0.6:
        return image
        
    result = image.copy()
    
    # Random màu xanh lam (Blue ink: B cao, G thấp, R thấp)
    b = random.randint(150, 255)
    g = random.randint(0, 100)
    r = random.randint(0, 50)
    color = (b, g, r)
    thickness = random.randint(1, 3)
    
    # Tạo ngẫu nhiên 3-6 đường cong dính liền nhau mô phỏng chữ ký
    num_strokes = random.randint(3, 6)
    
    # Vị trí ngẫu nhiên của chữ ký
    start_x = random.randint(50, w - 150)
    start_y = random.randint(50, h - 150)
    
    pts = [(start_x, start_y)]
    for _ in range(num_strokes):
        # Bước nhảy ngẫu nhiên để tạo các vòng lặp (loops) của chữ ký
        dx = random.randint(-50, 100)
        dy = random.randint(-50, 50)
        
        last_x, last_y = pts[-1]
        new_x = max(0, min(w-1, last_x + dx))
        new_y = max(0, min(h-1, last_y + dy))
        pts.append((new_x, new_y))
        
    # Làm mượt đường gấp khúc thành đường cong (Catmull-Rom spline xấp xỉ)
    pts_arr = np.array(pts, np.int32)
    pts_arr = pts_arr.reshape((-1, 1, 2))
    
    # Vẽ chữ ký
    cv2.polylines(result, [pts_arr], isClosed=False, color=color, thickness=thickness, lineType=cv2.LINE_AA)
    
    # Có thể vẽ thêm một đường gạch dưới đặc trưng của chữ ký
    if random.random() > 0.5:
        ul_start = (max(0, start_x - 20), min(h-1, start_y + 60))
        ul_end = (min(w-1, start_x + 100), min(h-1, start_y + random.randint(50, 70)))
        cv2.line(result, ul_start, ul_end, color, thickness, cv2.LINE_AA)
        
    return result

def overlay_stamp_realistic(background_patch, stamp):
    """
    Hòa trộn theo toán học Alpha Blending (mực thấm nền) vào giữa ô patch 512x512.
    """
    bg_h, bg_w = background_patch.shape[:2]
    st_h, st_w = stamp.shape[:2]

    # Nếu con dấu to hơn patch thì không dán được
    if bg_h < st_h or bg_w < st_w:
        return background_patch.copy()

    # Vị trí dán ngẫu nhiên trong khoảng patch 512
    y_offset = random.randint(0, bg_h - st_h)
    x_offset = random.randint(0, bg_w - st_w)

    # Lấy kênh Alpha và opacity ngẫu nhiên (simulate mực đậm lợt do người đóng tay lực khác nhau)
    opacity = random.uniform(0.65, 0.95)
    alpha_s = (stamp[:, :, 3] / 255.0) * opacity
    alpha_l = 1.0 - alpha_s

    result = background_patch.copy()

    for c in range(0, 3):
        # Trộn mực đỏ thấm vào nền text đen (Áp dụng lý thuyết alpha)
        overlay_color = (stamp[:, :, c] * alpha_s)
        background_color = (result[y_offset:y_offset+st_h, x_offset:x_offset+st_w, c] * alpha_l)
        result[y_offset:y_offset+st_h, x_offset:x_offset+st_w, c] = overlay_color + background_color

    return result

def main():
    create_dirs()
    stamp_files = list(STAMPS_DIR.glob("*.png"))
    bg_files = list(BG_TEXT_DIR.glob("*.*"))

    if not stamp_files or not bg_files:
        print("❌ Lỗi: Thư mục chứa Dấu (stamps_transparent) hoặc Nền (document_crops) trống!")
        return

    print(f"🚀 [Pix2Pix - Patch Based Strategy] Đang chuẩn bị sinh {NUM_IMAGES} cặp ảnh (1024x512) từ {len(bg_files)} trang A4...")

    for i in tqdm(range(NUM_IMAGES), desc="Generating Paired Dataset"):
        split = 'train' if random.random() < 0.85 else 'val'
        
        # 1. Đọc ảnh ngẫu nhiên
        bg_path = random.choice(bg_files)
        stamp_path = random.choice(stamp_files)
        
        bg_img = cv2.imread(str(bg_path))
        stamp_img = cv2.imread(str(stamp_path), cv2.IMREAD_UNCHANGED)
        
        if bg_img is None or stamp_img is None or stamp_img.shape[2] != 4:
            continue
            
        # 2. Xử lý Logic Patch (The Game Changer để giữ nguyên DPI của text)
        # Cắt 1 ô 512x512 trích ra từ trang A4 cực lớn
        patch_clean = random_crop_patch(bg_img, TARGET_SIZE)
        
        # 3. Augment con dấu (Scale tỷ lệ thuận với ô 512x512 và Xoay)
        stamp_aug = augment_stamp_for_patch(stamp_img, TARGET_SIZE)
        
        # 3.5 BƠM CHỮ KÝ XANH GIẢ LẬP VÀO NỀN (Giải cứu GAN)
        # Ta vẽ chữ ký xanh lên nền Clean. 
        # Nhờ đó Ground Truth (Clean) có chứa chữ ký xanh, và Input (Dơ) cũng có chữ ký xanh đè dưới dấu đỏ.
        patch_clean = draw_synthetic_blue_signature(patch_clean)
        
        # 4. Trộn con dấu sinh ra Input (Image A - Dơ/Bị đóng dấu)
        patch_stamped = overlay_stamp_realistic(patch_clean, stamp_aug)

        # 5. Ghép đôi thành Format Pix2Pix (A bên trái, B bên phải)
        # Width của ảnh sau ghép là 512 + 512 = 1024
        paired_img = np.concatenate([patch_stamped, patch_clean], axis=1)
        
        # 6. Lọc bớt nhiễu noise ảnh ghép và Ghi xuống đĩa cứng
        out_name = f"sample_patch_{i:06d}.jpg"
        cv2.imwrite(str(OUTPUT_DIR / split / out_name), paired_img)

    print(f"🎉 Rực rỡ! Hoàn thành xuất 10.000 cặp ảnh Patch-based tỷ lệ vàng. Sẵn sàng Train GAN!")

if __name__ == "__main__":
    main()
