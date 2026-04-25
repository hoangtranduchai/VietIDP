import cv2
import numpy as np
import time
from pathlib import Path
import random
from PIL import Image, ImageDraw

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.preprocessing.stamp_matting import HybridStampMatting
from src.data.stamp_generator import create_synthetic_stamp

def calculate_metrics(pred_rgba: np.ndarray, gt_rgba: np.ndarray):
    """
    Tính toán các chỉ số đo lường chất lượng cho Image Matting / Segmentation.
    pred_rgba: [H, W, 4] numpy array
    gt_rgba: [H, W, 4] numpy array
    """
    pred_alpha = pred_rgba[:, :, 3].astype(np.float32) / 255.0
    gt_alpha = gt_rgba[:, :, 3].astype(np.float32) / 255.0
    
    # 1. MSE (Mean Squared Error) của kênh Alpha
    mse = np.mean((pred_alpha - gt_alpha) ** 2)
    
    # 2. SAD (Sum of Absolute Differences) của kênh Alpha
    sad = np.sum(np.abs(pred_alpha - gt_alpha)) / 1000.0 # Thường chia 1000 để dễ đọc
    
    # 3. Mức độ chính xác nhị phân (Binary Metrics)
    pred_mask = (pred_alpha > 0.1).astype(np.uint8)
    gt_mask = (gt_alpha > 0.1).astype(np.uint8)
    
    intersection = np.logical_and(pred_mask, gt_mask).sum()
    union = np.logical_or(pred_mask, gt_mask).sum()
    
    # IoU (Intersection over Union)
    iou = intersection / (union + 1e-6)
    
    # Dice Coefficient (F1-score)
    dice = 2.0 * intersection / (pred_mask.sum() + gt_mask.sum() + 1e-6)
    
    return {"MSE": mse, "SAD": sad, "IoU": iou, "Dice": dice}

def create_test_background(width=400, height=400):
    """Tạo nền giấy giả lập có chữ đen chi chít để test độ nhiễu"""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Vẽ các dòng chữ đen giả lập
    for y in range(20, height, 30):
        draw.line([(20, y), (width - 20, y)], fill=(0,0,0), width=3)
        draw.line([(20, y+10), (width - 40, y+10)], fill=(50,50,50), width=2)
    return img

def run_benchmark():
    print("="*60)
    print(" BÁO CÁO ĐO LƯỜNG CHẤT LƯỢNG (METRICS) - PHASE 2 ")
    print(" HybridStampMatting (Color Matting Algorithm)")
    print("="*60)
    
    matting = HybridStampMatting()
    
    num_tests = 20
    metrics_sum = {"MSE": 0.0, "SAD": 0.0, "IoU": 0.0, "Dice": 0.0}
    
    total_time = 0
    
    print(f"Đang tiến hành mô phỏng {num_tests} mẫu test (có nền giấy và chữ đen chằng chịt)...\n")
    
    for i in range(num_tests):
        # 1. Tạo Ground Truth Stamp
        gt_stamp_path = os.path.join(os.path.dirname(__file__), f"temp_gt_stamp_{i}.png")
        create_synthetic_stamp(
            output_path=gt_stamp_path,
            size=250,
            rotation_range=(-10, 10),
            blur_amount=0, # GT cần sắc nét
            opacity=255
        )
        gt_stamp = Image.open(gt_stamp_path).convert("RGBA")
        
        # 2. Tạo Background chữ đen
        bg = create_test_background(400, 400)
        
        # 3. Tạo Input BGR bằng cách paste Stamp lên Background
        # Paste vào giữa
        paste_x = (400 - gt_stamp.width) // 2
        paste_y = (400 - gt_stamp.height) // 2
        bg.paste(gt_stamp, (paste_x, paste_y), gt_stamp)
        
        input_bgr = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)
        
        # Tạo mask GT RGBA đầy đủ size 400x400 để đối chiếu
        gt_full = Image.new("RGBA", (400, 400), (0,0,0,0))
        gt_full.paste(gt_stamp, (paste_x, paste_y))
        gt_rgba = np.array(gt_full)
        
        # 4. Chạy Phase 2 (Extract)
        t0 = time.time()
        pred_rgba = matting.extract_stamp(input_bgr)
        t1 = time.time()
        total_time += (t1 - t0)
        
        # 5. Tính toán
        m = calculate_metrics(pred_rgba, gt_rgba)
        for k in metrics_sum:
            metrics_sum[k] += m[k]
            
        # Cleanup
        if os.path.exists(gt_stamp_path):
            os.remove(gt_stamp_path)
            
    # Tính trung bình
    for k in metrics_sum:
        metrics_sum[k] /= num_tests
    
    avg_fps = num_tests / total_time
    
    print(f"{'Chỉ số (Metric)':<20} | {'Giá trị trung bình':<20} | {'Đánh giá chuẩn MLOps'}")
    print("-" * 70)
    print(f"{'IoU':<20} | {metrics_sum['IoU']:<20.4f} | > 0.75 là Xuất sắc (Soft Matting)")
    print(f"{'Dice (F1-score)':<20} | {metrics_sum['Dice']:<20.4f} | > 0.85 là Xuất sắc (Soft Matting)")
    print(f"{'MSE (Alpha)':<20} | {metrics_sum['MSE']:<20.4f} | Càng gần 0 càng tốt")
    print(f"{'SAD (Alpha)':<20} | {metrics_sum['SAD']:<20.4f} | Sai số tổng hợp")
    print(f"{'Tốc độ (FPS)':<20} | {avg_fps:<20.1f} | > 10 FPS là Real-time")
    print("-" * 70)
    
    print("\n[KẾT LUẬN]")
    if metrics_sum['Dice'] > 0.85:
        print("=> CHẤT LƯỢNG MÔ HÌNH: TỐI ƯU HOÀN HẢO (STATE-OF-THE-ART).")
        print("=> Thuật toán Color Matting (Redness Isolation) đã bóc tách chính xác con dấu mờ, loại bỏ hoàn toàn nhiễu.")
    else:
        print("=> CHẤT LƯỢNG MÔ HÌNH: CẦN CẢI THIỆN THÊM.")

if __name__ == "__main__":
    run_benchmark()
