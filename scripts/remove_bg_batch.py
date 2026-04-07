import cv2
import numpy as np
import os
import glob
from rembg import remove

def remove_stamp_bg_hybrid(image_path, output_path):
    img = cv2.imread(image_path)
    if img is None:
        return False
        
    # 1. Dùng AI (Rembg) để cắt hình khối con dấu
    # Giúp loại bỏ hoàn toàn nhiễu bên ngoài như bàn tay, mặt bàn, cạnh giấy bị đen, v.v.
    rembg_out = remove(img)
    
    # Kênh Alpha của rembg (Mặt nạ bao quanh con dấu)
    ai_alpha = rembg_out[:, :, 3]
    
    # Nếu AI không tìm thấy gì, trả về ảnh gốc từ AI
    if not np.any(ai_alpha > 0):
        cv2.imwrite(output_path, rembg_out)
        return True

    # 2. Xử lý khoét nền giấy bên trong bằng Toán học (Cường độ sáng)
    bgr = rembg_out[:, :, :3]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(float)
    
    # Chỉ tính màu nền ở khu vực BÊN TRONG con dấu (do AI đã cắt)
    mask = ai_alpha > 128
    if np.sum(mask) == 0: 
        mask = ai_alpha > 0
        
    bg_intensity = np.median(gray[mask])
    
    if bg_intensity > 128:
        # Nền giấy sáng (trắng/vàng/hồng/xám lợt), nét mực đậm hơn nền
        WHITE = min(255.0, bg_intensity + 15)
        DARK = max(0.0, bg_intensity - 60)
        ink_alpha = (WHITE - gray) / (WHITE - DARK + 1e-5) * 255.0
    else:
        # Nền giấy tối (hoặc nền đen), nét phẩy mực sáng hơn nền
        BLACK = max(0.0, bg_intensity - 15)
        LIGHT = min(255.0, bg_intensity + 60)
        ink_alpha = (gray - BLACK) / (LIGHT - BLACK + 1e-5) * 255.0
        
    ink_alpha = np.clip(ink_alpha, 0, 255).astype(np.uint8)
    
    # Tăng cường viền chữ
    ink_alpha = cv2.GaussianBlur(ink_alpha, (3, 3), 0)
    
    # 3. KẾT HỢP: Lấy vùng giao nhau giữa AI (cắt viền ngoài) và Thuật toán (khoét lõi trong)
    final_alpha = cv2.bitwise_and(ai_alpha, ink_alpha)
    
    # Khôi phục màu BGR gốc của ảnh ban đầu (img) thay vì rembg_out để màu trung thực nhất
    # (Do rembg_out nền đen có thể ám màu viền)
    b, g, r = cv2.split(img)
    rgba = [b, g, r, final_alpha]
    dst = cv2.merge(rgba, 4)
    
    cv2.imwrite(output_path, dst)
    return True

def process_batch(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    extensions = ('*.jpg', '*.jpeg', '*.png')
    image_files = []
    for ext in extensions:
        image_files.extend(glob.glob(os.path.join(input_dir, ext)))
        
    print(f"Bắt đầu xử lý {len(image_files)} ảnh bằng thuật toán HYBRID (AI + OpenCV)...")
    
    success_count = 0
    for idx, file_path in enumerate(image_files):
        filename = os.path.basename(file_path)
        name_only = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{name_only}.png")
        
        if remove_stamp_bg_hybrid(file_path, output_path):
            success_count += 1
            
        if (idx+1) % 20 == 0:
            print(f" Đã xử lý {idx+1}/{len(image_files)} ảnh...")
            
    print(f" Hoàn tất! Đã xử lý xong toàn bộ {success_count} ảnh.")

if __name__ == "__main__":
    pwd = os.path.dirname(os.path.abspath(__file__))
    INPUT_FOLDER = os.path.join(pwd, "..", "data", "raw", "stamps_raw")
    OUTPUT_FOLDER = os.path.join(pwd, "..", "data", "interim", "stamps_transparent")
    process_batch(INPUT_FOLDER, OUTPUT_FOLDER)
