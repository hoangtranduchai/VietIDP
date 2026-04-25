from docx import Document
import glob

files = glob.glob('data/raw_word_files/**/*.docx', recursive=True)[:3]
for f in files:
    print('=== FILE:', f)
    doc = Document(f)
    for p in doc.paragraphs[:20]:
        if p.text.strip():
            print(repr(p.text.strip()))
    print()
