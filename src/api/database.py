# -*- coding: utf-8 -*-
"""
Database Models (SQLAlchemy + PostgreSQL)
==========================================
Models lưu trữ văn bản, kết quả trích xuất và log xử lý.
"""

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float,
    DateTime, JSON, Boolean, ForeignKey, Enum
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from src.config import Config

Base = declarative_base()


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    extraction = relationship("ExtractionResult", back_populates="document", uselist=False, cascade="all, delete-orphan")
    logs = relationship("ProcessingLog", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
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
    processing_time = Column(Float)  # seconds

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="logs")


# ═══════════════════════════════════════════════════════════════════════
# Database Session Management
# ═══════════════════════════════════════════════════════════════════════

_engine = None
_SessionLocal = None


def get_engine():
    """Lấy hoặc tạo database engine."""
    global _engine
    if _engine is None:
        db_url = Config.DATABASE_URL
        # Fallback sang SQLite nếu PostgreSQL không available
        try:
            _engine = create_engine(db_url, echo=Config.DATABASE_ECHO)
            # Test connection
            with _engine.connect() as conn:
                conn.execute(Base.metadata.create_all(_engine) or "SELECT 1")
        except Exception:
            print("⚠️ PostgreSQL không khả dụng, dùng SQLite fallback")
            sqlite_path = str(Config.DATA_DIR / "vietidp.db")
            db_url = f"sqlite:///{sqlite_path}"
            _engine = create_engine(db_url, echo=Config.DATABASE_ECHO)

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
    print("✅ Database initialized")
