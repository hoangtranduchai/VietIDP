import cv2
import numpy as np

class DIPProcessor:
    """
    [V2 ARCHITECTURE] - Local Filtering & Global Restoration
    Giải quyết dứt điểm ranh giới đứt gãy ảnh (Frankenstein Image) và hiện tượng đa dấu.
    """
    def __init__(self):
        # Dải màu chuẩn của Mực Đỏ / Hồng con dấu trong không gian HSV
        self.red_lower1 = np.array([0, 50, 50])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([170, 50, 50])
        self.red_upper2 = np.array([180, 255, 255])

    def process_document(self, image_bgr, bboxes=None):
        """
        Luồng xử lý V2 phân cấp:
        - Tham số bboxes: Danh sách chứa CÁC tọa độ [(x1,y1,x2,y2), (x1,y1,x2,y2)...]
        """
        result_img = image_bgr.copy()
        
        # =========================================================
        # GIAI ĐOẠN 1: LOCAL PROCESSING (Lọc màu theo Bounding Box)
        # Mục tiêu: Đóng băng an toàn các logo đỏ trên tiêu đề, chỉ xóa màu đỏ ở vùng chữ ký.
        # =========================================================
        if bboxes and len(bboxes) > 0:
            for box in bboxes:
                x1, y1, x2, y2 = box
                
                # Tránh lỗi tràn viền nếu YOLO dự đoán lấn ra ngoài lề ảnh
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(result_img.shape[1], x2), min(result_img.shape[0], y2)
                
                roi = result_img[y1:y2, x1:x2]
                if roi.size == 0: continue
                
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
                mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
                red_mask = mask1 | mask2
                
                # Đổi pixel đỏ thành Trắng (255, 255, 255)
                roi[red_mask > 0] = (255, 255, 255)
                
                # Cập nhật ngược lại tấm ảnh gốc
                result_img[y1:y2, x1:x2] = roi

        # =========================================================
        # GIAI ĐOẠN 2: GLOBAL PROCESSING (Đồng bộ hóa Toàn trang A4)
        # Mục tiêu: Toàn bộ mặt trang giấy sẽ được ép về thang xám, sau đó nhị phân 
        # và hàn gắn nét đứt đồng loạt. Đảm bảo phông chữ đồng nhất 100% không chắp vá.
        # =========================================================
        gray = cv2.cvtColor(result_img, cv2.COLOR_BGR2GRAY)
        
        # 2.1 Nhị phân hóa toàn cục (Tẩy sạch bóng đổ, nền giấy xám, v.v)
        binary = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            blockSize=15, C=9
        )
        
        # 2.2 Hình thái học Toàn cục (Global Morphology)
        # Lấp đầy các khe đứt gãy của chữ tại vùng bị tẩy đỏ, đồng thời làm đậm đều nét chữ in toàn trang
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        repaired = cv2.erode(binary, kernel, iterations=1)
        
        # Chuyển về BGR để output
        final_bgr = cv2.cvtColor(repaired, cv2.COLOR_GRAY2BGR)
        
        return final_bgr
