import torch
import json
import logging
import sys
import re
from pathlib import Path
from PIL import Image, ImageDraw

# Yêu cầu cài đặt các thư viện:
# pip install torch transformers qwen_vl_utils pillow

from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
from qwen_vl_utils import process_vision_info

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class DocumentVLM:
    def __init__(self, model_name="Qwen/Qwen2-VL-2B-Instruct"):
        """
        Khởi tạo VLM Qwen2-VL.
        Sử dụng attn_implementation="sdpa" thay vì flash_attention_2 
        để tương thích hoàn hảo với Windows Native và tiết kiệm VRAM.
        """
        logging.info(f"⏳ Đang tải mô hình VLM: {model_name}...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load model với SDPA (Scaled Dot-Product Attention) - Mặc định của PyTorch 2.x
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16, # bfloat16 giúp tiết kiệm VRAM và giữ độ chính xác
            device_map="auto",
            attn_implementation="sdpa" 
        )
        self.processor = AutoProcessor.from_pretrained(model_name)
        logging.info("✅ Load VLM thành công!")
        
        # System Prompt siêu tối ưu (Thêm Negative Prompting & Spatial Cues)
        self.system_prompt = """You are an expert in Vietnamese administrative document analysis.
Extract information from the document image into a JSON object.

CRITICAL RULES FOR EXTRACTION:
1. "so_hieu": Document number. EXCLUDE the word "Số:" or "Số :". (Example: If the image says "Số: 123/QĐ-UBND", you MUST output "123/QĐ-UBND").
2. "ngay_ban_hanh": The date (DD/MM/YYYY) located at the top-right.
3. "co_quan_ban_hanh": The issuing agency at the TOP-LEFT. 
   -> NEGATIVE RULE: DO NOT extract "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" or "Độc lập - Tự do - Hạnh phúc". These are national mottos. Look strictly at the TOP-LEFT.
4. "trich_yeu": The subject. Starts with "V/v" or "Về việc". Do NOT include document types like "QUYẾT ĐỊNH" or "THÔNG BÁO".
5. "nguoi_ky": The human name at the BOTTOM-RIGHT. EXCLUDE all job titles like "CHỦ TỊCH", "KT. BỘ TRƯỞNG", "GIÁM ĐỐC", or "(Đã ký)". Extract ONLY the capitalized proper name (e.g., "NGUYỄN VĂN TEST").

OUTPUT EXACTLY THIS JSON FORMAT (No markdown blocks):
{
  "so_hieu": "",
  "ngay_ban_hanh": "",
  "co_quan_ban_hanh": "",
  "trich_yeu": "",
  "nguoi_ky": ""
}"""

    def _clean_extracted_data(self, data: dict) -> dict:
        """Lớp Hậu xử lý (Post-processing) - Vũ khí bí mật để đạt F1 = 1.0"""
        if not isinstance(data, dict): return data
        
        # 1. Dọn dẹp 'so_hieu' (Cắt bỏ chữ "Số:" nếu model vẫn ngoan cố xuất ra)
        if data.get('so_hieu') and data['so_hieu'] != "null":
            data['so_hieu'] = str(data['so_hieu']).replace('Số:', '').replace('Số :', '').replace('SỐ:', '').strip()
            
        # 2. Dọn dẹp 'co_quan_ban_hanh' (Fallback chặn Quốc hiệu)
        if data.get('co_quan_ban_hanh'):
            cq = str(data['co_quan_ban_hanh']).upper()
            if "CỘNG HÒA" in cq or "ĐỘC LẬP" in cq or "CỘNG HOÀ" in cq:
                logging.warning("⚠️ Model vẫn bắt nhầm Quốc hiệu. Đã xóa kết quả để tránh F1 False Positive.")
                data['co_quan_ban_hanh'] = None # Chấp nhận Null thay vì False Positive để báo cáo lỗi rõ ràng hơn
                
        # 3. Dọn dẹp 'nguoi_ky' (Lọc chức danh dính kèm)
        if data.get('nguoi_ky') and data['nguoi_ky'] != "null":
            nk = str(data['nguoi_ky'])
            titles_to_remove = ["CHỦ TỊCH", "GIÁM ĐỐC", "KT. BỘ TRƯỞNG", "BỘ TRƯỞNG", "PHÓ", "(Đã ký)", "TM."]
            for title in titles_to_remove:
                nk = re.sub(rf'\b{title}\b', '', nk, flags=re.IGNORECASE)
            
            # Lấy dòng cuối cùng (vì tên người luôn ở dòng dưới cùng của cụm chữ ký)
            lines = [line.strip() for line in nk.split('\n') if line.strip()]
            if lines:
                data['nguoi_ky'] = lines[-1].strip()

        # 4. Dọn dẹp 'trich_yeu' (Xóa khoảng trắng thừa)
        if data.get('trich_yeu') and data['trich_yeu'] != "null":
            data['trich_yeu'] = data['trich_yeu'].strip()

        return data

    def extract_information(self, image_path: str) -> str:
        """Đọc ảnh và trả về chuỗi JSON (String) để tương thích với evaluate_phase3.py"""
        if not Path(image_path).exists():
            logging.error(f"❌ Không tìm thấy ảnh: {image_path}")
            return "{}"

        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": self.system_prompt}]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": image_path,
                    },
                    {"type": "text", "text": "Extract the data into JSON."}
                ]
            }
        ]

        # Xử lý input cho Qwen-VL
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        ).to(self.device)

        # Suy luận (Inference)
        logging.info(f"🧠 VLM đang suy luận (Inference) cho tệp {Path(image_path).name}...")
        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=300)
            
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        raw_output = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        
        logging.debug(f"RAW Output: {raw_output}")
        
        # Robust JSON Parsing
        try:
            # Tìm vị trí dấu { và } để cắt chính xác chuỗi JSON, bất chấp model sinh thêm text rác
            start_idx = raw_output.find('{')
            end_idx = raw_output.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = raw_output[start_idx:end_idx+1]
                parsed_data = json.loads(json_str)
                
                # CHẠY QUA BỘ LỌC HẬU XỬ LÝ (Để đẩy điểm F1)
                cleaned_data = self._clean_extracted_data(parsed_data)
                
                # TRẢ VỀ STRING ĐỂ KHÔNG BỊ LỖI KHI GỌI json.loads() TỪ FILE KHÁC
                return json.dumps(cleaned_data, ensure_ascii=False)
            else:
                logging.warning("⚠️ Không tìm thấy cấu trúc JSON trong output.")
                err_dict = {"error": "No JSON found", "raw_output": raw_output}
                return json.dumps(err_dict, ensure_ascii=False)
                
        except json.JSONDecodeError:
            logging.error("❌ Lỗi parse JSON. Đầu ra của model bị hỏng cấu trúc.")
            err_dict = {"error": "JSON Decode Error", "raw_output": raw_output}
            return json.dumps(err_dict, ensure_ascii=False)


