import os
import sys
import cv2
import fitz  # PyMuPDF
import numpy as np
from pathlib import Path
from ultralytics import YOLO

# Fix python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.preprocessing.stamp_removal import StampRemover
from src.config import Config

def process_multipage_pdf():
    print("🚀 KHỞI ĐỘNG HỆ THỐNG XỬ LÝ PDF NHIỀU TRANG (YOLOv8 + Pix2Pix GAN) 🚀")
    
    # 1. Tải Mô hình
    yolo_path = Config.MODELS_DIR / "finetuned" / "stamp_detector" / "weights" / "best.pt"
    if not yolo_path.exists():
        print(f"❌ Không tìm thấy YOLO model tại {yolo_path}")
        return
    yolo_model = YOLO(str(yolo_path))
    remover = StampRemover(img_size=512)
    
    # 2. Tìm file PDF test
    test_pdf_path = Path("test_input.pdf")
    if not test_pdf_path.exists():
        print("⚠️ Vui lòng copy 1 file PDF nhiều trang vào thư mục gốc và đổi tên thành 'test_input.pdf'!")
        return
        
    print(f"\n📂 Đang mở file PDF: {test_pdf_path}")
    doc = fitz.open(test_pdf_path)
    print(f"📄 Phát hiện tổng cộng {len(doc)} trang.")
    
    # Chuẩn bị file PDF đầu ra
    out_pdf = fitz.open()

    # 3. Quét từng trang
    for page_num in range(len(doc)):
        print(f"\n⏳ Đang xử lý Trang {page_num + 1}/{len(doc)}...")
        page = doc[page_num]
        
        # Render trang PDF thành ảnh (Zoom độ phân giải cao 2x)
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        
        # Chuyển ảnh PyMuPDF sang OpenCV format (BGR)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4: # RGBA -> BGR
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else: # RGB -> BGR
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
        # 4. Kích hoạt YOLOv8 tìm con dấu trên trang này
        results = yolo_model(img_bgr, verbose=False)
        boxes_found = 0
        cleaned_page_bgr = img_bgr.copy()

        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = float(box.conf[0])
                if conf < 0.5:
                    continue
                    
                boxes_found += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Cắt ảnh với lề an toàn
                h, w = img_bgr.shape[:2]
                pad = 15
                px1, py1 = max(0, x1 - pad), max(0, y1 - pad)
                px2, py2 = min(w, x2 + pad), min(h, y2 + pad)
                stamp_crop = img_bgr[py1:py2, px1:px2]
                
                print(f"   🎯 Tẩy con dấu tại tọa độ [{px1}, {py1}]...")
                cleaned_crop = remover.remove_stamp(stamp_crop)
                
                # Dán đè lại
                crop_h, crop_w = stamp_crop.shape[:2]
                cleaned_crop_resized = cv2.resize(cleaned_crop, (crop_w, crop_h))
                cleaned_page_bgr[py1:py2, px1:px2] = cleaned_crop_resized

        if boxes_found == 0:
            print("   ✅ Không có dấu đỏ trên trang này.")
            
        # 5. Đóng gói lại thành PDF
        # Chuyển BGR (OpenCV) ngược về RGB (PyMuPDF)
        cleaned_page_rgb = cv2.cvtColor(cleaned_page_bgr, cv2.COLOR_BGR2RGB)
        
        # Tạo trang PDF mới từ ảnh đã xử lý
        img_bytes = fitz.Pixmap(fitz.csRGB, cleaned_page_bgr.shape[1], cleaned_page_bgr.shape[0], cleaned_page_rgb.tobytes(), cleaned_page_rgb.shape[2])
        out_page = out_pdf.new_page(width=page.rect.width, height=page.rect.height)
        out_page.insert_image(page.rect, pixmap=img_bytes)

    # 6. Lưu file PDF kết quả
    out_path = "test_e2e_result.pdf"
    out_pdf.save(out_path)
    out_pdf.close()
    doc.close()
    
    print(f"\n🎉 QUÁ TRÌNH HOÀN TẤT! Đã xuất xưởng file PDF sạch: {out_path}")
    print("👉 Hãy mở file PDF mới lên để xem toàn bộ tài liệu đã được đánh bay mọi dấu đỏ!")

if __name__ == "__main__":
    process_multipage_pdf()
