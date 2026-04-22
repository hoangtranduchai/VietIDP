# Kế hoạch Triển khai Hệ thống OCR-LLM cho Văn bản Hành chính Việt Nam

## Tổng quan Đề tài

Xây dựng hệ thống end-to-end pipeline: **Input (Scan/PDF)** → **Preprocessing (Stamp Removal)** → **OCR (Text Recognition)** → **LLM (Information Extraction)** → **Structured JSON Output**, phục vụ chuyển đổi số văn bản hành chính tiếng Việt.

### Tài nguyên hiện có
| Tài nguyên | Chi tiết |
|---|---|
| **2000 file docx sạch** | CV:600, HD:200, K:200, QD:600, TT:400 |
| **150 file PDF test** | Văn bản hành chính thực (có dấu, chữ ký) |
| **Python** | 3.12.12 (chưa cài thư viện ML) |
| **GPU** | NVIDIA RTX 5070 (8GB VRAM) |

---

## User Review Required

> [!IMPORTANT]
> **Về việc thu thập 200 con dấu**: Việc này **RẤT CẦN THIẾT** cho module Stamp Removal (Pix2Pix GAN). Tuy nhiên, thay vì thu thập thủ công, tôi đề xuất **phương án kết hợp**:
> 1. **Trích xuất tự động** con dấu từ 150 file PDF test sẵn có (dùng color segmentation)
> 2. **Tạo synthetic stamps** bằng Python (vẽ hình tròn/oval + text giống dấu thật)
> 3. Thu thập thêm từ nguồn công khai chỉ nếu cần bổ sung đa dạng
>
> Phương án này giúp tiết kiệm thời gian đáng kể và tạo ra **dataset không giới hạn** cho training.

> [!WARNING]
> **Về pip**: Hệ thống Python hiện tại (msys64) không có pip. Tôi đề xuất cài **Miniconda/uv** để quản lý môi trường. Bạn có muốn dùng Conda hay phương pháp khác?

---

## Proposed Changes

Dự án được chia thành **6 Phase** theo đúng đề cương nghiên cứu. Tôi sẽ **code từng module Python** hoàn chỉnh.

---

### Phase 0: Environment Setup

#### [NEW] [requirements.txt](file:///e:/OCR-LLM_Research/requirements.txt)
- Tất cả dependencies: `torch`, `transformers`, `peft`, `paddlepaddle`, `paddleocr`, `opencv-python`, `Pillow`, `fastapi`, `python-docx`, `pandas`, v.v.

#### [NEW] [setup_env.py](file:///e:/OCR-LLM_Research/setup_env.py)
- Script tự động kiểm tra và cài đặt môi trường

---

### Phase 1: Data Preparation (Tận dụng 2000 docx + 150 PDF)

> [!NOTE]
> **Vai trò của 2000 file docx**: Cực kỳ quan trọng! Đây là **ground truth** cho LLM fine-tuning:
> - Chuyển docx → PDF → Image để tạo training data cho OCR
> - Trích xuất metadata (tiêu đề, ngày, người ký) từ docx để tạo **instruction dataset** cho LLM
> - Tạo cặp {image + stamp} ↔ {clean image} cho GAN training

#### [NEW] [src/data/docx_to_pdf_converter.py](file:///e:/OCR-LLM_Research/src/data/docx_to_pdf_converter.py)
- Chuyển 2000 docx → PDF → Image (PNG) tự động
- Tạo version sạch (clean) và version có stamp (noisy) cho GAN

#### [NEW] [src/data/stamp_extractor.py](file:///e:/OCR-LLM_Research/src/data/stamp_extractor.py)
- Trích xuất con dấu đỏ từ 150 file PDF test bằng **HSV color segmentation**
- Lọc vùng đỏ → crop → lưu thành ảnh stamp riêng biệt

#### [NEW] [src/data/stamp_generator.py](file:///e:/OCR-LLM_Research/src/data/stamp_generator.py)
- **Tạo synthetic stamps** giống thật bằng Python:
  - Vẽ hình tròn/oval với viền đỏ
  - Thêm text cơ quan (font Vietnamese)
  - Thêm ngôi sao ở giữa
  - Random rotation, opacity, blur để tăng tính đa dạng
- Tạo **cặp dữ liệu training** cho Pix2Pix: overlay stamp lên ảnh sạch

#### [NEW] [src/data/llm_dataset_builder.py](file:///e:/OCR-LLM_Research/src/data/llm_dataset_builder.py)
- Parse 2000 file docx → trích xuất structured fields (Số hiệu, Ngày, Trích yếu, Người ký)
- Tạo **instruction-following dataset** dạng:
  ```json
  {
    "instruction": "Trích xuất thông tin từ văn bản sau...",
    "input": "<nội dung OCR text>",
    "output": "{\"so_hieu\": \"...\", \"ngay_ban_hanh\": \"...\", ...}"
  }
  ```

---

### Phase 2: Transparent Stamp Matting (The Extractor)

