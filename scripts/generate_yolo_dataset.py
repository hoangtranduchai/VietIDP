import os
import cv2
import numpy as np
import random
from pathlib import Path
import yaml
from tqdm import tqdm

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN MLOps
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
STAMPS_DIR = BASE_DIR / "data" / "interim" / "stamps_transparent"
BG_TEXT_DIR = BASE_DIR / "data" / "processed" / "clean_images"  # 2200 Ảnh A4 sạch
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "yolo_dataset"

# Số lượng dữ liệu YOLO cần sinh
NUM_IMAGES = 10000


# ==========================================
# AUGMENTATION FUNCTIONS
# Tất cả chỉ dùng cv2 + numpy, không thêm thư viện mới.
# Dựa trên phân tích gap từ Nghị định 30/2020/NĐ-CP
# và tài liệu nghiên cứu Gemini Research.
# ==========================================

def aug_gaussian_noise(img, intensity=None):
    """Mô phỏng nhiễu hạt từ scanner/camera kém chất lượng."""
    if intensity is None:
        intensity = random.uniform(5, 25)
    noise = np.random.normal(0, intensity, img.shape).astype(np.float32)
    noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy


def aug_motion_blur(img):
    """Mô phỏng rung tay khi scan/chụp."""
    size = random.choice([3, 5, 7])
    angle = random.uniform(0, 180)
    kernel = np.zeros((size, size))
    kernel[size // 2, :] = 1.0 / size
    M = cv2.getRotationMatrix2D((size / 2, size / 2), angle, 1.0)
    kernel = cv2.warpAffine(kernel, M, (size, size))
    kernel = kernel / kernel.sum() if kernel.sum() > 0 else kernel
    return cv2.filter2D(img, -1, kernel)


def aug_jpeg_artifact(img, quality=None):
    """Mô phỏng nén JPEG chất lượng thấp (real-world compression)."""
    if quality is None:
        quality = random.randint(15, 50)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, enc = cv2.imencode('.jpg', img, encode_param)
    return cv2.imdecode(enc, cv2.IMREAD_COLOR)


def aug_document_aging(img):
    """Mô phỏng giấy ố vàng, cũ kỹ."""
    # Thêm tint vàng nhạt lên toàn ảnh
    yellow_strength = random.uniform(0.05, 0.20)
    overlay = np.full_like(img, [180, 220, 245], dtype=np.uint8)  # BGR yellowish
    aged = cv2.addWeighted(img, 1.0 - yellow_strength, overlay, yellow_strength, 0)

    # Thêm vài đốm ẩm mốc ngẫu nhiên (stain circles)
    if random.random() < 0.4:
        for _ in range(random.randint(1, 3)):
            h, w = aged.shape[:2]
            cx, cy = random.randint(0, w), random.randint(0, h)
            radius = random.randint(20, min(h, w) // 8)
            stain_color = (
                random.randint(150, 200),  # B
                random.randint(180, 220),  # G
                random.randint(200, 240),  # R
            )
            stain = np.full_like(aged, stain_color, dtype=np.uint8)
            mask = np.zeros((h, w), dtype=np.float32)
            cv2.circle(mask, (cx, cy), radius, 1.0, -1)
            mask = cv2.GaussianBlur(mask, (radius * 2 + 1, radius * 2 + 1), radius // 2)
            mask = mask[:, :, np.newaxis]
            alpha_stain = random.uniform(0.1, 0.3)
            aged = np.clip(
                aged.astype(np.float32) * (1 - mask * alpha_stain) +
                stain.astype(np.float32) * mask * alpha_stain,
                0, 255
            ).astype(np.uint8)
    return aged


def aug_stamp_color_jitter(stamp):
    """Biến đổi màu con dấu: đỏ tươi → đỏ sẫm, tím, cam, xanh, phai."""
    hsv = cv2.cvtColor(stamp[:, :, :3], cv2.COLOR_BGR2HSV).astype(np.float32)

    # Hue shift: mô phỏng dấu đỏ, tím, cam, xanh
    hue_shift = random.uniform(-25, 25)
    hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180

    # Saturation jitter: mô phỏng mực phai
    sat_factor = random.uniform(0.5, 1.3)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_factor, 0, 255)

    # Value jitter: sáng/tối
    val_factor = random.uniform(0.7, 1.2)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * val_factor, 0, 255)

    bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    result = stamp.copy()
    result[:, :, :3] = bgr
    return result


def aug_brightness_contrast(img, alpha=None, beta=None):
    """Biến đổi độ sáng và tương phản (mô phỏng photocopy, đèn flash)."""
    if alpha is None:
        alpha = random.uniform(0.6, 1.4)  # Contrast
    if beta is None:
        beta = random.randint(-40, 40)     # Brightness
    return np.clip(img.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)


def aug_document_skew(img, bboxes_list):
    """
    Xoay toàn trang 1-5° (mô phỏng scan nghiêng).
    Phải cập nhật lại tọa độ bbox.
    Trả về (img_rotated, updated_bboxes).
    """
    h, w = img.shape[:2]
    angle = random.uniform(-5, 5)
    if abs(angle) < 0.5:
        return img, bboxes_list  # Quá nhỏ, bỏ qua

    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Tính kích thước mới để không cắt mất góc
    cos_a = abs(M[0, 0])
    sin_a = abs(M[0, 1])
    new_w = int(h * sin_a + w * cos_a)
    new_h = int(h * cos_a + w * sin_a)
    M[0, 2] += (new_w - w) / 2
    M[1, 2] += (new_h - h) / 2

    rotated = cv2.warpAffine(img, M, (new_w, new_h),
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(255, 255, 255))

    # Cập nhật bboxes
    updated = []
    for bbox_str in bboxes_list:
        parts = bbox_str.split()
        cls_id = parts[0]
        xc, yc, bw, bh = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])

        # Denormalize về pixel coords gốc
        px = xc * w
        py = yc * h

        # Áp dụng rotation transform
        new_px = M[0, 0] * px + M[0, 1] * py + M[0, 2]
        new_py = M[1, 0] * px + M[1, 1] * py + M[1, 2]

        # Normalize lại theo kích thước mới
        new_xc = new_px / new_w
        new_yc = new_py / new_h
        new_bw = bw * w / new_w
        new_bh = bh * h / new_h

        # Clamp
        new_xc = max(0.001, min(0.999, new_xc))
        new_yc = max(0.001, min(0.999, new_yc))
        new_bw = max(0.001, min(0.999, new_bw))
        new_bh = max(0.001, min(0.999, new_bh))

        updated.append(f"{cls_id} {new_xc:.6f} {new_yc:.6f} {new_bw:.6f} {new_bh:.6f}")

    return rotated, updated