if __name__ == "__main__":
    # Test script
    test_img = "data/processed/stamped_images/mock1_page_1.png"
    if len(sys.argv) > 1:
        test_img = sys.argv[1]
        
    # Tự động tạo ảnh giả lập nếu chưa có ảnh
    if not Path(test_img).exists():
        print(f"Ảnh {test_img} không tồn tại. Đang tạo ảnh giả lập để test...")
        img = Image.new('RGB', (800, 1000), color='white')
        d = ImageDraw.Draw(img)
        
        # Layout giả lập văn bản hành chính Việt Nam
        d.text((50, 50), "BỘ TÀI CHÍNH\nTỔNG CỤC THUẾ", fill=(0,0,0)) 
        d.text((450, 50), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc", fill=(0,0,0))
        d.text((50, 150), "Số: 456/TB-BTC", fill=(0,0,0))
        d.text((400, 150), "Hà Nội, ngày 20 tháng 03 năm 2024", fill=(0,0,0))
        d.text((350, 250), "THÔNG BÁO", fill=(0,0,0))
        d.text((50, 280), "V/v triển khai hệ thống AI mới trong xử lý văn bản", fill=(0,0,0))
        d.text((500, 800), "KT. BỘ TRƯỞNG\nTHỨ TRƯỞNG\n(Đã ký)\nCAO ANH TUẤN", fill=(0,0,0))
        
        Path(test_img).parent.mkdir(parents=True, exist_ok=True)
        img.save(test_img)
        print(f"✅ Đã tạo ảnh thành công tại {test_img}")
        
    # Khởi chạy Pipeline
    pipeline = DocumentVLM("Qwen/Qwen2-VL-2B-Instruct")
    result_json_str = pipeline.extract_information(test_img)
    
    print("\n" + "="*60)
    print(" KẾT QUẢ TRÍCH XUẤT TỪ VLM (JSON STRING - ĐÃ LÀM SẠCH) ")
    print("="*60)
    try:
        # Parse lại string ra dict để in hiển thị đẹp (indent=4)
        print(json.dumps(json.loads(result_json_str), indent=4, ensure_ascii=False))
    except Exception as e:
        print(result_json_str)