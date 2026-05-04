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
import platform
import shlex
import statistics
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import Config
from src.evaluation.bootstrap import DEFAULT_BOOTSTRAP_ITERATIONS, DEFAULT_CONFIDENCE, DEFAULT_SEED, bootstrap_ci_from_metric_path
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

    d = [[0 for _ in range(len(ref) + 1)] for _ in range(len(pred) + 1)]
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

    d = [[0 for _ in range(len(ref_words) + 1)] for _ in range(len(pred_words) + 1)]
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

def _current_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        return None
    commit = result.stdout.strip()
    return commit or None


def _cuda_runtime_info() -> dict:
    info = {"cuda_available": None, "gpu_name": None}
    try:
        torch = __import__("torch")
        info["cuda_available"] = bool(torch.cuda.is_available())
        if info["cuda_available"]:
            info["gpu_name"] = torch.cuda.get_device_name(0)
    except Exception:
        pass
    return info


def _reset_cuda_peak_memory() -> None:
    try:
        torch = __import__("torch")
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass


def _cuda_peak_memory_gb() -> float | None:
    try:
        torch = __import__("torch")
        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / (1024**3)
    except Exception:
        return None
    return None


def _runtime_provenance(manifest: DatasetManifest | None, official: bool) -> dict:
    return {
        "command": " ".join(shlex.quote(arg) for arg in sys.argv),
        "code_commit": _current_git_commit(),
        "model": {
            "ollama_model": Config.OLLAMA_MODEL,
            "vietocr_model": Config.VIETOCR_MODEL,
            "yolo_model": str(Config.STAMP_DETECTION_MODEL),
            "checksum": None,
        },
        "runtime": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "ocr_dpi": Config.OCR_DPI,
            "ollama_temperature": Config.OLLAMA_TEMPERATURE,
            "ollama_num_predict": Config.OLLAMA_NUM_PREDICT,
        },
        "hardware": _cuda_runtime_info(),
        "split": manifest.metadata.get("split") if manifest else None,
        "source_type": manifest.metadata.get("source_type") if manifest else None,
        "official": official,
    }


