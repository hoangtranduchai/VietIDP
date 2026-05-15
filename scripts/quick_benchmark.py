# -*- coding: utf-8 -*-
"""
Quick Benchmark — So sánh extraction vs ground truth cho N PDFs.
Chạy: python scripts/quick_benchmark.py --count 5
"""

import argparse
import functools
import json
import os
import sys
import time

# Force unbuffered output
print = functools.partial(print, flush=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline.ocr_llm_pipeline import VietIDPPipeline
from src.config import Config


def normalize_text(s: str) -> str:
    """Chuẩn hóa text để so sánh: lowercase, strip whitespace."""
    if not s:
        return ""
    return " ".join(s.lower().strip().split())


def exact_match(pred: str, gt: str) -> bool:
    return normalize_text(pred) == normalize_text(gt)


def containment_match(pred: str, gt: str) -> bool:
    """Check if pred contains gt or gt contains pred (for partial extractions)."""
    p = normalize_text(pred)
    g = normalize_text(gt)
    if not p or not g:
        return p == g
    return p in g or g in p


def token_f1(pred: str, gt: str) -> float:
    """Token-level F1 score."""
    p_tokens = set(normalize_text(pred).split())
    g_tokens = set(normalize_text(gt).split())
    if not p_tokens and not g_tokens:
        return 1.0
    if not p_tokens or not g_tokens:
        return 0.0
    common = p_tokens & g_tokens
    precision = len(common) / len(p_tokens)
    recall = len(common) / len(g_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def char_similarity(pred: str, gt: str) -> float:
    """Tính character-level similarity (1 - CER approximation)."""
    p = normalize_text(pred)
    g = normalize_text(gt)
    if not g:
        return 1.0 if not p else 0.0
    if not p:
        return 0.0
    # Simple longest common subsequence ratio
    m, n = len(p), len(g)
    if m == 0 or n == 0:
        return 0.0
    # Use set intersection as quick proxy
    common = sum(1 for c in set(p) if c in g)
    total = len(set(p) | set(g))
    return common / total if total > 0 else 0.0


def run_benchmark(count: int = 5):
    """Chạy benchmark trên count PDFs."""
    # Load ground truth
    gt_path = Config.BASE_DIR / "data" / "benchmark" / "ground_truth.json"
    if not gt_path.exists():
        print(f"❌ Ground truth không tìm thấy: {gt_path}")
        return

    gt = json.load(open(gt_path, "r", encoding="utf-8"))
    pdf_dir = Config.BASE_DIR / "data" / "raw" / "pdf_test"

    # Init pipeline
    print("=" * 60)
    print(f"📊 VietIDP Quick Benchmark — {count} PDFs")
    print("=" * 60)
    pipeline = VietIDPPipeline()

    fields = ["loai_van_ban", "so_hieu", "ngay_ban_hanh",
              "co_quan_ban_hanh", "trich_yeu", "nguoi_ky"]

    results = []
    field_scores = {f: [] for f in fields}

    for i in range(1, count + 1):
        pdf_name = f"pdf_test_{i}.pdf"
        pdf_path = pdf_dir / pdf_name

        if not pdf_path.exists():
            print(f"  ⚠️ Skip {pdf_name} — file không tồn tại")
            continue

        if pdf_name not in gt:
            print(f"  ⚠️ Skip {pdf_name} — không có ground truth")
            continue

        gt_entry = gt[pdf_name]
        print(f"\n{'='*40}")
        print(f"📄 [{i}/{count}] {pdf_name}")

        start = time.time()
        try:
            result = pipeline.process_file(str(pdf_path), save_result=True)
            elapsed = time.time() - start
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

        extraction = result.get("extraction", {})

        doc_result = {
            "file": pdf_name,
            "time_seconds": round(elapsed, 2),
            "fields": {}
        }

        for field in fields:
            pred = str(extraction.get(field, ""))
            truth = str(gt_entry.get(field, ""))
            em = exact_match(pred, truth)
            sim = char_similarity(pred, truth)
            field_scores[field].append(1.0 if em else 0.0)

            doc_result["fields"][field] = {
                "pred": pred,
                "truth": truth,
                "exact_match": em,
                "similarity": round(sim, 3)
            }

            status = "✅" if em else "⚠️"
            print(f"  {status} {field}: {pred[:60]}{'...' if len(pred)>60 else ''}")
            if not em:
                print(f"     GT: {truth[:60]}{'...' if len(truth)>60 else ''}")

        results.append(doc_result)

    # Summary
    print("\n" + "=" * 60)
    print("📊 BENCHMARK SUMMARY")
    print("=" * 60)

    total_docs = len(results)
    if total_docs == 0:
        print("❌ Không có document nào được xử lý")
        return

    print(f"Documents: {total_docs}/{count}")
    avg_time = sum(r["time_seconds"] for r in results) / total_docs
    print(f"Avg time: {avg_time:.1f}s")

    print(f"\n{'Field':<25} {'Exact Match':>12} {'Count':>8}")
    print("-" * 50)
    overall_em = []
    for field in fields:
        scores = field_scores[field]
        if scores:
            em_rate = sum(scores) / len(scores)
            overall_em.extend(scores)
            print(f"{field:<25} {em_rate*100:>10.1f}% {int(sum(scores)):>4}/{len(scores)}")

    if overall_em:
        total_em = sum(overall_em) / len(overall_em)
        print("-" * 50)
        print(f"{'OVERALL':<25} {total_em*100:>10.1f}% {int(sum(overall_em)):>4}/{len(overall_em)}")

    # Save results
    out_dir = Config.RESULTS_DIR / "benchmark"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"quick_benchmark_{count}docs.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "count": total_docs,
            "avg_time_seconds": round(avg_time, 2),
            "field_exact_match": {
                f: round(sum(field_scores[f]) / len(field_scores[f]) * 100, 1)
                if field_scores[f] else 0
                for f in fields
            },
            "overall_exact_match": round(total_em * 100, 1) if overall_em else 0,
            "details": results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Saved: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5,
                        help="Number of PDFs to benchmark")
    args = parser.parse_args()
    run_benchmark(args.count)