def aug_resolution_variation(img):
    """Mô phỏng ảnh scan DPI thấp hoặc ảnh chụp điện thoại."""
    h, w = img.shape[:2]
    scale = random.uniform(0.3, 0.7)  # Giảm xuống rồi phóng lại
    small = cv2.resize(img, (max(int(w * scale), 10), max(int(h * scale), 10)),
                        interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


# ==========================================
# CORE FUNCTIONS
# ==========================================

def create_yolo_structure():
    """Tạo kiến trúc thư mục chuẩn Ultralytics YOLOv8"""
    for folder in ['images/train', 'images/val', 'images/test',
                    'labels/train', 'labels/val', 'labels/test']:
        (OUTPUT_DIR / folder).mkdir(parents=True, exist_ok=True)

    yaml_config = {
        'path': str(OUTPUT_DIR.resolve()),
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'names': {0: 'stamp'}
    }
    with open(OUTPUT_DIR / 'dataset.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(yaml_config, f, sort_keys=False)

    print(f"[OK] Da tao cau truc YOLO tai: {OUTPUT_DIR}")


def augment_stamp(stamp, bg_width, bg_height):
    """
    Scale con dấu theo tỷ lệ trang A4 để bám sát thực tế.
    Một con dấu thật đường kính khoảng 3.5cm -> 4.5cm.
    Trang A4 ngang 21cm -> con dấu chiếm khoảng 13% - 28% chiều ngang.
    """
    target_width_ratio = random.uniform(0.13, 0.28)
    target_w = int(bg_width * target_width_ratio)

    current_h, current_w = stamp.shape[:2]
    scale = target_w / max(current_w, 1)

    new_w = max(int(current_w * scale), 10)
    new_h = max(int(current_h * scale), 10)

    stamp_resized = cv2.resize(stamp, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Xoay ngẫu nhiên
    angle = random.uniform(-15, 15)
    center = (new_w // 2, new_h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    stamp_rotated = cv2.warpAffine(stamp_resized, M, (new_w, new_h),
                                    borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))

    # 40% áp dụng color jitter cho stamp
    if random.random() < 0.40:
        stamp_rotated = aug_stamp_color_jitter(stamp_rotated)

    return stamp_rotated


def overlay_stamp_and_get_bbox(background, stamp, allow_partial_edge=False):
    """
    Dán dấu lên nền A4 và BÁO LẠI tọa độ YOLO.
    Quy tắc: 70% nửa dưới phải (ô số 7-8), 30% random.
    allow_partial_edge: cho phép stamp bị cắt viền (mô phỏng scan).
    """
    bg_h, bg_w = background.shape[:2]
    st_h, st_w = stamp.shape[:2]

    if st_h >= bg_h - 20 or st_w >= bg_w - 20:
        return background, None

    margin = 10 if allow_partial_edge else 50

    if allow_partial_edge and random.random() < 0.5:
        # Đặt stamp ở mép: trái/phải/trên/dưới
        edge = random.choice(['left', 'right', 'top', 'bottom'])
        if edge == 'left':
            x_offset = random.randint(-st_w // 3, margin)
            y_offset = random.randint(margin, bg_h - st_h - margin)
        elif edge == 'right':
            x_offset = random.randint(bg_w - st_w - margin, bg_w - st_w // 2)
            y_offset = random.randint(margin, bg_h - st_h - margin)
        elif edge == 'top':
            x_offset = random.randint(margin, bg_w - st_w - margin)
            y_offset = random.randint(-st_h // 3, margin)
        else:  # bottom
            x_offset = random.randint(margin, bg_w - st_w - margin)
            y_offset = random.randint(bg_h - st_h - margin, bg_h - st_h // 2)
    else:
        # Vị trí tiêu chuẩn
        if random.random() < 0.7:  # 70% vị trí ô 7-8 (nửa dưới phải)
            y_offset = random.randint(int(bg_h * 0.5), max(int(bg_h * 0.5) + 1, bg_h - st_h - 50))
            x_offset = random.randint(int(bg_w * 0.3), max(int(bg_w * 0.3) + 1, bg_w - st_w - 50))
        else:  # 30% random
            y_offset = random.randint(50, max(51, bg_h - st_h - 50))
            x_offset = random.randint(50, max(51, bg_w - st_w - 50))

    # Tính vùng overlap thực tế (crop nếu stamp ra ngoài viền)
    src_y_start = max(0, -y_offset)
    src_x_start = max(0, -x_offset)
    src_y_end = min(st_h, bg_h - y_offset)
    src_x_end = min(st_w, bg_w - x_offset)

    dst_y_start = max(0, y_offset)
    dst_x_start = max(0, x_offset)
    dst_y_end = dst_y_start + (src_y_end - src_y_start)
    dst_x_end = dst_x_start + (src_x_end - src_x_start)

    if src_y_end <= src_y_start or src_x_end <= src_x_start:
        return background, None

    stamp_crop = stamp[src_y_start:src_y_end, src_x_start:src_x_end]

    # Opacity: 10% ultra-faded (0.25-0.50), 90% normal (0.65-0.95)
    if random.random() < 0.10:
        opacity = random.uniform(0.25, 0.50)
    else:
        opacity = random.uniform(0.65, 0.95)

    alpha_s = (stamp_crop[:, :, 3] / 255.0) * opacity
    alpha_l = 1.0 - alpha_s

    result = background.copy()
    for c in range(3):
        result[dst_y_start:dst_y_end, dst_x_start:dst_x_end, c] = (
            stamp_crop[:, :, c] * alpha_s +
            result[dst_y_start:dst_y_end, dst_x_start:dst_x_end, c] * alpha_l
        )

    # Bounding box từ visible alpha pixels
    alpha_visible = stamp_crop[:, :, 3]
    coords = cv2.findNonZero(alpha_visible)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        real_x = dst_x_start + x
        real_y = dst_y_start + y

        x_center = (real_x + w / 2) / bg_w
        y_center = (real_y + h / 2) / bg_h
        norm_w = w / bg_w
        norm_h = h / bg_h

        x_center = max(0.001, min(0.999, x_center))
        y_center = max(0.001, min(0.999, y_center))
        norm_w = max(0.001, min(0.999, norm_w))
        norm_h = max(0.001, min(0.999, norm_h))

        # Bỏ qua bbox quá nhỏ (< 0.5% diện tích)
        if norm_w * norm_h < 0.00005:
            return result, None

        bbox = f"0 {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}"
        return result, bbox
    else:
        return background, None


def apply_post_augmentations(img, bboxes):
    """
    Áp dụng pipeline augmentation ngẫu nhiên SAU KHI đã dán stamp.
    Mỗi aug được áp dụng RIÊNG LẺ với xác suất nhất định.
    Nhiều aug có thể chồng chéo → tạo tổ hợp thực tế.
    """
    # 1. Scan degradation: noise
    if random.random() < 0.25:
        img = aug_gaussian_noise(img)

    # 2. Motion blur
    if random.random() < 0.15:
        img = aug_motion_blur(img)

    # 3. JPEG compression artifacts
    if random.random() < 0.20:
        img = aug_jpeg_artifact(img)

    # 4. Document aging (yellowish, stains)
    if random.random() < 0.15:
        img = aug_document_aging(img)

    # 5. Brightness/contrast variation
    if random.random() < 0.20:
        img = aug_brightness_contrast(img)

    # 6. Resolution variation (DPI thấp)
    if random.random() < 0.15:
        img = aug_resolution_variation(img)

    # 7. Document skew (rotation toàn trang) — phải cập nhật bbox
    if random.random() < 0.15:
        img, bboxes = aug_document_skew(img, bboxes)

    return img, bboxes


# ==========================================
# MAIN
# ==========================================

def main():
    random.seed(20260505)
    np.random.seed(20260505)

    create_yolo_structure()

    stamp_files = list(STAMPS_DIR.glob("*.png"))
    bg_files = list(BG_TEXT_DIR.glob("*.*"))

    if not stamp_files or not bg_files:
        print("[ERROR] Khong tim thay anh nen A4 hoac con dau.")
        print(f"   Stamps: {STAMPS_DIR} ({len(stamp_files)} files)")
        print(f"   Backgrounds: {BG_TEXT_DIR} ({len(bg_files)} files)")
        return

    print(f"[DATA] {len(stamp_files)} stamps, {len(bg_files)} backgrounds")
    print(f"[START] Sinh {NUM_IMAGES} mau (1-3 stamps/anh + 5% negative)")
    print(f"  Augmentations: noise, blur, JPEG, aging, color_jitter, edge_crop,")
    print(f"  brightness, faded, skew, resolution. Split: 70/15/15")

    success = 0
    stats = {
        '1_stamp': 0, '2_stamps': 0, '3_stamps': 0, 'negative': 0,
        'partial_edge': 0, 'faded': 0, 'aug_applied': 0
    }

    for i in tqdm(range(NUM_IMAGES), desc="Generating YOLO Dataset v2"):
        # Split: 70% train, 15% val, 15% test
        r = random.random()
        if r < 0.70:
            split = 'train'
        elif r < 0.85:
            split = 'val'
        else:
            split = 'test'

        bg_path = random.choice(bg_files)
        bg_img = cv2.imread(str(bg_path))

        if bg_img is None:
            continue

        out_name = f"doc_stamp_{i:06d}"
        all_bboxes = []
        result_img = bg_img.copy()

        # 5% negative samples
        if random.random() < 0.05:
            stats['negative'] += 1
        else:
            # Multi-stamp: 1 (70%), 2 (20%), 3 (10%)
            r2 = random.random()
            if r2 < 0.70:
                num_stamps = 1
            elif r2 < 0.90:
                num_stamps = 2
            else:
                num_stamps = 3

            stats[f'{num_stamps}_stamp{"s" if num_stamps > 1 else ""}'] += 1

            # 8% cho phép stamp bị cắt viền
            allow_edge = random.random() < 0.08
            if allow_edge:
                stats['partial_edge'] += 1

            for _ in range(num_stamps):
                stamp_path = random.choice(stamp_files)
                stamp_img = cv2.imread(str(stamp_path), cv2.IMREAD_UNCHANGED)

                if stamp_img is None or stamp_img.shape[2] != 4:
                    continue

                stamp_aug = augment_stamp(stamp_img, result_img.shape[1], result_img.shape[0])
                result_img, yolo_bbox = overlay_stamp_and_get_bbox(
                    result_img, stamp_aug, allow_partial_edge=allow_edge
                )

                if yolo_bbox:
                    all_bboxes.append(yolo_bbox)

        # Áp dụng post-augmentations (noise, blur, aging, skew, ...)
        result_img, all_bboxes = apply_post_augmentations(result_img, all_bboxes)

        # Lưu ảnh
        img_out_path = OUTPUT_DIR / f"images/{split}/{out_name}.jpg"
        cv2.imwrite(str(img_out_path), result_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

        # Lưu labels
        txt_out_path = OUTPUT_DIR / f"labels/{split}/{out_name}.txt"
        with open(txt_out_path, 'w') as f:
            f.write("\n".join(all_bboxes))

        success += 1

    print(f"\n[DONE] Da sinh {success}/{NUM_IMAGES} mau.")
    print(f"[STATS] 1_stamp={stats['1_stamp']}, 2_stamps={stats['2_stamps']}, "
          f"3_stamps={stats['3_stamps']}, negative={stats['negative']}")
    print(f"[STATS] partial_edge={stats['partial_edge']}")
    print(f"[OUTPUT] {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
