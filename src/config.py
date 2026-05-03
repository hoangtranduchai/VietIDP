# -*- coding: utf-8 -*-
"""
Centralized Configuration for VietIDP
======================================
Tất cả paths, model names, hyperparameters được quản lý tập trung.
Hỗ trợ override qua environment variables.
"""

import os
from pathlib import Path


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: list[str]) -> list[str]:
    value = os.environ.get(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    """Configuration chính cho toàn bộ VietIDP pipeline."""

    # ── Project Root ──────────────────────────────────────────────────────
    BASE_DIR = Path(os.environ.get(
        "VIETIDP_BASE_DIR",
        Path(__file__).resolve().parent.parent
    ))

    # ── Data Directories ─────────────────────────────────────────────────
    DATA_DIR = BASE_DIR / "data"
    RAW_DOCX_DIR = DATA_DIR / "raw_word_files"
    TEST_PDF_DIR = DATA_DIR / "test"
    STAMPS_DIR = DATA_DIR / "stamps"
    STAMPS_EXTRACTED_DIR = STAMPS_DIR / "extracted"
    STAMPS_SYNTHETIC_DIR = STAMPS_DIR / "synthetic"
    PROCESSED_DIR = DATA_DIR / "processed"
    CLEAN_IMAGES_DIR = PROCESSED_DIR / "clean_images"
    STAMPED_IMAGES_DIR = PROCESSED_DIR / "stamped_images"
    OCR_RESULTS_DIR = DATA_DIR / "ocr_results"
    LLM_TRAINING_DIR = DATA_DIR / "llm_training"

    # ── Model Directories ────────────────────────────────────────────────
    MODELS_DIR = BASE_DIR / "models"
    STAMP_DETECTION_MODEL = MODELS_DIR / "finetuned" / "stamp_detector" / "weights" / "best.pt"
    STAMP_REMOVAL_MODEL = MODELS_DIR / "finetuned" / "stamp_removal_gan" / "best_generator.pth"
    LLM_ADAPTER_PATH = MODELS_DIR / "qwen_finetuned" / "lora_adapters"
    YOLO_BASE_MODEL = BASE_DIR / "yolov8n.pt"

    # ── Results ──────────────────────────────────────────────────────────
    RESULTS_DIR = BASE_DIR / "results"

    # ── Ollama LLM Configuration (Qwen2.5-7B) ───────────────────────────
    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    OLLAMA_MAX_CHARS = int(os.environ.get("OLLAMA_MAX_CHARS", "32000"))
    OLLAMA_NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "3000"))
    OLLAMA_TEMPERATURE = float(os.environ.get("OLLAMA_TEMPERATURE", "0.1"))
    OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))
    OLLAMA_MAX_RETRIES = int(os.environ.get("OLLAMA_MAX_RETRIES", "3"))

    # ── OCR Configuration (VietOCR + EasyOCR) ────────────────────────────
    OCR_DPI = int(os.environ.get("OCR_DPI", "200"))
    OCR_LANG = os.environ.get("OCR_LANG", "vi")
    OCR_MIN_TEXT_THRESHOLD = int(os.environ.get("OCR_MIN_TEXT_THRESHOLD", "100"))
    # VietOCR settings
    VIETOCR_MODEL = os.environ.get("VIETOCR_MODEL", "vgg_transformer")
    VIETOCR_DEVICE = os.environ.get("VIETOCR_DEVICE", "cuda:0")
    # EasyOCR settings (used as text line detector only)
    EASYOCR_LANGS = ["vi"]
    EASYOCR_GPU = True

    # ── YOLO Stamp Detection ─────────────────────────────────────────────
    YOLO_CONF_THRESHOLD = float(os.environ.get("YOLO_CONF_THRESHOLD", "0.25"))
    YOLO_IMG_SIZE = int(os.environ.get("YOLO_IMG_SIZE", "640"))

    # ── GAN Stamp Removal (deprecated - using HybridStampMatting) ────────
    GAN_IMG_SIZE = 512
    GAN_BATCH_SIZE = 4
    GAN_NUM_EPOCHS = 60
    GAN_LEARNING_RATE = 2e-4
    GAN_LAMBDA_L1 = 100

    # ── LLM Fine-tuning (Qwen2.5-7B QLoRA) ──────────────────────────────
    LLM_BASE_MODEL = os.environ.get(
        "LLM_BASE_MODEL", "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
    )
    LORA_R = 16
    LORA_ALPHA = 32
    LORA_DROPOUT = 0.05
    LORA_TARGET_MODULES = [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ]
    LLM_MAX_SEQ_LENGTH = 2048
    LLM_BATCH_SIZE = 1
    LLM_GRADIENT_ACCUM = 4
    LLM_NUM_EPOCHS = 3
    LLM_LEARNING_RATE = 2e-4

    # ── Database ─────────────────────────────────────────────────────────
    # Production: set DATABASE_URL to PostgreSQL connection string
    # Development: defaults to SQLite for zero-setup dev experience
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.environ.get('VIETIDP_BASE_DIR', str(Path(__file__).resolve().parent.parent)), 'data', 'vietidp.db')}"
    )
    DATABASE_ECHO = os.environ.get("DATABASE_ECHO", "false").lower() == "true"

    # ── Celery / Redis Task Queue ────────────────────────────────────────
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

    # ── Security ─────────────────────────────────────────────────────────
    APP_ENV = os.environ.get("VIETIDP_ENV", os.environ.get("ENV", "development")).strip().lower()
    API_KEY = os.environ.get("VIETIDP_API_KEY", "").strip()
    REQUIRE_API_KEY = _env_flag("VIETIDP_REQUIRE_API_KEY", default=APP_ENV in {"production", "staging"})
    CORS_ORIGINS = _env_csv("VIETIDP_CORS_ORIGINS", [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ])

    # ── Vietnamese Fonts (Windows → Linux fallback) ──────────────────────
    FONT_PATHS = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/times.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]

    @classmethod
    def ensure_dirs(cls):
        """Tạo tất cả thư mục cần thiết."""
        dirs = [
            cls.DATA_DIR, cls.STAMPS_EXTRACTED_DIR, cls.STAMPS_SYNTHETIC_DIR,
            cls.CLEAN_IMAGES_DIR, cls.STAMPED_IMAGES_DIR,
            cls.OCR_RESULTS_DIR, cls.LLM_TRAINING_DIR,
            cls.MODELS_DIR, cls.RESULTS_DIR,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_font(cls):
        """Trả về font path đầu tiên tồn tại trên hệ thống."""
        for fp in cls.FONT_PATHS:
            if os.path.exists(fp):
                return fp
        return None
