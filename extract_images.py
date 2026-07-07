import docx
import os

doc_path = r"E:\OCR-LLM_Research\OCR-LLM_Research\Document\BaoCaoNCKH2026_OCRLLM_NguyenTien.docx"
out_dir = r"C:\Users\hoang\.gemini\antigravity\brain\9b6ad7f2-8303-494d-8f56-90a78ee06fa5"

doc = docx.Document(doc_path)
count = 0
for rel in doc.part.rels.values():
    if "image" in rel.target_ref:
        img_data = rel.target_part.blob
        ext = rel.target_part.content_type.split("/")[-1]
        img_name = f"image_{count}.{ext}"
        with open(os.path.join(out_dir, img_name), "wb") as f:
            f.write(img_data)
        print(f"Extracted: {img_name}")
        count += 1
