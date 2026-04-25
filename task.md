# 📋 Theo dõi Tiến độ Dự án NCKH (OCR-LLM 2.0 SOTA)

Danh sách công việc bám sát theo kiến trúc mới (Qwen2-VL, YOLOv11 TensorRT). Cập nhật `[x]` khi hoàn thành, `[/]` khi đang thực hiện.

- [x] **Giai đoạn 1: Chuẩn bị & Xử lý Dữ liệu (Dataset)**
  - [x] Thu thập nguồn dữ liệu văn bản thô (2000 - 3000 mẫu).
  - [x] Xây dựng công cụ/script để làm mờ thông tin nhạy cảm (PII Redaction) hoặc xử lý docx to pdf.
  - [x] Cài đặt công cụ gán nhãn (Label Studio hoặc PPOCRLabel) / tạo tool sinh JSON chuẩn tự động.
  - [x] Thực hiện gán nhãn vị trí hộp thoại (Bounding box) cho OCR / tạo ảnh có dấu mô phỏng.
  - [x] Thực hiện gán nhãn thực thể (Key-value JSON) cho phần LLM (llm_dataset_builder).
  - [x] **(Update 2.0)** Chuyển đổi format JSON text sang định dạng VQA (Visual Question Answering) cho VLM.

- [x] **Giai đoạn 2: Stamp Detection & Zero-VRAM Matting**
  - [x] Viết các script tiền xử lý (Auto-Deskew, Denoising).
  - [x] **(Update 2.0)** Giữ thuật toán HybridStampMatting (Color Matting R-max) thay vì DocRes để đạt VRAM=0MB. Đã đạt F1-score > 0.86.
  - [x] Giữ nguyên phiên bản YOLOv8x (theo yêu cầu) để đảm bảo tính ổn định và không cần cài đặt TensorRT phức tạp trên Windows.

- [x] **Giai đoạn 3: End-to-End Document AI (The Brain & Eye)**
  - [x] **(Update 2.0)** Tích hợp mô hình VLM: Qwen2-VL-2B-Instruct hoặc Qwen2-VL-7B (Q5_K_M).
  - [x] **(Update 2.0)** Cài đặt Inference Engine: Sử dụng `transformers` + `qwen-vl-utils` với `attn_implementation="sdpa"` tối ưu siêu việt cho Windows Native.
  - [x] Xây dựng file System Prompt đặc thù cho việc trích xuất văn bản hành chính Việt Nam.
  - [ ] (Tuỳ chọn) Chạy pipeline sinh data để QLoRA fine-tuning VLM trên tập dữ liệu đặc thù.

- [ ] **Giai đoạn 4: Fullstack WebApp & Multimodal Chat**
  - [x] Khởi tạo dự án React (Vite/Next.js) và FastAPI.
  - [x] Xây dựng UI Component: Upload File, Preview tài liệu.
  - [ ] Xây dựng Endpoint FastAPI bất đồng bộ (Streaming) nhận ảnh, trả về chuỗi JSON từ VLM.
  - [ ] **(Update 2.0)** Mở rộng React UI: Thêm cửa sổ Chat đa phương thức (Chatbot) để hỏi đáp trực tiếp với tài liệu.
  - [ ] Hoàn thiện hiển thị kết quả (Bảng JSON/Key-Value đẹp mắt).

- [ ] **Giai đoạn 5: Evaluation & Self-Correction**
  - [ ] Thêm Regex/Fuzzy Matching để kiểm tra chéo (Verify) kết quả JSON.
  - [ ] Đo đạc các chỉ số F1-Score (Extraction) trên 150 file test.
  - [ ] Đo Latency và Peak VRAM Usage, quay video demo hệ thống (Walkthrough).
