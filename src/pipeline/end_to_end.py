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

# Gọi module DIP thần thánh vừa tạo
from src.preprocessing.dip_extractor import DIPProcessor


class VietIDPPipeline:
    """
    Hệ thống End-to-End Trích xuất Thông tin Hành chính Việt Nam.
    Kiến trúc (Architectural Flow):
      Image -> YOLOv8 (Box) -> DIP Processor (Clean) -> PaddleOCR (Text) -> Qwen LLM (JSON)
    """
    def __init__(self, yolo_weights="models/finetuned/stamp_detector/weights/best.pt"):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.yolo_path = self.base_dir / yolo_weights
        
        print("[1/4] Khởi tạo Động cơ YOLOv8 (Localization)...")
        if YOLO and self.yolo_path.exists():
            self.detector = YOLO(str(self.yolo_path))
            print("  -> Tải trọng số YOLO thành công!")
        else:
            print("  -> ⚠️ YOLO đang chạy chế độ Offline Dummy (Chưa có Model hoặc thư viện).")
            self.detector = None
            
        print("[2/4] Khởi tạo Lõi Xử lý Ảnh Kỹ thuật số (DIP)...")
        self.dip_processor = DIPProcessor()
        
        print("[3/4] Khởi tạo Máy Dịch Quang Học (PaddleOCR)...")
        if PaddleOCR:
            # use_angle_cls=True giúp xoay lại chữ bị ngược/nghiêng
            self.ocr = PaddleOCR(use_angle_cls=True, lang="vi", show_log=False)
        else:
            print("  -> ⚠️ Chưa cài đặt module PaddleOCR. OCR sẽ trả về chuỗi rỗng.")
            self.ocr = None

        print("[4/4] Khởi tạo Qwen2.5 LLM (Giao tiếp API)...")
        # Sẽ kết nối cục bộ qua Ollama hoặc REST API của Qwen

    def process_file(self, image_path):
        """
        Thực thi toàn bộ luồng xử lý trên một tấm ảnh Đầu vào.
        """
        image_path = str(image_path)
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Không tìm thấy file: {image_path}")
            
        # 1. Mở file ảnh
        original_img = cv2.imread(image_path)
        if original_img is None:
            raise ValueError("File ảnh bị hỏng hoặc định dạng không hỗ trợ.")
        
        # 2. ĐỊNH VỊ CON DẤU (Localization)
        stamp_bbox = None
        if self.detector:
            results = self.detector(original_img, verbose=False)
            if len(results) > 0 and len(results[0].boxes) > 0:
                box = results[0].boxes[0]
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                stamp_bbox = (x1, y1, x2, y2)
                
        # 3. LÀM SẠCH VĂN BẢN (DIP Processing)
        # Chỉ áp dụng lọc màu và hàn gắn đứt gãy ở khu vực phát hiện con dấu.
        clean_img = self.dip_processor.process_document(original_img, bbox=stamp_bbox)
        
        # 4. CHUYỂN ĐỔI CHỮ (Optical Character Recognition)
        ocr_text = ""
        if self.ocr:
            ocr_results = self.ocr.ocr(clean_img, cls=True)
            if ocr_results and ocr_results[0]:
                # Gộp các dòng text đọc được thành một khối văn bản
                texts = [line[1][0] for line in ocr_results[0]]
                ocr_text = "\n".join(texts)
                
        # 5. RÚT TRÍCH CẤU TRÚC (LLM JSON Extraction)
        structured_data = self._invoke_llm_extraction(ocr_text)
        
        return {
            "status": "success",
            "stamp_detected": stamp_bbox is not None,
            "ocr_text_length": len(ocr_text),
            "structured_data": structured_data,
            "raw_text": ocr_text
        }
        
    def _invoke_llm_extraction(self, raw_text):
        """
        Hàm giao tiếp với Qwen LLM. Tương lai sẽ gắn thư viện Transformers/Ollama vào đây.
        """
        # Placeholder cho Mô hình ngôn ngữ lớn (LLM)
        if not raw_text.strip():
            return {}
            
        return {
            "document_type": "Tài liệu hành chính (Dự đoán)",
            "message": "Cần tích hợp Endpoint Qwen2.5 thực tế vào hàm này."
        }


if __name__ == "__main__":
    print("========================================")
    print(" VIETIDP - SCIENTIFIC PIPELINE TESTER ")
    print("========================================")
    
    pipeline = VietIDPPipeline()
    
    # Bạn có thể thay đổi đường dẫn này để Test trực tiếp trên Miniconda
    sample_path = "data/raw/sample_test.jpg"
    
    if os.path.exists(sample_path):
        result = pipeline.process_file(sample_path)
        print("\n📝 KẾT QUẢ TRÍCH XUẤT:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
    else:
        print(f"\n⚠️ Đã khởi tạo hoàn tất. Để Test, hãy cung cấp một ảnh tại: {sample_path}")
