# 🇻🇳 VietIDP — Vietnamese Intelligent Document Processing

> Hệ thống trích xuất thông tin tự động từ văn bản hành chính Việt Nam, sử dụng kết hợp **Computer Vision** (YOLOv8 + Pix2Pix GAN), **OCR** (PaddleOCR PP-OCRv4), và **LLM** (Qwen2.5:7b via Ollama).

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![NodeJS](https://img.shields.io/badge/Node.js-20-339933?logo=node.js&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![License](https://img.shields.io/badge/License-Internal-red)

## 📋 Tổng quan

VietIDP giải quyết bài toán **số hóa văn bản hành chính** end-to-end:

1. **Stamp Detection** (YOLOv8) — Phát hiện vị trí con dấu đỏ trên ảnh scan
2. **Stamp Removal** (Pix2Pix GAN) — Xóa con dấu để cải thiện OCR
3. **OCR** (PaddleOCR PP-OCRv4) — Nhận dạng chữ tiếng Việt (2-tier: text layer → OCR fallback)
4. **Information Extraction** (Qwen2.5:7b) — Trích xuất: loại văn bản, số hiệu, ngày, cơ quan, người ký
5. **QLoRA Fine-tuning** — Tinh chỉnh LLM trên dữ liệu hành chính Việt Nam

**100% xử lý cục bộ (offline)** — Không gửi dữ liệu ra internet.

## 🏗️ Kiến trúc hệ thống

```text
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React 18 + Vite)               │
│            Upload PDF/Image → Hiển thị kết quả              │
├──────────────────────────┬──────────────────────────────────┤
│   Backend (Express.js)   │      FastAPI (Python)            │
│   Port 5000              │      (Optional, Port 8000)       │
├──────────────────────────┴──────────────────────────────────┤
│                         src/ Pipeline                       │
│  ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │Preprocessing│→│   OCR    │→│   LLM    │→│  Validation  │ │
│  │Deskew+Denoi-│ │PaddleOCR │ │Qwen2.5:7b│ │ JSON Output  │ │
│  │se+GAN       │ │PP-OCRv4  │ │via Ollama│ │              │ │
│  └─────────────┘ └──────────┘ └──────────┘ └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Models: YOLOv8n │ U-Net GAN │ PaddleOCR │ Qwen2.5:7b       │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Cấu trúc thư mục (Chuẩn MLOps)

```text
OCR-LLM_Research/
│
├── data/                       # Dữ liệu phục vụ AI
│   ├── raw/                    # Dữ liệu gốc (docx_raw, pdf_test, stamps_raw)
│   ├── interim/                # Dữ liệu trung gian (stamps_transparent, stamps_synthetic)
│   └── processed/              # Dữ liệu đã làm sạch cho Train (pix2pix_dataset, yolo_dataset, llm_instruction)
│
├── models/                     # Trọng số mô hình
│   ├── base_models/            # Các model nền tảng tải từ ngoài (VD: yolov8n.pt)
│   └── finetuned/              # Checkpoint model sinh ra sau khi huấn luyện
│
├── src/                        # Chứa Core Modules (Production)
│   ├── api/                    # FastAPI
│   ├── data/                   # Utilities cho dữ liệu
│   ├── evaluation/             # Đánh giá Metrics (CER, WER, F1)
│   ├── llm/                    # Prompt Templates & Ollama logic
│   ├── ocr/                    # Lớp điều khiển PaddleOCR / VietOCR
│   ├── pipeline/               # Kịch bản tích hợp end-to-end
│   ├── preprocessing/          # Deskew, xóa dấu, lọc nhiễu
│   └── config.py               # Biến môi trường hệ thống
│
├── scripts/                    # Các script tạo data, thử nghiệm, training (Tooling)
│   ├── generate_dataset.py
│   ├── generate_pix2pix_dataset.py
│   ├── remove_bg_batch.py
│   └── train_yolo.py
│
├── apps/                       # Web Applications
│   ├── frontend/               # React18 + Vite (UI Side-by-side)
│   └── backend/                # Express.js HTTP Server
│
├── notebooks/                  # Các phase Jupyter Notebook Research thử nghiệm độc lập
│
├── docs/                       # Tài liệu nghiên cứu, công bố khoa học
│   ├── bao_cao_tien_do_nckh.md
│   ├── de_cuong_nghien_cuu.pdf
│   └── final_tri.pdf
│
└── config files (.env, .gitignore, requirements.txt, Dockerfile)
```

## 🚀 Cài đặt nhanh (Windows)

### Yêu cầu tối thiểu
- **RAM**: 16 GB (cho Qwen2.5:7b)
- **Storage**: 30 GB trống
- **Python**: 3.10+
- **Node.js**: 20+
- **Ollama**: Đã cài đặt ([ollama.ai](https://ollama.ai))

### Bước 1: Pull models

```powershell
# Pull Qwen2.5:7b LLM (4.7 GB)
ollama pull qwen2.5:7b

# (Tùy chọn) Pull embedding model cho RAG
ollama pull nomic-embed-text
```

### Bước 2: Cài dependencies

```powershell
# Python dependencies (CPU)
pip install -r requirements.txt

# Frontend dependencies
cd apps/frontend && npm install && cd ../..

# Backend dependencies
cd apps/backend && npm install && cd ../..
```

### Bước 3: Khởi động

```powershell
# Khởi động Backend + Frontend riêng biệt
ollama serve                                     # Terminal 1
node apps/backend/index.js                       # Terminal 2
cd apps/frontend && npx vite --port 5173         # Terminal 3
```

Truy cập: **http://localhost:5173**

## 🔧 Configuration

Sao chép `.env.example` → `.env` và sửa:

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model Ollama |
| `OLLAMA_MAX_CHARS` | `32000` | Giới hạn ký tự input |
| `OCR_DPI` | `200` | DPI render PDF→ảnh |
| `VIETIDP_API_KEY` | _(trống)_ | API key (trống = tắt auth) |

## 📊 Evaluation Metrics

| Metric | Mô tả | Target |
|--------|--------|--------|
| CER | Character Error Rate | < 5% |
| WER | Word Error Rate | < 10% |
| F1 | Trích xuất thông tin | > 85% |

```python
from src.evaluation import compute_cer
cer = compute_cer("Cộng hòa xã hội chủ nghĩa Việt Nam", ocr_text)
```

## 🔒 Bảo mật

- ✅ CORS restricted (localhost only)
- ✅ 100% offline processing
- ✅ No external API calls

## 📖 Nghiên cứu

Dự án phục vụ nghiên cứu khoa học, tham khảo:
- `docs/final_tri.pdf` — Bài báo nghiên cứu
- `docs/de_cuong_nghien_cuu.pdf` — Đề cương chi tiết
- `notebooks/` — 5 Phase nghiên cứu đầy đủ

---
**VietIDP v2.0** | VietIDP Research Team | 2026
