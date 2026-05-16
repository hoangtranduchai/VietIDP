# -*- coding: utf-8 -*-
"""
Fix Document Names Migration
=============================
One-time script to fix documents whose filename and file_type were
incorrectly overwritten with page image values (e.g., "abc_page_1.jpg"
instead of the original uploaded filename).

Usage:
    python scripts/fix_document_names.py
"""

import os
import re
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.database import get_session, Document


def fix_document_names():
    """Fix documents that have page image filenames instead of original names."""
    session = get_session()
    try:
        docs = session.query(Document).all()
        fixed_count = 0

        for doc in docs:
            # Detect the bug pattern: filename looks like "UUID_page_N.jpg"
            if doc.filename and re.match(r'^[a-f0-9]{32}_page_\d+\.jpg$', doc.filename):
                # This document was affected by the bug
                original_file_path = doc.file_path or ""

                # Try to infer original filename from file_path
                # The original PDF was stored at: uploads/UUID.pdf
                # After bug: file_path was changed to uploads/UUID_page_1.jpg
                uuid_hex = doc.filename.split('_page_')[0]

                # Check if original PDF still exists
                upload_dir = os.path.dirname(original_file_path)
                original_pdf = os.path.join(upload_dir, f"{uuid_hex}.pdf")

                if os.path.exists(original_pdf):
                    doc.file_path = original_pdf
                    doc.file_type = "pdf"
                    doc.filename = f"{uuid_hex}.pdf"  # Best we can do without original name
                    print(f"  ✅ Doc #{doc.id}: restored to PDF ({uuid_hex}.pdf)")
                    fixed_count += 1
                else:
                    # PDF was deleted/missing, just fix the file_type at least
                    print(f"  ⚠️ Doc #{doc.id}: original PDF not found, keeping current file_path")
                    # We can still fix file_type if the document was originally a PDF
                    # (all affected docs were PDFs that got converted)
                    if doc.num_pages and doc.num_pages > 1:
                        doc.file_type = "pdf"
                        print(f"      → Set file_type to 'pdf' (has {doc.num_pages} pages)")
                        fixed_count += 1

        if fixed_count > 0:
            session.commit()
            print(f"\n✅ Fixed {fixed_count} documents")
        else:
            print("\n✅ No documents need fixing")

    finally:
        session.close()


if __name__ == "__main__":
    fix_document_names()
