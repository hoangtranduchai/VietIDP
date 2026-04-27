import os
import cv2
import json
import random
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
STAMPS_DIR = BASE_DIR / "data" / "interim" / "stamps_transparent"
if not STAMPS_DIR.exists() or len(list(STAMPS_DIR.glob("*.png"))) == 0:
    STAMPS_DIR = BASE_DIR / "data" / "stamps" / "extracted"

OUT_IMG_DIR = BASE_DIR / "data" / "test"
OUT_LBL_DIR = BASE_DIR / "data" / "test" / "labels"

OUT_IMG_DIR.mkdir(parents=True, exist_ok=True)
OUT_LBL_DIR.mkdir(parents=True, exist_ok=True)

# Fonts
try:
    font_large = ImageFont.truetype("C:/Windows/Fonts/timesbd.ttf", 40)
    font_bold = ImageFont.truetype("C:/Windows/Fonts/timesbd.ttf", 32)
    font_regular = ImageFont.truetype("C:/Windows/Fonts/times.ttf", 30)
    font_italic = ImageFont.truetype("C:/Windows/Fonts/timesi.ttf", 30)
except Exception:
    print("Warning: Times New Roman font not found. Using default.")
    font_large = ImageFont.load_default()
    font_bold = ImageFont.load_default()
    font_regular = ImageFont.load_default()
    font_italic = ImageFont.load_default()

CO_QUAN = ["UBND TỈNH ĐỒNG NAI", "SỞ Y TẾ TP.HCM", "BỘ CÔNG THƯƠNG", "TRƯỜNG ĐH BÁCH KHOA", "CÔNG TY CP VINAMILK", "SỞ GIÁO DỤC VÀ ĐÀO TẠO"]
LOAI_VB = ["QUYẾT ĐỊNH", "THÔNG BÁO", "CHỈ THỊ", "TỜ TRÌNH", "KẾ HOẠCH"]
TRICH_YEU = [
    "Về việc ban hành quy định quản lý dự án đầu tư",
    "Về việc nghỉ lễ Quốc khánh 2/9",
    "Phê duyệt kết quả lựa chọn nhà thầu",
    "Triển khai công tác tuyển sinh năm học mới",
    "Về việc bổ nhiệm cán bộ quản lý",
    "Về việc phê duyệt đề án bảo vệ môi trường"
]
NGUOI_KY_TITLE = ["CHỦ TỊCH", "GIÁM ĐỐC", "HIỆU TRƯỞNG", "BỘ TRƯỞNG", "TỔNG GIÁM ĐỐC"]
NGUOI_KY_NAME = ["Nguyễn Văn A", "Trần Thị B", "Lê Văn C", "Phạm Văn D", "Hoàng Thị E", "Vũ Văn F"]

