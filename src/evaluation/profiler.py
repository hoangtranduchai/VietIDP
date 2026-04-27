# -*- coding: utf-8 -*-
"""
VietIDP Performance Profiler
==============================
Do Latency va Peak VRAM cho tung stage cua pipeline.

Su dung:
    conda activate vietidp
    python src/evaluation/profiler.py --input data/test/sample_test.jpg
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def get_gpu_memory():
    """Return current GPU memory in MB, or 0 if CUDA unavailable."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024**2)
    except Exception:
        pass
    return 0.0


def get_peak_gpu_memory():
    """Return peak GPU memory in MB."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / (1024**2)
    except Exception:
        pass
    return 0.0


def reset_gpu_stats():
    """Reset CUDA memory stats."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.empty_cache()
    except Exception:
        pass


class StageTimer:
    """Context manager to measure a pipeline stage."""
    def __init__(self, name):
        self.name = name
        self.start_time = 0
        self.elapsed = 0
        self.vram_before = 0
        self.vram_after = 0
        self.vram_peak = 0

    def __enter__(self):
        reset_gpu_stats()
        self.vram_before = get_gpu_memory()
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start_time
        self.vram_after = get_gpu_memory()
        self.vram_peak = get_peak_gpu_memory()

    def to_dict(self):
        return {
            'stage': self.name,
            'latency_s': round(self.elapsed, 3),
            'vram_before_mb': round(self.vram_before, 1),
            'vram_after_mb': round(self.vram_after, 1),
            'vram_peak_mb': round(self.vram_peak, 1),
            'vram_delta_mb': round(self.vram_after - self.vram_before, 1),
        }


def profile_pipeline(input_file):
    """Profile each stage of the VietIDP pipeline."""
    import numpy as np
    from PIL import Image

    stages = []

    print("\n" + "=" * 60)
    print("  VietIDP Performance Profiler")
    print("=" * 60)
    print(f"  Input: {input_file}")

    # Check GPU
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"  GPU: {gpu_name} ({total_vram:.1f} GB)")
        else:
            print("  GPU: CPU mode (no CUDA)")
    except Exception:
        print("  GPU: N/A")

    # ── Stage 1: Load Image ──────────────────────────────────────
    with StageTimer("1. Load Image") as t:
        img = np.array(Image.open(input_file).convert('RGB'))
        import cv2
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    stages.append(t.to_dict())
    print(f"\n  {t.name}: {t.elapsed:.3f}s | Image: {img.shape}")

    # ── Stage 2: YOLO Stamp Detection ────────────────────────────
    with StageTimer("2. YOLO Detection") as t:
        from src.config import Config
        from ultralytics import YOLO
        model = YOLO(str(Config.STAMP_DETECTION_MODEL))
        results = model(img_bgr, conf=0.25, verbose=False)
        stamps = len(results[0].boxes)
    stages.append(t.to_dict())
    print(f"  {t.name}: {t.elapsed:.3f}s | Stamps: {stamps} | VRAM: {t.vram_peak:.0f}MB")

    # ── Stage 3: Stamp Matting ───────────────────────────────────
    with StageTimer("3. Stamp Matting") as t:
        from src.preprocessing.stamp_matting import HybridStampMatting
        matting = HybridStampMatting()
        clean_img = matting.remove_stamp(img_bgr)
    stages.append(t.to_dict())
    print(f"  {t.name}: {t.elapsed:.3f}s | VRAM: {t.vram_peak:.0f}MB")

    # ── Stage 4: OCR ─────────────────────────────────────────────
    with StageTimer("4. OCR (VietOCR + EasyOCR)") as t:
        try:
            from src.ocr.engine import VietnameseOCREngine
            ocr = VietnameseOCREngine()
            ocr_result = ocr.process_image(clean_img)
            text = ocr_result.get('text', '') if isinstance(ocr_result, dict) else str(ocr_result)
        except Exception as e:
            text = ""
            print(f"    [WARN] OCR skipped: {e}")
    stages.append(t.to_dict())
    print(f"  {t.name}: {t.elapsed:.3f}s | Chars: {len(text)} | VRAM: {t.vram_peak:.0f}MB")

    # ── Stage 5: LLM Extraction ──────────────────────────────────
    with StageTimer("5. LLM Extraction (Qwen2.5-7B)") as t:
        try:
            from src.llm.ollama_client import OllamaClient
            from src.llm.prompts import PROMPTS
            client = OllamaClient()
            test_text = text if text else "QUYET DINH So: 123/QD-UBND"
            prompt = PROMPTS['extraction'].format(text=test_text[:8000])
            result, error = client.generate(prompt, format_json=True)
        except Exception as e:
            result = None
            print(f"    [WARN] LLM skipped: {e}")
    stages.append(t.to_dict())
    print(f"  {t.name}: {t.elapsed:.3f}s | VRAM: {t.vram_peak:.0f}MB")

    # ── Summary ──────────────────────────────────────────────────
    total_time = sum(s['latency_s'] for s in stages)
    max_vram = max(s['vram_peak_mb'] for s in stages)

    print(f"\n{'='*60}")
    print(f"  PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Stage':<35} {'Time':>8} {'VRAM Peak':>10}")
    print(f"  {'-'*55}")
    for s in stages:
        print(f"  {s['stage']:<35} {s['latency_s']:>7.3f}s {s['vram_peak_mb']:>9.0f}MB")
    print(f"  {'-'*55}")
    print(f"  {'TOTAL':<35} {total_time:>7.3f}s {max_vram:>9.0f}MB")

    # Save results
    output_dir = Path("results/benchmark")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "profiler_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'input_file': str(input_file),
            'total_time_s': round(total_time, 3),
            'peak_vram_mb': round(max_vram, 1),
            'stages': stages,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Results saved: {output_path}")

    return stages


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VietIDP Profiler")
    parser.add_argument("--input", default="data/raw/sample_test.jpg")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[FAIL] File not found: {args.input}")
        sys.exit(1)

    profile_pipeline(args.input)
