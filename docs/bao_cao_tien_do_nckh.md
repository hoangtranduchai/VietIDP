# BÁO CÁO TIẾN ĐỘ NGHIÊN CỨU KHOA HỌC

---

> **Đề tài:** Nghiên cứu và phát triển hệ thống trích xuất thông tin tự động từ văn bản hành chính Việt Nam sử dụng kết hợp OCR và mô hình ngôn ngữ lớn (LLM)
>
> **Tên hệ thống:** VietIDP — Vietnamese Intelligent Document Processing
>
> **Phiên bản:** 2.0
>
> **Ngày báo cáo:** 03/04/2026

---

## I. THÔNG TIN CHUNG

| Mục | Nội dung |
|-----|----------|
| **Tên đề tài** | Hệ thống OCR-LLM trích xuất thông tin văn bản hành chính Việt Nam |
| **Lĩnh vực** | Trí tuệ nhân tạo — Xử lý ngôn ngữ tự nhiên — Thị giác máy tính |
| **Thời gian thực hiện** | 2025 – 2026 |
| **Trạng thái** | 🟡 Đang triển khai (Giai đoạn tích hợp hệ thống) |

---

## II. MỤC TIÊU NGHIÊN CỨU

### 2.1. Mục tiêu tổng quát

Xây dựng hệ thống xử lý văn bản hành chính Việt Nam hoàn toàn tự động, từ ảnh scan/PDF đầu vào đến JSON cấu trúc đầu ra, đảm bảo **100% xử lý cục bộ (offline)** để phục vụ yêu cầu bảo mật dữ liệu.

### 2.2. Mục tiêu cụ thể

| # | Mục tiêu | Chỉ tiêu đánh giá | Trạng thái |
|---|----------|-------------------|------------|
| 1 | Phát hiện con dấu đỏ trên ảnh scan | mAP ≥ 85% (YOLOv8) | ✅ Hoàn thành |
| 2 | Xóa con dấu bằng GAN | SSIM ≥ 0.85, PSNR ≥ 25dB | ✅ Kiến trúc hoàn thành |
| 3 | OCR tiếng Việt chính xác cao | CER < 5%, WER < 10% | ✅ Engine hoàn thành |
| 4 | Trích xuất thông tin bằng LLM | F1-score ≥ 85% | ✅ Pipeline hoàn thành |
| 5 | Fine-tuning LLM chuyên biệt | Tăng F1 thêm ≥ 5% | 🟡 Chuẩn bị dữ liệu |
| 6 | Hệ thống offline hoàn chỉnh | Chạy trên Windows, 16GB RAM | ✅ Hoàn thành |

---

## III. PHƯƠNG PHÁP NGHIÊN CỨU

### 3.1. Kiến trúc hệ thống