#### [MODIFY/NEW] [src/preprocessing/stamp_matting.py](file:///e:/OCR-LLM_Research/src/preprocessing/stamp_matting.py)
- Kế thừa và chuẩn hóa đoạn code từ `scripts/remove_bg_batch.py` thành lớp OOP `HybridStampMatting`.
- Chạy siêu nhẹ, không tốn VRAM: Dùng **Rembg** lấy Alpha mask sơ bộ, dùng **OpenCV** (Math Thresholding) quét ảnh xám loại bỏ các điểm ảnh đen của chữ, giữ lại mực đỏ.
- Khớp nối trực tiếp với đầu ra của YOLOv8:
  1. Nhận Bounding Box BGR Crop từ YOLO (Phase 1).
  2. Bóc tách và trả về ảnh RGBA trong suốt.
  3. Cung cấp API trực tiếp lưu thành file hoặc trả về memory array cho Giao diện UI.

---

### Phase 3: Backend API (Giao tiếp Hệ thống - Tầng Stamp)

#### [MODIFY] [src/api/fastapi_app.py](file:///e:/OCR-LLM_Research/src/api/fastapi_app.py)
- Viết lại/Bổ sung endpoint `POST /api/extract_stamp` chuyên dụng cho giao diện web.
- Flow xử lý chính tại Endpoint:
  1. Nhận file Upload (PDF/Image) từ người dùng.
  2. Bắn qua model YOLOv8 (file `best.pt` ở Giai đoạn 1) để lấy array tọa độ chính xác `[x1, y1, x2, y2]`.
  3. Đẩy mảng ảnh Bounding Box đó qua class `HybridStampMatting` (Giai đoạn 2) để khử bóng chữ đen và nền trắng.
  4. (Tương lai) Kích hoạt chạy nền mạng Pix2Pix xóa dấu để OCR LLM đọc sau.
  5. Đóng gói ảnh RGBA kết quả ra thành chuỗi `Base64`, trả về JSON cùng tọa độ để React Frontend render "phù phép" con dấu đỏ nổi lề giấy.

#### [NEW] [src/pipeline/stamp_pipeline.py](file:///e:/OCR-LLM_Research/src/pipeline/stamp_pipeline.py)
- Cấu trúc class `StampDetectorPipeline` giúp load trước bộ tạ weights YOLOv8 và Rembg Session vào RAM để phục vụ Web với độ trễ cực thấp (<50ms).

---

### Phase 4: Giao diện React Chuyên nghiệp (GovTech/Enterprise Dashboard)

