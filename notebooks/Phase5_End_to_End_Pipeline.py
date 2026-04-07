# -*- coding: utf-8 -*-
"""
Phase 5: End-to-End Pipeline + FastAPI Web Service
===================================================
Tích hợp toàn bộ pipeline: Image → Preprocess → OCR → LLM → JSON

Có thể chạy:
1. Standalone script (xử lý file đơn hoặc batch)
2. FastAPI server (API service)
3. Trên Google Colab (demo)
"""

# ==============================================================================
# CELL 1: CÀI ĐẶT
# ==============================================================================
# !pip install -q torch transformers peft bitsandbytes
# !pip install -q paddlepaddle-gpu paddleocr
# !pip install -q fastapi uvicorn python-multipart aiofiles
# !pip install -q PyMuPDF Pillow opencv-python-headless

import os
import json
import time
import torch
import numpy as np
import cv2
from PIL import Image
from datetime import datetime

# ==============================================================================
# CELL 2: CẤU HÌNH
# ==============================================================================
# from google.colab import drive
# drive.mount('/content/drive')
# BASE_DIR = "/content/drive/MyDrive/OCR-LLM_Research"
BASE_DIR = r"E:\OCR-LLM_Research"

STAMP_MODEL_PATH = os.path.join(BASE_DIR, "models/stamp_removal/best_generator.pth")
LLM_ADAPTER_PATH = os.path.join(BASE_DIR, "models/qwen_finetuned/lora_adapters")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


