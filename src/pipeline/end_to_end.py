# -*- coding: utf-8 -*-
# ⚠️ DEPRECATED — Sử dụng src.pipeline.ocr_llm_pipeline.VietIDPPipeline thay thế.
# File này giữ lại để tương thích ngược với demo_app.py cũ.
import warnings
warnings.warn(
    "end_to_end.py is deprecated. Use src.pipeline.ocr_llm_pipeline.VietIDPPipeline.",
    DeprecationWarning, stacklevel=2
)
import cv2
import os
import sys
import json
from pathlib import Path
from PIL import Image

# Thêm thư mục Root của dự án vào đường dẫn Python để fix lỗi ModuleNotFoundError
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Thư viện mạng Neural
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    from vietocr.tool.predictor import Predictor
    from vietocr.tool.config import Cfg
except ImportError:
    Predictor = None

# Lõi xử lý Xử lý Ảnh V2 (Chuyển sang dùng HybridStampMatting theo Đề tài 2026)
from src.preprocessing.stamp_matting import HybridStampMatting


class VietIDPPipeline:
    """
    Hệ thống End-to-End [Phiên bản V2 - Ép Xung Phần Cứng RTX 5070].
    Kiến trúc: Image -> YOLOv8x -> DIP (Local+Global) -> VietOCR (Thuần PyTorch) -> Qwen2.5-7B (4-bit)
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
            
        print("[2/4] Khởi tạo Lõi Xóa Dấu (Hybrid Stamp Matting)...")
        self.stamp_matter = HybridStampMatting()
        
        print("[3/4] Khởi tạo Máy Dịch Quang Học (VietOCR VGG-Transformer Thuần PyTorch)...")
        if Predictor and easyocr:
            # 1. Trình dò tìm dòng chữ (Text Detector) từ EasyOCR
            self.text_detector = easyocr.Reader(['vi'], gpu=True)
            
            # 2. Trình đọc chữ Tiếng Việt siêu việt (VietOCR)
            config = Cfg.load_config_from_name('vgg_transformer')
            config['device'] = 'cuda:0' # Ép chạy trên RTX 5070
            self.vietocr_predictor = Predictor(config)
            print("  -> Sẵn sàng động cơ OCR (VietOCR + Text Detector)!")
        else:
            print("  -> ⚠️ Chưa cài đặt VietOCR hoặc EasyOCR.")
            self.text_detector = None
            self.vietocr_predictor = None

        print("[4/4] Khởi tạo Cầu Nối Qwen2.5 LLM (Ollama Client)...")
        if OpenAI:
            self._ensure_ollama_running()
            print("  -> Cầu nối Ollama API sẵn sàng ở cổng 11434.")
        else:
            print("  -> ⚠️ Chưa cài đặt thư viện 'openai' để kết nối Ollama.")

    def _ensure_ollama_running(self):
        """Tự động bật Ollama ngầm nếu chưa chạy"""
        import socket
        import time
        import subprocess
        
        def is_port_in_use(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0

        if not is_port_in_use(11434):
            print("  -> Đang tự động kích hoạt máy chủ Ollama ngầm...")
            try:
                # Bật Ollama ngầm trên Windows không hiện cửa sổ
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                # Đợi máy chủ khởi động
                for _ in range(15):
                    time.sleep(1)
                    if is_port_in_use(11434):
                        print("  -> Động cơ LLM đã được đánh thức!")
                        return
                print("  -> ⚠️ Thời gian chờ bật Ollama quá lâu.")
            except FileNotFoundError:
                print("  -> ⚠️ Lỗi: Chưa cài đặt phần mềm Ollama (Không tìm thấy lệnh 'ollama').")

    def _process_single_image(self, original_img):
        """Xử lý nội bộ 1 bức ảnh (1 trang văn bản)"""
        # 2. ĐỊNH VỊ CON DẤU (MULTI-STAMP)
        stamp_bboxes = []
        if self.detector:
            # YOLOv8x cực kỳ nhạy, conf=0.25 là đủ để càn quét
            results = self.detector(original_img, conf=0.25, verbose=False)
            if len(results) > 0 and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    stamp_bboxes.append((x1, y1, x2, y2))
                
        # 3. LÀM SẠCH VĂN BẢN (Xóa con dấu đỏ bằng HybridStampMatting)
        # Sử dụng stamp_matting lên toàn bộ ảnh (được tối ưu hóa bằng YOLO bounding box nếu có)
        clean_img = original_img.copy()
        for box in stamp_bboxes:
            x1, y1, x2, y2 = box
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(clean_img.shape[1], x2), min(clean_img.shape[0], y2)
            
            roi = clean_img[y1:y2, x1:x2]
            if roi.size > 0:
                clean_roi = self.stamp_matter.remove_stamp(roi)
                if clean_roi is not None:
                    clean_img[y1:y2, x1:x2] = clean_roi
                    
        
        # 4. CHUYỂN ĐỔI CHỮ (VietOCR Hybrid)
        ocr_text = ""
        if self.text_detector and self.vietocr_predictor:
            # Bước 4.1: Tìm các dòng chữ (Bounding Boxes)
            horizontal_list, free_list = self.text_detector.detect(clean_img)
            
            texts = []
            if horizontal_list and len(horizontal_list[0]) > 0:
                bboxes = horizontal_list[0]
                # Sắp xếp các box từ trên xuống dưới (theo tọa độ y)
                bboxes.sort(key=lambda b: (b[2] + b[3]) / 2) # Sắp xếp theo y_min
                
                for box in bboxes:
                    x_min, x_max, y_min, y_max = map(int, box)
                    
                    # Cắt lề chống lỗi
                    x_min, y_min = max(0, x_min), max(0, y_min)
                    x_max, y_max = min(clean_img.shape[1], x_max), min(clean_img.shape[0], y_max)
                    
                    if x_max <= x_min or y_max <= y_min:
                        continue
                        
                    crop_img = clean_img[y_min:y_max, x_min:x_max]
                    img_pil = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
                    
                    # Bước 4.2: Đưa cho VietOCR đọc chuẩn tiếng Việt
                    line_text = self.vietocr_predictor.predict(img_pil)
                    if line_text:
                        texts.append(line_text)
                        
            ocr_text = "\n".join(texts)
            
        # Vẽ Box lên ảnh kết quả
        output_img = original_img.copy()
        for box in stamp_bboxes:
            x1, y1, x2, y2 = box
            cv2.rectangle(output_img, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(output_img, "STAMP DETECTED", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            
        return ocr_text, stamp_bboxes, output_img

    def process_file(self, file_path):
        """Thực thi luồng E2E trên 1 văn bản đầu vào (hỗ trợ cả Ảnh và PDF nhiều trang)"""
        file_path = str(file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
            
        import numpy as np
        images = []
        
        # Nhận diện định dạng PDF
        if file_path.lower().endswith('.pdf'):
            try:
                import fitz
            except ImportError:
                raise ImportError("Vui lòng cài đặt PyMuPDF (pip install PyMuPDF) để đọc PDF.")
                
            doc = fitz.open(file_path)
            for i in range(len(doc)):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=200) # Render chất lượng cao
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                if pix.n == 4:
                    img_rgb = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
                else:
                    img_rgb = img_array
                cv_img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                images.append(cv_img)
            doc.close()
        else:
            # File ảnh thông thường
            img = cv2.imread(file_path)
            if img is None:
                raise ValueError("File ảnh bị hỏng hoặc định dạng không hỗ trợ.")
            images.append(img)
            
        # Duyệt qua từng trang
        full_ocr_text = ""
        all_stamp_bboxes = []
        processed_images = []
        
        for idx, img in enumerate(images):
            page_text, bboxes, out_img = self._process_single_image(img)
            if len(images) > 1:
                full_ocr_text += f"\n\n--- TRANG {idx + 1} ---\n{page_text}"
            else:
                full_ocr_text = page_text
                
            for box in bboxes:
                all_stamp_bboxes.append({"page": idx + 1, "box": box})
                
            processed_images.append(out_img)
                
        # 5. RÚT TRÍCH CẤU TRÚC (Qwen2.5-7B LLM Extraction)
        # Chỉ gọi LLM 1 lần duy nhất cho toàn bộ văn bản
        structured_data = self._invoke_llm_extraction(full_ocr_text)
        
        return {
            "status": "success",
            "total_pages": len(images),
            "stamps_count": len(all_stamp_bboxes),
            "stamp_coordinates": all_stamp_bboxes,
            "ocr_text_length": len(full_ocr_text),
            "structured_data": structured_data,
            "raw_text": full_ocr_text,
            "processed_images": processed_images
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
