import os
import sys
import cv2
import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Thêm root vào sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.pipeline.ocr_llm_pipeline import VietIDPPipeline

def visualize_pipeline(image_path, save_dir="results/debug_outputs", show_plot=True):
    print("=" * 60)
    print(" CHẾ ĐỘ VISUAL DEBUG - QUÁ TRÌNH HOẠT ĐỘNG PIPELINE")
    print("=" * 60)
    
    base_name = Path(image_path).stem
    # Tạo thư mục con riêng cho từng ảnh để tránh lộn xộn
    save_path = Path(save_dir) / base_name
    save_path.mkdir(parents=True, exist_ok=True)
    
    pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)
    
    print(f"\n[1] Đọc ảnh đầu vào: {image_path}")
    if not os.path.exists(image_path):
        print(f"❌ Không tìm thấy file: {image_path}")
        return
        
    image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    
    # ---------------------------------------------------------
    print("\n[2] Stage 1 & 2: YOLO Stamp Detection & HybridStampMatting")
    # ---------------------------------------------------------
    prep_img = pipeline.preprocess_image(image)
    clean_img, stamps = pipeline.detect_and_remove_stamps(prep_img)
    
    # Vẽ Bounding Box YOLO
    yolo_img = prep_img.copy()
    for s in stamps:
        cv2.rectangle(yolo_img, (s['x1'], s['y1']), (s['x2'], s['y2']), (0, 0, 255), 4)
        cv2.putText(yolo_img, f"Stamp {s['confidence']:.2f}", (s['x1'], max(30, s['y1']-10)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                    
    # ---------------------------------------------------------
    print("\n[3] Stage 3: OCR Engine (EasyOCR + VietOCR)")
    # ---------------------------------------------------------
    text, raw_lines = pipeline.run_ocr(clean_img)
    
    # Vẽ các dòng OCR (tuỳ chọn)
    ocr_img = clean_img.copy()
    for line in raw_lines:
        bbox = line.get('bbox', [])
        if bbox and len(bbox) == 4:
            pts = np.array(bbox, np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(ocr_img, [pts], True, (0, 255, 0), 2)
            
    # ---------------------------------------------------------
    print("\n[4] Stage 4: LLM Extraction (Qwen2.5-7B)")
    # ---------------------------------------------------------
    extracted = pipeline.extract_info(text)
    validated = pipeline.validate_output(extracted)
    
    print("\n" + "="*50)
    print("KẾT QUẢ TRÍCH XUẤT (JSON Output)")
    print("="*50)
    
    # Gộp cả Raw Text vào để dễ debug xem lỗi do OCR hay do LLM
    debug_output = {
        "source_file": base_name,
        "ocr_raw_text": text,
        "extraction_result": validated
    }
    
    json_output = json.dumps(debug_output, indent=4, ensure_ascii=False)
    print(json_output)
    print("="*50)
    
    # ---------------------------------------------------------
    # Lưu file từng giai đoạn (Dành cho báo cáo / Demo)
    # ---------------------------------------------------------
    print(f"\n[5] Đang lưu các file báo cáo vào: {save_path.absolute()}")
    cv2.imwrite(str(save_path / "stage1_yolo.jpg"), yolo_img)
    cv2.imwrite(str(save_path / "stage2_matting.jpg"), clean_img)
    cv2.imwrite(str(save_path / "stage3_ocr.jpg"), ocr_img)
    with open(save_path / "stage4_llm.json", "w", encoding="utf-8") as f:
        f.write(json_output)
    
    # ---------------------------------------------------------
    # Hiển thị Matplotlib trực quan (cửa sổ Popup)
    # ---------------------------------------------------------
    fig = plt.figure(figsize=(18, 6))
    
    plt.subplot(1, 3, 1)
    plt.title(f"Stage 1: YOLOv8x Detection\n(Phát hiện {len(stamps)} con dấu)")
    plt.imshow(cv2.cvtColor(yolo_img, cv2.COLOR_BGR2RGB))
    plt.axis('off')
    
    plt.subplot(1, 3, 2)
    plt.title("Stage 2: HybridStampMatting\n(Xóa nền & con dấu)")
    plt.imshow(cv2.cvtColor(clean_img, cv2.COLOR_BGR2RGB))
    plt.axis('off')
    
    plt.subplot(1, 3, 3)
    plt.title(f"Stage 3: OCR Detection\n(Phát hiện {len(raw_lines)} dòng text)")
    plt.imshow(cv2.cvtColor(ocr_img, cv2.COLOR_BGR2RGB))
    plt.axis('off')
    
    plt.tight_layout()
    plt.savefig(str(save_path / "combined_stages.jpg"), dpi=150)
    print(f"✅ Đã lưu toàn bộ kết quả gọn gàng tại thư mục: {save_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close(fig)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="VietIDP Visual Debugger")
    parser.add_argument("--input", default="data/test/bench_000.jpg", help="Đường dẫn file ảnh hoặc thư mục cần test")
    parser.add_argument("--save-dir", default="results/debug_outputs", help="Thư mục lưu ảnh các giai đoạn")
    parser.add_argument("--no-show", action="store_true", help="Chỉ lưu file, không hiển thị cửa sổ Popup (tránh lag)")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if input_path.is_dir():
        print(f"📁 Đã chọn thư mục: {input_path}")
        print("🔄 Sẽ xử lý tất cả các file ảnh bên trong (Tự động tắt Popup).")
        image_files = list(input_path.glob("*.jpg")) + list(input_path.glob("*.png"))
        
        for idx, img_file in enumerate(image_files):
            print(f"\n[{idx+1}/{len(image_files)}] Đang xử lý: {img_file.name}")
            visualize_pipeline(str(img_file), args.save_dir, show_plot=False)
            
        print(f"\n🎉 HOÀN TẤT! Đã xuất dữ liệu debug cho {len(image_files)} file vào {args.save_dir}")
    else:
        visualize_pipeline(str(input_path), args.save_dir, show_plot=not args.no_show)
