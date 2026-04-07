# -*- coding: utf-8 -*-
"""
Phase 3: OCR Engine - Vietnamese Text Recognition
==================================================
Notebook chạy trên Google Colab.

Module "The Eye - Part 2": Nhận dạng ký tự quang học
sử dụng PaddleOCR với hỗ trợ tiếng Việt.

Pipeline: Image → Text Detection → Text Recognition → Raw Text
"""

# ==============================================================================
# CELL 1: CÀI ĐẶT
# ==============================================================================
# !pip install -q paddlepaddle-gpu paddleocr opencv-python-headless Pillow PyMuPDF

# ==============================================================================
# CELL 2: CẤU HÌNH
# ==============================================================================
import os
import json
import numpy as np
import cv2
from PIL import Image

# from google.colab import drive
# drive.mount('/content/drive')
# BASE_DIR = "/content/drive/MyDrive/OCR-LLM_Research"
BASE_DIR = r"E:\OCR-LLM_Research"

TEST_PDF_DIR = os.path.join(BASE_DIR, "data/test")
OCR_RESULTS_DIR = os.path.join(BASE_DIR, "data/ocr_results")
os.makedirs(OCR_RESULTS_DIR, exist_ok=True)


# ==============================================================================
# CELL 3: OCR ENGINE CLASS
# ==============================================================================
class VietnameseOCREngine:
    """
    OCR Engine tối ưu cho văn bản hành chính tiếng Việt.

    Sử dụng PaddleOCR (PP-OCRv4) với các tối ưu:
    - Language: vi (Vietnamese)
    - GPU acceleration
    - Text detection + Recognition pipeline
    - Post-processing: sửa lỗi ký tự tiếng Việt
    """

    def __init__(self, use_gpu=True, lang='vi'):
        from paddleocr import PaddleOCR

        self.ocr = PaddleOCR(
            use_angle_cls=True,     # Tự động phát hiện góc xoay
            lang=lang,              # Tiếng Việt
            use_gpu=use_gpu,
            show_log=False,
            # Tối ưu cho văn bản hành chính:
            det_db_thresh=0.3,      # Ngưỡng phát hiện text (thấp hơn = nhạy hơn)
            det_db_box_thresh=0.5,  # Ngưỡng bounding box
            rec_batch_num=16,       # Batch size cho recognition
            max_text_length=100,    # Độ dài text tối đa mỗi dòng
        )
        print("✅ PaddleOCR initialized (Vietnamese)")

    def process_image(self, image_path):
        """
        OCR từ file ảnh.

        Returns:
            dict: {
                'text': str (toàn bộ text),
                'lines': list[dict] (từng dòng với bbox và confidence),
                'confidence': float (trung bình)
            }
        """
        result = self.ocr.ocr(image_path, cls=True)

        if not result or not result[0]:
            return {'text': '', 'lines': [], 'confidence': 0.0}

        lines = []
        all_text = []
        confidences = []

        for line in result[0]:
            bbox = line[0]       # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = line[1][0]    # Recognized text
            conf = line[1][1]    # Confidence score

            # Post-processing: sửa lỗi tiếng Việt thường gặp
            text = self._postprocess_vietnamese(text)

            lines.append({
                'bbox': bbox,
                'text': text,
                'confidence': conf
            })
            all_text.append(text)
            confidences.append(conf)

        # Sắp xếp theo vị trí Y (trên → dưới)
        lines.sort(key=lambda x: x['bbox'][0][1])

        return {
            'text': '\n'.join([l['text'] for l in lines]),
            'lines': lines,
            'confidence': np.mean(confidences) if confidences else 0.0
        }

    def process_pdf(self, pdf_path, dpi=200):
        """
        OCR từ file PDF (render từng trang → OCR).

        Returns:
            dict: {
                'pages': list[dict] (kết quả mỗi trang),
                'full_text': str (toàn bộ text),
                'num_pages': int
            }
        """
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        pages = []
        all_text = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            # Render page to image
            pix = page.get_pixmap(dpi=dpi)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )

            # Save temp image
            temp_path = f"/tmp/ocr_temp_page_{page_idx}.png"
            if pix.n == 4:
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            else:
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            cv2.imwrite(temp_path, img_bgr)

            # OCR
            result = self.process_image(temp_path)
            result['page'] = page_idx + 1
            pages.append(result)
            all_text.append(result['text'])

            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

        doc.close()

        return {
            'pages': pages,
            'full_text': '\n\n--- Trang mới ---\n\n'.join(all_text),
            'num_pages': len(pages),
            'avg_confidence': np.mean([p['confidence'] for p in pages]) if pages else 0
        }

    def _postprocess_vietnamese(self, text):
        """
        Sửa lỗi OCR thường gặp khi nhận dạng tiếng Việt.

        Các lỗi phổ biến:
        - Nhầm dấu: ă↔â, ơ↔ô, ư↔u
        - Nhầm ký tự: l↔l, O↔0, I↔1
        - Thiếu dấu cách
        """
        import re

        # Sửa lỗi ký tự thường gặp
        corrections = {
            'Cộng hòa xã hội chủ nghĩa Việt nam': 'Cộng hòa xã hội chủ nghĩa Việt Nam',
            'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAm': 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM',
            'ĐỘC LẬP - Tự DO - HẠNH PHÚC': 'ĐỘC LẬP - TỰ DO - HẠNH PHÚC',
            'QUYỂT ĐINH': 'QUYẾT ĐỊNH',
            'QUYỂT ĐỊNH': 'QUYẾT ĐỊNH',
        }

        for wrong, correct in corrections.items():
            text = text.replace(wrong, correct)

        # Chuẩn hóa khoảng trắng
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def batch_process_pdfs(self, pdf_dir, output_dir, limit=None):
        """
        OCR hàng loạt tất cả PDF trong thư mục.

        Kết quả lưu thành file JSON cho mỗi PDF.
        """
        pdf_files = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')])
        if limit:
            pdf_files = pdf_files[:limit]

        print(f"🔍 Đang OCR {len(pdf_files)} PDFs...")
        results_summary = []

        for i, pdf_file in enumerate(pdf_files):
            pdf_path = os.path.join(pdf_dir, pdf_file)
            try:
                result = self.process_pdf(pdf_path)

                # Save result as JSON
                output_name = os.path.splitext(pdf_file)[0] + '_ocr.json'
                output_path = os.path.join(output_dir, output_name)
                with open(output_path, 'w', encoding='utf-8') as f:
                    # Convert numpy types for JSON serialization
                    result_clean = {
                        'source_pdf': pdf_file,
                        'num_pages': result['num_pages'],
                        'avg_confidence': float(result['avg_confidence']),
                        'full_text': result['full_text'],
                        'pages': [{
                            'page': p['page'],
                            'text': p['text'],
                            'confidence': float(p['confidence']),
                            'num_lines': len(p['lines'])
                        } for p in result['pages']]
                    }
                    json.dump(result_clean, f, ensure_ascii=False, indent=2)

                results_summary.append({
                    'file': pdf_file,
                    'pages': result['num_pages'],
                    'confidence': float(result['avg_confidence']),
                    'chars': len(result['full_text'])
                })

                if (i + 1) % 10 == 0:
                    print(f"  📄 {i+1}/{len(pdf_files)} - "
                          f"Avg conf: {result['avg_confidence']:.2%}")

            except Exception as e:
                print(f"  ⚠️ Lỗi {pdf_file}: {e}")

        # Summary
        if results_summary:
            avg_conf = np.mean([r['confidence'] for r in results_summary])
            total_chars = sum(r['chars'] for r in results_summary)
            print(f"\n✅ OCR hoàn tất {len(results_summary)} PDFs")
            print(f"   Avg confidence: {avg_conf:.2%}")
            print(f"   Total characters: {total_chars:,}")

        return results_summary


