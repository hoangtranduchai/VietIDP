import os
import sys
# Fix xung đột OpenMP giữa PyTorch và EasyOCR trên Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import cv2
import numpy as np
import json
from pathlib import Path
from ultralytics import YOLO

# Fix python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.ocr.engine import VietnameseOCREngine

def remove_red_stamp_hsv(img):
    """Xóa con dấu đỏ bằng kỹ thuật HSV + PDE Inpainting (Telea)"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Dải màu đỏ (bao gồm hồng nhạt và viền)
    lower_red1 = np.array([0, 30, 40])
    upper_red1 = np.array([15, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)

    lower_red2 = np.array([165, 30, 40])
    upper_red2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

    red_mask = mask1 + mask2

    # Giãn nở nhẹ để bao trọn vùng mực
    kernel = np.ones((3, 3), np.uint8)
    red_mask_dilated = cv2.dilate(red_mask, kernel, iterations=1)

    # Inpainting bằng Telea để giữ lại nét chữ đen/xanh
    result = cv2.inpaint(img, red_mask_dilated, 3, cv2.INPAINT_TELEA)
    return result

def run_end_to_end_pipeline():
    print("🚀 KHỞI ĐỘNG HỆ THỐNG END-TO-END (YOLOv8 + HSV + PaddleOCR + Qwen-3B) 🚀\n")
    
    # 1. Tải mô hình YOLOv8 (Định vị)
    yolo_path = Config.MODELS_DIR / "finetuned" / "stamp_detector" / "weights" / "best.pt"
    if not yolo_path.exists():
        print(f"❌ Không tìm thấy YOLO model tại {yolo_path}")
        return
    yolo_model = YOLO(str(yolo_path))
    print("✅ [1/4] Đã nạp YOLOv8 (Detector).")

    # 2. Khởi tạo PaddleOCR
    ocr_engine = VietnameseOCREngine()
    if not ocr_engine.is_loaded:
        print("❌ Lỗi tải PaddleOCR.")
        return
    print("✅ [2/4] Đã nạp PaddleOCR (Reader).")

    # 3. Tải mô hình LLM (Qwen 3B + LoRA qua Unsloth)
    try:
        from unsloth import FastLanguageModel
        max_seq_length = Config.LLM_MAX_SEQ_LENGTH
        print("⏳ Đang nạp Qwen-3B LoRA Adapter vào VRAM...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name = str(Config.LLM_ADAPTER_PATH),
            max_seq_length = max_seq_length,
            dtype = None,
            load_in_4bit = True,
        )
        FastLanguageModel.for_inference(model) # Bật chế độ tăng tốc Inference (nhanh gấp 2 lần)
        print("✅ [3/4] Đã nạp Qwen-2.5-3B (Semantic Corrector).")
    except Exception as e:
        print(f"❌ Lỗi tải LLM: {e}")
        return

    # 4. Tìm file A4 test
    test_img_path = Path("test_input_a4.png")
    if not test_img_path.exists():
        print("⚠️ Vui lòng copy 1 tờ A4 nguyên vẹn (có đóng dấu) vào thư mục gốc và đổi tên thành 'test_input_a4.png'!")
        return
        
    print(f"\n🔍 Đang xử lý tờ A4: {test_img_path}")
    img_a4 = cv2.imread(str(test_img_path))
    if img_a4 is None:
        print("❌ Lỗi đọc ảnh.")
        return

    # BƯỚC A: Tẩy Dấu bằng YOLO + HSV
    results = yolo_model(img_a4, verbose=False)
    cleaned_a4 = img_a4.copy()
    boxes_found = 0

    for r in results:
        boxes = r.boxes
        for box in boxes:
            conf = float(box.conf[0])
            if conf < 0.5: continue
                
            boxes_found += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            pad = 15
            h, w = img_a4.shape[:2]
            px1, py1 = max(0, x1 - pad), max(0, y1 - pad)
            px2, py2 = min(w, x2 + pad), min(h, y2 + pad)
            
            stamp_crop = img_a4[py1:py2, px1:px2]
            cleaned_crop = remove_red_stamp_hsv(stamp_crop)
            
            crop_h, crop_w = stamp_crop.shape[:2]
            cleaned_crop_resized = cv2.resize(cleaned_crop, (crop_w, crop_h))
            cleaned_a4[py1:py2, px1:px2] = cleaned_crop_resized

    print(f"✅ Đã tẩy sạch {boxes_found} con dấu đỏ, bảo toàn chữ ký xanh.")
    cv2.imwrite("test_e2e_cleaned.png", cleaned_a4)

    # BƯỚC B: OCR trích xuất chuỗi thô
    print("\n⏳ Đang trích xuất văn bản bằng PaddleOCR...")
    ocr_result = ocr_engine.process_image(cleaned_a4)
    raw_text = ocr_result['text']
    print(f"✅ OCR hoàn tất. Trích xuất được {len(raw_text)} ký tự.")

    # BƯỚC C: LLM Sửa lỗi & Đóng gói JSON
    print("\n⏳ Đang gửi văn bản thô cho Qwen-3B để sửa lỗi và phân tích JSON...")
    
    prompt_template = """Dưới đây là văn bản OCR được trích xuất từ một tài liệu hành chính Việt Nam. Văn bản này có thể chứa một số lỗi nhận dạng chính tả (typos).
Hãy sửa các lỗi chính tả đó dựa trên ngữ cảnh, sau đó trích xuất các thông tin quan trọng ra định dạng JSON.

### Văn bản OCR thô:
{}

### Kết quả JSON xuất ra:
"""
    prompt = prompt_template.format(raw_text)
    inputs = tokenizer([prompt], return_tensors="pt").to("cuda")

    outputs = model.generate(
        **inputs, 
        max_new_tokens=1024, 
        use_cache=True,
        temperature=0.1
    )
    
    decoded_output = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
    
    # Cắt bỏ phần prompt để lấy JSON
    json_response = decoded_output.split("### Kết quả JSON xuất ra:")[-1].strip()
    
    print("\n🎉 KẾT QUẢ ĐẦU RA TỪ LLM:\n")
    print("="*60)
    print(json_response)
    print("="*60)

    # Lưu kết quả
    with open("test_e2e_output.json", "w", encoding="utf-8") as f:
        f.write(json_response)
    print("\n👉 Đã lưu kết quả tại 'test_e2e_output.json' và 'test_e2e_cleaned.png'")

if __name__ == "__main__":
    run_end_to_end_pipeline()
