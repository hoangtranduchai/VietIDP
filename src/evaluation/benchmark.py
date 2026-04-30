# -*- coding: utf-8 -*-
"""
VietIDP Benchmark — Evaluation Pipeline
=========================================
Chạy pipeline trên tập dữ liệu test, tính CER/WER/F1.

Sử dụng:
    python src/evaluation/benchmark.py --input data/test --ground-truth data/test/labels
    python src/evaluation/benchmark.py --manifest data/benchmarks/synthetic_regenerated/manifest.json --official
"""

import os
import sys
import json
import time
import argparse
import numpy as np
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import Config
from src.evaluation.extraction_metrics import compute_field_metrics
from src.evaluation.manifest import INPUT_SUFFIXES, DatasetManifest, ManifestEntry, ManifestError


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

    def __init__(self, input_dir=None, gt_dir=None, output_dir=None, limit=None, manifest_path=None, official=False):
        self.input_dir = input_dir
        self.gt_dir = gt_dir
        self.output_dir = output_dir or str(Config.RESULTS_DIR / "benchmark")
        self.limit = limit
        self.official = official
        self.manifest = DatasetManifest.load(manifest_path) if manifest_path else None
        self.manifest_sha256 = self.manifest.manifest_sha256 if self.manifest else None
        os.makedirs(self.output_dir, exist_ok=True)

        if self.manifest:
            self.manifest.validate(require_labels=True, verify_hashes=True, check_split_leakage=True)
        elif self.official:
            self._validate_official_inputs()

    def _validate_official_inputs(self):
        input_path = Path(self.input_dir)
        if not input_path.exists():
            raise ManifestError(f"Official benchmark input directory does not exist: {input_path}")

        input_ids = {
            path.stem for path in input_path.iterdir()
            if path.is_file() and path.suffix.lower() in INPUT_SUFFIXES
        }
        label_path = Path(self.gt_dir) if self.gt_dir else input_path / "labels"
        label_ids = {path.stem for path in label_path.glob("*.json")} if label_path.exists() else set()

        if label_ids and not input_ids:
            raise ManifestError(f"Official benchmark has labels in {label_path} but no matching input files in {input_path}")
        missing_inputs = sorted(label_ids - input_ids)
        missing_labels = sorted(input_ids - label_ids) if label_path.exists() else sorted(input_ids)
        if missing_inputs:
            raise ManifestError("Official benchmark labels without input files: " + ", ".join(missing_inputs[:20]))
        if missing_labels:
            raise ManifestError("Official benchmark inputs without labels: " + ", ".join(missing_labels[:20]))

    def find_test_files(self):
        """Tìm tất cả file test."""
        if self.manifest:
            return list(self.manifest.iter_files(self.limit))

        files = []
        for f in sorted(os.listdir(self.input_dir)):
            if Path(f).suffix.lower() in INPUT_SUFFIXES:
                files.append(os.path.join(self.input_dir, f))
        if self.limit:
            files = files[:self.limit]
        return files

    def _filename(self, file_ref):
        if isinstance(file_ref, ManifestEntry):
            return file_ref.input_path.name
        return os.path.basename(file_ref)

    def _filepath(self, file_ref):
        if isinstance(file_ref, ManifestEntry):
            return str(file_ref.input_path)
        return str(file_ref)

    def load_ground_truth(self, file_ref):
        """Load ground truth JSON cho 1 file."""
        if isinstance(file_ref, ManifestEntry):
            if file_ref.label_path and file_ref.label_path.exists():
                with file_ref.label_path.open('r', encoding='utf-8') as f:
                    return json.load(f)
            return None

        if not self.gt_dir:
            return None
        base = os.path.splitext(os.path.basename(file_ref))[0]
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
        print(f"   Manifest: {self.manifest.path if self.manifest else 'None'}")
        print(f"   Manifest SHA256: {self.manifest_sha256 or 'None'}")
        print(f"   Input: {self.input_dir or self.manifest.root}")
        print(f"   GT: {self.gt_dir or 'manifest labels' if self.manifest else 'None'}")
        print(f"   Official: {self.official}")

        # Load pipeline
        from src.pipeline.ocr_llm_pipeline import VietIDPPipeline
        pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)

        results = []
        total_time = 0
        vram_peak = 0

        for i, file_ref in enumerate(files):
            filename = self._filename(file_ref)
            filepath = self._filepath(file_ref)
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
                if isinstance(file_ref, ManifestEntry):
                    entry['manifest_entry_id'] = file_ref.id
                    entry['input_sha256'] = file_ref.input_sha256
                    entry['label_sha256'] = file_ref.label_sha256
                    entry['split'] = file_ref.split
                    entry['source_type'] = file_ref.source_type

                # Compare with ground truth
                gt = self.load_ground_truth(file_ref)
                if gt is not None:
                    ocr_gt_text = gt.get('full_text', '')
                    ocr_pred_text = result.get('full_text', '')

                    entry['cer'] = character_error_rate(ocr_pred_text, ocr_gt_text)
                    entry['wer'] = word_error_rate(ocr_pred_text, ocr_gt_text)

                    gt_extraction = gt.get('extraction', gt)
                    legacy_f1_result = extraction_f1(result.get('extraction', {}), gt_extraction)
                    strict_metrics = compute_field_metrics(result.get('extraction', {}), gt_extraction)
                    entry['legacy_debug_extraction_f1'] = legacy_f1_result
                    entry['strict_extraction_metrics'] = strict_metrics

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
                'official': self.official,
                'manifest_path': str(self.manifest.path) if self.manifest else None,
                'manifest_sha256': self.manifest_sha256,
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
        legacy_debug_f1_scores = [
            r['legacy_debug_extraction_f1']['f1']
            for r in successful if 'legacy_debug_extraction_f1' in r
        ]
        strict_macro_strict = [
            r['strict_extraction_metrics']['macro']['strict_exact_match']
            for r in successful if 'strict_extraction_metrics' in r
        ]
        strict_macro_normalized = [
            r['strict_extraction_metrics']['macro']['normalized_exact_match']
            for r in successful if 'strict_extraction_metrics' in r
        ]
        strict_macro_token_f1 = [
            r['strict_extraction_metrics']['macro']['token_f1']
            for r in successful if 'strict_extraction_metrics' in r
        ]
        strict_macro_char_similarity = [
            r['strict_extraction_metrics']['macro']['character_similarity']
            for r in successful if 'strict_extraction_metrics' in r
        ]

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
            'legacy_debug_avg_f1': round(np.mean(legacy_debug_f1_scores), 4) if legacy_debug_f1_scores else None,
            'strict_macro_exact_match': round(np.mean(strict_macro_strict), 4) if strict_macro_strict else None,
            'strict_macro_normalized_exact_match': round(np.mean(strict_macro_normalized), 4) if strict_macro_normalized else None,
            'strict_macro_token_f1': round(np.mean(strict_macro_token_f1), 4) if strict_macro_token_f1 else None,
            'strict_macro_character_similarity': round(np.mean(strict_macro_char_similarity), 4) if strict_macro_char_similarity else None,
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

        if summary['legacy_debug_avg_f1'] is not None:
            print(f"\n  Extraction Metrics:")
            print(f"    Legacy debug F1: {summary['legacy_debug_avg_f1']:.4f}")

        if summary['strict_macro_exact_match'] is not None:
            print(f"\n  Strict Extraction Metrics:")
            print(f"    Macro strict exact: {summary['strict_macro_exact_match']:.4f}")
            print(f"    Macro normalized exact: {summary['strict_macro_normalized_exact_match']:.4f}")
            print(f"    Macro token F1: {summary['strict_macro_token_f1']:.4f}")
            print(f"    Macro char similarity: {summary['strict_macro_character_similarity']:.4f}")


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VietIDP Benchmark")
    parser.add_argument("--input", default="data/test", help="Input directory")
    parser.add_argument("--ground-truth", default=None, help="Ground truth JSON directory")
    parser.add_argument("--manifest", default=None, help="Dataset manifest JSON")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of files")
    parser.add_argument("--official", action="store_true", help="Require manifest or complete input/label pairs; disable raw fallback")
    parser.add_argument("--use-raw", action="store_true", help="Explicitly use data/raw if selected input has no files")
    args = parser.parse_args()

    input_dir = args.input
    gt_dir = args.ground_truth

    if not args.manifest:
        if not os.path.isdir(input_dir):
            raise SystemExit(f"[ERROR] Input directory does not exist: {input_dir}")

        has_inputs = any(
            Path(f).suffix.lower() in INPUT_SUFFIXES
            for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
        )
        if not has_inputs and args.use_raw and not args.official:
            fallback = "data/raw"
            if os.path.isdir(fallback):
                print(f"[INFO] {input_dir} is empty, explicit fallback to {fallback}")
                input_dir = fallback

        # Auto-detect ground-truth directory
        if gt_dir is None:
            candidate = os.path.join(input_dir, "labels")
            if os.path.isdir(candidate):
                gt_dir = candidate
                print(f"[INFO] Auto-detected ground truth: {gt_dir}")

    try:
        runner = BenchmarkRunner(
            input_dir=input_dir,
            gt_dir=gt_dir,
            output_dir=args.output,
            limit=args.limit,
            manifest_path=args.manifest,
            official=args.official,
        )
        runner.run()
    except ManifestError as exc:
        raise SystemExit(f"[ERROR] {exc}")
