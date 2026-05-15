# -*- coding: utf-8 -*-
"""Extract sample text from PDFs to understand LLM input format."""
import fitz, os, json, re

pdf_dir = 'data/raw/pdf_test'
gt = json.load(open('data/benchmark/ground_truth.json', 'r', encoding='utf-8'))

def filter_wm(text):
    text = re.sub(r'Người ký:\s*CỔNG THÔNG TIN ĐIỆN TỬ CHÍNH PHỦ.*?(?:Thời gian ký:[\d\s:\+\-\.]+|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'Người ký:\s*CỔNG THÔNG TIN.*?(?:\+07:00|$)', '', text, flags=re.DOTALL)
    return text.strip()

# Sample: 2 born-digital + 2 scanned (page 1 only)
samples = {
    'born_digital': ['pdf_test_11.pdf', 'pdf_test_42.pdf', 'pdf_test_87.pdf'],
    'scanned': ['pdf_test_1.pdf', 'pdf_test_88.pdf'],
}

for category, files in samples.items():
    print(f"\n{'='*70}")
    print(f"  {category.upper()}")
    print(f"{'='*70}")
    for f in files:
        path = os.path.join(pdf_dir, f)
        doc = fitz.open(path)
        total = ''.join(p.get_text() for p in doc)
        clean = filter_wm(total)
        gt_entry = gt.get(f, {})
        
        print(f"\n--- {f} ({len(doc)} pages, {len(clean)} chars) ---")
        print(f"GT: {json.dumps(gt_entry, ensure_ascii=False)[:200]}")
        print(f"\nFIRST 1500 chars:")
        print(clean[:1500])
        print(f"\nLAST 500 chars:")
        print(clean[-500:] if len(clean) > 500 else clean)
        print()
        doc.close()
