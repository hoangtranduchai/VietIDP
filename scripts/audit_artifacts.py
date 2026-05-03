#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Artifact Audit Script — VietIDP
================================
Scans the repository for files that should NOT be committed to Git:
- Sensitive documents (PDF, DOCX, images in wrong locations)
- Model weights (.pt, .pth, .onnx, .safetensors, .gguf, .bin)
- Database files (.db, .sqlite, .sqlite3)
- Log files (.log)
- Upload/result artifacts
- Large files (>50MB)

Usage:
    python scripts/audit_artifacts.py [--fix]

With --fix, it will add discovered paths to .gitignore.
Without --fix, it prints a report only.
"""

import os
import sys
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# File extensions that should never be committed
BLOCKED_EXTENSIONS = {
    # Model weights
    ".pt", ".pth", ".onnx", ".safetensors", ".bin", ".gguf",
    ".h5", ".pb", ".tflite", ".ckpt",
    # Sensitive documents
    ".pdf", ".docx", ".doc",
    # Database
    ".db", ".sqlite", ".sqlite3",
    # Logs
    ".log",
}

# Directories that should be fully ignored (relative to root)
BLOCKED_DIRS = {
    "data/uploads",
    "data/raw",
    "data/interim",
    "data/processed",
    "data/llm_training",
    "data/raw_word_files",
    "apps/backend/uploads",
    "apps/frontend/public/temp_uploads",
    "backend/uploads",
    "results",
    "debug_outputs",
    "artifacts",
    "outputs",
    "runs",
    "wandb",
    "mlruns",
    "logs",
    "pgdata",
    "postgres_data",
    "redis-data",
    "redis_data",
    "chromadb",
    "cache",
    ".tmp",
    "tmp",
    "unsloth_compiled_cache",
}

# Allowed exceptions (files that ARE okay to commit despite extension)
ALLOWED_PATHS = {
    "README.md",
    "docs/",
    ".gitkeep",
    "data/test/labels/",  # benchmark labels (JSON) are okay
}

# Max file size before warning (50 MB)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


def is_in_git(path: Path) -> bool:
    """Check if a path is tracked by git (not in .gitignore)."""
    rel = path.relative_to(ROOT)
    result = os.popen(f'git -C "{ROOT}" check-ignore -q "{rel}" 2>&1').close()
    return result is not None  # None means exit 0 = ignored


def scan_repository() -> dict:
    """Scan the repository and categorize findings."""
    findings = {
        "blocked_extensions": [],
        "blocked_dirs": [],
        "large_files": [],
        "sensitive_in_root": [],
    }

    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = Path(dirpath).relative_to(ROOT)
        rel_dir_str = str(rel_dir).replace("\\", "/")

        # Skip .git directory
        if ".git" in dirpath.split(os.sep):
            continue
        # Skip node_modules
        if "node_modules" in dirpath.split(os.sep):
            continue
        # Skip .venv
        if ".venv" in dirpath.split(os.sep):
            continue
        # Skip __pycache__
        if "__pycache__" in dirpath.split(os.sep):
            continue

        # Check if this directory itself should be blocked
        for blocked in BLOCKED_DIRS:
            if rel_dir_str == blocked or rel_dir_str.startswith(blocked + "/"):
                # Check if any files here are tracked
                for fn in filenames:
                    fp = Path(dirpath) / fn
                    if fn != ".gitkeep":
                        findings["blocked_dirs"].append(
                            str(fp.relative_to(ROOT)).replace("\\", "/")
                        )
                dirnames.clear()  # Don't recurse
                break

        for fn in filenames:
            fp = Path(dirpath) / fn
            rel_fp = str(fp.relative_to(ROOT)).replace("\\", "/")

            # Skip allowed paths
            if any(rel_fp.startswith(a) or rel_fp == a for a in ALLOWED_PATHS):
                continue

            ext = fp.suffix.lower()

            # Check blocked extensions
            if ext in BLOCKED_EXTENSIONS:
                findings["blocked_extensions"].append(rel_fp)

            # Check large files
            try:
                size = fp.stat().st_size
                if size > MAX_FILE_SIZE_BYTES:
                    findings["large_files"].append(
                        (rel_fp, f"{size / (1024*1024):.1f} MB")
                    )
            except OSError:
                pass

    return findings


def print_report(findings: dict) -> int:
    """Print a human-readable report. Returns count of issues."""
    total = 0
    print("=" * 60)
    print(" VietIDP Artifact Audit Report")
    print("=" * 60)

    if findings["blocked_extensions"]:
        print(f"\n🔴 Blocked file extensions ({len(findings['blocked_extensions'])} files):")
        for f in sorted(findings["blocked_extensions"])[:30]:
            print(f"   - {f}")
        if len(findings["blocked_extensions"]) > 30:
            print(f"   ... and {len(findings['blocked_extensions']) - 30} more")
        total += len(findings["blocked_extensions"])

    if findings["blocked_dirs"]:
        print(f"\n🟡 Files in blocked directories ({len(findings['blocked_dirs'])} files):")
        for f in sorted(findings["blocked_dirs"])[:20]:
            print(f"   - {f}")
        if len(findings["blocked_dirs"]) > 20:
            print(f"   ... and {len(findings['blocked_dirs']) - 20} more")
        total += len(findings["blocked_dirs"])

    if findings["large_files"]:
        print(f"\n🟠 Large files > 50MB ({len(findings['large_files'])} files):")
        for f, size in sorted(findings["large_files"]):
            print(f"   - {f} ({size})")
        total += len(findings["large_files"])

    if total == 0:
        print("\n✅ No commit-eligible sensitive artifacts found!")
    else:
        print(f"\n⚠️  Total issues: {total}")
        print("   Run with --fix to add missing entries to .gitignore")

    print("=" * 60)
    return total


def main():
    fix_mode = "--fix" in sys.argv

    print("Scanning repository...")
    findings = scan_repository()
    issues = print_report(findings)

    if fix_mode and issues > 0:
        print("\n🔧 Fix mode: Adding missing entries to .gitignore...")
        gitignore_path = ROOT / ".gitignore"
        existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""

        new_entries = []
        for f in findings["blocked_extensions"] + findings["blocked_dirs"]:
            entry = f"/{f}"
            if entry not in existing:
                new_entries.append(entry)

        if new_entries:
            with open(gitignore_path, "a", encoding="utf-8") as fh:
                fh.write("\n# Auto-added by audit_artifacts.py\n")
                for entry in new_entries:
                    fh.write(f"{entry}\n")
            print(f"   Added {len(new_entries)} entries to .gitignore")
        else:
            print("   All issues are already in .gitignore")

    sys.exit(1 if issues > 0 else 0)


if __name__ == "__main__":
    main()