#### Thiết kế Hành chính Quốc gia (Enterprise Minimalist)
![Premium UI Mockup](file:///C:/Users/ADMIN/.gemini/antigravity/brain/3cc31bf7-580b-42bd-b678-63bae1be7321/enterprise_ui_mockup_1776848744632.png)
*(Bản vẽ UI/UX đề xuất: Phong cách Light-mode hiện đại, sáng sủa, thanh lịch, chuẩn mực và mang tính bảo mật đặc trưng của hệ thống hành chính)*

#### [NEW] [apps/frontend/src/components/DocumentViewer.jsx](file:///e:/OCR-LLM_Research/OCR-LLM_Research/apps/frontend/src/components/DocumentViewer.jsx)
- **Vùng chính (Main Viewer):** Giao diện hiển thị PDF/Layout trắng sáng sắc nét (Off-white `#F8FAFC`). Khác với kiểu viền Neon giải trí, Bounding Box AI ở đây là một đường nét đứt, chính xác màu Đỏ Hành Chính (`#DC2626`) đi kèm góc tọa độ vuông vắn (như giao diện phần mềm Adobe Acrobat hay các hệ thống chuyên ngành Khoa học).
- **Hiệu ứng Hoạt hình (Framer Motion):** Giữ sự mượt mà nhưng bỏ đi yếu tố "nảy" (bounce) để tạo cảm giác nghiêm túc. Viền đỏ sẽ xuất hiện bằng hiệu ứng Fade In, sau đó ảnh crop sẽ "Trượt" (Slide & Ease-in-out) một cách thanh lịch sang thanh công cụ bên phải mà không gây mất tập trung.

#### [NEW] [apps/frontend/src/components/StampPanel.jsx](file:///e:/OCR-LLM_Research/OCR-LLM_Research/apps/frontend/src/components/StampPanel.jsx)
- **Panel Điều Kiển (Inspector Sidebar):** Khối UI nằm bên lề phải với tông màu trắng tinh khôi và Shadow đổ bóng tinh tế (Soft material shadow). Thể hiện các metadata phân tích của AI.
- **Mặt nền Trong suốt:** Một Container bao bọc kết quả cắt nền trong suốt RGBA. Hình nền sử dụng lưới ô Caro (Checkerboard) rất phổ biến trong các báo cáo trích xuất hình ảnh, làm minh chứng trực quan cho sự triệt để của kỹ thuật OCR/Matting.

---

### Phase 5: LLM Fine-tuning (The Brain)

#### [NEW] [src/llm/finetune_qwen.py](file:///e:/OCR-LLM_Research/src/llm/finetune_qwen.py)
- QLoRA fine-tuning pipeline cho Qwen-2.5-7B-Instruct
- 4-bit quantization (BitsAndBytes)
- LoRA config: r=16, alpha=32
- Training trên instruction dataset từ Phase 1

#### [NEW] [src/llm/inference.py](file:///e:/OCR-LLM_Research/src/llm/inference.py)
- Load quantized model → nhận text → trả JSON
- Document classification (5 loại: CV, HD, QD, TT, K)
- Key-value extraction (Số hiệu, Ngày, Trích yếu, Người ký)

#### [NEW] [src/llm/evaluator.py](file:///e:/OCR-LLM_Research/src/llm/evaluator.py)
- Precision/Recall/F1-Score cho từng trường thông tin
- Confusion matrix cho document classification

---

### Phase 5: End-to-End Pipeline & API

#### [NEW] [src/pipeline/end_to_end.py](file:///e:/OCR-LLM_Research/src/pipeline/end_to_end.py)
- Pipeline hoàn chỉnh: Image → Preprocess → OCR → LLM → JSON
- Xử lý PDF nhiều trang

#### [NEW] [src/api/main.py](file:///e:/OCR-LLM_Research/src/api/main.py)
- FastAPI server với endpoints:
  - `POST /api/process` - Upload và xử lý văn bản
  - `GET /api/results/{id}` - Lấy kết quả
  - `GET /api/health` - Health check

---

### Phase 6: Evaluation

#### [NEW] [src/evaluation/benchmark.py](file:///e:/OCR-LLM_Research/src/evaluation/benchmark.py)
- Chạy benchmark trên 150 file PDF test
- Sinh báo cáo metrics tổng hợp

---

## Cấu trúc Thư mục Dự án

```
e:/OCR-LLM_Research/
├── Document/                      # Tài liệu nghiên cứu (đã có)
├── data/
│   ├── raw_word_files/            # 2000 docx gốc (đã có)
│   │   ├── CV/ (600)
│   │   ├── HD/ (200)
│   │   ├── K/  (200)
│   │   ├── QD/ (600)
│   │   └── TT/ (400)
│   ├── test/                      # 150 PDF test (đã có)
│   ├── processed/                 # [NEW] Ảnh sau xử lý
│   │   ├── clean_images/          # Ảnh sạch từ docx
│   │   └── stamped_images/        # Ảnh có stamp overlay
│   ├── stamps/                    # [NEW] Extracted & synthetic stamps
│   └── llm_training/              # [NEW] Dataset cho LLM fine-tuning
├── src/
│   ├── data/                      # [NEW] Data preparation scripts
│   ├── preprocessing/             # [NEW] Stamp removal & image preprocessing
│   ├── ocr/                       # [NEW] OCR engine
│   ├── llm/                       # [NEW] LLM fine-tuning & inference
│   ├── pipeline/                  # [NEW] End-to-end pipeline
│   ├── api/                       # [NEW] FastAPI backend
│   └── evaluation/                # [NEW] Benchmarking tools
├── models/                        # [NEW] Saved model weights
├── configs/                       # [NEW] Configuration files
├── requirements.txt               # [NEW]
└── README.md                      # [NEW]
```

---

## Verification Plan

### Automated Tests

1. **Phase 1 - Data Pipeline**:
   ```bash
   python -m src.data.stamp_extractor --input data/test --output data/stamps --limit 5
   python -m src.data.stamp_generator --output data/stamps/synthetic --count 10
   ```
   Verify: Kiểm tra file ảnh stamp được tạo ra, mở xem bằng mắt

2. **Phase 2 - Stamp Matting**:
   ```bash
   python -m src.preprocessing.stamp_matting --test --input data/raw/stamps_raw --output data/interim/stamps_transparent
   ```
   Verify: Mở ảnh đầu ra kiểm tra bằng mắt, nền phải trong suốt chuẩn xác, mực đỏ còn nguyên, không dính chữ đen.

3. **Phase 3 - Backend API**:
   ```bash
   uvicorn src.api.fastapi_app:app --reload --port 8000
   ```
   Verify: Dùng Postman hoặc CURL gửi file ảnh có dấu vào endpoint `/api/extract_stamp`. Đảm bảo JSON response trả về chứa trường base64 hợp lệ, khi decode ra là ảnh PNG trong suốt chính xác tuyệt đối.

4. **Phase 4 - UI React Component Test**:
   ```bash
   cd apps/frontend && npm run dev
   ```
   Verify: Upload file từ giao diện. Bounding Box neon đỏ bọc trúng con dấu. Animation bay đúng quỹ đạo sang phải. Nền Panel Caro hiện rõ với con dấu ở trung tâm.
   
5. **Phase 5 - LLM**:
   ```bash
   python -m src.llm.evaluator --model models/qwen-finetuned --test-data data/llm_training/test.json
   ```
   Verify: F1-Score > 90% trên các trường tiêu chuẩn

5. **Phase 5 - End-to-End**:
   ```bash
   python -m src.pipeline.end_to_end --input data/test/QD_0001.pdf --output results/
   ```
   Verify: JSON output chứa đầy đủ các trường thông tin

### Manual Verification
- Upload PDF qua Web UI → kiểm tra kết quả side-by-side với ảnh gốc
- Đối chiếu kết quả trích xuất JSON với nội dung thực của văn bản
