import cv2
import os
import json
from pathlib import Path

# Thư viện mạng Neural
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

# Lõi xử lý Xử lý Ảnh V2
from src.preprocessing.dip_extractor import DIPProcessor


class VietIDPPipeline:
    """
    Hệ thống End-to-End [Phiên bản V2] Hỗ trợ Đa Dấu và Khôi phục Toàn cục.
    Kiến trúc: Image -> YOLOv8 (Mảng Bboxes) -> DIP (Local+Global) -> PaddleOCR -> Qwen LLM
    """
    def __init__(self, yolo_weights="models/finetuned/stamp_detector/weights/best.pt"):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.yolo_path = self.base_dir / yolo_weights
        
        print("[1/4] Khởi tạo Động cơ YOLOv8 (Multi-Localization)...")
        if YOLO and self.yolo_path.exists():
            self.detector = YOLO(str(self.yolo_path))
            print("  -> Tải trọng số YOLO thành công!")
        else:
            print("  -> ⚠️ YOLO đang chạy chế độ Offline Dummy.")
            self.detector = None
            
        print("[2/4] Khởi tạo Lõi DIP V2 (Local Filtering & Global Repair)...")
        self.dip_processor = DIPProcessor()
        
        print("[3/4] Khởi tạo Máy Dịch Quang Học (PaddleOCR)...")
        if PaddleOCR:
            self.ocr = PaddleOCR(use_angle_cls=True, lang="vi", show_log=False)
        else:
            print("  -> ⚠️ Chưa cài đặt module PaddleOCR. OCR sẽ trả về chuỗi rỗng.")
            self.ocr = None

        print("[4/4] Khởi tạo Qwen2.5 LLM (Giao tiếp API)...")

    def process_file(self, image_path):
        """Thực thi luồng E2E trên 1 văn bản đầu vào"""
        image_path = str(image_path)
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Không tìm thấy file: {image_path}")
            
        original_img = cv2.imread(image_path)
        if original_img is None:
            raise ValueError("File ảnh bị hỏng hoặc định dạng không hỗ trợ.")
        
        # 2. ĐỊNH VỊ CON DẤU (MULTI-STAMP)
        # Quét ra toàn bộ mảng [Bbox1, Bbox2,...] thay vì chỉ lấy 1 con dấu
        stamp_bboxes = []
        if self.detector:
            # Tham số conf=0.25 để không bỏ sót các con dấu mờ
            results = self.detector(original_img, conf=0.25, verbose=False)
            if len(results) > 0 and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    stamp_bboxes.append((x1, y1, x2, y2))
                
        # 3. LÀM SẠCH VĂN BẢN (DIP Processing V2)
        # Ném nguyên mảng array bboxes vào cho Lõi tính toán
        clean_img = self.dip_processor.process_document(original_img, bboxes=stamp_bboxes)
        
        # 4. CHUYỂN ĐỔI CHỮ (Optical Character Recognition)
        ocr_text = ""
        if self.ocr:
            ocr_results = self.ocr.ocr(clean_img, cls=True)
            if ocr_results and ocr_results[0]:
                texts = [line[1][0] for line in ocr_results[0]]
                ocr_text = "\n".join(texts)
                
        # 5. RÚT TRÍCH CẤU TRÚC (LLM JSON Extraction)
        structured_data = self._invoke_llm_extraction(ocr_text)
        
        return {
            "status": "success",
            "stamps_count": len(stamp_bboxes),
            "stamp_coordinates": stamp_bboxes,
            "ocr_text_length": len(ocr_text),
            "structured_data": structured_data,
            "raw_text": ocr_text
        }
        
    def _invoke_llm_extraction(self, raw_text):
        if not raw_text.strip(): return {}
        return {
            "document_type": "Tài liệu hành chính (Dự đoán)",
            "message": "Cần tích hợp Endpoint Qwen2.5 thực tế vào hàm này."
        }


if __name__ == "__main__":
    print("========================================")
    print(" VIETIDP V2 - ADVANCED E2E PIPELINE ")
    print("========================================")
    
    pipeline = VietIDPPipeline()
    sample_path = "data/raw/sample_test.jpg"
    
    if os.path.exists(sample_path):
        result = pipeline.process_file(sample_path)
        print("\n📝 KẾT QUẢ TRÍCH XUẤT:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
    else:
        print(f"\n⚠️ Đã khởi tạo hoàn tất. Để Test, hãy cung cấp một ảnh tại: {sample_path}")
