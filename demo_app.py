import gradio as gr
import cv2
import json
import numpy as np
from PIL import Image
from src.pipeline.end_to_end import VietIDPPipeline

# Khởi tạo Pipeline dùng chung (Tải model 1 lần duy nhất khi bật app)
print("Đang tải các mô hình AI lên RTX 5070. Vui lòng chờ...")
pipeline = VietIDPPipeline()

def process_file_input(file_path):
    if file_path is None:
        return None, "Vui lòng tải tệp lên", "{}"
        
    try:
        # Gọi luồng xử lý chính (Pipeline giờ đã tự động xử lý PDF đa trang)
        result = pipeline.process_file(file_path)
        
        # Chuyển list ảnh BGR (từ OpenCV) sang RGB để Gradio hiển thị lên Gallery
        output_images_rgb = []
        for img_bgr in result.get("processed_images", []):
            output_images_rgb.append(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
            
        # Định dạng JSON đẹp đẽ
        json_output = json.dumps(result.get("structured_data", {}), indent=4, ensure_ascii=False)
        raw_text = result.get("raw_text", "")
        
        return output_images_rgb, raw_text, json_output
        
    except Exception as e:
        import traceback
        return None, "Lỗi xảy ra trong quá trình xử lý: " + str(e), "{}"

# Xây dựng giao diện Web
with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue")) as demo:
    gr.Markdown(
        """
        # 🚀 HỆ THỐNG TRÍCH XUẤT VĂN BẢN HÀNH CHÍNH (VIET-IDP)
        **Kiến trúc:** YOLOv8x (Detection) ➡️ OpenCV (DIP) ➡️ VietOCR Hybrid ➡️ Qwen2.5-7B (LLM)  
        **Phần cứng:** Chạy hoàn toàn Offline (Local) trên RTX 5070 8GB VRAM.
        """
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            input_file = gr.File(label="Tải lên Văn bản (Hỗ trợ PDF, JPG, PNG)", file_types=[".pdf", ".jpg", ".png", ".jpeg"])
            submit_btn = gr.Button("🚀 Phân tích & Trích xuất", variant="primary")
            
        with gr.Column(scale=1):
            output_image = gr.Gallery(label="Kết quả Định vị & Xử lý (Các trang PDF)", preview=True, object_fit="contain")
            
    with gr.Row():
        with gr.Column(scale=1):
            raw_text = gr.Textbox(label="Văn bản bóc tách (VietOCR VGG-Transformer)", lines=15)
        with gr.Column(scale=1):
            json_output = gr.Code(label="Dữ liệu Cấu trúc (Qwen2.5-7B JSON)", language="json", lines=15)
            
    submit_btn.click(
        fn=process_file_input,
        inputs=[input_file],
        outputs=[output_image, raw_text, json_output]
    )

if __name__ == "__main__":
    print("Khởi động Máy chủ Giao diện...")
    demo.launch(server_name="0.0.0.0", server_port=7860, inbrowser=True)
