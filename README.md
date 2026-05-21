# VietIDP — Vietnamese Intelligent Document Processing

<p align="center">
  <strong>Hệ thống trích xuất và cấu trúc hóa thông tin tự động từ văn bản hành chính tiếng Việt</strong><br>
  <em>OCR + LLM | 100% Offline | GPU Accelerated | On-Premise</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/CUDA-12.8-76B900?logo=nvidia&logoColor=white" alt="CUDA">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

---

## 📋 Mục lục

1. [Giới thiệu dự án](#-giới-thiệu-dự-án)
2. [Tính năng chính](#-tính-năng-chính)
3. [Tech Stack](#-tech-stack)
4. [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
5. [Cài đặt](#-cài-đặt)
6. [Biến môi trường](#-biến-môi-trường)
7. [Chạy local](#-chạy-local)
8. [Build](#-build)
9. [Test](#-test)
10. [Deploy](#-deploy)
11. [Troubleshooting](#-troubleshooting)
12. [Tài khoản demo](#-tài-khoản-demo)

---

## 1. 🎯 Giới thiệu dự án

**VietIDP** (Vietnamese Intelligent Document Processing) là hệ thống xử lý tài liệu thông minh chạy **100% cục bộ (on-premise)**, được thiết kế đặc biệt cho văn bản hành chính tiếng Việt.

**Tên đề tài:** Nghiên cứu xây dựng hệ thống trích xuất và cấu trúc hóa thông tin tự động từ văn bản hành chính tiếng Việt sử dụng Mô hình ngôn ngữ lớn (LLMs) và công nghệ OCR phục vụ công tác chuyển đổi số.

**Thành tích:** Top 7 (giải khuyến khích) đề tài xuất sắc nhất khoa IT, Đại học Bách khoa Đà Nẵng.

Hệ thống kết hợp **Computer Vision** (YOLO, OCR) với **Large Language Model** (Qwen2.5-7B) để tự động:

- 🔍 Phát hiện và xóa con dấu đỏ trên văn bản
- 📝 Nhận dạng chữ tiếng Việt với độ chính xác cao
- 🧠 Trích xuất thông tin cấu trúc (số hiệu, ngày ban hành, cơ quan, nội dung...)
- 💬 Hỗ trợ hỏi đáp ngữ nghĩa (RAG) trên kho văn bản

### Pipeline End-to-End

```
Image/PDF → Deskew → Denoise
          → YOLOv8x Stamp Detect → HybridStampMatting Remove
          → EasyOCR Detect + VietOCR Recognize → Raw Text
          → Qwen2.5-7B (Ollama 4-bit) → Structured JSON
          → Validation → Database + Export
```

### Yêu cầu phần cứng

| Cấu hình | CPU | RAM | GPU | Disk |
|-----------|-----|-----|-----|------|
| **Tối thiểu** (dev frontend/backend) | Intel i7 Gen 11+ | 8 GB | — | 10 GB |
| **Khuyến nghị** (full pipeline) | Intel i7 Gen 11+ | 24 GB+ | NVIDIA RTX 5070 (8 GB VRAM) | 50 GB+ |

**OS hỗ trợ:** Windows 10/11, Ubuntu 22.04+

---

## 2. ✨ Tính năng chính

### Xử lý tài liệu

| Tính năng | Mô tả |
|-----------|--------|
| **Stamp Detection** | Phát hiện vùng con dấu đỏ bằng YOLOv8x |
| **Stamp Removal** | Xóa dấu bằng HybridStampMatting (Color Matting + Rembg ONNX) — 0 VRAM |
| **Text Detection** | Phát hiện dòng chữ (bounding boxes) bằng EasyOCR |
| **Text Recognition** | Nhận dạng tiếng Việt chính xác bằng VietOCR (vgg_transformer) |
| **Information Extraction** | Trích xuất thông tin cấu trúc JSON bằng Qwen2.5-7B (4-bit quantized) |
| **RAG Search** | Tìm kiếm ngữ nghĩa trên văn bản bằng ChromaDB + nomic-embed-text |

### Giao diện người dùng (VietIDP Web UI)

- **Dashboard** — Tổng quan hệ thống, thống kê xử lý
- **Workspace** — Upload, xem preview, chỉnh sửa extraction
- **Processing** — Theo dõi tiến trình xử lý realtime
- **History** — Lịch sử tài liệu đã xử lý
- **Benchmark** — Đánh giá hiệu năng pipeline
- **Chatbot** — Hỏi đáp ngữ nghĩa trên kho văn bản
- **Export** — Xuất kết quả JSON / CSV
- 🌙 Dark mode, 🌐 Đa ngôn ngữ (VI/EN), 📱 Responsive

### Bảo mật

- **100% On-Premise** — Không gửi dữ liệu ra ngoài
- **API Key Auth** — Bảo vệ endpoints (configurable)
- **Upload Validation** — Kiểm tra MIME type, kích thước file
- **No Public Upload Serving** — Preview qua authenticated endpoints

---

## 3. 🛠️ Tech Stack

### Backend

| Thành phần | Công nghệ | Phiên bản |
|------------|-----------|-----------|
| Web Framework | FastAPI | ≥ 0.100 |
| ORM | SQLAlchemy | ≥ 2.0 |
| Database (prod) | PostgreSQL | 16 |
| Database (dev) | SQLite | — |
| Validation | Pydantic | ≥ 2.0 |
| ASGI Server | Uvicorn | ≥ 0.23 |

### AI / ML Pipeline

| Thành phần | Công nghệ | Vai trò |
|------------|-----------|---------|
| Stamp Detection | YOLOv8x (Ultralytics) | Phát hiện con dấu |
| Stamp Removal | HybridStampMatting + Rembg | Xóa dấu (Color Matting + ONNX) |
| Text Detection | EasyOCR | Phát hiện bounding boxes |
| Text Recognition | VietOCR (vgg_transformer) | Nhận dạng tiếng Việt |
| LLM Extraction | Qwen2.5-7B via Ollama (4-bit) | Trích xuất cấu trúc JSON |
| RAG | ChromaDB + nomic-embed-text | Tìm kiếm ngữ nghĩa |
| Image Processing | OpenCV, Pillow, PyMuPDF | Deskew, denoise, PDF→Image |
| GPU Runtime | PyTorch + CUDA 12.8 | GPU acceleration |

### Frontend

| Thành phần | Công nghệ | Phiên bản |
|------------|-----------|-----------|
| UI Framework | React | 18 |
| Build Tool | Vite | 5 |
| Routing | React Router | 6 |
| HTTP Client | Axios | ^1.7 |
| Icons | Lucide React | ^0.460 |
| Notifications | React Toastify | ^10.0 |
| File Upload | React Dropzone | ^14.3 |

### DevOps

| Thành phần | Công nghệ |
|------------|-----------|
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Linting | ESLint (frontend), pre-commit (backend) |

### VRAM Budget (RTX 5070 — 8 GB)

| Model | VRAM | Ghi chú |
|-------|------|---------|
| YOLOv8x | ~600 MB | Stamp detection |
| EasyOCR | ~500 MB | Text detection |
| VietOCR | ~300 MB | Text recognition |
| Rembg | ~200 MB | Stamp matting (ONNX) |
| Qwen2.5-7B Q4 | ~4.7 GB | LLM extraction |
| **Tổng** | **~6.3 GB / 8 GB** | ✅ Vừa RTX 5070 |

---

## 4. 📁 Cấu trúc thư mục

```
OCR-LLM_Research/
├── src/                          # Source code chính (Python)
│   ├── api/                      # FastAPI backend
│   │   ├── fastapi_app.py        #   App entry point + middleware
│   │   ├── routes.py             #   API endpoints
│   │   ├── database.py           #   SQLAlchemy models + session
│   │   ├── schemas.py            #   Pydantic request/response schemas
│   │   ├── tasks.py              #   Background document processing
│   │   ├── auth.py               #   API key authentication
│   │   └── storage.py            #   File storage management
│   ├── pipeline/                 # VietIDP Pipeline
│   │   ├── ocr_llm_pipeline.py   #   Unified E2E pipeline (main)
│   │   ├── end_to_end.py         #   Simplified E2E runner
│   │   ├── layout_regions.py     #   Document layout analysis
│   │   └── stamp_pipeline.py     #   Stamp-only sub-pipeline
│   ├── ocr/                      # OCR Engine
│   │   ├── engine.py             #   VietOCR + EasyOCR integration
│   │   ├── pdf_reader.py         #   PDF → Image converter
│   │   └── postprocess.py        #   OCR text post-processing
│   ├── llm/                      # LLM Engine
│   │   ├── ollama_client.py      #   Ollama API client
│   │   ├── prompts.py            #   Prompt templates (hard-prompting)
│   │   ├── rag_engine.py         #   ChromaDB RAG search
│   │   └── qlora_engine.py       #   QLoRA fine-tuning engine
│   ├── preprocessing/            # Image Preprocessing
│   │   ├── deskew.py             #   Document deskew correction
│   │   ├── denoise.py            #   Noise removal
│   │   ├── stamp_matting.py      #   HybridStampMatting (color-based)
│   │   └── stamp_removal.py      #   Stamp removal orchestrator
│   ├── evaluation/               # Benchmark & Metrics
│   │   ├── benchmark.py          #   Full benchmark runner
│   │   ├── extraction_metrics.py #   Field-level accuracy metrics
│   │   ├── ocr_metrics.py        #   OCR CER/WER metrics
│   │   ├── profiler.py           #   Performance profiler
│   │   └── report_generator.py   #   HTML/Markdown report generation
│   └── config.py                 # Centralized configuration
│
├── apps/
│   └── frontend/                 # React + Vite (VietIDP Web UI)
│       ├── src/
│       │   ├── pages/            #   Dashboard, Workspace, History, ...
│       │   ├── components/       #   Reusable UI components
│       │   ├── hooks/            #   Custom React hooks
│       │   ├── services/         #   API service layer
│       │   ├── layouts/          #   Page layouts
│       │   └── ui/               #   Base UI primitives
│       ├── index.html
│       └── vite.config.js
│
├── scripts/                      # Utility scripts
│   ├── train_yolo.py             #   Train YOLO stamp detector
│   ├── train_qlora.py            #   QLoRA fine-tuning
│   ├── run_full_benchmark.py     #   Complete benchmark suite
│   ├── audit_artifacts.py        #   Check for uncommittable files
│   └── ...
│
├── tests/                        # Unit & integration tests
│   ├── test_api_health.py
│   ├── test_pipeline.py
│   ├── test_evaluation_bootstrap.py
│   └── test_normalization_metrics.py
│
├── models/                       # Model weights (git-ignored)
├── data/                         # Documents & uploads (git-ignored)
├── docs/                         # Research papers & documentation
│
├── docker-compose.yml            # Full stack deployment
├── Dockerfile.backend            # Backend CUDA image
├── Dockerfile.frontend           # Frontend Nginx image
├── requirements.txt              # Core Python dependencies
├── requirements-gpu.txt          # GPU-specific dependencies
├── requirements-full.txt         # All dependencies (research)
├── package.json                  # Monorepo root scripts
├── .env.example                  # Environment template
├── .github/workflows/ci.yml      # GitHub Actions CI
├── start_dev.bat                 # 1-click dev startup (CMD)
├── start_vietidp.ps1             # 1-click dev startup (PowerShell)
├── run_vietidp.bat               # Quick launch (hidden windows)
└── README.md
```

---

## 5. 📦 Cài đặt

### Bước 1: Clone repository

```bash
git clone <repo-url>
cd OCR-LLM_Research
```

### Bước 2: Tạo môi trường Python

```bash
# Option A: Conda (khuyến nghị)
conda create -n vietidp python=3.10 -y
conda activate vietidp

# Option B: venv
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac
```

### Bước 3: Cài PyTorch GPU (chỉ khi có NVIDIA GPU)

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

> **Lưu ý:** Nếu không có GPU, bỏ qua bước này. Pipeline sẽ chạy trên CPU (chậm hơn đáng kể).

### Bước 4: Cài Python dependencies

```bash
pip install -r requirements.txt

# Optional: GPU-specific packages (onnxruntime-gpu)
pip install -r requirements-gpu.txt

# Optional: Full research dependencies (training, visualization)
pip install -r requirements-full.txt
```

### Bước 5: Cài Ollama + Pull models

```bash
# Tải Ollama: https://ollama.ai
ollama pull qwen2.5:7b          # ~4.7 GB — LLM extraction
ollama pull nomic-embed-text    # ~274 MB — RAG embeddings
```

### Bước 6: Cài Frontend

```bash
cd apps/frontend
npm install
```

---

## 6. 🔐 Biến môi trường

Sao chép file mẫu và chỉnh sửa:

```bash
cp .env.example .env
```

### Danh sách biến

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| **Ollama LLM** | | |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model LLM sử dụng |
| `OLLAMA_MAX_CHARS` | `32000` | Giới hạn ký tự input |
| `OLLAMA_NUM_PREDICT` | `3000` | Max tokens output |
| `OLLAMA_TEMPERATURE` | `0.1` | Sampling temperature |
| `OLLAMA_TIMEOUT` | `300` | Timeout (giây) |
| **OCR** | | |
| `OCR_DPI` | `200` | DPI khi chuyển PDF→Image |
| `OCR_LANG` | `vi` | Ngôn ngữ OCR |
| **YOLO** | | |
| `YOLO_CONF_THRESHOLD` | `0.5` | Ngưỡng confidence stamp detection |
| **Security** | | |
| `VIETIDP_ENV` | `development` | Môi trường: `development` / `production` |
| `VIETIDP_REQUIRE_API_KEY` | `false` | Bật/tắt xác thực API key |
| `VIETIDP_API_KEY` | _(trống)_ | API key (bắt buộc nếu require=true) |
| `VIETIDP_CORS_ORIGINS` | `http://localhost:3000,...` | Danh sách CORS origins |
| **Frontend (Vite)** | | |
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL cho frontend |
| `VITE_API_KEY` | _(trống)_ | API key cho frontend (dev only) |
| **Server** | | |
| `PORT` | `8000` | Backend port |
| `DATABASE_URL` | `sqlite:///data/vietidp.db` | Database connection string |

---

## 7. ▶️ Chạy local

### Option 1: 1-Click Script (khuyến nghị)

```bash
# Windows — Anaconda Prompt / CMD
start_dev.bat

# Windows — PowerShell
.\start_vietidp.ps1

# Quick launch (bật tất cả ẩn + mở browser)
run_vietidp.bat
```

Script tự động: activate conda → kiểm tra GPU → kiểm tra dependencies → start Ollama → pull model → start frontend + backend.

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
| 🖥️ Frontend | http://localhost:5173 |
| ⚡ Backend API | http://localhost:8000 |
| 📖 API Docs (Swagger) | http://localhost:8000/docs |
| 🤖 Ollama | http://localhost:11434 |

### API Endpoints chính

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/process_document` | Upload + xử lý văn bản |
| `GET` | `/api/documents` | Danh sách documents |
| `GET` | `/api/documents/{id}` | Chi tiết 1 document |
| `GET` | `/api/documents/{id}/preview` | Preview ảnh document |
| `PUT` | `/api/documents/{id}` | Cập nhật extraction |
| `DELETE` | `/api/documents/{id}` | Xóa document |
| `GET` | `/api/export/{id}?format=json\|csv` | Export kết quả |
| `POST` | `/api/chat` | Q&A trên tài liệu (RAG) |
| `GET` | `/api/health` | System health check |
| `GET` | `/api/task_status/{task_id}` | Task processing status |

---

## 8. 🏗️ Build

### Frontend production build

```bash
cd apps/frontend
npm run build
```

Output tĩnh nằm trong `apps/frontend/dist/`, sẵn sàng serve qua Nginx hoặc bất kỳ static server.

### Preview production build locally

```bash
cd apps/frontend
npm run preview
```

### Docker images

```bash
# Build backend image (CUDA 12.8)
docker build -f Dockerfile.backend -t vietidp-backend .

# Build frontend image (Nginx)
docker build -f Dockerfile.frontend -t vietidp-frontend .

# Build cả hai qua Compose
docker compose build
```

### Frontend build với custom API URL

```bash
VITE_API_URL=https://api.example.com npm run build
```

---

## 9. 🧪 Test

### Unit & Integration tests

```bash
# Chạy toàn bộ test suite
pytest tests/ -v

# Chạy với coverage report
pytest tests/ -v --tb=short --cov=src

# Chạy test cụ thể
pytest tests/test_api_health.py -v
pytest tests/test_pipeline.py -v
pytest tests/test_normalization_metrics.py -v
```

### Frontend linting

```bash
cd apps/frontend
npx eslint src/
```

### Artifact guard (kiểm tra file không nên commit)

```bash
python scripts/audit_artifacts.py
```

### Benchmark pipeline (cần GPU + Ollama)

```bash
# Quick benchmark
python scripts/quick_benchmark.py

# Full benchmark với ground truth
python scripts/run_full_benchmark.py

# Benchmark evaluation module
python src/evaluation/benchmark.py --input data/test --ground-truth data/test/labels
```

### CI/CD (GitHub Actions)

CI tự động chạy khi push lên `main`/`develop` hoặc tạo PR vào `main`:

- ✅ **backend-tests** — `pytest tests/ -v` (Python 3.10)
- ✅ **frontend-build** — `npm ci && npm run build` (Node 20)
- ✅ **artifact-guard** — Kiểm tra model weights, DB files, logs không bị commit
- ✅ **docker-smoke** — Build Docker images (chỉ trên `main`)

---

## 10. 🚀 Deploy

### Option 1: Docker Compose (khuyến nghị cho production)

```bash
# 1. Cấu hình biến môi trường
cp .env.example .env
# Sửa .env: DATABASE_URL, VIETIDP_ENV=production, VIETIDP_REQUIRE_API_KEY=true, ...

# 2. Start toàn bộ stack
docker compose up -d

# 3. Pull model Ollama (lần đầu)
docker exec -it vietidp-ollama ollama pull qwen2.5:7b
docker exec -it vietidp-ollama ollama pull nomic-embed-text

# 4. Kiểm tra health
curl http://localhost:8000/api/health
```

**Stack bao gồm:**

| Container | Port | Mô tả |
|-----------|------|-------|
| `vietidp-backend` | 8000 | FastAPI + GPU pipeline |
| `vietidp-frontend` | 3000 | Nginx serving React SPA |
| `vietidp-postgres` | — | PostgreSQL 16 (internal only) |
| `vietidp-ollama` | — | Ollama LLM server (internal only) |

> **Yêu cầu:** `nvidia-container-toolkit` cho GPU passthrough.

### Option 2: Deploy thủ công

```bash
# 1. Database: PostgreSQL
export DATABASE_URL=postgresql://vietidp:password@localhost:5432/vietidp

# 2. Ollama
ollama serve &
ollama pull qwen2.5:7b

# 3. Backend
uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000 --workers 1

# 4. Frontend (build + serve qua Nginx)
cd apps/frontend && npm run build
# Copy dist/ vào Nginx webroot
```

### Lưu ý production

- Đặt `VIETIDP_ENV=production` và `VIETIDP_REQUIRE_API_KEY=true`
- Sử dụng PostgreSQL thay SQLite
- Đặt `VIETIDP_CORS_ORIGINS` chỉ chứa domain thật
- **Không** expose port Ollama/PostgreSQL ra ngoài
- Cấu hình reverse proxy (Nginx/Caddy) với HTTPS

---

## 11. 🔧 Troubleshooting

### Ollama không khởi động

```bash
# Kiểm tra Ollama đang chạy
curl http://localhost:11434/api/tags

# Khởi động lại
ollama serve

# Kiểm tra model đã pull
ollama list
```

### CUDA / GPU không nhận

```bash
# Kiểm tra PyTorch nhận GPU
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"

# Nếu False, cài lại PyTorch đúng CUDA version
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

### Out of VRAM

- Đảm bảo tổng VRAM < 8 GB (xem bảng VRAM Budget)
- Đóng các app khác đang dùng GPU
- Giảm `YOLO_IMG_SIZE` trong `.env`
- Sử dụng model nhỏ hơn: `ollama pull qwen2.5:3b`

### Frontend không kết nối được Backend

```bash
# Kiểm tra backend đang chạy
curl http://localhost:8000/api/health

# Kiểm tra CORS — đảm bảo frontend origin nằm trong VIETIDP_CORS_ORIGINS
# Kiểm tra VITE_API_URL trong .env trỏ đúng backend
```

### Database lỗi `PendingRollbackError`

```bash
# SQLite (dev) — xóa DB và tạo lại
rm data/vietidp.db
# Restart backend, DB sẽ tự tạo lại

# PostgreSQL — kiểm tra connection
psql -U vietidp -h localhost -d vietidp
```

### Port đã bị chiếm

```bash
# Windows — tìm process dùng port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux
lsof -i :8000
kill -9 <PID>
```

### Import lỗi module `src`

```bash
# Chạy từ project root, không phải sub-folder
# Đảm bảo PYTHONPATH chứa project root
set PYTHONPATH=E:\OCR-LLM_Research    # Windows
export PYTHONPATH=/path/to/OCR-LLM_Research  # Linux
```

---

## 12. 👤 Tài khoản demo

### API Key (Development)

Ở chế độ `development` (mặc định), API **không yêu cầu authentication**. Bạn có thể truy cập tất cả endpoints mà không cần API key.

Để bật authentication:

```env
VIETIDP_REQUIRE_API_KEY=true
VIETIDP_API_KEY=your-secret-key-here
```

Sau đó gửi request với header:

```bash
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/api/documents
```

Frontend cũng cần set `VITE_API_KEY` tương ứng trong `.env`.

### Swagger UI

Truy cập http://localhost:8000/docs để thử API trực tiếp trên trình duyệt với giao diện Swagger tự động từ FastAPI.

---

## 📝 License

MIT — Dự án nghiên cứu khoa học sinh viên, Khoa Công nghệ Thông tin, Trường Đại học Bách khoa, Đại học Đà Nẵng (DUT).

---

## 👥 Thông tin nhóm nghiên cứu

**Đề tài:** Nghiên cứu xây dựng hệ thống trích xuất và cấu trúc thông tin tự động từ văn bản hành chính tiếng Việt sử dụng mô hình ngôn ngữ lớn (LLMs) và công nghệ OCR phục vụ công tác chuyển đổi số

| Vai trò | Họ và tên | Email |
|---------|-----------|-------|
| **SVTH** | Nguyễn Tiến | nguyentien281006@gmail.com |
| **SVTH** | Nguyễn Hữu Thái | thaivuivui@gmail.com |
| **SVTH** | Hoàng Trần Đức Hải | hoangtranduchai@gmail.com |
| **GVHD** | TS. Nguyễn Năng Hùng Vân | nguyenvan@dut.udn.vn |

**Lớp:** 24T_Nhat1 · **Khoa:** Công nghệ Thông tin · **Trường:** Đại học Bách khoa, Đại học Đà Nẵng

---

<p align="center">
  <sub>Built with ❤️ by Nguyễn Tiến, Nguyễn Hữu Thái, Hoàng Trần Đức Hải — DUT 2025-2026</sub>
</p>
