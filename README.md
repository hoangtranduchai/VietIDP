# VietIDP — Vietnamese Intelligent Document Processing

<p align="center">
  <strong>Hệ thống trích xuất và cấu trúc hóa thông tin tự động từ văn bản hành chính tiếng Việt</strong><br>
  <em>OCR + LLM | 100% Offline | GPU Accelerated</em>
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

### Yêu cầu phần cứng

- **GPU**: NVIDIA RTX 5070 (8GB VRAM) hoặc tương đương
- **RAM**: 16GB+ (khuyến nghị 24GB)
- **Disk**: 20GB+ (cho models)
- **OS**: Windows 10/11, Ubuntu 22.04+

---

## 🚀 Cài đặt nhanh (Miniconda)

### 1. Tạo môi trường

```bash
conda create -n vietidp python=3.10 -y
conda activate vietidp
```

### 2. Cài PyTorch GPU

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

### 3. Cài dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-gpu.txt
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

### Option 1: 1-Click Script (Anaconda Prompt)

```bash
conda activate vietidp
cd /d E:\OCR-LLM_Research\OCR-LLM_Research
start_dev.bat
```

### Option 2: Chạy thủ công (3 terminals)

```bash
# Terminal 1 — Ollama
ollama serve

# Terminal 2 — Backend (Anaconda Prompt)
conda activate vietidp
cd /d E:\OCR-LLM_Research\OCR-LLM_Research
uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3 — Frontend
cd /d E:\OCR-LLM_Research\OCR-LLM_Research\apps\frontend
npm run dev
```

### Option 3: Docker Compose

```bash
docker compose up -d
```

### Truy cập

| Service | URL |
|---------|-----|
| Frontend (NeuralIDP) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Ollama | http://localhost:11434 |

---

## 🏗️ Kiến trúc

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
│   └── config.py         # Centralized configuration
├── apps/
│   ├── frontend/         # React + Vite (NeuralIDP Enterprise UI)
│   └── backend/          # Express.js (legacy, deprecated)
├── models/               # YOLO weights, LoRA adapters
├── data/                 # Raw documents, uploads, ChromaDB
├── docker-compose.yml    # Full stack deployment
├── start_dev.bat         # 1-click dev startup
└── README.md
```

---

## 🔌 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/process_document` | Upload + xử lý văn bản |
| `GET` | `/api/documents` | Danh sách documents |
| `GET` | `/api/documents/{id}` | Chi tiết 1 document |
| `PUT` | `/api/documents/{id}` | Cập nhật extraction |
| `DELETE` | `/api/documents/{id}` | Xóa document |
| `GET` | `/api/export/{id}?format=json|csv` | Export kết quả |
| `POST` | `/api/chat` | Q&A trên tài liệu |
| `GET` | `/api/health` | System health check |
| `GET` | `/api/task_status/{task_id}` | Celery task status |

---

## 📊 VRAM Budget

| Model | VRAM | Ghi chú |
|-------|------|---------|
| YOLOv8x | ~600MB | Stamp detection |
| EasyOCR | ~500MB | Text detection |
| VietOCR | ~300MB | Text recognition |
| Rembg | ~200MB | Stamp matting (ONNX) |
| Qwen2.5-7B Q4 | ~4.7GB | LLM extraction |
| **Tổng** | **~6.3GB / 8GB** | ✅ Vừa RTX 5070 |

---

## 📝 License

Dự án nghiên cứu — Đại học Bách Khoa TP.HCM
