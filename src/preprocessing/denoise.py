# -*- coding: utf-8 -*-
"""
Denoise Module
==============
Giảm nhiễu ảnh scan sử dụng Non-Local Means Denoising.

Nguồn: Phase5_End_to_End_Pipeline.py, line 158
"""

import cv2
import numpy as np


def denoise_image(
    image: np.ndarray,
    h: int = 10,
    hForColorComponents: int = 10,
    templateWindowSize: int = 7,
    searchWindowSize: int = 21
) -> np.ndarray:
    """
    Giảm nhiễu ảnh scan bằng fastNlMeansDenoisingColored.

    Args:
        image: BGR numpy array
        h: Filter strength (luminance). Lớn hơn → mịn hơn nhưng mất chi tiết.
        hForColorComponents: Filter strength (color channels).
        templateWindowSize: Kích thước template patch (lẻ).
        searchWindowSize: Kích thước vùng tìm kiếm (lẻ).

    Returns:
        BGR numpy array đã giảm nhiễu.
    """
    if image is None or image.size == 0:
        return image

    denoised = cv2.fastNlMeansDenoisingColored(
        image, None, h, hForColorComponents,
        templateWindowSize, searchWindowSize
    )
    return denoised