class BenchmarkRunner:
    """Chạy benchmark toàn bộ pipeline."""

    def __init__(self, input_dir=None, gt_dir=None, output_dir=None, limit=None, manifest_path=None, official=False):
        self.input_dir = input_dir
        self.gt_dir = gt_dir
        self.output_dir = output_dir or str(Config.RESULTS_DIR / "benchmark")
        self.limit = limit
        self.official = official
        if self.official and not manifest_path:
            raise ManifestError("Official benchmark requires --manifest")
        if self.official and self.limit is not None:
            raise ManifestError("Official benchmark cannot use --limit; evaluate the full manifest")

        self.manifest = DatasetManifest.load(manifest_path) if manifest_path else None
        self.manifest_sha256 = self.manifest.manifest_sha256 if self.manifest else None
        self.provenance = _runtime_provenance(self.manifest, self.official)
        os.makedirs(self.output_dir, exist_ok=True)

        if self.manifest:
            self.manifest.validate(require_labels=True, verify_hashes=True, check_split_leakage=True)

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
                _reset_cuda_peak_memory()

                start = time.time()
                result = pipeline.process_file(filepath, save_result=False)
                elapsed = time.time() - start
                total_time += elapsed

                peak = _cuda_peak_memory_gb()
                if peak is not None:
                    vram_peak = max(vram_peak, peak)

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
                'provenance': self.provenance,
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

        confidence_intervals = {
            'avg_cer': bootstrap_ci_from_metric_path(successful, 'cer'),
            'avg_wer': bootstrap_ci_from_metric_path(successful, 'wer'),
            'legacy_debug_avg_f1': bootstrap_ci_from_metric_path(successful, 'legacy_debug_extraction_f1.f1'),
            'strict_macro_exact_match': bootstrap_ci_from_metric_path(successful, 'strict_extraction_metrics.macro.strict_exact_match'),
            'strict_macro_normalized_exact_match': bootstrap_ci_from_metric_path(successful, 'strict_extraction_metrics.macro.normalized_exact_match'),
            'strict_macro_token_f1': bootstrap_ci_from_metric_path(successful, 'strict_extraction_metrics.macro.token_f1'),
            'strict_macro_character_similarity': bootstrap_ci_from_metric_path(successful, 'strict_extraction_metrics.macro.character_similarity'),
        }

        return {
            'total_files': len(results),
            'successful': len(successful),
            'failed': len(results) - len(successful),
            'success_rate': round(len(successful) / max(len(results), 1), 4),
            'total_time': round(total_time, 2),
            'avg_time': round(statistics.mean(times), 2) if times else 0,
            'median_time': round(statistics.median(times), 2) if times else 0,
            'min_time': round(min(times), 2) if times else 0,
            'max_time': round(max(times), 2) if times else 0,
            'avg_cer': round(statistics.mean(cer_scores), 4) if cer_scores else None,
            'avg_wer': round(statistics.mean(wer_scores), 4) if wer_scores else None,
            'legacy_debug_avg_f1': round(statistics.mean(legacy_debug_f1_scores), 4) if legacy_debug_f1_scores else None,
            'strict_macro_exact_match': round(statistics.mean(strict_macro_strict), 4) if strict_macro_strict else None,
            'strict_macro_normalized_exact_match': round(statistics.mean(strict_macro_normalized), 4) if strict_macro_normalized else None,
            'strict_macro_token_f1': round(statistics.mean(strict_macro_token_f1), 4) if strict_macro_token_f1 else None,
            'strict_macro_character_similarity': round(statistics.mean(strict_macro_char_similarity), 4) if strict_macro_char_similarity else None,
            'confidence_intervals': confidence_intervals,
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

        def _print_ci(metric_key, label):
            ci = summary.get('confidence_intervals', {}).get(metric_key)
            if ci and ci.get('lower') is not None and ci.get('upper') is not None:
                confidence_pct = int(round(ci.get('confidence', DEFAULT_CONFIDENCE) * 100))
                print(
                    f"      {label} {confidence_pct}% CI: "
                    f"[{ci['lower']:.4f}, {ci['upper']:.4f}] "
                    f"(n={ci.get('sample_size', 0)}, iters={ci.get('iterations', DEFAULT_BOOTSTRAP_ITERATIONS)}, seed={ci.get('seed', DEFAULT_SEED)})"
                )

        if summary['avg_cer'] is not None:
            print(f"\n  OCR Metrics (vs Ground Truth):")
            print(f"    CER: {summary['avg_cer']:.4f}")
            print(f"    WER: {summary['avg_wer']:.4f}")
            _print_ci('avg_cer', 'CER')
            _print_ci('avg_wer', 'WER')

        if summary['legacy_debug_avg_f1'] is not None:
            print(f"\n  Extraction Metrics:")
            print(f"    Legacy debug F1: {summary['legacy_debug_avg_f1']:.4f}")
            _print_ci('legacy_debug_avg_f1', 'Legacy debug F1')

        if summary['strict_macro_exact_match'] is not None:
            print(f"\n  Strict Extraction Metrics:")
            print(f"    Macro strict exact: {summary['strict_macro_exact_match']:.4f}")
            print(f"    Macro normalized exact: {summary['strict_macro_normalized_exact_match']:.4f}")
            print(f"    Macro token F1: {summary['strict_macro_token_f1']:.4f}")
            print(f"    Macro char similarity: {summary['strict_macro_character_similarity']:.4f}")
            _print_ci('strict_macro_exact_match', 'Macro strict exact')
            _print_ci('strict_macro_normalized_exact_match', 'Macro normalized exact')
            _print_ci('strict_macro_token_f1', 'Macro token F1')
            _print_ci('strict_macro_character_similarity', 'Macro char similarity')


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
    parser.add_argument("--official", action="store_true", help="Require a manifest and disable raw fallback")
    parser.add_argument("--use-raw", action="store_true", help="Explicitly use data/raw if selected input has no files")
    args = parser.parse_args()

    input_dir = args.input
    gt_dir = args.ground_truth

    if args.official and not args.manifest:
        raise SystemExit("[ERROR] Official benchmark requires --manifest")
    if args.official and args.limit is not None:
        raise SystemExit("[ERROR] Official benchmark cannot use --limit; evaluate the full manifest")

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
