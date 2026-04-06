import sys
import json
import cv2
import os
import tempfile
import contextlib
import io
import fitz  # PyMuPDF
import numpy as np
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "stamp_model", "weights", "best.pt")

# DPI for PDF rendering (200 recommended for small text)
DPI = int(os.environ.get("OCR_DPI", "200"))


def extract_pages_as_images(img_path):
    """Trả về (images_array, extracted_text)"""
    images = []
    text = ""
    if img_path.lower().endswith('.pdf'):
        doc = fitz.open(img_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text() + "\n"
            pix = page.get_pixmap(dpi=DPI)

            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            else:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            images.append(img)
    else:
        images.append(cv2.imread(img_path))
    return images, text


def detect_and_draw(img_path):
    # Input validation
    img_path = os.path.abspath(img_path)
    if not os.path.exists(img_path):
        print(json.dumps({"error": f"File not found: {img_path}"}))
        return

    images, extracted_text = extract_pages_as_images(img_path)

    if not images or any(img is None for img in images):
        print(json.dumps({"error": f"Cannot read file: {img_path}"}))
        return

    pages_result = []
    total_conf = 0
    total_stamps = 0

    has_model = os.path.exists(MODEL_PATH)
    model = None
    if has_model:
        with contextlib.redirect_stdout(io.StringIO()):
            model = YOLO(MODEL_PATH)

    # Use temp directory for output images
    temp_dir = tempfile.mkdtemp(prefix="vietidp_")

    for idx, img in enumerate(images):
        orig_filename = f"orig_p{idx}.jpg"
        annot_filename = f"annot_p{idx}.jpg"
        orig_path = os.path.join(temp_dir, orig_filename)
        out_path = os.path.join(temp_dir, annot_filename)
        cv2.imwrite(orig_path, img)

        stamps = []
        if not has_model:
            h, w = img.shape[:2]
            cx, cy, bw, bh = w // 2, h // 2, min(w, h) // 4, min(w, h) // 4
            x1, y1 = cx - bw // 2, cy - bh // 2

            cv2.rectangle(img, (x1, y1), (x1 + bw, y1 + bh), (0, 0, 255), 3)
            cv2.putText(img, "Stamp Mock", (x1, max(y1 - 10, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            stamps.append({"x": x1, "y": y1, "w": bw, "h": bh, "confidence": 98.5})
            total_stamps += 1
            total_conf += 98.5
        else:
            with contextlib.redirect_stdout(io.StringIO()):
                results = model.predict(source=img, conf=0.5, save=False, verbose=False)

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    total_conf += conf
                    total_stamps += 1

                    stamps.append({
                        "x": int(x1), "y": int(y1),
                        "w": int(x2 - x1), "h": int(y2 - y1),
                        "confidence": round(conf * 100, 2)
                    })

                    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)),
                                  (0, 0, 255), 3)
                    cv2.putText(img, f"Stamp {conf:.2f}",
                                (int(x1), max(int(y1) - 10, 0)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        cv2.imwrite(out_path, img)

        img_h, img_w = img.shape[:2]

        pages_result.append({
            "original_image": orig_path,
            "output_image": out_path,
            "img_w": int(img_w),
            "img_h": int(img_h),
            "stamps": stamps
        })

    avg_conf = round((total_conf / total_stamps * 100) if total_stamps else 0, 2)

    summary_data = None
    if extracted_text and len(extracted_text.strip()) > 30:
        try:
            from summarize import summarize_with_ollama
            summary_res, err = summarize_with_ollama(extracted_text)
            if not err:
                summary_data = summary_res
        except Exception:
            pass

    print(json.dumps({
        "pages": pages_result,
        "confidence_avg": avg_conf,
        "summary": summary_data
    }))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No image path provided"}))
        sys.exit(1)

    img_path = sys.argv[1]

    try:
        detect_and_draw(img_path)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
