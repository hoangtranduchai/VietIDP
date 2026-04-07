# -*- coding: utf-8 -*-
"""
Synthetic Stamp Generator
==========================
Tạo con dấu giả lập (dấu tròn/oval đỏ) cho data augmentation.

Nguồn: Phase1_Data_Preparation.py, line 205-454
"""

import os
import math
import random

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from src.config import Config


def create_synthetic_stamp(
    output_path: str,
    org_name: str = "CƠ QUAN BAN HÀNH",
    sub_text: str = "Số: ___/QĐ-UBND",
    stamp_type: str = "circle",
    size: int = 250,
    color: tuple = (200, 30, 30),
    has_star: bool = True,
    rotation_range: tuple = (-15, 15),
    blur_amount: float = 0.5,
    opacity: int = 200,
) -> Image.Image:
    """
    Tạo con dấu giả lập bằng PIL.

    Returns:
        PIL Image (RGBA)
    """
    canvas_size = int(size * 1.5)
    img = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center_x = canvas_size // 2
    center_y = canvas_size // 2
    radius = size // 2

    border_width = max(3, size // 40)
    if stamp_type == "oval":
        rx, ry = radius, int(radius * 0.75)
    else:
        rx, ry = radius, radius

    # Viền ngoài
    draw.ellipse(
        [center_x - rx, center_y - ry, center_x + rx, center_y + ry],
        outline=(*color, opacity), width=border_width
    )
    # Viền trong
    inner_gap = max(4, size // 30)
    draw.ellipse(
        [center_x - rx + inner_gap, center_y - ry + inner_gap,
         center_x + rx - inner_gap, center_y + ry - inner_gap],
        outline=(*color, opacity), width=max(1, border_width // 2)
    )

    # Ngôi sao
    if has_star:
        _draw_star(draw, center_x, center_y, size // 6, color, opacity)

    # Font
    font_size = max(10, size // 12)
    font = _get_font(font_size)

    # Text cong phía trên
    _draw_curved_text(
        draw, org_name.upper(), center_x, center_y,
        radius - inner_gap - font_size, font, color, opacity,
        start_angle=210, end_angle=330, clockwise=True
    )

    # Text phía dưới
    if sub_text:
        small_font = _get_font(max(8, size // 16))
        _draw_curved_text(
            draw, sub_text, center_x, center_y,
            radius - inner_gap - max(8, size // 16),
            small_font, color, opacity,
            start_angle=150, end_angle=30, clockwise=False
        )

    # Post-processing
    rotation = random.uniform(*rotation_range)
    img = img.rotate(rotation, resample=Image.BICUBIC, expand=False)

    if blur_amount > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_amount))

    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG')
    return img


def _get_font(size: int):
    """Load font với fallback."""
    font_path = Config.get_font()
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()


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

    total_angle = (end_angle - start_angle) if clockwise else (start_angle - end_angle)
    angle_per_char = total_angle / max(len(text), 1)

    for i, char in enumerate(text):
        if clockwise:
            angle = math.radians(start_angle + i * angle_per_char)
        else:
            angle = math.radians(start_angle - i * angle_per_char)

        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)

        char_img = Image.new('RGBA', (30, 30), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((5, 5), char, font=font, fill=(*color, opacity))

        rot_angle = -math.degrees(angle) - 90 if clockwise else -math.degrees(angle) + 90
        char_img = char_img.rotate(rot_angle, resample=Image.BICUBIC, expand=True)

        paste_x = int(x - char_img.width // 2)
        paste_y = int(y - char_img.height // 2)
        draw.bitmap((paste_x, paste_y), char_img.split()[-1], fill=(*color, opacity))


# ═══════════════════════════════════════════════════════════════════════════
# Batch Generation
# ═══════════════════════════════════════════════════════════════════════════

ORG_NAMES = [
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

SUB_TEXTS = [
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
    "ĐỘC LẬP - TỰ DO - HẠNH PHÚC",
    "TỈNH HỒ CHÍ MINH", "THÀNH PHỐ HÀ NỘI",
    "TỈNH BÌNH DƯƠNG", "THÀNH PHỐ ĐÀ NẴNG",
    "TỈNH ĐỒNG NAI", "THÀNH PHỐ CẦN THƠ",
    "", "",
]


def generate_batch_stamps(output_dir: str, count: int = 200) -> list:
    """Tạo hàng loạt synthetic stamps."""
    os.makedirs(output_dir, exist_ok=True)
    stamps_generated = []

    for i in range(count):
        org = random.choice(ORG_NAMES)
        sub = random.choice(SUB_TEXTS)
        stamp_type = random.choice(["circle", "circle", "oval"])
        size = random.randint(180, 320)
        r = random.randint(170, 220)
        g = random.randint(10, 50)
        b = random.randint(10, 50)
        output_path = os.path.join(output_dir, f"stamp_synthetic_{i:04d}.png")

        try:
            create_synthetic_stamp(
                output_path=output_path, org_name=org, sub_text=sub,
                stamp_type=stamp_type, size=size, color=(r, g, b),
                has_star=random.random() > 0.1,
                rotation_range=(-20, 20),
                blur_amount=random.uniform(0.3, 1.2),
                opacity=random.randint(160, 240),
            )
            stamps_generated.append(output_path)
        except Exception as e:
            print(f"  ⚠️ Lỗi stamp {i}: {e}")

        if (i + 1) % 50 == 0:
            print(f"  🔴 Đã tạo {i+1}/{count} stamps")

    print(f"\n✅ Tạo xong {len(stamps_generated)} synthetic stamps")
    return stamps_generated
