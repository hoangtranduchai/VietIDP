import sys
import json
import cv2

def run_ocr(image_path):
    try:
        from paddleocr import PaddleOCR
        # Khởi tạo PaddleOCR (Chạy trên môi trường riêng lập)
        ocr = PaddleOCR(use_textline_orientation=True, lang="vi")
        
        img = cv2.imread(image_path)
        if img is None:
            print(json.dumps({"error": "Cannot read image"}))
            return
            
        ocr_results = ocr.predict(img)
        texts = []
        if ocr_results:
            for res in ocr_results:
                if isinstance(res, dict):
                    texts.extend(res.get('rec_text', []))
                elif isinstance(res, list):
                    for line in res:
                        if len(line) >= 2:
                            texts.append(line[1][0])
                            
        print(json.dumps({"text": "\n".join(texts)}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_ocr(sys.argv[1])
    else:
        print(json.dumps({"error": "No image path provided"}))
