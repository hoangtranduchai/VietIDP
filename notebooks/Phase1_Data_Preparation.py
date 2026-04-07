# -*- coding: utf-8 -*-
"""
Phase 1: Data Preparation & Synthetic Data Generation
=====================================================
Notebook này chạy trên Google Colab.
Upload folder 'data/' lên Google Drive trước khi chạy.

Nội dung:
1. Cài đặt môi trường
2. Trích xuất con dấu từ PDF test
3. Tạo synthetic stamps
4. Chuyển docx → Image + Overlay stamps
5. Tạo LLM training dataset
"""

# ==============================================================================
# CELL 1: CÀI ĐẶT MÔI TRƯỜNG (Chạy 1 lần)
# ==============================================================================
# !pip install -q python-docx pdf2image Pillow opencv-python-headless numpy pandas
# !pip install -q PyMuPDF   # fitz - đọc PDF nhanh
# !apt-get install -y poppler-utils fonts-noto-cjk > /dev/null 2>&1

# ==============================================================================
# CELL 2: MOUNT GOOGLE DRIVE
# ==============================================================================
# from google.colab import drive
# drive.mount('/content/drive')

# ==============================================================================
# CELL 3: CẤU HÌNH ĐƯỜNG DẪN
# ==============================================================================
import os

# === CẤU HÌNH: Thay đổi đường dẫn phù hợp với Google Drive của bạn ===
# Khi chạy trên Colab, dùng đường dẫn Google Drive:
# BASE_DIR = "/content/drive/MyDrive/OCR-LLM_Research"
# Khi chạy local:
BASE_DIR = r"E:\OCR-LLM_Research"

DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DOCX_DIR = os.path.join(DATA_DIR, "raw_word_files")
TEST_PDF_DIR = os.path.join(DATA_DIR, "test")
STAMPS_DIR = os.path.join(DATA_DIR, "stamps")
STAMPS_EXTRACTED_DIR = os.path.join(STAMPS_DIR, "extracted")
STAMPS_SYNTHETIC_DIR = os.path.join(STAMPS_DIR, "synthetic")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
CLEAN_IMAGES_DIR = os.path.join(PROCESSED_DIR, "clean_images")
STAMPED_IMAGES_DIR = os.path.join(PROCESSED_DIR, "stamped_images")
LLM_TRAINING_DIR = os.path.join(DATA_DIR, "llm_training")

# Tạo thư mục
for d in [STAMPS_EXTRACTED_DIR, STAMPS_SYNTHETIC_DIR,
          CLEAN_IMAGES_DIR, STAMPED_IMAGES_DIR, LLM_TRAINING_DIR]:
    os.makedirs(d, exist_ok=True)

print(f"✅ BASE_DIR: {BASE_DIR}")
print(f"✅ Số file docx categories: {os.listdir(RAW_DOCX_DIR) if os.path.exists(RAW_DOCX_DIR) else 'NOT FOUND'}")
print(f"✅ Số file PDF test: {len([f for f in os.listdir(TEST_PDF_DIR) if f.endswith('.pdf')]) if os.path.exists(TEST_PDF_DIR) else 'NOT FOUND'}")


# ==============================================================================
# CELL 4: TRÍCH XUẤT CON DẤU TỪ PDF (Stamp Extractor)
# ==============================================================================
import numpy as np
import cv2
from PIL import Image
import fitz  # PyMuPDF


