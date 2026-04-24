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

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Lõi xử lý Xử lý Ảnh V2
from src.preprocessing.dip_extractor import DIPProcessor


class VietIDPPipeline:
    """
    Hệ thống End-to-End [Phiên bản V2 - Ép Xung Phần Cứng RTX 5070].
    Kiến trúc: Image -> YOLOv8x -> DIP (Local+Global) -> PaddleOCR Server -> Qwen2.5-7B (4-bit)
    """
    def __init__(self, yolo_weights="models/finetuned/stamp_detector/weights/best.pt"):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.yolo_path = self.base_dir / yolo_weights
        
        print("[1/4] Khởi tạo Động cơ YOLOv8x (Multi-Localization)...")
        if YOLO and self.yolo_path.exists():
            self.detector = YOLO(str(self.yolo_path))
            print("  -> Tải trọng số YOLOv8x thành công!")
        else:
            print("  -> ⚠️ YOLO đang chạy chế độ Offline Dummy.")
            self.detector = None
            
        print("[2/4] Khởi tạo Lõi DIP V2 (Local Filtering & Global Repair)...")
        self.dip_processor = DIPProcessor()
        
        print("[3/4] Khởi tạo Máy Dịch Quang Học (PaddleOCR Server Grade)...")
        if PaddleOCR:
            # Ép xung: Bật use_gpu và tăng tốc bằng mkldnn để tận dụng phần cứng siêu khủng
            self.ocr = PaddleOCR(use_angle_cls=True, lang="vi", show_log=False, 
                                 use_gpu=True, enable_mkldnn=True)
            print("  -> Sẵn sàng động cơ OCR!")
        else:
            print("  -> ⚠️ Chưa cài đặt module PaddleOCR. OCR sẽ trả về chuỗi rỗng.")
            self.ocr = None

        print("[4/4] Khởi tạo Cầu Nối Qwen2.5 LLM (Ollama Client)...")
        if OpenAI:
            print("  -> Cầu nối Ollama API sẵn sàng ở cổng 11434.")
        else:
            print("  -> ⚠️ Chưa cài đặt thư viện 'openai' để kết nối Ollama.")

    def process_file(self, image_path):
        """Thực thi luồng E2E trên 1 văn bản đầu vào"""
        image_path = str(image_path)
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Không tìm thấy file: {image_path}")
            
        original_img = cv2.imread(image_path)
        if original_img is None:
            raise ValueError("File ảnh bị hỏng hoặc định dạng không hỗ trợ.")
        
        # 2. ĐỊNH VỊ CON DẤU (MULTI-STAMP)
        stamp_bboxes = []
        if self.detector:
            # YOLOv8x cực kỳ nhạy, conf=0.25 là đủ để càn quét
            results = self.detector(original_img, conf=0.25, verbose=False)
            if len(results) > 0 and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    stamp_bboxes.append((x1, y1, x2, y2))
                
        # 3. LÀM SẠCH VĂN BẢN (DIP Processing V2)
        clean_img = self.dip_processor.process_document(original_img, bboxes=stamp_bboxes)
        
        # 4. CHUYỂN ĐỔI CHỮ (Optical Character Recognition)
        ocr_text = ""
        if self.ocr:
            ocr_results = self.ocr.ocr(clean_img, cls=True)
            if ocr_results and ocr_results[0]:
                texts = [line[1][0] for line in ocr_results[0]]
                ocr_text = "\n".join(texts)
                
        # 5. RÚT TRÍCH CẤU TRÚC (Qwen2.5-7B LLM Extraction)
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
        """Gọi API tới LLM Qwen2.5-7B 4-bit qua Ollama để cấu trúc hóa JSON mà không tràn VRAM"""
        if not raw_text.strip(): return {}
        if not OpenAI: return {"error": "Chưa cài thư viện openai (pip install openai)"}
        
        try:
            # Trỏ thẳng vào Ollama đang chạy Local
            client = OpenAI(
                base_url='http://localhost:11434/v1',
                api_key='ollama'
            )
            
            prompt = f"""Bạn là một AI chuyên phân tích dữ liệu hành chính Việt Nam.
Hãy đọc đoạn OCR thô dưới đây và xuất ra ĐÚNG 1 ĐỐI TƯỢNG JSON (Không giải thích, không bọc bằng markdown json).
Các trường cần có: "loai_van_ban", "ngay_thang_nam", "co_quan_ban_hanh", "nguoi_ky", "tom_tat".
VĂN BẢN:
{raw_text}"""
            
            response = client.chat.completions.create(
                model="qwen2.5:7b",
                messages=[
                    {"role": "system", "content": "You are a JSON extractor. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            # Xử lý vệ sinh JSON nếu LLM cố tình xuất thẻ Markdown
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
                
            return json.loads(content)
        except Exception as e:
            return {"error": f"Lỗi LLM: {str(e)}"}


if __name__ == "__main__":
    print("======================================================")
    print(" VIETIDP - RTX 5070 OVERCLOCKED E2E PIPELINE ")
    print("======================================================")
    
    pipeline = VietIDPPipeline()
    sample_path = "data/raw/sample_test.jpg"
    
    if os.path.exists(sample_path):
        result = pipeline.process_file(sample_path)
        print("\n📝 KẾT QUẢ TRÍCH XUẤT:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
    else:
        print(f"\n⚠️ Đã khởi tạo hoàn tất. Để Test, hãy cung cấp một ảnh tại: {sample_path}")
