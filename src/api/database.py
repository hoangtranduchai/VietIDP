# -*- coding: utf-8 -*-
"""
Database Models (SQLAlchemy + PostgreSQL/SQLite)
================================================
Models lưu trữ văn bản, kết quả trích xuất và log xử lý.

Database selection:
- Production: PostgreSQL (set DATABASE_URL env var)
- Development: SQLite auto-fallback (explicit, not silent)
"""

import logging
import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text, create_engine, event,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from src.config import Config

logger = logging.getLogger(__name__)

Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════
# ORM Models
# ═══════════════════════════════════════════════════════════════════════


def _utcnow():
    return datetime.now(timezone.utc)


class Document(Base):
    """Văn bản được upload lên hệ thống."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_type = Column(String(20))  # pdf, png, jpg
    file_size = Column(Integer)  # bytes
    num_pages = Column(Integer, default=1)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    extraction = relationship("ExtractionResult", back_populates="document", uselist=False, cascade="all, delete-orphan")
    logs = relationship("ProcessingLog", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "storage_name": os.path.basename(self.file_path) if self.file_path else self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "num_pages": self.num_pages,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "extraction": self.extraction.to_dict() if self.extraction else None,
        }


class ExtractionResult(Base):
    """Kết quả trích xuất thông tin từ văn bản."""
    __tablename__ = "extraction_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, unique=True)

    # Extracted fields
    loai_van_ban = Column(String(100))
    so_hieu = Column(String(100))
    ngay_ban_hanh = Column(String(20))
    co_quan_ban_hanh = Column(String(300))
    trich_yeu = Column(Text)
    nguoi_ky = Column(String(200))

    # Full data
    full_text = Column(Text)
    raw_json = Column(JSON)  # JSON gốc từ LLM
    edited_json = Column(JSON)  # JSON đã chỉnh sửa bởi user

    # Metrics
    ocr_confidence = Column(Float)
    llm_confidence = Column(Float)
    total_stamps = Column(Integer, default=0)
    stamp_coordinates = Column(JSON, default=list)

    processing_time = Column(Float)  # seconds

    # Timestamps
    created_at = Column(DateTime, default=_utcnow)
    verified_by_user = Column(Boolean, default=False)

    # Relationship
    document = relationship("Document", back_populates="extraction")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "loai_van_ban": self.loai_van_ban,
            "so_hieu": self.so_hieu,
            "ngay_ban_hanh": self.ngay_ban_hanh,
            "co_quan_ban_hanh": self.co_quan_ban_hanh,
            "trich_yeu": self.trich_yeu,
            "nguoi_ky": self.nguoi_ky,
            "ocr_confidence": self.ocr_confidence,
            "llm_confidence": self.llm_confidence,
            "total_stamps": self.total_stamps,
            "stamp_coordinates": self.stamp_coordinates,
            "processing_time": self.processing_time,
            "verified_by_user": self.verified_by_user,
            "raw_json": self.raw_json,
            "edited_json": self.edited_json,
            "full_text": self.full_text,
        }


class ProcessingLog(Base):
    """Log chi tiết quá trình xử lý."""
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    stage = Column(String(50))  # preprocessing, stamp_detection, ocr, llm, validation
    status = Column(String(20))  # started, completed, failed
    message = Column(Text)
    duration = Column(Float)  # seconds
    created_at = Column(DateTime, default=_utcnow)

    document = relationship("Document", back_populates="logs")


# ═══════════════════════════════════════════════════════════════════════
# Database Session Management
# ═══════════════════════════════════════════════════════════════════════

_engine = None
_SessionLocal = None


def _resolve_database_url() -> str:
    """Resolve the database URL with explicit dev/prod logic.

    - Production (VIETIDP_ENV=production): PostgreSQL required, no fallback.
    - Development (default): Try PostgreSQL first, fallback to SQLite with warning.
    """
    db_url = Config.DATABASE_URL
    is_prod = Config.APP_ENV in {"production", "staging"}

    if db_url.startswith("sqlite"):
        # Explicit SQLite — always allowed
        logger.info("Using explicit SQLite database: %s", db_url)
        return db_url

    # Try PostgreSQL connection
    try:
        test_engine = create_engine(db_url, echo=False)
        with test_engine.connect() as conn:
            conn.execute(test_engine.raw_connection().cursor().execute("SELECT 1") or "SELECT 1")
        test_engine.dispose()
        logger.info("Connected to PostgreSQL: %s", db_url[:50])
        return db_url
    except Exception as e:
        if is_prod:
            logger.critical("PostgreSQL connection failed in production mode: %s", e)
            raise RuntimeError(
                f"PostgreSQL is required in production mode but connection failed: {e}. "
                "Set DATABASE_URL to a valid PostgreSQL connection string."
            ) from e

        # Dev mode: graceful SQLite fallback
        sqlite_path = str(Config.DATA_DIR / "vietidp.db")
        sqlite_url = f"sqlite:///{sqlite_path}"
        logger.warning(
            "PostgreSQL unavailable (%s). Using SQLite dev fallback: %s",
            type(e).__name__, sqlite_path,
        )
        return sqlite_url


def get_engine():
    """Lấy hoặc tạo database engine."""
    global _engine
    if _engine is None:
        db_url = _resolve_database_url()

        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        _engine = create_engine(
            db_url,
            echo=Config.DATABASE_ECHO,
            connect_args=connect_args,
        )

        # Enable WAL mode for SQLite (better concurrent reads)
        if db_url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        Base.metadata.create_all(_engine)
    return _engine


def get_session():
    """Tạo database session mới."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db():
    """Khởi tạo database (tạo tất cả bảng)."""
    engine = get_engine()
    Base.metadata.create_all(engine)

    db_type = "PostgreSQL" if "postgresql" in str(engine.url) else "SQLite"
    logger.info("✅ Database initialized (%s)", db_type)
