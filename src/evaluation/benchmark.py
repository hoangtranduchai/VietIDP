# -*- coding: utf-8 -*-
"""
VietIDP Benchmark — Evaluation Pipeline
=========================================
Chạy pipeline trên tập dữ liệu test, tính CER/WER/F1.

Sử dụng:
    conda activate vietidp
    python src/evaluation/benchmark.py --input data/test --ground-truth data/test/labels
"""

import os
import re
import sys
import json
import time
import argparse
import numpy as np
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import Config


# ═══════════════════════════════════════════════════════════════════════
# Metrics
# ═══════════════════════════════════════════════════════════════════════

def character_error_rate(prediction: str, reference: str) -> float:
    """Tính Character Error Rate (CER) bằng Levenshtein distance."""
    if not reference:
        return 0.0 if not prediction else 1.0

    pred = prediction.strip()
    ref = reference.strip()

    d = np.zeros((len(pred) + 1, len(ref) + 1), dtype=int)
    for i in range(len(pred) + 1):
        d[i][0] = i
    for j in range(len(ref) + 1):
        d[0][j] = j

    for i in range(1, len(pred) + 1):
        for j in range(1, len(ref) + 1):
            cost = 0 if pred[i - 1] == ref[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)

    return float(d[len(pred)][len(ref)]) / max(len(ref), 1)


def word_error_rate(prediction: str, reference: str) -> float:
    """Tính Word Error Rate (WER)."""
    pred_words = prediction.strip().split()
    ref_words = reference.strip().split()

    if not ref_words:
        return 0.0 if not pred_words else 1.0

    d = np.zeros((len(pred_words) + 1, len(ref_words) + 1), dtype=int)
    for i in range(len(pred_words) + 1):
        d[i][0] = i
    for j in range(len(ref_words) + 1):
        d[0][j] = j

    for i in range(1, len(pred_words) + 1):
        for j in range(1, len(ref_words) + 1):
            cost = 0 if pred_words[i - 1] == ref_words[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)

    return float(d[len(pred_words)][len(ref_words)]) / max(len(ref_words), 1)


def extraction_f1(predicted: dict, ground_truth: dict) -> dict:
    """Tính Precision, Recall, F1 cho từng field trích xuất."""
    fields = ['loai_van_ban', 'so_hieu', 'ngay_ban_hanh',
              'co_quan_ban_hanh', 'trich_yeu', 'nguoi_ky']

    results = {}
    tp = fp = fn = 0

    for field in fields:
        pred_val = str(predicted.get(field, '')).strip().lower()
        gt_val = str(ground_truth.get(field, '')).strip().lower()

        if gt_val and pred_val:
            if pred_val == gt_val or gt_val in pred_val or pred_val in gt_val:
                tp += 1
                results[field] = 'correct'
            else:
                fp += 1
                results[field] = 'wrong'
        elif gt_val and not pred_val:
            fn += 1
            results[field] = 'missed'
        elif not gt_val and pred_val:
            results[field] = 'extra'
        else:
            results[field] = 'both_empty'

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)

    return {
        'field_results': results,
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'tp': tp, 'fp': fp, 'fn': fn,
    }


# ═══════════════════════════════════════════════════════════════════════
# Benchmark Runner
# ═══════════════════════════════════════════════════════════════════════