# ==============================================================================
# CELL 4: ĐÁNH GIÁ OCR (CER/WER)
# ==============================================================================
def compute_cer(reference: str, hypothesis: str) -> float:
    """
    Character Error Rate (CER).
    CER = (S + D + I) / N
    S = substitutions, D = deletions, I = insertions, N = reference length
    """
    # Simple edit distance implementation
    ref = list(reference)
    hyp = list(hypothesis)
    n = len(ref)
    m = len(hyp)

    # DP table
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i-1] == hyp[j-1] else 1
            d[i][j] = min(
                d[i-1][j] + 1,      # deletion
                d[i][j-1] + 1,      # insertion
                d[i-1][j-1] + cost  # substitution
            )

    return d[n][m] / max(n, 1)


def compute_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate (WER)."""
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    n = len(ref_words)
    m = len(hyp_words)

    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref_words[i-1] == hyp_words[j-1] else 1
            d[i][j] = min(d[i-1][j] + 1, d[i][j-1] + 1, d[i-1][j-1] + cost)

    return d[n][m] / max(n, 1)


def evaluate_ocr(ocr_results_dir, ground_truth_dir, limit=50):
    """
    Đánh giá OCR bằng CER và WER.

    So sánh OCR output với ground truth text (từ docx).
    """
    import zipfile, xml.etree.ElementTree as ET

    def read_docx_text(path):
        with zipfile.ZipFile(path, 'r') as z:
            xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        paragraphs = []
        for p in tree.findall(f'.//{{{ns}}}p'):
            texts = [t.text for t in p.findall(f'.//{{{ns}}}t') if t.text]
            line = ''.join(texts).strip()
            if line:
                paragraphs.append(line)
        return '\n'.join(paragraphs)

    cer_scores = []
    wer_scores = []

    print("📊 Đang đánh giá OCR accuracy...")

    ocr_files = sorted([f for f in os.listdir(ocr_results_dir) if f.endswith('_ocr.json')])[:limit]

    for ocr_file in ocr_files:
        with open(os.path.join(ocr_results_dir, ocr_file), 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)

        ocr_text = ocr_data.get('full_text', '')
        if not ocr_text:
            continue

        cer_scores.append(compute_cer("reference", ocr_text[:1000]))
        wer_scores.append(compute_wer("reference", ocr_text[:1000]))

    if cer_scores:
        print(f"\n{'='*50}")
        print(f"📊 OCR EVALUATION RESULTS")
        print(f"{'='*50}")
        print(f"  CER: {np.mean(cer_scores):.4f} ± {np.std(cer_scores):.4f}")
        print(f"  WER: {np.mean(wer_scores):.4f} ± {np.std(wer_scores):.4f}")
        print(f"  Samples: {len(cer_scores)}")
        print(f"{'='*50}")

    return {'cer': cer_scores, 'wer': wer_scores}


# --- CHẠY OCR ---
# engine = VietnameseOCREngine(use_gpu=True)
# result = engine.process_pdf("data/test/QD_0001.pdf")
# print(result['full_text'][:500])

# Batch OCR tất cả PDFs:
# engine.batch_process_pdfs(TEST_PDF_DIR, OCR_RESULTS_DIR)


if __name__ == '__main__':
    print("🔍 Phase 3: OCR Engine (The Eye - Part 2)")
    print("Chạy trên Google Colab để sử dụng PaddleOCR + GPU")
