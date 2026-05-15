# -*- coding: utf-8 -*-
"""
Benchmark Pipeline — Đo F1/Exact Match trên 20 PDF
====================================================
So sánh kết quả pipeline (QLoRA) với ground truth labels.

Metrics:
  - Field-level Precision, Recall, F1 (normalized string match)
  - Document-level Exact Match (tất cả 6 trường đúng = 1)
  - Per-field accuracy

Sử dụng: python scripts/benchmark_pipeline.py
"""

import os
import sys
import json
import re
import unicodedata
import pathlib

# [HOTFIX] Windows UTF-8
_original_read_text = pathlib.Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    return _original_read_text(self, encoding=encoding or "utf-8", errors=errors)
pathlib.Path.read_text = _utf8_read_text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def normalize_text(text: str) -> str:
    """Chuẩn hóa text để so sánh: lowercase, bỏ dấu cách thừa, NFC."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def char_similarity(pred: str, gt: str) -> float:
    """Tính character-level similarity (Sørensen–Dice)."""
    pred_n = normalize_text(pred)
    gt_n = normalize_text(gt)
    if not pred_n and not gt_n:
        return 1.0
    if not pred_n or not gt_n:
        return 0.0
    
    pred_chars = set(enumerate(pred_n))
    gt_chars = set(enumerate(gt_n))
    
    # Use sequence matching for better comparison
    from difflib import SequenceMatcher
    return SequenceMatcher(None, pred_n, gt_n).ratio()


def token_f1(pred: str, gt: str) -> dict:
    """Tính token-level Precision, Recall, F1."""
    pred_tokens = set(normalize_text(pred).split())
    gt_tokens = set(normalize_text(gt).split())
    
    if not pred_tokens and not gt_tokens:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not pred_tokens or not gt_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    
    common = pred_tokens & gt_tokens
    precision = len(common) / len(pred_tokens) if pred_tokens else 0
    recall = len(common) / len(gt_tokens) if gt_tokens else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {"precision": precision, "recall": recall, "f1": f1}


def main():
    gt_path = os.path.join("data", "benchmark", "ground_truth.json")
    results_dir = "results"
    
    # Load ground truth
    with open(gt_path, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    print(f"📊 Benchmark Pipeline VietIDP (QLoRA Backend)")
    print(f"{'='*60}")
    print(f"📂 Ground truth: {len(ground_truth)} files")
    
    # Load pipeline results
    fields = ["loai_van_ban", "so_hieu", "ngay_ban_hanh", 
              "co_quan_ban_hanh", "trich_yeu", "nguoi_ky"]
    
    field_scores = {f: {"exact": [], "char_sim": [], "f1": []} for f in fields}
    doc_exact_matches = []
    evaluated = 0
    
    print(f"\n{'File':<16} {'loai_vb':>8} {'so_hieu':>8} {'ngay':>6} {'co_quan':>8} {'trich_yeu':>10} {'nguoi_ky':>9}")
    print(f"{'-'*16} {'-'*8} {'-'*8} {'-'*6} {'-'*8} {'-'*10} {'-'*9}")
    
    for pdf_name, gt in ground_truth.items():
        result_name = pdf_name.replace('.pdf', '_result.json')
        result_path = os.path.join(results_dir, result_name)
        
        if not os.path.exists(result_path):
            continue
        
        with open(result_path, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
        
        pred = result_data.get("extraction", {})
        evaluated += 1
        
        doc_all_exact = True
        row_scores = []
        
        for field in fields:
            gt_val = gt.get(field, "")
            pred_val = pred.get(field, "")
            
            # Bỏ qua trường không có ground truth
            if not gt_val:
                row_scores.append("  —   ")
                continue
            
            # Exact match (normalized)
            exact = 1 if normalize_text(pred_val) == normalize_text(gt_val) else 0
            
            # Character similarity
            sim = char_similarity(pred_val, gt_val)
            
            # Token F1
            tf1 = token_f1(pred_val, gt_val)
            
            field_scores[field]["exact"].append(exact)
            field_scores[field]["char_sim"].append(sim)
            field_scores[field]["f1"].append(tf1["f1"])
            
            if exact == 0:
                doc_all_exact = False
            
            row_scores.append(f" {sim:.2f}  ")
        
        doc_exact_matches.append(1 if doc_all_exact else 0)
        
        scores_str = "".join(row_scores)
        print(f"  {pdf_name:<14} {scores_str}")
    
    # Tổng kết
    print(f"\n{'='*60}")
    print(f"📊 TỔNG KẾT BENCHMARK ({evaluated} files đánh giá)")
    print(f"{'='*60}\n")
    
    print(f"  {'Field':<20} {'Exact Match':>12} {'Char Sim':>10} {'Token F1':>10} {'N':>4}")
    print(f"  {'-'*20} {'-'*12} {'-'*10} {'-'*10} {'-'*4}")
    
    total_exact = []
    total_sim = []
    total_f1 = []
    
    for field in fields:
        scores = field_scores[field]
        n = len(scores["exact"])
        if n == 0:
            print(f"  {field:<20} {'—':>12} {'—':>10} {'—':>10} {0:>4}")
            continue
        
        avg_exact = sum(scores["exact"]) / n
        avg_sim = sum(scores["char_sim"]) / n
        avg_f1 = sum(scores["f1"]) / n
        
        total_exact.extend(scores["exact"])
        total_sim.extend(scores["char_sim"])
        total_f1.extend(scores["f1"])
        
        print(f"  {field:<20} {avg_exact:>11.1%} {avg_sim:>9.1%} {avg_f1:>9.1%} {n:>4}")
    
    print(f"  {'-'*20} {'-'*12} {'-'*10} {'-'*10} {'-'*4}")
    
    if total_exact:
        print(f"  {'MACRO AVERAGE':<20} {sum(total_exact)/len(total_exact):>11.1%} "
              f"{sum(total_sim)/len(total_sim):>9.1%} "
              f"{sum(total_f1)/len(total_f1):>9.1%} {len(total_exact):>4}")
    
    if doc_exact_matches:
        print(f"\n  📈 Document Exact Match: {sum(doc_exact_matches)}/{len(doc_exact_matches)} "
              f"({sum(doc_exact_matches)/len(doc_exact_matches):.1%})")
    
    # Save benchmark report
    report = {
        "evaluated_files": evaluated,
        "field_scores": {},
        "macro_avg": {},
        "doc_exact_match": sum(doc_exact_matches) / len(doc_exact_matches) if doc_exact_matches else 0
    }
    for field in fields:
        scores = field_scores[field]
        n = len(scores["exact"])
        if n > 0:
            report["field_scores"][field] = {
                "exact_match": sum(scores["exact"]) / n,
                "char_similarity": sum(scores["char_sim"]) / n,
                "token_f1": sum(scores["f1"]) / n,
                "n_samples": n
            }
    if total_exact:
        report["macro_avg"] = {
            "exact_match": sum(total_exact) / len(total_exact),
            "char_similarity": sum(total_sim) / len(total_sim),
            "token_f1": sum(total_f1) / len(total_f1),
        }
    
    report_path = os.path.join("data", "benchmark", "benchmark_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 Report saved: {report_path}")


if __name__ == "__main__":
    main()