class BenchmarkRunner:
    """Chạy benchmark toàn bộ pipeline."""

    def __init__(self, input_dir, gt_dir=None, output_dir=None, limit=None):
        self.input_dir = input_dir
        self.gt_dir = gt_dir
        self.output_dir = output_dir or str(Config.RESULTS_DIR / "benchmark")
        self.limit = limit
        os.makedirs(self.output_dir, exist_ok=True)

    def find_test_files(self):
        """Tìm tất cả file test."""
        files = []
        for f in sorted(os.listdir(self.input_dir)):
            if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                files.append(os.path.join(self.input_dir, f))
        if self.limit:
            files = files[:self.limit]
        return files

    def load_ground_truth(self, filename):
        """Load ground truth JSON cho 1 file."""
        if not self.gt_dir:
            return None
        base = os.path.splitext(filename)[0]
        gt_path = os.path.join(self.gt_dir, base + '.json')
        if os.path.exists(gt_path):
            with open(gt_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def run(self):
        """Chạy benchmark trên toàn bộ test files."""
        files = self.find_test_files()
        if not files:
            print("❌ No test files found")
            return None

        print(f"\n📊 Starting benchmark on {len(files)} files...")
        print(f"   Input: {self.input_dir}")
        print(f"   GT: {self.gt_dir or 'None'}")

        # Load pipeline
        from src.pipeline.ocr_llm_pipeline import VietIDPPipeline
        pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)

        results = []
        total_time = 0
        vram_peak = 0

        for i, filepath in enumerate(files):
            filename = os.path.basename(filepath)
            print(f"\n[{i+1}/{len(files)}] {filename}")

            try:
                # Track VRAM
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.reset_peak_memory_stats()
                except Exception:
                    pass

                start = time.time()
                result = pipeline.process_file(filepath, save_result=False)
                elapsed = time.time() - start
                total_time += elapsed

                # VRAM
                try:
                    import torch
                    if torch.cuda.is_available():
                        peak = torch.cuda.max_memory_allocated() / (1024**3)
                        vram_peak = max(vram_peak, peak)
                except Exception:
                    pass

                entry = {
                    'filename': filename,
                    'status': result.get('status'),
                    'processing_time': round(elapsed, 2),
                    'num_pages': result.get('num_pages', 1),
                    'total_stamps': result.get('total_stamps', 0),
                    'text_length': len(result.get('full_text', '')),
                    'extraction': result.get('extraction', {}),
                }

                # Compare with ground truth
                gt = self.load_ground_truth(filename)
                if gt:
                    ocr_gt_text = gt.get('full_text', '')
                    ocr_pred_text = result.get('full_text', '')

                    entry['cer'] = character_error_rate(ocr_pred_text, ocr_gt_text)
                    entry['wer'] = word_error_rate(ocr_pred_text, ocr_gt_text)

                    gt_extraction = gt.get('extraction', gt)
                    f1_result = extraction_f1(result.get('extraction', {}), gt_extraction)
                    entry['f1_score'] = f1_result

                results.append(entry)
                print(f"   ✅ {elapsed:.1f}s | {entry['text_length']} chars | "
                      f"{entry['total_stamps']} stamps")

            except Exception as e:
                print(f"   ❌ Error: {e}")
                results.append({
                    'filename': filename,
                    'status': 'failed',
                    'error': str(e),
                })

        # ── Summary ─────────────────────────────────────────────────
        summary = self._compute_summary(results, total_time, vram_peak)

        # Save results
        output_path = os.path.join(self.output_dir, 'benchmark_results.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': summary,
                'results': results,
            }, f, ensure_ascii=False, indent=2)

        self._print_summary(summary)
        print(f"\n💾 Results saved: {output_path}")
        return summary

    def _compute_summary(self, results, total_time, vram_peak):
        """Tính toán summary metrics."""
        successful = [r for r in results if r.get('status') == 'success']
        times = [r['processing_time'] for r in successful if 'processing_time' in r]
        cer_scores = [r['cer'] for r in successful if 'cer' in r]
        wer_scores = [r['wer'] for r in successful if 'wer' in r]
        f1_scores = [r['f1_score']['f1'] for r in successful if 'f1_score' in r]

        return {
            'total_files': len(results),
            'successful': len(successful),
            'failed': len(results) - len(successful),
            'success_rate': round(len(successful) / max(len(results), 1), 4),
            'total_time': round(total_time, 2),
            'avg_time': round(np.mean(times), 2) if times else 0,
            'median_time': round(np.median(times), 2) if times else 0,
            'min_time': round(min(times), 2) if times else 0,
            'max_time': round(max(times), 2) if times else 0,
            'avg_cer': round(np.mean(cer_scores), 4) if cer_scores else None,
            'avg_wer': round(np.mean(wer_scores), 4) if wer_scores else None,
            'avg_f1': round(np.mean(f1_scores), 4) if f1_scores else None,
            'vram_peak_gb': round(vram_peak, 2),
        }

    def _print_summary(self, summary):
        """In summary metrics."""
        print(f"\n{'='*60}")
        print(f"  BENCHMARK SUMMARY")
        print(f"{'='*60}")
        print(f"  Files: {summary['successful']}/{summary['total_files']} "
              f"({summary['success_rate']*100:.1f}% success)")
        print(f"  Total time: {summary['total_time']:.1f}s")
        print(f"  Avg time/file: {summary['avg_time']:.1f}s")
        print(f"  VRAM peak: {summary['vram_peak_gb']:.2f} GB")

        if summary['avg_cer'] is not None:
            print(f"\n  OCR Metrics (vs Ground Truth):")
            print(f"    CER: {summary['avg_cer']:.4f}")
            print(f"    WER: {summary['avg_wer']:.4f}")

        if summary['avg_f1'] is not None:
            print(f"\n  Extraction Metrics:")
            print(f"    F1 Score: {summary['avg_f1']:.4f}")


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VietIDP Benchmark")
    parser.add_argument("--input", default="data/test", help="Input directory")
    parser.add_argument("--ground-truth", default=None, help="Ground truth JSON directory")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of files")
    args = parser.parse_args()

    runner = BenchmarkRunner(args.input, args.ground_truth, args.output, args.limit)
    runner.run()
