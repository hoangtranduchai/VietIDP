# -*- coding: utf-8 -*-
"""OCR module: Vietnamese text recognition engine."""

from src.ocr.engine import VietnameseOCREngine
from src.ocr.postprocess import postprocess_vietnamese
from src.ocr.pdf_reader import PDFTextReader

__all__ = ["VietnameseOCREngine", "postprocess_vietnamese", "PDFTextReader"]
