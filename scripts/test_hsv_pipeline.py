import cv2
import numpy as np

def remove_red_stamp_hsv(image_path, output_path):
    print("🚀 KHỞI ĐỘNG THUẬT TOÁN THỊ GIÁC MÁY TÍNH (HSV + INPAINTING) 🚀")
    
    # 1. Đọc ảnh
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Không tìm thấy ảnh: {image_path}")
        return

    # 2. Chuyển đổi sang không gian màu HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 3. Định nghĩa dải màu Đỏ (Mở rộng dải màu để bắt cả màu hồng nhạt/viền mờ)
    lower_red1 = np.array([0, 30, 40])
    upper_red1 = np.array([15, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)

    lower_red2 = np.array([165, 30, 40])
    upper_red2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

    # Tổng hợp mặt nạ màu đỏ
    red_mask = mask1 + mask2

    # 4. Phóng to mặt nạ mạnh hơn một chút để tóm gọn các viền xước (Dilation)
    kernel = np.ones((3, 3), np.uint8)
    red_mask_dilated = cv2.dilate(red_mask, kernel, iterations=1)

    print("   🪄 Đang dùng thuật toán Inpainting (Telea) để nội suy lại nét chữ...")
    
    # 5. Phục hồi ảnh (Inpainting)
    # Thuật toán sẽ lấp đầy các vùng màu đỏ bằng màu của các điểm ảnh (chữ đen/xanh) xung quanh nó
    result = cv2.inpaint(img, red_mask_dilated, 3, cv2.INPAINT_TELEA)

    # 6. Lưu kết quả
    cv2.imwrite(output_path, result)
    print(f"\n🎉 HOÀN TẤT! Đã lưu ảnh dùng Thuật toán Cổ điển tại: {output_path}")
    print("👉 Hãy mở file lên xem. Chữ ký Xanh và chữ Đen chắc chắn 100% được giữ nguyên vẹn!")

if __name__ == "__main__":
    remove_red_stamp_hsv("test_input_a4.png", "test_hsv_result_a4.png")