def extract_stamps_from_pdf(pdf_path, output_dir, min_area=500, max_stamps=5):
    """
    Trích xuất con dấu đỏ từ file PDF bằng HSV color segmentation.

    Thuật toán:
    1. Render PDF page → image
    2. Chuyển sang HSV color space
    3. Tạo mask cho vùng màu đỏ (con dấu)
    4. Tìm contours → crop vùng dấu
    5. Lưu ảnh stamp riêng biệt

    Args:
        pdf_path: Đường dẫn file PDF
        output_dir: Thư mục lưu stamps trích xuất
        min_area: Diện tích tối thiểu (pixel²) để lọc nhiễu
        max_stamps: Số stamp tối đa trích xuất mỗi trang
    Returns:
        List đường dẫn file stamp đã trích xuất
    """
    doc = fitz.open(pdf_path)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    extracted_paths = []

    for page_idx in range(min(len(doc), 5)):  # Giới hạn 5 trang đầu
        page = doc[page_idx]
        # Render page ở 200 DPI
        pix = page.get_pixmap(dpi=200)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )

        # Chuyển RGB → BGR (OpenCV format)
        if pix.n == 4:  # RGBA
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        else:  # RGB
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # Chuyển sang HSV
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        # Mask cho màu đỏ (dấu đỏ):
        # Đỏ nằm ở 2 vùng trong HSV: [0-10] và [160-180] (Hue)
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 50, 50])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        # Morphological operations để làm sạch mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # Tìm contours
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Lọc và sắp xếp theo diện tích (lớn nhất = dấu chính)
        valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
        valid_contours.sort(key=cv2.contourArea, reverse=True)

        for i, contour in enumerate(valid_contours[:max_stamps]):
            x, y, w, h = cv2.boundingRect(contour)

            # Kiểm tra tỷ lệ khung hình (dấu thường gần tròn, ratio ~ 0.5-2.0)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                continue

            # Kiểm tra kích thước tối thiểu (dấu thường > 50x50 px ở 200dpi)
            if w < 50 or h < 50:
                continue

            # Padding thêm 10px
            pad = 10
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(img_bgr.shape[1], x + w + pad)
            y2 = min(img_bgr.shape[0], y + h + pad)

            # Crop vùng stamp
            stamp_crop = img_bgr[y1:y2, x1:x2]

            # Tạo ảnh stamp với nền trong suốt (RGBA)
            stamp_mask_crop = red_mask[y1:y2, x1:x2]
            stamp_rgba = cv2.cvtColor(stamp_crop, cv2.COLOR_BGR2BGRA)
            stamp_rgba[:, :, 3] = stamp_mask_crop  # Alpha channel = red mask

            # Lưu
            stamp_filename = f"{pdf_name}_p{page_idx}_stamp{i}.png"
            stamp_path = os.path.join(output_dir, stamp_filename)
            cv2.imwrite(stamp_path, stamp_rgba)
            extracted_paths.append(stamp_path)

    doc.close()
    return extracted_paths


def batch_extract_stamps(pdf_dir, output_dir, limit=None):
    """Trích xuất stamps từ tất cả PDF trong thư mục."""
    pdf_files = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')])
    if limit:
        pdf_files = pdf_files[:limit]

    all_stamps = []
    for i, pdf_file in enumerate(pdf_files):
        pdf_path = os.path.join(pdf_dir, pdf_file)
        try:
            stamps = extract_stamps_from_pdf(pdf_path, output_dir)
            all_stamps.extend(stamps)
            if (i + 1) % 10 == 0:
                print(f"  📄 Đã xử lý {i+1}/{len(pdf_files)} PDFs, tìm thấy {len(all_stamps)} stamps")
        except Exception as e:
            print(f"  ⚠️ Lỗi xử lý {pdf_file}: {e}")

    print(f"\n✅ Tổng cộng trích xuất được {len(all_stamps)} stamps từ {len(pdf_files)} PDFs")
    return all_stamps


# --- CHẠY TRÍCH XUẤT ---
# Uncomment để chạy:
# print("🔍 Đang trích xuất con dấu từ PDFs...")
# extracted = batch_extract_stamps(TEST_PDF_DIR, STAMPS_EXTRACTED_DIR)


# ==============================================================================
# CELL 5: TẠO SYNTHETIC STAMPS (Stamp Generator)
# ==============================================================================
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import math


