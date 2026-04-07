# -*- coding: utf-8 -*-
"""
Stamp Extractor
================
Trích xuất con dấu đỏ từ PDF bằng HSV color segmentation.

Nguồn: Phase1_Data_Preparation.py, line 70-188
"""

import os
import numpy as np
import cv2


def extract_stamps_from_pdf(pdf_path: str, output_dir: str,
                            min_area: int = 500, max_stamps: int = 5,
                            dpi: int = 200) -> list:
    """
    Trích xuất con dấu đỏ từ file PDF bằng HSV color segmentation.

    Thuật toán:
    1. Render PDF page → image (200 DPI)
    2. Chuyển sang HSV color space
    3. Tạo mask cho vùng màu đỏ (H: [0-10] ∪ [160-180])
    4. Morphological operations → Tìm contours → crop

    Args:
        pdf_path: Đường dẫn file PDF
        output_dir: Thư mục lưu stamps
        min_area: Diện tích tối thiểu (pixel²)
        max_stamps: Số stamp tối đa/trang
        dpi: DPI khi render

    Returns:
        List đường dẫn stamp files
    """
    import fitz

    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    extracted_paths = []

    for page_idx in range(min(len(doc), 5)):
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=dpi)
        img_array = np.frombuffer(
            pix.samples, dtype=np.uint8
        ).reshape(pix.height, pix.width, pix.n)

        if pix.n == 4:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        else:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # HSV segmentation
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 50, 50])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(
            red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
        valid_contours.sort(key=cv2.contourArea, reverse=True)

        for i, contour in enumerate(valid_contours[:max_stamps]):
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.3 or aspect_ratio > 3.0 or w < 50 or h < 50:
                continue

            pad = 10
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(img_bgr.shape[1], x + w + pad)
            y2 = min(img_bgr.shape[0], y + h + pad)

            stamp_crop = img_bgr[y1:y2, x1:x2]
            stamp_mask_crop = red_mask[y1:y2, x1:x2]
            stamp_rgba = cv2.cvtColor(stamp_crop, cv2.COLOR_BGR2BGRA)
            stamp_rgba[:, :, 3] = stamp_mask_crop

            stamp_filename = f"{pdf_name}_p{page_idx}_stamp{i}.png"
            stamp_path = os.path.join(output_dir, stamp_filename)
            cv2.imwrite(stamp_path, stamp_rgba)
            extracted_paths.append(stamp_path)

    doc.close()
    return extracted_paths


def batch_extract_stamps(pdf_dir: str, output_dir: str, limit: int = None) -> list:
    """Trích xuất stamps từ tất cả PDF trong thư mục."""
    pdf_files = sorted([
        f for f in os.listdir(pdf_dir)
        if f.lower().endswith('.pdf')
    ])
    if limit:
        pdf_files = pdf_files[:limit]

    all_stamps = []
    for i, pdf_file in enumerate(pdf_files):
        pdf_path = os.path.join(pdf_dir, pdf_file)
        try:
            stamps = extract_stamps_from_pdf(pdf_path, output_dir)
            all_stamps.extend(stamps)
            if (i + 1) % 10 == 0:
                print(f"  📄 Đã xử lý {i+1}/{len(pdf_files)} PDFs, "
                      f"tìm thấy {len(all_stamps)} stamps")
        except Exception as e:
            print(f"  ⚠️ Lỗi {pdf_file}: {e}")

    print(f"\n✅ Tổng cộng trích xuất {len(all_stamps)} stamps")
    return all_stamps
