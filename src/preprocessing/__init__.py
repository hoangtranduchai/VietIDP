# -*- coding: utf-8 -*-
"""Preprocessing module: deskew, denoise, stamp removal."""

from src.preprocessing.deskew import auto_deskew
from src.preprocessing.denoise import denoise_image

__all__ = ["auto_deskew", "denoise_image"]
