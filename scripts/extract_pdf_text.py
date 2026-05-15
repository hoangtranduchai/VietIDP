"""
Script to extract text from PDF files for ground truth creation.
Extracts first 2 pages of text from each PDF to identify metadata fields.
"""
import fitz  # PyMuPDF
import json
import os
import sys

PDF_DIR = r"e:\OCR-LLM_Research\OCR-LLM_Research\data\raw\pdf_test"
OUTPUT_DIR = r"e:\OCR-LLM_Research\OCR-LLM_Research\data\benchmark"

def extract_text_from_pdf(pdf_path, max_pages=2):
    """Extract text from first max_pages of a PDF."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(min(max_pages, len(doc))):
            page = doc[page_num]
            text += f"\n--- PAGE {page_num + 1} ---\n"
            text += page.get_text("text")
        doc.close()
        return text
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    # Process PDFs 13-100
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 13
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    output_file = os.path.join(OUTPUT_DIR, f"pdf_texts_{start}_{end}.txt")
    
    with open(output_file, "w", encoding="utf-8") as f:
        for i in range(start, end + 1):
            filename = f"pdf_test_{i}.pdf"
            filepath = os.path.join(PDF_DIR, filename)
            
            if not os.path.exists(filepath):
                f.write(f"\n{'='*80}\n{filename}: FILE NOT FOUND\n{'='*80}\n")
                continue
            
            text = extract_text_from_pdf(filepath)
            f.write(f"\n{'='*80}\n")
            f.write(f"FILE: {filename}\n")
            f.write(f"{'='*80}\n")
            f.write(text)
            f.write("\n")
    
    print(f"Extracted text saved to: {output_file}")

if __name__ == "__main__":
    main()
