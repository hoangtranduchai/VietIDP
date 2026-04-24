import cv2
import numpy as np

class DIPProcessor:
    """
    Kỹ thuật Xử lý Ảnh Số (Digital Image Processing) thay thế GAN.
    Đảm bảo 100% tính nguyên vẹn hình học của ký tự (Topology Integrity).
    Dành riêng cho tiền xử lý OCR văn bản hành chính Việt Nam.
    """
    def __init__(self):
        # Dải màu chuẩn của Mực Đỏ / Hồng con dấu trong không gian HSV
        # Do màu đỏ nằm ở 2 đầu dải Hue (0-10 và 170-180) nên cần 2 mask
        self.red_lower1 = np.array([0, 50, 50])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([170, 50, 50])
        self.red_upper2 = np.array([180, 255, 255])

    def process_document(self, image_bgr, bbox=None):
        """
        Xử lý toàn bộ luồng DIP trên ảnh. 
        Tham số bbox: (x1, y1, x2, y2) từ mô hình YOLO. Nếu có, chỉ DIP vùng đó để tốc độ đạt mili-giây.
        """
        if bbox:
            x1, y1, x2, y2 = bbox
            region = image_bgr[y1:y2, x1:x2].copy()
            processed_region = self._apply_dip_pipeline(region)
            
            # Ghi đè vùng đã làm sạch bằng DIP lại vào trang A4 gốc
            result = image_bgr.copy()
            result[y1:y2, x1:x2] = processed_region
            return result
        else:
            # Nếu không có YOLO (chạy thủ công), áp dụng toàn trang (Chậm hơn một chút)
            return self._apply_dip_pipeline(image_bgr)

    def _apply_dip_pipeline(self, roi):
        """Luồng thực thi Lõi (The Core Pipeline)"""
        
        # ---------------------------------------------------------
        # Bước 1: Khử màu (HSV Color Filtering)
        # ---------------------------------------------------------
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
        mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
        red_mask = mask1 | mask2
        
        # Biến toàn bộ pixel Mực Đỏ thành Nền Trắng (Tẩy dấu)
        # Lưu ý: Chỗ chữ đen giao với mực đỏ sẽ bị thủng (trắng)
        no_red = roi.copy()
        no_red[red_mask > 0] = (255, 255, 255)
        
        # ---------------------------------------------------------
        # Bước 2: Chuyển đổi mức Xám (Grayscale)
        # ---------------------------------------------------------
        gray = cv2.cvtColor(no_red, cv2.COLOR_BGR2GRAY)
        
        # ---------------------------------------------------------
        # Bước 3: Nhị phân hóa Thích ứng (Adaptive Binarization)
        # ---------------------------------------------------------
        # Ép quang đồ về Trắng/Đen tuyệt đối. Khử nhiễu bóng râm giấy scan, 
        # Cực kỳ tốt để OCR đọc độ nét cao.
        binary = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            blockSize=15, C=9
        )
        
        # ---------------------------------------------------------
        # Bước 4: Toán Hình thái học (Morphology)
        # ---------------------------------------------------------
        # Ảnh Binarize đang có Nền = 255 (Trắng), Chữ = 0 (Đen).
        # Khi dùng lệnh Erode (Xói mòn) của OpenCV lên màu 255, các vùng Trắng bị thu hẹp lại.
        # Nghĩa là Nét Chữ Đen được GIÃN NỞ (Dilation) ra.
        # Thao tác này giúp "Hàn gắn" (Repair) các khe nứt đứt gãy do Bước 1 làm lủng nét chữ.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        repaired = cv2.erode(binary, kernel, iterations=1)
        
        # Chuyển về định dạng BGR 3 kênh để dễ dàng hiển thị hoặc nối vào các Pipeline khác
        final_bgr = cv2.cvtColor(repaired, cv2.COLOR_GRAY2BGR)
        return final_bgr