def generate_document(idx):
    img = Image.new('RGB', (1200, 1600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # 1. Generate Metadata
    co_quan = random.choice(CO_QUAN)
    loai_vb = random.choice(LOAI_VB)
    so_hieu = f"{random.randint(10, 999)}/{'QĐ' if loai_vb == 'QUYẾT ĐỊNH' else 'TB'}-{co_quan.split()[-1]}"
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(2020, 2026)
    ngay_ban_hanh = f"{day:02d}/{month:02d}/{year}"
    ngay_text = f"Ngày {day:02d} tháng {month:02d} năm {year}"
    trich_yeu = random.choice(TRICH_YEU)
    title = random.choice(NGUOI_KY_TITLE)
    name = random.choice(NGUOI_KY_NAME)

    # 2. Draw Text (Basic layout)
    # Header Left (Cơ quan)
    draw.text((150, 100), co_quan, fill=(0,0,0), font=font_bold, anchor="mm")
    draw.text((150, 140), f"Số: {so_hieu}", fill=(0,0,0), font=font_regular, anchor="mm")
    
    # Header Right (Quốc hiệu)
    draw.text((800, 100), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", fill=(0,0,0), font=font_bold, anchor="mm")
    draw.text((800, 140), "Độc lập - Tự do - Hạnh phúc", fill=(0,0,0), font=font_bold, anchor="mm")
    draw.text((800, 180), ngay_text, fill=(0,0,0), font=font_italic, anchor="mm")

    # Title
    draw.text((600, 300), loai_vb, fill=(0,0,0), font=font_large, anchor="mm")
    draw.text((600, 350), trich_yeu, fill=(0,0,0), font=font_bold, anchor="mm")

    # Body
    body_text = "Căn cứ vào Luật Tổ chức chính phủ ngày 19 tháng 6 năm 2015;\n" \
                "Căn cứ vào nghị định số 123/2016/NĐ-CP của Chính phủ;\n" \
                f"Xét đề nghị của Giám đốc Sở Nội vụ và Trưởng phòng Hành chính,\n\n" \
                f"QUYẾT ĐỊNH/THÔNG BÁO:\n\n" \
                f"Điều 1. Phê duyệt {trich_yeu.lower()} đối với các cơ quan, đơn vị trực thuộc.\n" \
                f"Điều 2. Giao cho phòng Tài chính - Kế toán chịu trách nhiệm thi hành.\n" \
                f"Điều 3. Quyết định/Thông báo này có hiệu lực kể từ ngày ký."
    
    y = 450
    for line in body_text.split('\n'):
        draw.text((100, y), line, fill=(0,0,0), font=font_regular)
        y += 40

    # Footer (Signer)
    draw.text((900, y + 100), title, fill=(0,0,0), font=font_bold, anchor="mm")
    draw.text((900, y + 250), name, fill=(0,0,0), font=font_bold, anchor="mm")

    # Convert to OpenCV format (BGR)
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # 3. Add noise (scan effect)
    noise = np.random.normal(0, 5, cv_img.shape).astype(np.uint8)
    cv_img = cv2.add(cv_img, noise)

    # 4. Overlay Stamp
    stamp_files = list(STAMPS_DIR.glob("*.png"))
    if stamp_files:
        stamp_path = random.choice(stamp_files)
        stamp = cv2.imread(str(stamp_path), cv2.IMREAD_UNCHANGED)
        
        if stamp is not None:
            # Resize stamp
            target_w = random.randint(200, 300)
            scale = target_w / max(stamp.shape[1], 1)
            new_h = int(stamp.shape[0] * scale)
            stamp = cv2.resize(stamp, (target_w, new_h))

            # Position over the signature
            x_offset = 900 - target_w // 2 + random.randint(-50, 50)
            y_offset = y + 150 + random.randint(-20, 20)

            # Overlay
            alpha_s = stamp[:, :, 3] / 255.0
            alpha_l = 1.0 - alpha_s
            for c in range(0, 3):
                cv_img[y_offset:y_offset+new_h, x_offset:x_offset+target_w, c] = (
                    alpha_s * stamp[:, :, c] +
                    alpha_l * cv_img[y_offset:y_offset+new_h, x_offset:x_offset+target_w, c]
                )

    # 5. Save File
    filename = f"bench_{idx:03d}.jpg"
    filepath = OUT_IMG_DIR / filename
    cv2.imwrite(str(filepath), cv_img)

    # 6. Save Ground Truth JSON
    full_text = f"{co_quan}\nSố: {so_hieu}\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n{ngay_text}\n{loai_vb}\n{trich_yeu}\n{body_text}\n{title}\n{name}"
    gt_data = {
        "filename": filename,
        "full_text": full_text,
        "extraction": {
            "loai_van_ban": loai_vb.capitalize(),
            "so_hieu": so_hieu,
            "ngay_ban_hanh": ngay_ban_hanh,
            "co_quan_ban_hanh": co_quan,
            "trich_yeu": trich_yeu,
            "nguoi_ky": name
        }
    }
    with open(OUT_LBL_DIR / f"bench_{idx:03d}.json", "w", encoding="utf-8") as f:
        json.dump(gt_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print("[INFO] Starting to generate 100 benchmark files...")
    
    # Xóa file cũ
    for f in OUT_IMG_DIR.glob("bench_*.jpg"):
        f.unlink()
    for f in OUT_LBL_DIR.glob("bench_*.json"):
        f.unlink()

    for i in range(100):
        generate_document(i)
        if (i+1) % 10 == 0:
            print(f"Generated {i+1}/100")
            
    print(f"[SUCCESS] Completed generating 100 files at {OUT_IMG_DIR}")