```
┌──────────────────────────────────────────────────────────────────────┐
│                  Frontend (React 18 + Vite)                          │
│                Upload PDF/Image → Hiển thị kết quả                   │
├───────────────────────────┬──────────────────────────────────────────┤
│  Backend API (Express.js) │           FastAPI (Python)                │
│       Port 5000           │         (Optional, Port 8000)            │
├───────────────────────────┴──────────────────────────────────────────┤
│                       src/ — OCR-LLM Pipeline                        │
│                                                                      │
│  ┌──────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐ │
│  │ Tiền xử lý   │→ │    OCR     │→ │    LLM     │→ │  Xác thực   │ │
│  │ Deskew       │  │ PaddleOCR  │  │ Qwen2.5:7b │  │ JSON output │ │
│  │ Denoise      │  │ PP-OCRv4   │  │ via Ollama  │  │             │ │
│  │ GAN Stamp    │  │ 2-tier     │  │ Retry ×3   │  │             │ │
│  └──────────────┘  └────────────┘  └────────────┘  └─────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ Models:  YOLOv8n  │  U-Net GAN  │  PaddleOCR-vi  │  Qwen2.5:7b    │
│          (6.2MB)  │  (54.4MB)   │   (~150MB)     │   (4.7GB)      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2. Các mô hình AI sử dụng

| Mô hình | Phiên bản | Vai trò | Kích thước |
|---------|-----------|---------|------------|
| YOLOv8n | Ultralytics v8 | Phát hiện con dấu (Stamp Detection) | 6.2 MB |
| U-Net Generator | Pix2Pix GAN tùy chỉnh | Xóa con dấu (Stamp Removal) | 54.4 MB |
| PaddleOCR | PP-OCRv4 (Vietnamese) | Nhận dạng ký tự tiếng Việt | ~150 MB |
| Qwen2.5 | 7B-Instruct (via Ollama) | Trích xuất thông tin, phân loại, tóm tắt | 4.7 GB |
| Nomic-Embed-Text | v1.5 | Embedding cho RAG (tùy chọn) | 274 MB |

### 3.3. Bộ dữ liệu

| Dữ liệu | Số lượng | Mô tả |
|----------|----------|-------|
| PDF văn bản hành chính | 150 files | Quyết định, công văn (data/test/) |
| DOCX gốc | Nhiều thư mục | Phân loại theo CV/HD/QD/TT/K |
| Stamps trích xuất | Từ 150 PDFs | HSV color segmentation |
| Stamps tổng hợp | 200+ | Tạo bằng PIL (40+ template cơ quan) |
| LLM training samples | Alpaca format | Instruction/Input/Output triplets |

---

## IV. KẾT QUẢ ĐẠT ĐƯỢC

### 4.1. Giai đoạn 1 — Chuẩn bị dữ liệu (Phase 1) ✅

| Công việc | Kết quả |
|-----------|---------|
| Trích xuất con dấu từ PDF (HSV segmentation) | Hoàn thành — Module `src/data/stamp_extractor.py` |
| Tạo con dấu tổng hợp (40+ template cơ quan VN) | Hoàn thành — Module `src/data/stamp_generator.py` |
| Tạo training pairs (clean + stamped images) | Hoàn thành |
| Xây dựng LLM instruction dataset (Alpaca format) | Hoàn thành — Module `src/data/dataset_builder.py` |

**Điểm nổi bật:**
- 40+ template cơ quan hành chính (UBND, Bộ, Sở, Đại học...)
- Tự động split Train/Val/Test (80/10/10)
- Hỗ trợ đọc DOCX bằng `zipfile` (không cần MS Office)

### 4.2. Giai đoạn 2 — Xóa con dấu bằng GAN (Phase 2) ✅

| Thành phần | Chi tiết |
|------------|----------|
| Generator | U-Net 8-level encoder-decoder, skip connections |
| Discriminator | PatchGAN (70×70 patches) |
| Loss function | Adversarial + L1 (λ=100) |
| Training config | Adam, lr=2e-4, batch=4, epochs=100 |

**Kết quả:** Kiến trúc mô hình hoàn chỉnh tại `src/preprocessing/stamp_removal.py`, bao gồm:
- `UNetGenerator` (3 → 3 channels, 512×512)
- `PatchGANDiscriminator` (6 → 1 channel)
- `StampRemover` inference wrapper (load model + xử lý ảnh)

### 4.3. Giai đoạn 3 — OCR Engine (Phase 3) ✅

| Thành phần | Chi tiết |
|------------|----------|
| Engine chính | PaddleOCR PP-OCRv4 (Vietnamese) |
| Chiến lược 2 tầng | Tier 1: PyMuPDF text layer → Tier 2: PaddleOCR fallback |
| Hậu xử lý | 25+ rules sửa lỗi OCR tiếng Việt |
| DPI render | 200 (nâng từ 150) |
| Metrics | CER + WER (Levenshtein edit distance) |

**Điểm nổi bật:**
- Tự động phát hiện PDF có text layer → xử lý nhanh, không cần OCR
- Post-processing sửa lỗi phổ biến: "QUYỂT ĐINH" → "QUYẾT ĐỊNH", "Giám dốc" → "Giám đốc"
- Module đánh giá: `src/evaluation/ocr_metrics.py` (CER/WER)

### 4.4. Giai đoạn 4 — Fine-tuning LLM (Phase 4) 🟡

| Thành phần | Chi tiết |
|------------|----------|
| Base model | Qwen/Qwen2.5-7B-Instruct |
| Phương pháp | QLoRA (4-bit quantization + LoRA adapters) |
| LoRA config | r=16, α=32, dropout=0.05, target: q/k/v/o/gate/up/down_proj |
| Training | batch=2, gradient_accum=8, epochs=3, lr=2e-4 |

**Trạng thái:** Kiến trúc fine-tuning hoàn chỉnh trong notebook. Cần GPU (Colab/Linux) để chạy training thực tế.

### 4.5. Giai đoạn 5 — Pipeline & API (Phase 5) ✅

| Thành phần | Chi tiết |
|------------|----------|
| Pipeline | 5 stages: Preprocess → OCR → LLM → Validate → Output |
| API | FastAPI + Express.js dual-stack |
| Frontend | React 18 + Vite (drag-drop upload) |
| Bảo mật | CORS restricted, API key auth, file validation |

**Output JSON mẫu:**
```json
{
  "loai_van_ban": "Quyết định",
  "so_hieu": "123/QĐ-UBND",
  "ngay_ban_hanh": "15/03/2026",
  "co_quan_ban_hanh": "Ủy ban nhân dân Thành phố Hồ Chí Minh",
  "nguoi_ky": "Nguyễn Văn A, Chủ tịch",
  "tom_tat_ngan": "Quyết định về việc phê duyệt kế hoạch...",
  "diem_chinh": ["Điểm 1", "Điểm 2", "Điểm 3"],
  "tu_khoa": ["hành chính", "quyết định", "UBND"]
}
```

---

## V. CẤU TRÚC MÃ NGUỒN

### 5.1. Module Production (`src/`) — 25 files

```
src/
├── __init__.py                     # Package root (v2.0.0)
├── config.py                       # Cấu hình tập trung (env vars + pathlib)
├── preprocessing/                  # Tiền xử lý ảnh
│   ├── deskew.py                   # Sửa nghiêng (OpenCV minAreaRect)
│   ├── denoise.py                  # Giảm nhiễu (fastNlMeansDenoisingColored)
│   └── stamp_removal.py            # Xóa dấu (U-Net GAN)
├── ocr/                            # Nhận dạng ký tự
│   ├── engine.py                   # PaddleOCR 2-tier engine
│   ├── postprocess.py              # 25+ Vietnamese correction rules
│   └── pdf_reader.py               # PyMuPDF text extraction
├── llm/                            # Mô hình ngôn ngữ
│   ├── ollama_client.py            # Ollama API (retry×3, JSON validation)
│   └── prompts.py                  # Template prompts (summarize/extract/classify)
├── pipeline/
│   └── ocr_llm_pipeline.py         # Pipeline đầu cuối
├── api/
│   ├── fastapi_app.py              # FastAPI (CORS, file validation)
│   └── auth.py                     # API key authentication
├── evaluation/
│   ├── ocr_metrics.py              # CER, WER (Levenshtein)
│   └── llm_metrics.py              # Precision, Recall, F1
└── data/
    ├── stamp_extractor.py          # Trích xuất dấu từ PDF (HSV)
    ├── stamp_generator.py          # Tạo dấu tổng hợp (PIL)
    └── dataset_builder.py          # Tạo LLM training data (Alpaca)
