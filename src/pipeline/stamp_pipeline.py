import cv2
import numpy as np
import base64
from pathlib import Path
from ultralytics import YOLO
from src.config import Config
from src.preprocessing.stamp_matting import HybridStampMatting

class StampDetectorPipeline:
    def __init__(self):
        # 1. Load YOLOv8 Model (Pre-load weights)
        yolo_path = Config.MODELS_DIR / "finetuned" / "stamp_detector" / "weights" / "best.pt"
        if not yolo_path.exists():
            print(f"Warning: YOLO model not found at {yolo_path}, falling back to yolov8n.pt")
            self.yolo = YOLO("yolov8n.pt")
        else:
            self.yolo = YOLO(str(yolo_path))
            
        # 2. Load Hybrid Matting (Rembg ONNX Session initializes once)
        self.matting = HybridStampMatting()
        self.is_loaded = True
        
    def process_image(self, file_path_or_bytes):
        """
        Processes image bytes (or file path), detects stamps with YOLO, 
        extracts transparent foreground using Matting, and returns Base64.
        """
        if isinstance(file_path_or_bytes, (str, Path)):
            img = cv2.imread(str(file_path_or_bytes))
        else:
            nparr = np.frombuffer(file_path_or_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
        if img is None:
            return {"success": False, "error": "Invalid image format"}
            
        # 1. YOLO Detection
        results = self.yolo(img, verbose=False)
        stamps = []
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                if conf < 0.5: # Configurable threshold
                    continue
                    
                # 2. Crop Stamp Area
                # Add a small padding to ensure the whole stamp is included
                h, w = img.shape[:2]
                pad = 10
                px1, py1 = max(0, x1 - pad), max(0, y1 - pad)
                px2, py2 = min(w, x2 + pad), min(h, y2 + pad)
                crop_img = img[py1:py2, px1:px2]
                
                # 3. Stamp Matting (Extract red stamp to transparent background)
                rgba_stamp = self.matting.extract_stamp(crop_img)
                if rgba_stamp is None:
                    continue
                    
                # 4. Convert to Base64 PNG for web
                success, encoded_img = cv2.imencode('.png', rgba_stamp)
                if success:
                    b64_string = base64.b64encode(encoded_img).decode('utf-8')
                    stamps.append({
                        "coords": [x1, y1, x2, y2],
                        "confidence": round(conf, 4),
                        "base64": f"data:image/png;base64,{b64_string}"
                    })
                    
        return {
            "success": True,
            "count": len(stamps),
            "image_width": img.shape[1],
            "image_height": img.shape[0],
            "stamps": stamps
        }
