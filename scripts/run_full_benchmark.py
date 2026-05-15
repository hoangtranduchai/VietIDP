# -*- coding: utf-8 -*-
"""
VietIDP Full Benchmark — 100 PDF Test Runner (Research Edition)
================================================================
Chạy pipeline trên 100 PDF test và so sánh với ground truth.
Lưu TOÀN BỘ output từ mọi bước xử lý để làm bằng chứng nghiên cứu.

Output:
  results/benchmark/
  ├── benchmark_results.json          — Kết quả tổng hợp
  ├── benchmark_report.txt            — Báo cáo text đầy đủ
  ├── per_file/                       — Chi tiết từng file
  │   ├── pdf_test_1/
  │   │   ├── ocr_text.txt            — Text OCR đầy đủ
  │   │   ├── llm_input.txt           — Text gửi cho LLM
  │   │   ├── llm_output.json         — JSON LLM trả về
  │   │   ├── extraction_result.json  — Kết quả trích xuất (sau validate)
  │   │   ├── field_comparison.json   — So sánh từng trường vs GT
  │   │   └── processing_log.txt      — Log chi tiết quá trình xử lý
  │   ├── pdf_test_2/
  │   ...

Sử dụng:
    python scripts/run_full_benchmark.py
    python scripts/run_full_benchmark.py --limit 5
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from io import StringIO

# Fix encoding
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.evaluation.extraction_metrics import compute_field_metrics, STANDARD_FIELDS


def load_ground_truth(gt_path: str) -> dict:
    """Load ground truth JSON."""
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def setup_logging(output_dir: str) -> tuple:
    """Setup dual logging: console + file."""
    log_path = os.path.join(output_dir, 'benchmark_report.txt')
    os.makedirs(output_dir, exist_ok=True)

    # File handler
    file_handler = logging.FileHandler(log_path, encoding='utf-8', mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(message)s'))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))

    logger = logging.getLogger('benchmark')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger, log_path


def save_per_file_output(output_dir: str, filename: str, data: dict):
    """Lưu chi tiết output cho từng file."""
    basename = os.path.splitext(filename)[0]
    file_dir = os.path.join(output_dir, 'per_file', basename)
    os.makedirs(file_dir, exist_ok=True)

    # 1. OCR text
    ocr_text = data.get('ocr_text', '')
    with open(os.path.join(file_dir, 'ocr_text.txt'), 'w', encoding='utf-8') as f:
        f.write(f"# OCR Text Output — {filename}\n")
        f.write(f"# Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"# Total chars: {len(ocr_text)}\n")
        f.write(f"# Pages: {data.get('num_pages', '?')}\n")
        f.write(f"{'='*70}\n\n")
        f.write(ocr_text)

    # 2. LLM input (text gửi cho LLM)
    llm_input = data.get('llm_input', '')
    with open(os.path.join(file_dir, 'llm_input.txt'), 'w', encoding='utf-8') as f:
        f.write(f"# LLM Input Text — {filename}\n")
        f.write(f"# Total chars: {len(llm_input)}\n")
        f.write(f"{'='*70}\n\n")
        f.write(llm_input)

    # 3. LLM raw output
    llm_output = data.get('llm_output', {})
    with open(os.path.join(file_dir, 'llm_output.json'), 'w', encoding='utf-8') as f:
        json.dump(llm_output, f, ensure_ascii=False, indent=2)

    # 4. Extraction result (sau validate + normalize)
    extraction = data.get('extraction', {})
    with open(os.path.join(file_dir, 'extraction_result.json'), 'w', encoding='utf-8') as f:
        json.dump(extraction, f, ensure_ascii=False, indent=2)

    # 5. Field comparison
    comparison = data.get('comparison', {})
    with open(os.path.join(file_dir, 'field_comparison.json'), 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

    # 6. Processing log
    proc_log = data.get('processing_log', '')
    with open(os.path.join(file_dir, 'processing_log.txt'), 'w', encoding='utf-8') as f:
        f.write(proc_log)

    # 7. Per-page OCR details
    pages = data.get('pages', [])
    if pages:
        with open(os.path.join(file_dir, 'pages_detail.json'), 'w', encoding='utf-8') as f:
            # Remove image data before saving
            clean_pages = []
            for p in pages:
                cp = {k: v for k, v in p.items()
                      if k not in ('original_image', 'detection_image', 'clean_image',
                                   'processed_images')}
                clean_pages.append(cp)
            json.dump(clean_pages, f, ensure_ascii=False, indent=2)


def run_benchmark(input_dir: str, gt_path: str, output_dir: str, limit: int = None):
    """Chạy full benchmark với logging đầy đủ."""

    # Setup
    logger, log_path = setup_logging(output_dir)
    gt = load_ground_truth(gt_path)

    logger.info(f"{'='*70}")
    logger.info(f"  VIETIDP FULL BENCHMARK — RESEARCH EDITION")
    logger.info(f"{'='*70}")
    logger.info(f"  Timestamp:  {datetime.now().isoformat()}")
    logger.info(f"  Input:      {input_dir}")
    logger.info(f"  GT:         {gt_path}")
    logger.info(f"  Output:     {output_dir}")
    logger.info(f"  GT entries: {len(gt)}")
    if limit:
        logger.info(f"  Limit:      {limit}")
    logger.info(f"")

    # Log system info
    logger.info(f"  --- System Configuration ---")
    logger.info(f"  OCR DPI:          {Config.OCR_DPI}")
    logger.info(f"  Ollama Model:     {Config.OLLAMA_MODEL}")
    logger.info(f"  Ollama Temp:      {Config.OLLAMA_TEMPERATURE}")
    logger.info(f"  Ollama MaxChars:  {Config.OLLAMA_MAX_CHARS}")
    logger.info(f"  VietOCR Model:    {Config.VIETOCR_MODEL}")
    logger.info(f"  VietOCR Device:   {Config.VIETOCR_DEVICE}")
    logger.info(f"")

    # Load pipeline
    logger.info(f"  Loading pipeline...")
    from src.pipeline.ocr_llm_pipeline import VietIDPPipeline
    pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)
    logger.info(f"  Pipeline loaded successfully!")
    logger.info(f"")

    os.makedirs(os.path.join(output_dir, 'per_file'), exist_ok=True)

    # Get files to process
    files = sorted(gt.keys(), key=lambda x: int(x.replace('pdf_test_', '').replace('.pdf', '')))
    if limit:
        files = files[:limit]

    results = []
    total_time = 0

    # Per-field counters
    field_correct = {f: 0 for f in STANDARD_FIELDS}
    field_wrong = {f: 0 for f in STANDARD_FIELDS}
    field_total = {f: 0 for f in STANDARD_FIELDS}

    for i, filename in enumerate(files):
        filepath = os.path.join(input_dir, filename)
        if not os.path.exists(filepath):
            logger.warning(f"\n[{i+1}/{len(files)}] {filename} — SKIPPED (not found)")
            continue

        logger.info(f"\n{'─'*70}")
        logger.info(f"[{i+1}/{len(files)}] {filename}")
        logger.info(f"{'─'*70}")
        gt_entry = gt[filename]

        # Capture stdout from pipeline
        old_stdout = sys.stdout
        captured = StringIO()
        sys.stdout = captured

        try:
            start = time.time()
            result = pipeline.process_file(filepath, save_result=False)
            elapsed = time.time() - start
            total_time += elapsed

            # Restore stdout
            sys.stdout = old_stdout
            processing_log = captured.getvalue()

            # Log processing output
            logger.debug(f"\n  --- Processing Log ---")
            for line in processing_log.strip().split('\n'):
                logger.debug(f"  {line}")

            predicted = result.get('extraction', {})
            metrics = compute_field_metrics(predicted, gt_entry)

            # Collect full text
            full_text = ''
            pages_data = result.get('pages', [])
            if pages_data:
                full_text = '\n\n'.join(p.get('text', '') for p in pages_data)
            elif result.get('ocr_text'):
                full_text = result['ocr_text']

            # Save per-file output
            save_per_file_output(output_dir, filename, {
                'ocr_text': full_text,
                'llm_input': result.get('llm_input_text', full_text[:8000]),
                'llm_output': result.get('llm_raw_output', predicted),
                'extraction': predicted,
                'comparison': {
                    'predicted': predicted,
                    'ground_truth': gt_entry,
                    'metrics': metrics,
                },
                'processing_log': processing_log,
                'pages': pages_data,
                'num_pages': len(pages_data),
            })

            entry = {
                'filename': filename,
                'status': 'success',
                'processing_time': round(elapsed, 2),
                'num_pages': len(pages_data),
                'ocr_chars': len(full_text),
                'predicted': predicted,
                'ground_truth': gt_entry,
                'metrics': metrics,
            }
            results.append(entry)

            # Print per-field comparison
            logger.info(f"  Time: {elapsed:.1f}s | Pages: {len(pages_data)} | "
                        f"OCR chars: {len(full_text)}")
            any_wrong = False
            for field in STANDARD_FIELDS:
                fm = metrics['fields'][field]
                pred_val = predicted.get(field, '')
                gt_val = gt_entry.get(field, '')

                field_total[field] += 1
                if fm['normalized_exact_match']:
                    field_correct[field] += 1
                    marker = "✅"
                else:
                    field_wrong[field] += 1
                    marker = "❌"
                    any_wrong = True

                if not fm['normalized_exact_match']:
                    logger.info(f"  {marker} {field}:")
                    logger.info(f"       PRED: {str(pred_val)[:150]}")
                    logger.info(f"       GT:   {str(gt_val)[:150]}")
                    logger.info(f"       Sim:  {fm['character_similarity']:.3f}")
                else:
                    logger.debug(f"  {marker} {field}: {str(pred_val)[:100]}")

            if not any_wrong:
                logger.info(f"  ✅ ALL 6 FIELDS CORRECT!")

        except Exception as e:
            sys.stdout = old_stdout
            processing_log = captured.getvalue()
            logger.error(f"  ❌ ERROR: {e}")
            logger.debug(f"  Processing log before error:\n{processing_log}")
            results.append({
                'filename': filename,
                'status': 'error',
                'error': str(e),
                'processing_log': processing_log,
            })

    # ═══════════════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════════════
    successful = [r for r in results if r['status'] == 'success']
    errors = [r for r in results if r['status'] == 'error']
    all_6_correct = sum(
        1 for r in successful
        if all(r['metrics']['fields'][f]['normalized_exact_match'] for f in STANDARD_FIELDS)
    )

    logger.info(f"\n\n{'='*70}")
    logger.info(f"  BENCHMARK SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"  Total files:     {len(files)}")
    logger.info(f"  Successful:      {len(successful)}")
    logger.info(f"  Errors:          {len(errors)}")
    logger.info(f"  Total time:      {total_time:.1f}s")
    if successful:
        logger.info(f"  Avg time/file:   {total_time/len(successful):.1f}s")
    logger.info(f"")
    logger.info(f"  ═══ ACCURACY ═══")
    logger.info(f"  Documents ALL 6 correct: {all_6_correct}/{len(successful)} "
                f"({all_6_correct/max(len(successful),1)*100:.1f}%)")
    logger.info(f"")

    logger.info(f"  Per-field accuracy (Normalized Exact Match):")
    logger.info(f"  {'Field':<25} {'Correct':>8} {'Wrong':>8} {'Total':>8} {'Accuracy':>10}")
    logger.info(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")
    for field in STANDARD_FIELDS:
        c = field_correct[field]
        w = field_wrong[field]
        t = field_total[field]
        acc = c / max(t, 1) * 100
        logger.info(f"  {field:<25} {c:>8} {w:>8} {t:>8} {acc:>9.1f}%")

    if errors:
        logger.info(f"\n  ═══ ERROR FILES ═══")
        for r in errors:
            logger.info(f"  {r['filename']}: {r.get('error', 'unknown')}")

    # Wrong cases detail
    logger.info(f"\n\n{'='*70}")
    logger.info(f"  WRONG CASES DETAIL")
    logger.info(f"{'='*70}")
    for field in STANDARD_FIELDS:
        wrong_cases = []
        for r in successful:
            fm = r['metrics']['fields'][field]
            if not fm['normalized_exact_match']:
                wrong_cases.append({
                    'file': r['filename'],
                    'predicted': fm['predicted'],
                    'ground_truth': fm['ground_truth'],
                    'char_sim': fm['character_similarity'],
                })
        if wrong_cases:
            logger.info(f"\n  [{field}] — {len(wrong_cases)} errors:")
            for wc in wrong_cases:
                logger.info(f"    {wc['file']}:")
                logger.info(f"      PRED: {str(wc['predicted'])[:200]}")
                logger.info(f"      GT:   {str(wc['ground_truth'])[:200]}")
                logger.info(f"      CharSim: {wc['char_sim']:.3f}")
        else:
            logger.info(f"\n  [{field}] — ✅ 0 errors (100% accuracy)")

    # ═══════════════════════════════════════════════════════════════════
    # Compute research-grade metrics
    # ═══════════════════════════════════════════════════════════════════
    macro_metrics = {f: {'token_f1': [], 'char_sim': [], 'strict_em': [], 'norm_em': [], 'accent_em': []}
                     for f in STANDARD_FIELDS}
    status_matrix = {f: {'correct': 0, 'wrong': 0, 'missed': 0, 'extra': 0, 'both_empty': 0}
                     for f in STANDARD_FIELDS}
    processing_times = []

    for r in successful:
        processing_times.append(r['processing_time'])
        for field in STANDARD_FIELDS:
            fm = r['metrics']['fields'][field]
            macro_metrics[field]['token_f1'].append(fm['token_f1'])
            macro_metrics[field]['char_sim'].append(fm['character_similarity'])
            macro_metrics[field]['strict_em'].append(float(fm['strict_exact_match']))
            macro_metrics[field]['norm_em'].append(float(fm['normalized_exact_match']))
            macro_metrics[field]['accent_em'].append(float(fm['accent_insensitive_exact_match']))
            status_matrix[field][fm['status']] += 1

    # Compute averages
    research_per_field = {}
    for field in STANDARD_FIELDS:
        m = macro_metrics[field]
        n = len(m['token_f1']) or 1
        research_per_field[field] = {
            'normalized_exact_match': round(sum(m['norm_em']) / n, 4),
            'strict_exact_match': round(sum(m['strict_em']) / n, 4),
            'accent_insensitive_em': round(sum(m['accent_em']) / n, 4),
            'token_f1': round(sum(m['token_f1']) / n, 4),
            'character_similarity': round(sum(m['char_sim']) / n, 4),
            'correct': status_matrix[field]['correct'],
            'wrong': status_matrix[field]['wrong'],
            'missed': status_matrix[field]['missed'],
            'extra': status_matrix[field]['extra'],
            'both_empty': status_matrix[field]['both_empty'],
        }

    # Overall macro averages
    all_norm_em = [research_per_field[f]['normalized_exact_match'] for f in STANDARD_FIELDS]
    all_token_f1 = [research_per_field[f]['token_f1'] for f in STANDARD_FIELDS]
    all_char_sim = [research_per_field[f]['character_similarity'] for f in STANDARD_FIELDS]

    # Log extended metrics
    logger.info(f"\n  ═══ RESEARCH METRICS (for paper) ═══")
    logger.info(f"  {'Field':<25} {'NormEM':>8} {'StrictEM':>9} {'AccentEM':>9} {'TokenF1':>8} {'CharSim':>8}")
    logger.info(f"  {'-'*25} {'-'*8} {'-'*9} {'-'*9} {'-'*8} {'-'*8}")
    for field in STANDARD_FIELDS:
        rf = research_per_field[field]
        logger.info(f"  {field:<25} {rf['normalized_exact_match']:>7.1%} {rf['strict_exact_match']:>8.1%} "
                     f"{rf['accent_insensitive_em']:>8.1%} {rf['token_f1']:>7.4f} {rf['character_similarity']:>7.4f}")
    logger.info(f"  {'-'*25} {'-'*8} {'-'*9} {'-'*9} {'-'*8} {'-'*8}")
    macro_norm = sum(all_norm_em)/len(all_norm_em)
    macro_f1 = sum(all_token_f1)/len(all_token_f1)
    macro_cs = sum(all_char_sim)/len(all_char_sim)
    logger.info(f"  {'MACRO AVERAGE':<25} {macro_norm:>7.1%} {'':>9} {'':>9} {macro_f1:>7.4f} {macro_cs:>7.4f}")
    logger.info(f"")
    if processing_times:
        logger.info(f"  ═══ PROCESSING TIME STATISTICS ═══")
        logger.info(f"  Total:     {sum(processing_times):.1f}s")
        logger.info(f"  Mean:      {sum(processing_times)/len(processing_times):.1f}s")
        logger.info(f"  Min:       {min(processing_times):.1f}s")
        logger.info(f"  Max:       {max(processing_times):.1f}s")
        sorted_times = sorted(processing_times)
        median_idx = len(sorted_times) // 2
        logger.info(f"  Median:    {sorted_times[median_idx]:.1f}s")
        logger.info(f"  Files/min: {len(processing_times)/(sum(processing_times)/60):.2f}")

    # Save JSON results
    output_json = os.path.join(output_dir, 'benchmark_results.json')
    summary = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'pipeline': 'VietIDP OCR-LLM Pipeline v5.1',
            'pipeline_version': '5.1',
            'ocr_engine': 'EasyOCR (detection) + VietOCR vgg_transformer (recognition)',
            'llm_model': Config.OLLAMA_MODEL,
            'llm_temperature': Config.OLLAMA_TEMPERATURE,
            'ocr_dpi': Config.OCR_DPI,
            'vietocr_model': Config.VIETOCR_MODEL,
            'stamp_detector': 'YOLOv8x',
            'stamp_matting': 'HybridStampMatting (Color + Rembg)',
            'gpu': 'NVIDIA RTX 5070',
        },
        'summary': {
            'total_files': len(files),
            'successful': len(successful),
            'errors': len(errors),
            'all_6_correct': all_6_correct,
            'perfect_rate': round(all_6_correct / max(len(successful), 1), 4),
            'total_time_seconds': round(total_time, 2),
            'avg_time_per_file': round(total_time / max(len(successful), 1), 2),
            'per_field_accuracy': {
                f: round(field_correct[f] / max(field_total[f], 1), 4)
                for f in STANDARD_FIELDS
            },
        },
        'research_metrics': {
            'per_field': research_per_field,
            'macro_normalized_em': round(macro_norm, 4),
            'macro_token_f1': round(macro_f1, 4),
            'macro_character_similarity': round(macro_cs, 4),
        },
        'results': results,
    }

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Save research_metrics.json separately (clean, paper-ready)
    research_json = os.path.join(output_dir, 'research_metrics.json')
    with open(research_json, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': summary['metadata'],
            'document_level': {
                'total_documents': len(successful),
                'perfect_documents': all_6_correct,
                'perfect_rate': round(all_6_correct / max(len(successful), 1), 4),
            },
            'field_level': research_per_field,
            'macro_averages': {
                'normalized_exact_match': round(macro_norm, 4),
                'token_f1': round(macro_f1, 4),
                'character_similarity': round(macro_cs, 4),
            },
            'processing_time': {
                'total_seconds': round(sum(processing_times), 2) if processing_times else 0,
                'mean_seconds': round(sum(processing_times)/max(len(processing_times),1), 2) if processing_times else 0,
                'min_seconds': round(min(processing_times), 2) if processing_times else 0,
                'max_seconds': round(max(processing_times), 2) if processing_times else 0,
            },
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\n\n{'='*70}")
    logger.info(f"  OUTPUT FILES")
    logger.info(f"{'='*70}")
    logger.info(f"  Report:      {log_path}")
    logger.info(f"  Results:     {output_json}")
    logger.info(f"  Metrics:     {research_json}")
    logger.info(f"  Per-file:    {os.path.join(output_dir, 'per_file')}/")
    logger.info(f"{'='*70}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VietIDP Full Benchmark (Research Edition)")
    parser.add_argument("--input", default="data/raw/pdf_test",
                        help="Input directory with PDFs")
    parser.add_argument("--gt", default="data/benchmark/ground_truth.json",
                        help="Ground truth JSON")
    parser.add_argument("--output", default="results/benchmark",
                        help="Output directory")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of files to process")
    args = parser.parse_args()

    run_benchmark(args.input, args.gt, args.output, args.limit)
