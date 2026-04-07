# -*- coding: utf-8 -*-
"""
Auto-Deskew Module
==================
Tự động phát hiện và sửa ảnh bị nghiêng (skew correction).

Thuật toán:
1. Chuyển ảnh sang grayscale → threshold (Otsu)
2. Tìm minAreaRect trên tọa độ pixel > 0
3. Tính góc nghiêng → xoay lại bằng warpAffine

Nguồn: Phase5_End_to_End_Pipeline.py, line 166-194
"""

import cv2
import numpy as np


def auto_deskew(image: np.ndarray, max_angle: float = 10.0) -> np.ndarray:
    """
    Tự động xoay ảnh bị nghiêng.

    Args:
        image: BGR numpy array
        max_angle: Góc tối đa cho phép xoay (độ). Tránh xoay sai ảnh thẳng.

    Returns:
        BGR numpy array đã được deskew.
    """
    if image is None or image.size == 0:
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )[1]

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 100:
        return image

    angle = cv2.minAreaRect(coords)[-1]

    # OpenCV minAreaRect trả về góc trong [-90, 0)
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Chỉ xoay nếu góc nhỏ để tránh xoay sai
    if abs(angle) > max_angle or abs(angle) < 0.1:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return rotated
