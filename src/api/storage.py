# -*- coding: utf-8 -*-
"""
Storage Management — VietIDP
==============================
Centralized path generation, file management, and retention policy
for all document processing artifacts.

Storage layout:
    data/uploads/          — Raw uploaded files (safe filenames)
    data/uploads/previews/ — Derived page previews (PDF → images)
    results/               — Processing result JSONs
    results/debug_outputs/ — Debug stage outputs
"""

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from src.config import Config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Path Configuration
# ═══════════════════════════════════════════════════════════════════════

UPLOAD_DIR = Config.DATA_DIR / "uploads"
PREVIEW_DIR = UPLOAD_DIR / "previews"
RESULTS_DIR = Config.RESULTS_DIR
DEBUG_DIR = RESULTS_DIR / "debug_outputs"

# Ensure directories exist
for _dir in (UPLOAD_DIR, PREVIEW_DIR, RESULTS_DIR, DEBUG_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# Allowed extensions and size limits
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


# ═══════════════════════════════════════════════════════════════════════
# Path Generation
# ═══════════════════════════════════════════════════════════════════════


def generate_storage_name(extension: str) -> str:
    """Generate a safe, unique storage filename."""
    ext = extension.lower().lstrip(".")
    return f"{uuid.uuid4().hex}.{ext}"


def get_upload_path(storage_name: str) -> Path:
    """Get the full path for a stored upload."""
    return UPLOAD_DIR / storage_name


def get_preview_path(storage_name: str) -> Path:
    """Get the full path for a preview image."""
    return PREVIEW_DIR / storage_name


def get_result_path(doc_id: int, suffix: str = "result") -> Path:
    """Get the full path for a processing result file."""
    return RESULTS_DIR / f"doc_{doc_id}_{suffix}.json"


def get_debug_path(doc_id: int, stage: str) -> Path:
    """Get the full path for a debug output."""
    doc_dir = DEBUG_DIR / f"doc_{doc_id}"
    doc_dir.mkdir(parents=True, exist_ok=True)
    return doc_dir / f"{stage}.json"


# ═══════════════════════════════════════════════════════════════════════
# File Operations
# ═══════════════════════════════════════════════════════════════════════


def resolve_safe_path(candidate: Path, allowed_root: Path) -> Optional[Path]:
    """Resolve and validate a path is within the allowed root directory.

    Returns None if the path escapes the allowed root (path traversal protection).
    """
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError):
        return None

    root_resolved = allowed_root.resolve()
    if resolved == root_resolved or root_resolved in resolved.parents:
        return resolved

    logger.warning("Path traversal attempt blocked: %s not under %s", candidate, allowed_root)
    return None


def delete_document_files(
    file_path: Optional[str],
    page_files: Optional[List[str]] = None,
) -> int:
    """Delete all files associated with a document.

    Args:
        file_path: The main uploaded file path.
        page_files: List of page preview filenames.

    Returns:
        Number of files successfully deleted.
    """
    deleted = 0
    candidates: List[Path] = []

    if file_path:
        candidates.append(Path(file_path))

    if page_files:
        for pf in page_files:
            candidates.append(UPLOAD_DIR / str(pf))

    for candidate in candidates:
        safe_path = resolve_safe_path(candidate, UPLOAD_DIR)
        if safe_path and safe_path.is_file():
            try:
                os.remove(safe_path)
                deleted += 1
                logger.info("Deleted file: %s", safe_path.name)
            except OSError as e:
                logger.warning("Failed to delete %s: %s", safe_path, e)

    return deleted


def cleanup_orphan_uploads(known_filenames: set[str]) -> int:
    """Remove upload files that are not tracked in the database.

    Args:
        known_filenames: Set of storage_name values from the database.

    Returns:
        Number of orphan files removed.
    """
    removed = 0
    for entry in UPLOAD_DIR.iterdir():
        if entry.is_file() and entry.name not in known_filenames:
            try:
                os.remove(entry)
                removed += 1
                logger.info("Removed orphan upload: %s", entry.name)
            except OSError as e:
                logger.warning("Failed to remove orphan %s: %s", entry, e)
    return removed


# ═══════════════════════════════════════════════════════════════════════
# Disk Usage
# ═══════════════════════════════════════════════════════════════════════


def get_storage_stats() -> dict:
    """Get storage usage statistics."""
    stats = {}
    for label, directory in [
        ("uploads", UPLOAD_DIR),
        ("previews", PREVIEW_DIR),
        ("results", RESULTS_DIR),
        ("debug", DEBUG_DIR),
    ]:
        total_size = 0
        file_count = 0
        if directory.exists():
            for f in directory.rglob("*"):
                if f.is_file():
                    total_size += f.stat().st_size
                    file_count += 1
        stats[label] = {
            "path": str(directory),
            "files": file_count,
            "size_mb": round(total_size / (1024 * 1024), 2),
        }
    return stats