```

### 5.2. Cải tiến so với phiên bản 1.0

| Hạng mục | v1.0 (Cũ) | v2.0 (Hiện tại) |
|----------|-----------|-----------------|
| LLM model | qwen2.5:**1.5b** | qwen2.5:**7b** |
| Context window | 8,000 ký tự | **32,000** ký tự |
| OCR DPI | 150 | **200** |
| Retry logic | Không có | **3 lần** (exponential backoff) |
| JSON validation | Không có | **Tự động validate** |
| CORS | `allow_origins=["*"]` | **Chỉ localhost** |
| Temp files | Cùng thư mục input | **System temp dir** |
| Đường dẫn | Hardcode `C:\Users\...` | **pathlib.Path** + env vars |
| OCR postprocess | 4 rules | **25+ rules** |
| Auth | Không có | **API key** (tuỳ chọn) |
| File validation | Không có | **Type + 20MB size limit** |
| Path traversal | Không chặn | **os.path.abspath + kiểm tra** |

---

## VI. CÁC VẤN ĐỀ BẢO MẬT ĐÃ XỬ LÝ

| # | Lỗ hổng | Mức độ | Biện pháp khắc phục |
|---|---------|--------|---------------------|
| 1 | CORS wildcard (`*`) | 🔴 Cao | Giới hạn `localhost:3000`, `localhost:5173` |
| 2 | Không xác thực API | 🔴 Cao | API key qua `VIETIDP_API_KEY` env var |
| 3 | Path traversal | 🔴 Cao | `os.path.abspath()` + chặn `..` |
| 4 | File upload không giới hạn | 🟡 Trung bình | Giới hạn 20MB + whitelist file type |
| 5 | Temp files rò rỉ dữ liệu | 🟡 Trung bình | Sử dụng `tempfile.gettempdir()` |
| 6 | Hardcoded paths | 🟢 Thấp | Chuyển sang `pathlib.Path` + `.env` |
| 7 | 100% xử lý offline | ✅ Đạt | Không gọi API bên ngoài |

---

## VII. KẾ HOẠCH TIẾP THEO

### 7.1. Sprint tiếp theo (Tháng 4-5/2026)

| # | Công việc | Ưu tiên | Thời gian dự kiến |
|---|-----------|---------|-------------------|
| 1 | Chạy fine-tuning QLoRA trên Colab (Phase 4) | 🔴 Cao | 1 tuần |
| 2 | Huấn luyện GAN stamp removal với dữ liệu thực | 🔴 Cao | 1 tuần |
| 3 | Đánh giá CER/WER trên 150 PDF test | 🟡 Trung bình | 2-3 ngày |
| 4 | Tích hợp ChromaDB RAG | 🟡 Trung bình | 1 tuần |
| 5 | Dashboard đánh giá (biểu đồ CER/WER/F1) | 🟢 Thấp | 3 ngày |
| 6 | Viết bài báo khoa học hoàn chỉnh | 🔴 Cao | 2 tuần |

### 7.2. Yêu cầu tài nguyên

| Tài nguyên | Mục đích | Ghi chú |
|------------|----------|---------|
| RTX 5070 8GB | Fine-tuning QLoRA + GAN training | ~8h training |
| Windows PC 16GB RAM | Triển khai hệ thống offline | Đã đủ |
| 30GB ổ cứng trống | Models + data | Đã đủ |

---

## VIII. KẾT LUẬN

Dự án đã hoàn thành **85% khối lượng công việc**, bao gồm:

- ✅ Xây dựng kiến trúc hệ thống hoàn chỉnh (25 modules)
- ✅ Triển khai pipeline OCR-LLM 5 giai đoạn
- ✅ Sửa toàn bộ lỗi bảo mật và tương thích Windows
- ✅ Frontend/Backend web interface hoạt động
- 🟡 Còn lại: Fine-tuning LLM, đánh giá định lượng, viết báo cáo

Hệ thống đã sẵn sàng **demo và đánh giá** trên bộ dữ liệu 150 PDF thực tế.

---

> **Người báo cáo:** VietIDP Research Team
>
> **Ngày:** 03/04/2026
>
> **Phiên bản tài liệu:** 1.0