# ==============================================================================
# CELL 3: END-TO-END PIPELINE CLASS
# ==============================================================================
class OCRLLMPipeline:
    """
    Pipeline đầu cuối cho xử lý văn bản hành chính Việt Nam.

    Quy trình 5 giai đoạn:
    1. Preprocessing: Deskew, denoise, stamp removal (GAN)
    2. OCR: PaddleOCR → raw text
    3. LLM: Qwen-7B → classification + extraction
    4. Validation: Kiểm tra format JSON
    5. Output: Structured JSON

    Tất cả model được load 1 lần và cache trong bộ nhớ.
    """

    def __init__(self, load_stamp_model=True, load_llm=True):
        """
        Khởi tạo pipeline, load tất cả models.

        Args:
            load_stamp_model: Load GAN stamp removal model
            load_llm: Load fine-tuned LLM
        """
        print("🚀 Khởi tạo OCR-LLM Pipeline...")
        self.stamp_model = None
        self.ocr_engine = None
        self.llm_model = None
        self.llm_tokenizer = None

        # 1. Load Stamp Removal GAN
        if load_stamp_model and os.path.exists(STAMP_MODEL_PATH):
            self._load_stamp_model()

        # 2. Load OCR Engine
        self._load_ocr_engine()

        # 3. Load LLM
        if load_llm and os.path.exists(LLM_ADAPTER_PATH):
            self._load_llm()

        print("✅ Pipeline sẵn sàng!")

    def _load_stamp_model(self):
        """Load Pix2Pix Generator cho stamp removal."""
        from notebooks.Phase2_Stamp_Removal_GAN import UNetGenerator
        print("  🔄 Loading Stamp Removal Model...")
        self.stamp_model = UNetGenerator().to(DEVICE)
        checkpoint = torch.load(STAMP_MODEL_PATH, map_location=DEVICE)
        self.stamp_model.load_state_dict(checkpoint['gen_state'])
        self.stamp_model.eval()
        print("  ✅ Stamp Removal Model loaded")

    def _load_ocr_engine(self):
        """Load PaddleOCR."""
        try:
            from paddleocr import PaddleOCR
            print("  🔄 Loading OCR Engine...")
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang='vi',
                use_gpu=torch.cuda.is_available(),
                show_log=False,
                det_db_thresh=0.3,
                det_db_box_thresh=0.5,
            )
            print("  ✅ OCR Engine loaded (PaddleOCR Vietnamese)")
        except ImportError:
            print("  ⚠️ PaddleOCR not installed. OCR will be skipped.")

    def _load_llm(self):
        """Load fine-tuned Qwen model."""
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel

        print("  🔄 Loading LLM (Qwen-2.5-7B + LoRA)...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        base_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-7B-Instruct",
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        self.llm_model = PeftModel.from_pretrained(base_model, LLM_ADAPTER_PATH)
        self.llm_tokenizer = AutoTokenizer.from_pretrained(LLM_ADAPTER_PATH)
        self.llm_model.eval()
        print("  ✅ LLM loaded")

    # -----------------------------------------------------------------------
    # Stage 1: Preprocessing
    # -----------------------------------------------------------------------
    def preprocess_image(self, image):
        """
        Tiền xử lý ảnh: deskew, denoise, stamp removal.

        Args:
            image: numpy array (BGR) hoặc PIL Image
        Returns:
            numpy array (BGR) đã xử lý
        """
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Auto-deskew
        image = self._auto_deskew(image)

        # Denoise
        image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)

        # Stamp removal (nếu model đã load)
        if self.stamp_model is not None:
            image = self._remove_stamp(image)

        return image

    def _auto_deskew(self, image):
        """Tự động xoay ảnh bị nghiêng."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255,
                               cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return image

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Chỉ xoay nếu góc nhỏ (< 10 độ) để tránh xoay sai
        if abs(angle) > 10:
            return image

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h),
                                  flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def _remove_stamp(self, image):
        """Xóa con dấu đỏ bằng GAN."""
        from torchvision import transforms

        transform = transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
            transforms.Normalize([0.5]*3, [0.5]*3)
        ])

        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        orig_size = pil_img.size
        input_tensor = transform(pil_img).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            output = self.stamp_model(input_tensor)

        output = output.squeeze(0).cpu() * 0.5 + 0.5
        output = output.clamp(0, 1)
        output_img = transforms.ToPILImage()(output)
        output_img = output_img.resize(orig_size, Image.LANCZOS)

        return cv2.cvtColor(np.array(output_img), cv2.COLOR_RGB2BGR)

    # -----------------------------------------------------------------------
    # Stage 2: OCR
    # -----------------------------------------------------------------------
    def run_ocr(self, image):
        """
        Nhận dạng text từ ảnh.

        Args:
            image: numpy array (BGR)
        Returns:
            str: raw text
        """
        if self.ocr_engine is None:
            return ""

        # Save temp image for PaddleOCR
        temp_path = "/tmp/ocr_pipeline_temp.png"
        cv2.imwrite(temp_path, image)

        result = self.ocr_engine.ocr(temp_path, cls=True)

        if os.path.exists(temp_path):
            os.remove(temp_path)

        if not result or not result[0]:
            return ""

        # Sort by Y position (top to bottom)
        lines = sorted(result[0], key=lambda x: x[0][0][1])
        text = '\n'.join([line[1][0] for line in lines])

        return text

    # -----------------------------------------------------------------------
    # Stage 3: LLM Extraction
    # -----------------------------------------------------------------------
    def extract_info(self, text):
        """
        Trích xuất thông tin từ text bằng LLM.

        Args:
            text: Raw OCR text
        Returns:
            dict: Structured information
        """
        if self.llm_model is None or self.llm_tokenizer is None:
            # Fallback: regex-based extraction
            return self._regex_extraction(text)

        instruction = (
            "Bạn là chuyên gia trích xuất thông tin từ văn bản hành chính Việt Nam. "
            "Hãy đọc văn bản sau và trích xuất các thông tin theo định dạng JSON:\n"
            "{\n"
            '  "loai_van_ban": "<Công văn|Hợp đồng|Quy định|Tờ trình|Khác>",\n'
            '  "so_hieu": "<số hiệu văn bản>",\n'
            '  "ngay_ban_hanh": "<DD/MM/YYYY>",\n'
            '  "co_quan_ban_hanh": "<tên cơ quan>",\n'
            '  "trich_yeu": "<trích yếu nội dung>",\n'
            '  "nguoi_ky": "<họ tên người ký>"\n'
            "}\n"
            "Nếu không tìm thấy thông tin, để trống (\"\")."
        )

        messages = [
            {"role": "system", "content": "Bạn là chuyên gia phân tích văn bản hành chính."},
            {"role": "user", "content": f"{instruction}\n\n{text[:3000]}"}
        ]

        input_text = self.llm_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.llm_tokenizer(input_text, return_tensors="pt").to(self.llm_model.device)

        with torch.no_grad():
            outputs = self.llm_model.generate(
                **inputs, max_new_tokens=512,
                temperature=0.1, do_sample=True,
                pad_token_id=self.llm_tokenizer.pad_token_id,
            )

        generated = outputs[0][inputs['input_ids'].shape[1]:]
        result_text = self.llm_tokenizer.decode(generated, skip_special_tokens=True)

        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return self._regex_extraction(text)

    def _regex_extraction(self, text):
        """Fallback: Trích xuất bằng regex khi LLM chưa sẵn sàng."""
        import re

        result = {
            "loai_van_ban": "",
            "so_hieu": "",
            "ngay_ban_hanh": "",
            "co_quan_ban_hanh": "",
            "trich_yeu": "",
            "nguoi_ky": ""
        }

        # Classification keywords
        text_lower = text.lower()
        if 'quyết định' in text_lower:
            result['loai_van_ban'] = 'Quy định'
        elif 'công văn' in text_lower:
            result['loai_van_ban'] = 'Công văn'
        elif 'hợp đồng' in text_lower:
            result['loai_van_ban'] = 'Hợp đồng'
        elif 'tờ trình' in text_lower:
            result['loai_van_ban'] = 'Tờ trình'
        else:
            result['loai_van_ban'] = 'Khác'

        # Số hiệu
        match = re.search(r'[Ss]ố[:\s]+(\d+[\/-][A-ZĐa-zđ\d\/-]+)', text)
        if match:
            result['so_hieu'] = match.group(1)

        # Ngày ban hành
        match = re.search(r'[Nn]gày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', text)
        if match:
            d, m, y = match.groups()
            result['ngay_ban_hanh'] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"

        # Trích yếu
        match = re.search(r'[Vv]\/[Vv][:\s]+(.+?)(?:\n|$)', text)
        if match:
            result['trich_yeu'] = match.group(1).strip()[:200]

        return result

    # -----------------------------------------------------------------------
    # Stage 4: Validation
    # -----------------------------------------------------------------------
    def validate_output(self, extracted):
        """Kiểm tra và chuẩn hóa dữ liệu đầu ra."""
        import re

        validated = dict(extracted)

        # Validate date format
        if validated.get('ngay_ban_hanh'):
            date_str = validated['ngay_ban_hanh']
            if not re.match(r'\d{2}/\d{2}/\d{4}', date_str):
                # Try to normalize
                match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', date_str)
                if match:
                    d, m, y = match.groups()
                    validated['ngay_ban_hanh'] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"

        # Validate document type
        valid_types = ['Công văn', 'Hợp đồng', 'Quy định', 'Tờ trình', 'Khác']
        if validated.get('loai_van_ban') not in valid_types:
            validated['loai_van_ban'] = 'Khác'

        return validated

    # -----------------------------------------------------------------------
    # Main Processing Function
    # -----------------------------------------------------------------------
    def process_file(self, file_path, save_result=True):
        """
        Xử lý 1 file PDF/Image đầu cuối.

        Args:
            file_path: Đường dẫn file PDF hoặc ảnh
            save_result: Lưu kết quả JSON
        Returns:
            dict: Kết quả trích xuất
        """
        start_time = time.time()
        print(f"\n📄 Đang xử lý: {os.path.basename(file_path)}")

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.pdf':
            results = self._process_pdf(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            image = cv2.imread(file_path)
            results = self._process_single_image(image, file_path)
        else:
            print(f"  ⚠️ Unsupported file format: {file_ext}")
            return None

        # Timing
        elapsed = time.time() - start_time
        results['processing_time_seconds'] = round(elapsed, 2)
        results['source_file'] = os.path.basename(file_path)
        results['processed_at'] = datetime.now().isoformat()

        print(f"  ⏱️ Thời gian xử lý: {elapsed:.2f}s")

        # Save result
        if save_result:
            output_name = os.path.splitext(os.path.basename(file_path))[0] + '_result.json'
            output_path = os.path.join(RESULTS_DIR, output_name)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"  💾 Kết quả: {output_path}")

        return results

    def _process_pdf(self, pdf_path):
        """Xử lý file PDF (render từng trang → pipeline)."""
        import fitz

        doc = fitz.open(pdf_path)
        pages_results = []
        all_text = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=200)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            else:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            # Preprocess
            img = self.preprocess_image(img)

            # OCR
            text = self.run_ocr(img)
            all_text.append(text)

            pages_results.append({
                'page': page_idx + 1,
                'text': text
            })
            print(f"  📄 Trang {page_idx + 1}/{len(doc)}")

        doc.close()

        full_text = '\n'.join(all_text)

        # LLM extraction on combined text
        extracted = self.extract_info(full_text)
        validated = self.validate_output(extracted)

        return {
            'num_pages': len(pages_results),
            'pages': pages_results,
            'full_text': full_text,
            'extraction': validated,
        }

    def _process_single_image(self, image, source=''):
        """Xử lý 1 ảnh đơn."""
        # Preprocess
        image = self.preprocess_image(image)

        # OCR
        text = self.run_ocr(image)

        # LLM extraction
        extracted = self.extract_info(text)
        validated = self.validate_output(extracted)

        return {
            'num_pages': 1,
            'full_text': text,
            'extraction': validated,
        }

    def batch_process(self, input_dir, output_dir=None, limit=None):
        """Xử lý hàng loạt tất cả PDF/ảnh trong thư mục."""
        if output_dir is None:
            output_dir = RESULTS_DIR

        files = sorted([
            f for f in os.listdir(input_dir)
            if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))
        ])[:limit]

        print(f"🔄 Batch processing {len(files)} files...")
        results = []

        for i, filename in enumerate(files):
            file_path = os.path.join(input_dir, filename)
            try:
                result = self.process_file(file_path, save_result=True)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"  ⚠️ Error: {filename} - {e}")

        # Summary
        if results:
            avg_time = np.mean([r['processing_time_seconds'] for r in results])
            print(f"\n✅ Batch hoàn tất: {len(results)}/{len(files)} files")
            print(f"   Avg time/file: {avg_time:.2f}s")

        return results


# ==============================================================================
# CELL 4: FASTAPI WEB SERVICE
# ==============================================================================
def create_api_app():
    """
    Tạo FastAPI web service cho OCR-LLM pipeline.

    Endpoints:
    - POST /api/process     : Upload & xử lý 1 file
    - GET  /api/results     : Lấy danh sách kết quả
    - GET  /api/results/{id}: Lấy chi tiết 1 kết quả
    - GET  /api/health      : Health check
    """
    from fastapi import FastAPI, UploadFile, File, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import shutil
    import uuid

    app = FastAPI(
        title="OCR-LLM Vietnamese Document Processing API",
        description="API trích xuất thông tin từ văn bản hành chính Việt Nam",
        version="1.0.0"
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize pipeline (load models once)
    pipeline = None

    @app.on_event("startup")
    async def startup():
        nonlocal pipeline
        pipeline = OCRLLMPipeline(load_stamp_model=True, load_llm=True)

    @app.get("/api/health")
    async def health_check():
        return {
            "status": "healthy",
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "models_loaded": {
                "stamp_removal": pipeline.stamp_model is not None if pipeline else False,
                "ocr": pipeline.ocr_engine is not None if pipeline else False,
                "llm": pipeline.llm_model is not None if pipeline else False,
            }
        }

    @app.post("/api/process")
    async def process_document(file: UploadFile = File(...)):
        """Upload và xử lý file PDF/Image."""
        # Validate file type
        allowed = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed:
            raise HTTPException(400, f"Unsupported file type: {ext}")

        # Save uploaded file
        job_id = str(uuid.uuid4())[:8]
        upload_dir = os.path.join(RESULTS_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{job_id}_{file.filename}")

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Process
        try:
            result = pipeline.process_file(file_path, save_result=True)
            result['job_id'] = job_id
            return JSONResponse(content=result)
        except Exception as e:
            raise HTTPException(500, f"Processing error: {str(e)}")

    @app.get("/api/results")
    async def list_results():
        """Lấy danh sách kết quả đã xử lý."""
        results = []
        for f in os.listdir(RESULTS_DIR):
            if f.endswith('_result.json'):
                path = os.path.join(RESULTS_DIR, f)
                with open(path, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                results.append({
                    'filename': f,
                    'source': data.get('source_file', ''),
                    'processed_at': data.get('processed_at', ''),
                    'doc_type': data.get('extraction', {}).get('loai_van_ban', ''),
                })
        return results

    @app.get("/api/results/{filename}")
    async def get_result(filename: str):
        """Lấy chi tiết 1 kết quả."""
        path = os.path.join(RESULTS_DIR, filename)
        if not os.path.exists(path):
            raise HTTPException(404, "Result not found")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    return app


# ==============================================================================
# CELL 5: CHẠY
# ==============================================================================

# --- Standalone ---
# pipeline = OCRLLMPipeline(load_stamp_model=False, load_llm=False)
# result = pipeline.process_file("data/test/QD_0001.pdf")
# print(json.dumps(result['extraction'], ensure_ascii=False, indent=2))

# --- Batch ---
# pipeline = OCRLLMPipeline()
# pipeline.batch_process("data/test", limit=10)

# --- FastAPI Server ---
# app = create_api_app()
# import uvicorn
# uvicorn.run(app, host="0.0.0.0", port=8000)

# --- Colab: expose API with ngrok ---
# !pip install pyngrok
# from pyngrok import ngrok
# public_url = ngrok.connect(8000)
# print(f"🌐 API URL: {public_url}")


if __name__ == '__main__':
    print("🚀 Phase 5: End-to-End Pipeline & API")
    print()
    print("Modes:")
    print("  1. Standalone: process_file('path/to/pdf')")
    print("  2. Batch: batch_process('data/test/')")
    print("  3. API Server: uvicorn.run(create_api_app())")
