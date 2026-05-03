# VietIDP — Vietnamese Intelligent Document Processing

<p align="center">
  <strong>Hệ thống trích xuất và cấu trúc hóa thông tin tự động từ văn bản hành chính tiếng Việt</strong><br>
  <em>OCR + LLM | 100% Offline | GPU Accelerated | On-Premise</em>
</p>

---

## 📋 Tổng quan

VietIDP là hệ thống xử lý tài liệu thông minh (IDP) chạy hoàn toàn cục bộ, kết hợp:

| Thành phần | Công nghệ | Vai trò |
|-----------|-----------|---------|
| Stamp Detection | **YOLOv8x** | Phát hiện vùng con dấu đỏ |
| Stamp Removal | **HybridStampMatting** | Xóa dấu (Color Matting + Rembg) |
| Text Detection | **EasyOCR** | Phát hiện dòng chữ (bounding boxes) |
| Text Recognition | **VietOCR** (vgg_transformer) | Nhận dạng tiếng Việt chính xác |
| Information Extraction | **Qwen2.5-7B** (Ollama, 4-bit) | Trích xuất thông tin cấu trúc JSON |
| RAG Search | **ChromaDB** + nomic-embed-text | Tìm kiếm ngữ nghĩa trên văn bản |

---

## 🏛️ Canonical Stack (Architecture Decision)

> **Quyết định kiến trúc (2026-05-03):** Hệ thống sử dụng duy nhất stack sau đây.
> Legacy Express backend (`apps/backend/`) đã được lưu trữ và không được sử dụng.

| Layer | Technology | Location |
|-------|-----------|----------|
| **Backend** | FastAPI + SQLAlchemy | `src/api/` |
| **Frontend** | React 18 + Vite | `apps/frontend/` |
| **Database** | PostgreSQL (production) / SQLite (dev) | `src/api/database.py` |
| **LLM Runtime** | Ollama (local, offline) | `src/llm/ollama_client.py` |
| **Pipeline** | VietIDPPipeline | `src/pipeline/ocr_llm_pipeline.py` |
| **Deployment** | Docker Compose | `docker-compose.yml` |

### Tại sao FastAPI thay Express?

- **Type safety**: Pydantic models + auto API docs
- **Async**: Native async/await cho GPU pipeline
- **Python ecosystem**: Trực tiếp gọi OCR/LLM Python code
- **Single language**: Không cần bridge giữa Node.js ↔ Python

---

## 💻 Yêu cầu phần cứng

### Tối thiểu (chỉ dev frontend/backend, không GPU)
- **CPU**: Intel i7 Gen 11+
- **RAM**: 8GB
- **Disk**: 10GB+

### Khuyến nghị (chạy full pipeline)
- **GPU**: NVIDIA RTX 5070 (8GB VRAM) hoặc tương đương
- **RAM**: 24GB+
- **Disk**: 50GB+ (cho models + data)
- **OS**: Windows 10/11, Ubuntu 22.04+

---

## 🚀 Cài đặt nhanh

### 1. Clone & tạo môi trường Python

```bash
git clone <repo-url>
cd OCR-LLM_Research

# Option A: Conda
conda create -n vietidp python=3.10 -y
conda activate vietidp

# Option B: venv
python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate  # Linux/Mac
```

### 2. Cài PyTorch GPU (chỉ khi có NVIDIA GPU)

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

### 3. Cài dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-gpu.txt  # Optional: GPU-specific packages
```

### 4. Cài Ollama + Pull model

```bash
# Tải Ollama: https://ollama.ai
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### 5. Cài Frontend

```bash
cd apps/frontend
npm install
```

---

## ▶️ Chạy hệ thống

### Option 1: 1-Click Script

```bash
# Windows (PowerShell)
.\start_vietidp.ps1

# Windows (CMD / Anaconda Prompt)
start_dev.bat

# Quick launch (bật tất cả ẩn + mở browser)
run_vietidp.bat
```

### Option 2: Chạy thủ công (3 terminals)

```bash
# Terminal 1 — Ollama LLM server
ollama serve

# Terminal 2 — Backend FastAPI
uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3 — Frontend React
cd apps/frontend && npm run dev
```

### Option 3: Docker Compose

```bash
docker compose up -d
```

### Truy cập

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Ollama | http://localhost:11434 |

---

## 🏗️ Kiến trúc Pipeline

```
E2E Pipeline: Image/PDF → Deskew → Denoise
              → YOLOv8x Stamp Detect → HybridStampMatting Remove
              → EasyOCR Detect + VietOCR Recognize → Raw Text
              → Qwen2.5-7B (Ollama) → Structured JSON
              → Validation → Database + Export
```

### Cấu trúc thư mục

```
├── src/
│   ├── api/              # FastAPI backend (routes, database, tasks, auth)
│   ├── llm/              # Ollama client, prompts, RAG engine
│   ├── ocr/              # VietOCR + EasyOCR engine
│   ├── pipeline/         # VietIDPPipeline (unified E2E)
│   ├── preprocessing/    # Deskew, denoise, stamp_matting
│   ├── evaluation/       # Benchmark, metrics, profiler
│   └── config.py         # Centralized configuration
├── apps/
│   ├── frontend/         # React + Vite (NeuralIDP Enterprise UI)
│   └── backend/          # ⚠️ ARCHIVED — Legacy Express (do not use)
├── scripts/              # Training, evaluation, dataset generation
├── tests/                # Unit & integration tests
├── models/               # YOLO weights, LoRA adapters (git-ignored)
├── data/                 # Raw documents, uploads (git-ignored)
├── docker-compose.yml    # Full stack deployment
└── README.md
```

---

## 🔌 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/process_document` | Upload + xử lý văn bản |
| `GET` | `/api/documents` | Danh sách documents |
| `GET` | `/api/documents/{id}` | Chi tiết 1 document |
| `GET` | `/api/documents/{id}/preview` | Preview ảnh document |
| `PUT` | `/api/documents/{id}` | Cập nhật extraction |
| `DELETE` | `/api/documents/{id}` | Xóa document |
| `GET` | `/api/export/{id}?format=json\|csv` | Export kết quả |
| `POST` | `/api/chat` | Q&A trên tài liệu |
| `GET` | `/api/health` | System health check |
| `GET` | `/api/task_status/{task_id}` | Task processing status |

---

## 📊 VRAM Budget (RTX 5070 8GB)

| Model | VRAM | Ghi chú |
|-------|------|---------|
| YOLOv8x | ~600MB | Stamp detection |
| EasyOCR | ~500MB | Text detection |
| VietOCR | ~300MB | Text recognition |
| Rembg | ~200MB | Stamp matting (ONNX) |
| Qwen2.5-7B Q4 | ~4.7GB | LLM extraction |
| **Tổng** | **~6.3GB / 8GB** | ✅ Vừa RTX 5070 |

---

## 🔒 Bảo mật

- **100% On-Premise**: Không gửi dữ liệu ra ngoài
- **API Key Auth**: Bảo vệ endpoints (configurable)
- **Upload Validation**: Kiểm tra MIME type, kích thước file
- **No Public Upload Serving**: Preview qua authenticated endpoints

---

## 🧪 Chạy audit & tests

```bash
# Kiểm tra artifacts không nên commit
python scripts/audit_artifacts.py

# Chạy unit tests
pytest tests/ -v

# Chạy benchmark (cần GPU)
python src/evaluation/benchmark.py --input data/test --ground-truth data/test/labels
```

---

## 📝 License

Dự án nghiên cứu — Đại học Bách Khoa TP.HCM
