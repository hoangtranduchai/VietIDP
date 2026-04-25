# Kế hoạch Triển khai Hệ thống OCR-LLM 2.0 (SOTA Architecture)

Dự án **"Nghiên cứu xây dựng hệ thống trích xuất và cấu trúc hóa thông tin tự động từ văn bản hành chính tiếng Việt sử dụng Mô hình ngôn ngữ lớn đa phương thức (VLMs) phục vụ công tác chuyển đổi số"**.

## Tóm tắt Mục tiêu (Bản Nâng Cấp)
Thay thế pipeline OCR tĩnh truyền thống bằng cấu trúc **Vision-Language Model (Qwen2-VL)** kết hợp **YOLOv11 TensorRT**, nhằm xử lý ảnh văn bản End-to-End, giữ nguyên layout, đạt tốc độ realtime trên phần cứng RTX 5070 (8GB VRAM).

## User Review Required
> [!IMPORTANT]
> **Giới hạn VRAM 8GB vs DocRes:** Đề xuất của bạn về việc dùng Deep Learning (DocRes) để xóa dấu là rất hiện đại. Tuy nhiên, DocRes sẽ "tranh giành" trực tiếp phần VRAM ít ỏi (8GB) với Qwen2-VL và YOLOv11. 
> *Đề xuất của tôi:* Giữ lại `HybridStampMatting` (Toán học/CPU) vì nó có chi phí VRAM = 0MB, tốc độ siêu nhanh và đã đạt Dice 0.86, nhường toàn bộ 8GB VRAM cho **Qwen2-VL-7B (Quantized) hoặc 2B**. Bạn đồng ý chứ?

> [!CAUTION]
> **Hệ sinh thái Inference:** vLLM chạy rất tốt trên Linux/WSL2 nhưng trên Windows Native đôi khi gặp lỗi build Triton. Nếu bạn chạy Windows 11 thuần, chúng ta có thể phải dùng `llama.cpp` (bản hỗ trợ LLaVA/Qwen-VL) kết hợp server GGUF để tối ưu FP8/Q5_K_M. Hãy xác nhận bạn dùng WSL2 hay Windows thuần?

## Open Questions
> [!NOTE]
> 1. Với VLM, chúng ta có thể hỏi đáp đa phương thức (Multimodal RAG) ngay trên ảnh. Bạn có muốn mở rộng UI React để bổ sung khung Chatbot tương tác trực tiếp với văn bản không (bên cạnh việc trích xuất JSON)?

## Proposed Changes (Kiến trúc 2.0)

Dựa trên phân tích thắt cổ chai (Bottleneck) và giới hạn 8GB VRAM, hệ thống được cấu trúc lại thành 5 Module cốt lõi:

---

### Giai đoạn 1: Data Engineering & Synthetic Generation
- Vẫn giữ nguyên luồng `docx_to_pdf_converter.py` và `stamp_generator.py` để tạo dữ liệu.
- **Nâng cấp:** Thay vì tạo text JSON cho LLM thuần, ta tạo dataset chuẩn **VQA (Visual Question Answering)** cho VLM. Định dạng: `{ "image": "img.png", "conversations": [{"from":"user", "value":"Trích xuất số ký hiệu..."}, {"from":"assistant", "value":"..."}] }`.

### Giai đoạn 2: Stamp Detection & Zero-VRAM Matting
- **Model:** Giữ nguyên phiên bản **YOLOv8x** do hệ thống đang chạy ổn định và đạt độ chính xác cần thiết.
- **Inference:** Bỏ qua TensorRT để tránh các lỗi liên quan đến CUDA Build Native trên Windows.
- **Matting:** Sử dụng thuật toán `HybridStampMatting` (Color Matting - CPU) đã tối ưu để bóc con dấu mà không chiếm VRAM.

### Giai đoạn 3: End-to-End Document AI (The Brain & Eye)
- **Model:** Thay thế toàn bộ cụm `VietOCR + LLM` bằng **Qwen2-VL-2B-Instruct** hoặc **Qwen2-VL-7B (Q5_K_M)**.
- **Tính năng:**
  - Bỏ qua OCR truyền thống, VLM đọc trực tiếp ảnh văn bản (chống mất mát Layout).
  - Trích xuất thẳng ra cấu trúc JSON (Zero-shot hoặc Fine-tuned PEFT).
  - Có thể giải thích ngữ cảnh: "Chữ ký này thuộc về ai?", "Con dấu đóng đè lên chữ gì?".
- **Tối ưu hóa:** Sử dụng **Flash Attention 2** và Quantization GGUF/AWQ để nhét vừa 8GB VRAM.

### Giai đoạn 4: Fullstack WebApp & Multimodal Chat
- **Backend (FastAPI):** Streaming kết quả từ VLM (tránh timeout), gọi TensorRT engine bất đồng bộ.
- **Frontend (ReactJS):** Thêm tính năng **Document Chat** (hỏi đáp trên tài liệu) bên cạnh Inspector Sidebar.

### Giai đoạn 5: Evaluation & Self-Correction
- **Tự sửa lỗi (Self-Correction):** Thêm module Regex/Fuzzy Matching hậu xử lý JSON đầu ra của VLM để đảm bảo chuẩn form hành chính.
- **Metrics:** Đánh giá F1-score của JSON, đo Token-per-second (TPS), Latency.

## Verification Plan

### Automated Tests
- Chạy đánh giá F1-Score Information Extraction trên 150 file PDF test bằng script tự động.
- Đo VRAM Peak Memory Usage: Đảm bảo khi YOLOv11 và Qwen2-VL chạy đồng thời không vượt ngưỡng 7.5GB.

### Manual Verification
- Người dùng upload ảnh văn bản khó (nhiều bảng biểu, nhiều dấu) lên Web UI.
- Kiểm tra tính năng Chat với tài liệu: Đặt câu hỏi truy vấn không gian ("Góc phải trên cùng ghi chữ gì?").
