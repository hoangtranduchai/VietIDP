import os
import sys
import cv2
import torch
from pathlib import Path

# Fix python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.preprocessing.stamp_removal import StampRemover
from src.config import Config

def test_stamp_remover():
    print("🚀 Đang nạp Mô hình Pix2Pix GAN từ Epoch 50...")
    
    # 1. Khởi tạo Mô hình Xóa dấu
    # Config.STAMP_REMOVAL_MODEL đã trỏ về models/finetuned/stamp_removal_gan/best_generator.pth
    remover = StampRemover(img_size=512)
    
    if not remover.is_loaded:
        print("❌ Lỗi: Không thể tải mô hình. Vui lòng kiểm tra lại đường dẫn trong config.py")
        return

    # 2. Tìm một ảnh test ngẫu nhiên (chứa dấu đỏ)
    test_dir = Config.DATA_DIR / "raw" # Hoặc bạn có thể tự trỏ tới 1 file ảnh có dấu cụ thể
    
    # Giả lập tìm 1 file PNG hoặc JPG đầu tiên trong data/raw
    test_img_path = None
    if test_dir.exists():
        for f in test_dir.glob("*.*"):
            if f.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                test_img_path = f
                break
                
    if not test_img_path:
        # Nhập thủ công nếu không tìm thấy tự động
        print("⚠️ Không tìm thấy ảnh test tự động. Hãy copy một ảnh có dấu vào thư mục hiện tại và đặt tên là 'test_input.png'")
        test_img_path = Path("test_input.png")
        if not test_img_path.exists():
            return
            
    print(f"🔍 Đang tiến hành xóa dấu trên ảnh: {test_img_path}")
    
    # 3. Chạy Inference
    input_img = cv2.imread(str(test_img_path))
    if input_img is None:
        print("❌ Lỗi đọc ảnh")
        return
        
    cleaned_img = remover.remove_stamp(input_img)
    
    # 4. Xuất kết quả ghép đôi (Input -> Output)
    h, w = input_img.shape[:2]
    # Resize cleaned_img về đúng kích thước input để ghép ngang nếu cần
    cleaned_img_resized = cv2.resize(cleaned_img, (w, h))
    
    comparison = cv2.hconcat([input_img, cleaned_img_resized])
    
    out_path = "test_pix2pix_result.png"
    cv2.imwrite(out_path, comparison)
    print(f"✅ Tuyệt vời! Đã lưu ảnh so sánh Trước/Sau khi xóa tại: {out_path}")
    print("👉 Mở file test_pix2pix_result.png lên để chiêm ngưỡng phép màu của 50 Epochs nhé!")

if __name__ == "__main__":
    test_stamp_remover()
