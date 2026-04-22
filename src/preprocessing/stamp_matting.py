import cv2
import numpy as np
import os
import glob
from rembg import remove, new_session
from pathlib import Path

class HybridStampMatting:
    """
    Kế thừa thuật toán Hybrid (AI Segment + OpenCV Thresholding)
    Bóc tách con dấu đỏ khỏi văn bản một cách trong suốt.
    """
    def __init__(self):
        # Tối ưu: Khởi tạo session đúng 1 lần duy nhất để giải phóng RAM
        self.session = new_session()
        
    def extract_stamp(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Nhận vào numpy array BGR (Bounding Box), trả ra numpy array RGBA trong suốt.
        """
        if img_bgr is None:
            return None
            
        # 1. Dùng AI (Rembg) để cắt hình khối con dấu
        rembg_out = remove(img_bgr, session=self.session)
        
        # Kênh Alpha của rembg (Mặt nạ bao quanh con dấu)
        ai_alpha = rembg_out[:, :, 3]
        
        # Nếu AI không tìm thấy gì, trả về ảnh gốc từ AI
        if not np.any(ai_alpha > 0):
            return rembg_out

        # 2. Xử lý khoét nền giấy bên trong bằng Toán học (Cường độ sáng)
        bgr = rembg_out[:, :, :3]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(float)
        
        # Chỉ tính màu nền ở khu vực BÊN TRONG con dấu (do AI đã cắt)
        mask = ai_alpha > 128
        if np.sum(mask) == 0: 
            mask = ai_alpha > 0
            
        bg_intensity = np.median(gray[mask])
        
        if bg_intensity > 128:
            WHITE = min(255.0, bg_intensity + 15)
            DARK = max(0.0, bg_intensity - 60)
            ink_alpha = (WHITE - gray) / (WHITE - DARK + 1e-5) * 255.0
        else:
            BLACK = max(0.0, bg_intensity - 15)
            LIGHT = min(255.0, bg_intensity + 60)
            ink_alpha = (gray - BLACK) / (LIGHT - BLACK + 1e-5) * 255.0
            
        ink_alpha = np.clip(ink_alpha, 0, 255).astype(np.uint8)
        ink_alpha = cv2.GaussianBlur(ink_alpha, (3, 3), 0)
        
        # 3. KẾT HỢP
        final_alpha = cv2.bitwise_and(ai_alpha, ink_alpha)
        
        b, g, r = cv2.split(img_bgr)
        rgba = [b, g, r, final_alpha]
        dst = cv2.merge(rgba, 4)
        
        return dst

def test_matting():
    # Helper để test module
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run module test")
    parser.add_argument("--input", type=str, help="Input directory")
    parser.add_argument("--output", type=str, help="Output directory")
    args = parser.parse_args()

    if args.test and args.input and args.output:
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        matting = HybridStampMatting()
        input_dir = Path(args.input)
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        image_files = []
        for ext in ('*.jpg', '*.jpeg', '*.png'):
            image_files.extend(input_dir.glob(ext))
            
        print(f"🚀 Khởi chạy Hybrid Stamp Matting trên {len(image_files)} ảnh...")
        
        def process(path):
            img = cv2.imread(str(path))
            res = matting.extract_stamp(img)
            if res is not None:
                out_path = output_dir / f"{path.stem}.png"
                cv2.imwrite(str(out_path), res)
                return True
            return False

        start_t = time.time()
        success = 0
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(process, path): path for path in image_files}
            for i, future in enumerate(as_completed(futures)):
                if future.result():
                    success += 1
                if (i + 1) % 10 == 0:
                    print(f" Đã xử lý {i + 1}/{len(image_files)}...")
                    
        print(f"✅ Hoàn tất bóc tách {success}/{len(image_files)} ảnh trong {time.time() - start_t:.2f}s!")

if __name__ == "__main__":
    test_matting()
