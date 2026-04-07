# -*- coding: utf-8 -*-
"""
PDF Text Reader
===============
Đọc text từ PDF sử dụng PyMuPDF (text layer).

Nguồn: ai/detect_api.py + Phase3_OCR_Engine.py
"""

import os
import tempfile
import numpy as np
import cv2


def read_pdf_text(pdf_path: str, dpi: int = 200) -> dict:
    """
    Đọc text từ PDF sử dụng PyMuPDF text layer.

    Args:
        pdf_path: Đường dẫn file PDF
        dpi: DPI khi render ảnh (cho trang scan)

    Returns:
        dict: {
            'text': str,
            'pages': list[dict],
            'images': list[np.ndarray] (BGR arrays)
        }
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    pages = []
    images = []
    all_text = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text().strip()
        all_text.append(text)

        # Render page to image
        pix = page.get_pixmap(dpi=dpi)
        img_array = np.frombuffer(
            pix.samples, dtype=np.uint8
        ).reshape(pix.height, pix.width, pix.n)

        if pix.n == 4:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        else:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        images.append(img_bgr)
        pages.append({
            'page': page_idx + 1,
            'text': text,
            'width': pix.width,
            'height': pix.height,
        })

    doc.close()

    return {
        'text': '\n\n'.join(all_text),
        'pages': pages,
        'images': images,
        'num_pages': len(pages),
    }