def create_synthetic_stamp(
    output_path,
    org_name="CƠ QUAN BAN HÀNH",
    sub_text="Số: ___/QĐ-UBND",
    stamp_type="circle",  # "circle" hoặc "oval"
    size=250,
    color=(200, 30, 30),  # Màu đỏ đậm
    has_star=True,
    rotation_range=(-15, 15),
    blur_amount=0.5,
    opacity=200  # 0-255
):
    """
    Tạo con dấu giả lập giống thật bằng Python.

    Dấu gồm:
    - Viền tròn/oval đỏ (2 viền)
    - Text tên cơ quan bao quanh (curved text)
    - Ngôi sao 5 cánh ở giữa
    - Random rotation & blur để tăng tính thực tế

    Args:
        output_path: Đường dẫn lưu ảnh stamp
        org_name: Tên cơ quan (hiển thị bao quanh)
        sub_text: Dòng chữ phụ bên dưới
        stamp_type: "circle" hoặc "oval"
        size: Kích thước (pixel)
        color: Màu RGB
        has_star: Có ngôi sao giữa không
        rotation_range: Phạm vi xoay ngẫu nhiên (độ)
        blur_amount: Mức blur
        opacity: Độ trong suốt (0=trong suốt, 255=đặc)
    Returns:
        PIL Image (RGBA)
    """
    # Tạo canvas lớn hơn để xoay không bị cắt
    canvas_size = int(size * 1.5)
    img = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center_x = canvas_size // 2
    center_y = canvas_size // 2
    radius = size // 2

    # --- Vẽ viền ngoài ---
    border_width = max(3, size // 40)
    if stamp_type == "oval":
        rx, ry = radius, int(radius * 0.75)
    else:
        rx, ry = radius, radius

    # Viền ngoài
    draw.ellipse(
        [center_x - rx, center_y - ry, center_x + rx, center_y + ry],
        outline=(*color, opacity),
        width=border_width
    )
    # Viền trong (cách viền ngoài 5px)
    inner_gap = max(4, size // 30)
    draw.ellipse(
        [center_x - rx + inner_gap, center_y - ry + inner_gap,
         center_x + rx - inner_gap, center_y + ry - inner_gap],
        outline=(*color, opacity),
        width=max(1, border_width // 2)
    )

    # --- Vẽ ngôi sao 5 cánh ở giữa ---
    if has_star:
        star_size = size // 6
        _draw_star(draw, center_x, center_y, star_size, color, opacity)

    # --- Vẽ text cong theo viền ---
    try:
        # Thử dùng font có sẵn
        font_size = max(10, size // 12)
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/times.ttf",
        ]
        font = None
        for fp in font_paths:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Vẽ text cong phía trên (tên cơ quan)
    _draw_curved_text(draw, org_name.upper(), center_x, center_y,
                      radius - inner_gap - font_size, font, color, opacity,
                      start_angle=210, end_angle=330, clockwise=True)

    # Vẽ text phía dưới (sub_text)
    if sub_text:
        small_font_size = max(8, size // 16)
        try:
            small_font = ImageFont.truetype(font_paths[0] if os.path.exists(font_paths[0]) else font_paths[2], small_font_size)
        except Exception:
            small_font = ImageFont.load_default()
        _draw_curved_text(draw, sub_text, center_x, center_y,
                          radius - inner_gap - small_font_size,
                          small_font, color, opacity,
                          start_angle=150, end_angle=30, clockwise=False)

    # --- Post-processing: Xoay ngẫu nhiên ---
    rotation = random.uniform(*rotation_range)
    img = img.rotate(rotation, resample=Image.BICUBIC, expand=False)

    # Blur nhẹ để giống scan thật
    if blur_amount > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_amount))

    # Crop bỏ padding
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Lưu
    img.save(output_path, 'PNG')
    return img


def _draw_star(draw, cx, cy, size, color, opacity):
    """Vẽ ngôi sao 5 cánh."""
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = size if i % 2 == 0 else size * 0.4
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=(*color, opacity))


def _draw_curved_text(draw, text, cx, cy, radius, font, color, opacity,
                      start_angle=210, end_angle=330, clockwise=True):
    """Vẽ text cong theo đường tròn."""
    if not text:
        return

    if clockwise:
        total_angle = end_angle - start_angle
    else:
        total_angle = start_angle - end_angle

    angle_per_char = total_angle / max(len(text), 1)

    for i, char in enumerate(text):
        if clockwise:
            angle = math.radians(start_angle + i * angle_per_char)
        else:
            angle = math.radians(start_angle - i * angle_per_char)

        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)

        # Tạo ảnh nhỏ cho từng ký tự và xoay
        char_img = Image.new('RGBA', (30, 30), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((5, 5), char, font=font, fill=(*color, opacity))

        # Xoay ký tự theo góc tiếp tuyến
        rot_angle = -math.degrees(angle) - 90 if clockwise else -math.degrees(angle) + 90
        char_img = char_img.rotate(rot_angle, resample=Image.BICUBIC, expand=True)

        # Paste lên canvas chính
        paste_x = int(x - char_img.width // 2)
        paste_y = int(y - char_img.height // 2)
        draw.bitmap((paste_x, paste_y), char_img.split()[-1], fill=(*color, opacity))


def generate_batch_stamps(output_dir, count=200):
    """
    Tạo hàng loạt synthetic stamps với đa dạng cơ quan.

    Tạo stamps đa dạng:
    - Các cơ quan khác nhau (UBND, Bộ, Trường ĐH, Sở, v.v.)
    - Kích thước khác nhau
    - Xoay/blur ngẫu nhiên
    - Cả dạng tròn và oval
    """
    org_names = [
        "ỦY BAN NHÂN DÂN", "BỘ GIÁO DỤC VÀ ĐÀO TẠO", "BỘ CÔNG AN",
        "BỘ TÀI CHÍNH", "BỘ Y TẾ", "BỘ NGOẠI GIAO",
        "TRƯỜNG ĐẠI HỌC BÁCH KHOA", "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ",
        "TRƯỜNG ĐẠI HỌC KHOA HỌC TỰ NHIÊN", "TRƯỜNG ĐẠI HỌC SƯ PHẠM",
        "SỞ GIÁO DỤC VÀ ĐÀO TẠO", "SỞ TÀI CHÍNH",
        "SỞ KẾ HOẠCH VÀ ĐẦU TƯ", "SỞ CÔNG THƯƠNG",
        "CHI CỤC THUẾ", "CỤC THUẾ", "KHO BẠC NHÀ NƯỚC",
        "NGÂN HÀNG NHÀ NƯỚC", "VIỆN KIỂM SÁT NHÂN DÂN",
        "TÒA ÁN NHÂN DÂN", "HỘI ĐỒNG NHÂN DÂN",
        "ĐẢNG ỦY", "CÔNG ĐOÀN", "ĐOÀN THANH NIÊN",
        "TỔNG CỤC HẢI QUAN", "CỤC QUẢN LÝ THỊ TRƯỜNG",
        "BAN QUẢN LÝ DỰ ÁN", "TRUNG TÂM Y TẾ",
        "BỆNH VIỆN ĐA KHOA", "PHÒNG GIÁO DỤC VÀ ĐÀO TẠO",
        "UBND QUẬN", "UBND PHƯỜNG", "UBND HUYỆN", "UBND XÃ",
        "CÔNG TY TNHH", "CÔNG TY CỔ PHẦN",
        "TỔNG CÔNG TY", "TẬP ĐOÀN",
        "CƠ QUAN ĐẢNG", "HỘI LIÊN HIỆP PHỤ NỮ",
    ]

    sub_texts = [
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "ĐỘC LẬP - TỰ DO - HẠNH PHÚC",
        "TỈNH HỒ CHÍ MINH", "THÀNH PHỐ HÀ NỘI",
        "TỈNH BÌNH DƯƠNG", "THÀNH PHỐ ĐÀ NẴNG",
        "TỈNH ĐỒNG NAI", "THÀNH PHỐ CẦN THƠ",
        "", "",  # Một số dấu không có sub_text
    ]

    stamps_generated = []
    for i in range(count):
        org = random.choice(org_names)
        sub = random.choice(sub_texts)
        stamp_type = random.choice(["circle", "circle", "oval"])  # 2/3 tròn
        size = random.randint(180, 320)
        # Màu đỏ với variation nhẹ
        r = random.randint(170, 220)
        g = random.randint(10, 50)
        b = random.randint(10, 50)
        opacity = random.randint(160, 240)
        blur = random.uniform(0.3, 1.2)

        output_path = os.path.join(output_dir, f"stamp_synthetic_{i:04d}.png")
        try:
            create_synthetic_stamp(
                output_path=output_path,
                org_name=org,
                sub_text=sub,
                stamp_type=stamp_type,
                size=size,
                color=(r, g, b),
                has_star=random.random() > 0.1,  # 90% có sao
                rotation_range=(-20, 20),
                blur_amount=blur,
                opacity=opacity
            )
            stamps_generated.append(output_path)
        except Exception as e:
            print(f"  ⚠️ Lỗi tạo stamp {i}: {e}")

        if (i + 1) % 50 == 0:
            print(f"  🔴 Đã tạo {i+1}/{count} stamps")

    print(f"\n✅ Tạo xong {len(stamps_generated)} synthetic stamps tại {output_dir}")
    return stamps_generated


# --- CHẠY TẠO STAMPS ---
# Uncomment để chạy:
# print("🔴 Đang tạo 200 synthetic stamps...")
# stamps = generate_batch_stamps(STAMPS_SYNTHETIC_DIR, count=200)


# ==============================================================================
# CELL 6: CHUYỂN DOCX → IMAGE + OVERLAY STAMP
# ==============================================================================
import zipfile
import xml.etree.ElementTree as ET


def docx_to_text(docx_path):
    """Đọc text từ file docx (không cần python-docx, dùng zipfile)."""
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        paragraphs = []
        for p in tree.findall(f'.//{{{ns}}}p'):
            texts = [t.text for t in p.findall(f'.//{{{ns}}}t') if t.text]
            line = ''.join(texts).strip()
            if line:
                paragraphs.append(line)
        return '\n'.join(paragraphs)
    except Exception as e:
        return f"ERROR: {e}"


def text_to_image(text, output_path, width=2480, min_height=3508, font_size=32, margin=100):
    """
    Render text thành ảnh (giống trang A4 scan).

    Args:
        text: Nội dung văn bản
        output_path: Đường dẫn lưu ảnh
        width: Chiều rộng (2480px = A4 ở 300dpi)
        min_height: Chiều cao tối thiểu
        font_size: Cỡ chữ
        margin: Lề
    """
    # Font
    font = None
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "C:/Windows/Fonts/times.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            font = ImageFont.truetype(fp, font_size)
            break
    if font is None:
        font = ImageFont.load_default()

    # wrap text
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append('')
            continue
        words = paragraph.split()
        current_line = ''
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = font.getbbox(test_line)
            if bbox[2] > width - 2 * margin:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)

    # Tính chiều cao
    line_height = int(font_size * 1.5)
    text_height = len(lines) * line_height + 2 * margin
    height = max(min_height, text_height)

    # Tạo ảnh nền trắng
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Vẽ text
    y = margin
    for line in lines:
        draw.text((margin, y), line, font=font, fill=(0, 0, 0))
        y += line_height

    img.save(output_path, 'PNG')
    return img


def overlay_stamp_on_image(clean_image_path, stamp_path, output_path,
                           position='bottom_right'):
    """
    Overlay con dấu lên ảnh sạch để tạo cặp training data cho GAN.

    Args:
        clean_image_path: Ảnh sạch (không có dấu)
        stamp_path: Ảnh con dấu (RGBA, nền trong suốt)
        output_path: Đường dẫn lưu ảnh có dấu
        position: Vị trí đặt dấu ('bottom_right', 'bottom_center', 'random')
    """
    clean = Image.open(clean_image_path).convert('RGBA')
    stamp = Image.open(stamp_path).convert('RGBA')

    # Resize stamp nếu quá lớn (dấu thường chiếm ~15-25% chiều rộng trang)
    max_stamp_w = int(clean.width * random.uniform(0.12, 0.22))
    scale = max_stamp_w / stamp.width
    new_w = int(stamp.width * scale)
    new_h = int(stamp.height * scale)
    stamp = stamp.resize((new_w, new_h), Image.LANCZOS)

    # Xác định vị trí
    if position == 'bottom_right':
        x = clean.width - new_w - random.randint(50, 200)
        y = clean.height - new_h - random.randint(100, 400)
    elif position == 'bottom_center':
        x = (clean.width - new_w) // 2 + random.randint(-100, 100)
        y = clean.height - new_h - random.randint(100, 400)
    else:  # random
        x = random.randint(clean.width // 3, clean.width - new_w - 50)
        y = random.randint(clean.height // 2, clean.height - new_h - 50)

    x = max(0, min(x, clean.width - new_w))
    y = max(0, min(y, clean.height - new_h))

    # Paste stamp
    clean.paste(stamp, (x, y), stamp)

    # Convert back to RGB for saving
    result = clean.convert('RGB')
    result.save(output_path, 'PNG')
    return output_path


def create_training_pairs(docx_dir, stamps_dir, clean_output_dir,
                          stamped_output_dir, limit=None):
    """
    Tạo cặp training data {ảnh sạch} ↔ {ảnh có stamp} từ docx files.

    Pipeline: docx → text → clean_image → stamped_image
    """
    # Lấy danh sách stamps
    stamp_files = [
        os.path.join(stamps_dir, f)
        for f in os.listdir(stamps_dir)
        if f.endswith('.png')
    ]
    if not stamp_files:
        print("⚠️ Không tìm thấy stamp files! Hãy chạy generate_batch_stamps trước.")
        return

    # Lấy danh sách docx
    docx_files = []
    for category in os.listdir(docx_dir):
        cat_dir = os.path.join(docx_dir, category)
        if os.path.isdir(cat_dir):
            for f in os.listdir(cat_dir):
                if f.endswith('.docx'):
                    docx_files.append((os.path.join(cat_dir, f), category))

    if limit:
        docx_files = docx_files[:limit]

    pairs_created = 0
    for docx_path, category in docx_files:
        filename = os.path.splitext(os.path.basename(docx_path))[0]

        # 1. Đọc text
        text = docx_to_text(docx_path)
        if text.startswith("ERROR") or len(text) < 50:
            continue

        # 2. Tạo clean image
        clean_path = os.path.join(clean_output_dir, f"{category}_{filename}.png")
        text_to_image(text, clean_path)

        # 3. Overlay stamp ngẫu nhiên
        stamp_path = random.choice(stamp_files)
        stamped_path = os.path.join(stamped_output_dir, f"{category}_{filename}.png")
        position = random.choice(['bottom_right', 'bottom_center', 'random'])
        overlay_stamp_on_image(clean_path, stamp_path, stamped_path, position)

        pairs_created += 1
        if pairs_created % 100 == 0:
            print(f"  📝 Đã tạo {pairs_created} cặp training data")

    print(f"\n✅ Tạo xong {pairs_created} cặp training data")
    print(f"   Clean images: {clean_output_dir}")
    print(f"   Stamped images: {stamped_output_dir}")


# --- CHẠY TẠO TRAINING PAIRS ---
# Uncomment để chạy:
# print("📝 Đang tạo training pairs...")
# create_training_pairs(
#     RAW_DOCX_DIR, STAMPS_SYNTHETIC_DIR,
#     CLEAN_IMAGES_DIR, STAMPED_IMAGES_DIR,
#     limit=500  # Bắt đầu với 500 cặp
# )


# ==============================================================================
# CELL 7: TẠO LLM TRAINING DATASET
# ==============================================================================
import json
import re


def extract_metadata_from_docx(docx_path, category):
    """
    Trích xuất metadata từ file docx để tạo training labels cho LLM.

    Sử dụng regex patterns để tìm:
    - Số hiệu văn bản
    - Ngày ban hành
    - Trích yếu
    - Người ký
    - Cơ quan ban hành

    Args:
        docx_path: Đường dẫn file docx
        category: Loại văn bản (CV, HD, QD, TT, K)
    Returns:
        dict chứa metadata đã trích xuất
    """
    text = docx_to_text(docx_path)
    if text.startswith("ERROR"):
        return None

    # Map category codes
    category_map = {
        'CV': 'Công văn',
        'HD': 'Hợp đồng',
        'QD': 'Quy định',
        'TT': 'Tờ trình',
        'K': 'Khác'
    }

    metadata = {
        "loai_van_ban": category_map.get(category, "Khác"),
        "so_hieu": "",
        "ngay_ban_hanh": "",
        "trich_yeu": "",
        "nguoi_ky": "",
        "co_quan_ban_hanh": "",
    }

    # --- Regex patterns cho văn bản hành chính tiếng Việt ---

    # Số hiệu: "Số: 123/QĐ-UBND" hoặc "Số: 456/2024/NQ-HĐND"
    so_hieu_patterns = [
        r'[Ss]ố[:\s]+(\d+[\/-][A-ZĐa-zđ\d\/-]+)',
        r'[Ss]ố[:\s]+(\d+\/\d+\/[A-ZĐ\-]+)',
    ]
    for pattern in so_hieu_patterns:
        match = re.search(pattern, text)
        if match:
            metadata["so_hieu"] = match.group(1).strip()
            break

    # Ngày ban hành: "ngày 15 tháng 3 năm 2024" hoặc "15/03/2024"
    date_patterns = [
        r'[Nn]gày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
        r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            if len(match.groups()) == 3:
                d, m, y = match.groups()
                metadata["ngay_ban_hanh"] = f"{d.zfill(2)}/{m.zfill(2)}/{y}"
            break

    # Trích yếu: thường nằm sau "V/v:" hoặc dòng in đậm đầu tiên
    trich_yeu_patterns = [
        r'[Vv]\/[Vv][:\s]+(.+?)(?:\n|$)',
        r'[Tt]rích yếu[:\s]+(.+?)(?:\n|$)',
    ]
    for pattern in trich_yeu_patterns:
        match = re.search(pattern, text)
        if match:
            metadata["trich_yeu"] = match.group(1).strip()[:200]
            break

    # Người ký: thường ở cuối văn bản, sau chức vụ
    lines = text.strip().split('\n')
    for line in reversed(lines[-10:]):
        line = line.strip()
        if line and len(line) < 50 and not any(c.isdigit() for c in line):
            if any(kw in line.lower() for kw in ['giám đốc', 'trưởng', 'chủ tịch',
                                                   'phó', 'thứ trưởng', 'bộ trưởng']):
                continue  # Đây là chức vụ, người ký ở dòng tiếp
            # Tên người Việt: 2-4 từ, viết hoa
            words = line.split()
            if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w):
                metadata["nguoi_ky"] = line
                break

    return metadata


def build_llm_instruction_dataset(docx_dir, output_dir, limit=None):
    """
    Tạo instruction-following dataset cho LLM fine-tuning.

    Format: Alpaca-style
    {
        "instruction": "Hãy trích xuất thông tin từ văn bản hành chính sau...",
        "input": "<nội_dung_văn_bản>",
        "output": "<json_kết_quả>"
    }
    """
    dataset = []

    # Đếm file
    all_files = []
    for category in os.listdir(docx_dir):
        cat_dir = os.path.join(docx_dir, category)
        if os.path.isdir(cat_dir):
            for f in sorted(os.listdir(cat_dir)):
                if f.endswith('.docx'):
                    all_files.append((os.path.join(cat_dir, f), category))

    if limit:
        all_files = all_files[:limit]

    # --- Task 1: Document Classification ---
    classification_instruction = (
        "Bạn là chuyên gia phân loại văn bản hành chính Việt Nam. "
        "Hãy phân loại văn bản sau vào một trong các loại: "
        "Công văn, Hợp đồng, Quy định, Tờ trình, Khác. "
        "Chỉ trả lời tên loại văn bản, không giải thích thêm."
    )

    # --- Task 2: Key Information Extraction ---
    extraction_instruction = (
        "Bạn là chuyên gia trích xuất thông tin từ văn bản hành chính Việt Nam. "
        "Hãy đọc văn bản sau và trích xuất các thông tin theo định dạng JSON:\n"
        "{\n"
        '  "loai_van_ban": "<Công văn|Hợp đồng|Quy định|Tờ trình|Khác>",\n'
        '  "so_hieu": "<số hiệu văn bản>",\n'
        '  "ngay_ban_hanh": "<DD/MM/YYYY>",\n'
        '  "co_quan_ban_hanh": "<tên cơ quan>",\n'
        '  "trich_yeu": "<trích yếu nội dung>",\n'
        '  "nguoi_ky": "<họ tên người ký>"\n'
        "}\n"
        "Nếu không tìm thấy thông tin, để trống (\"\")."
    )

    category_map = {'CV': 'Công văn', 'HD': 'Hợp đồng', 'QD': 'Quy định',
                    'TT': 'Tờ trình', 'K': 'Khác'}

    for i, (docx_path, category) in enumerate(all_files):
        text = docx_to_text(docx_path)
        if text.startswith("ERROR") or len(text) < 30:
            continue

        # Truncate nếu quá dài (Qwen context ~4096 tokens)
        if len(text) > 3000:
            text = text[:3000] + "\n[...văn bản bị cắt bớt...]"

        # Task 1: Classification samples
        dataset.append({
            "instruction": classification_instruction,
            "input": text,
            "output": category_map.get(category, "Khác")
        })

        # Task 2: Extraction samples
        metadata = extract_metadata_from_docx(docx_path, category)
        if metadata:
            dataset.append({
                "instruction": extraction_instruction,
                "input": text,
                "output": json.dumps(metadata, ensure_ascii=False, indent=2)
            })

        if (i + 1) % 200 == 0:
            print(f"  📊 Đã xử lý {i+1}/{len(all_files)} files, "
                  f"tạo {len(dataset)} samples")

    # Split train/val/test (80/10/10)
    random.shuffle(dataset)
    n = len(dataset)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)

    splits = {
        'train': dataset[:train_end],
        'val': dataset[train_end:val_end],
        'test': dataset[val_end:]
    }

    for split_name, split_data in splits.items():
        output_path = os.path.join(output_dir, f"{split_name}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(split_data, f, ensure_ascii=False, indent=2)
        print(f"  💾 {split_name}: {len(split_data)} samples → {output_path}")

    print(f"\n✅ Tổng cộng tạo {len(dataset)} training samples")
    return dataset


# --- CHẠY TẠO DATASET ---
# Uncomment để chạy:
# print("📊 Đang tạo LLM training dataset...")
# dataset = build_llm_instruction_dataset(RAW_DOCX_DIR, LLM_TRAINING_DIR)


# ==============================================================================
# CELL 8: THỐNG KÊ VÀ KIỂM TRA
# ==============================================================================
def verify_data_preparation():
    """Kiểm tra kết quả chuẩn bị dữ liệu."""
    print("=" * 60)
    print("📊 THỐNG KÊ DỮ LIỆU")
    print("=" * 60)

    # Stamps
    if os.path.exists(STAMPS_EXTRACTED_DIR):
        extracted = len([f for f in os.listdir(STAMPS_EXTRACTED_DIR) if f.endswith('.png')])
        print(f"🔴 Stamps trích xuất từ PDF: {extracted}")

    if os.path.exists(STAMPS_SYNTHETIC_DIR):
        synthetic = len([f for f in os.listdir(STAMPS_SYNTHETIC_DIR) if f.endswith('.png')])
        print(f"🔴 Stamps synthetic: {synthetic}")

    # Training pairs
    if os.path.exists(CLEAN_IMAGES_DIR):
        clean = len([f for f in os.listdir(CLEAN_IMAGES_DIR) if f.endswith('.png')])
        print(f"📄 Clean images: {clean}")

    if os.path.exists(STAMPED_IMAGES_DIR):
        stamped = len([f for f in os.listdir(STAMPED_IMAGES_DIR) if f.endswith('.png')])
        print(f"📄 Stamped images: {stamped}")

    # LLM dataset
    if os.path.exists(LLM_TRAINING_DIR):
        for split in ['train', 'val', 'test']:
            path = os.path.join(LLM_TRAINING_DIR, f"{split}.json")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"🧠 LLM {split} set: {len(data)} samples")

    print("=" * 60)


# --- CHẠY KIỂM TRA ---
# verify_data_preparation()


# ==============================================================================
# CELL 9: DEMO - CHẠY THỬ TỪNG BƯỚC
# ==============================================================================
if __name__ == '__main__':
    print("🚀 OCR-LLM Research - Phase 1: Data Preparation")
    print("=" * 60)
    print()
    print("Hãy uncomment và chạy từng Cell theo thứ tự:")
    print("  1. Cell 1: Cài đặt packages (Colab)")
    print("  2. Cell 2: Mount Google Drive (Colab)")
    print("  3. Cell 3: Cấu hình đường dẫn")
    print("  4. Cell 4: Trích xuất stamps từ 150 PDFs")
    print("  5. Cell 5: Tạo 200 synthetic stamps")
    print("  6. Cell 6: Tạo training pairs (docx → image + stamp)")
    print("  7. Cell 7: Tạo LLM training dataset")
    print("  8. Cell 8: Kiểm tra kết quả")
