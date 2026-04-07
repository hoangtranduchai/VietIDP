# -*- coding: utf-8 -*-
"""
LLM Extraction Evaluation
===========================
Đánh giá Precision/Recall/F1 cho trích xuất thông tin.

Nguồn: Phase4_LLM_Finetuning.py, line 485-594
"""

import os
import json


def evaluate_extraction(predictions_dir: str, ground_truth_path: str,
                        limit: int = None) -> dict:
    """
    Đánh giá độ chính xác trích xuất thông tin.

    Metrics:
    - Classification Accuracy
    - Per-field Precision/Recall/F1
    - Overall F1-Score

    Args:
        predictions_dir: Thư mục chứa *_extracted.json
        ground_truth_path: Đường dẫn file ground truth JSON
        limit: Giới hạn số file đánh giá

    Returns:
        dict với classification_accuracy, overall_f1, per_field
    """
    with open(ground_truth_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)

    fields = ['loai_van_ban', 'so_hieu', 'ngay_ban_hanh',
              'co_quan_ban_hanh', 'trich_yeu', 'nguoi_ky']

    field_scores = {f: {'tp': 0, 'fp': 0, 'fn': 0} for f in fields}
    classification_correct = 0
    total = 0

    pred_files = sorted([
        f for f in os.listdir(predictions_dir)
        if f.endswith('_extracted.json')
    ])
    if limit:
        pred_files = pred_files[:limit]

    for pred_file in pred_files:
        with open(os.path.join(predictions_dir, pred_file), 'r', encoding='utf-8') as f:
            pred = json.load(f)

        if pred.get('extraction_json') is None:
            continue

        source = pred.get('source_file', '')
        gt_match = None
        for gt in gt_data:
            if gt.get('source', '') == source or gt.get('filename', '') == source:
                gt_match = gt
                break

        if gt_match is None:
            continue

        total += 1
        pred_json = pred['extraction_json']

        if pred.get('classification', '').strip() == gt_match.get('loai_van_ban', '').strip():
            classification_correct += 1

        for field in fields:
            pred_val = str(pred_json.get(field, '')).strip()
            gt_val = str(gt_match.get(field, '')).strip()

            if pred_val and gt_val:
                if pred_val.lower() == gt_val.lower():
                    field_scores[field]['tp'] += 1
                else:
                    field_scores[field]['fp'] += 1
                    field_scores[field]['fn'] += 1
            elif pred_val and not gt_val:
                field_scores[field]['fp'] += 1
            elif not pred_val and gt_val:
                field_scores[field]['fn'] += 1

    # Calculate metrics
    print("=" * 60)
    print("🧠 LLM EXTRACTION EVALUATION")
    print("=" * 60)

    if total > 0:
        print(f"\n📊 Classification Accuracy: {classification_correct}/{total} "
              f"({classification_correct/total:.2%})")

    print(f"\n{'Field':<20} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("-" * 52)

    overall_tp, overall_fp, overall_fn = 0, 0, 0

    for field in fields:
        tp = field_scores[field]['tp']
        fp = field_scores[field]['fp']
        fn = field_scores[field]['fn']

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        print(f"  {field:<20} {precision:>9.2%} {recall:>9.2%} {f1:>9.2%}")

        overall_tp += tp
        overall_fp += fp
        overall_fn += fn

    overall_p = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) > 0 else 0
    overall_r = overall_tp / (overall_tp + overall_fn) if (overall_tp + overall_fn) > 0 else 0
    overall_f1 = 2 * overall_p * overall_r / (overall_p + overall_r) if (overall_p + overall_r) > 0 else 0

    print("-" * 52)
    print(f"  {'OVERALL':<20} {overall_p:>9.2%} {overall_r:>9.2%} {overall_f1:>9.2%}")
    print("=" * 60)

    return {
        'classification_accuracy': classification_correct / max(total, 1),
        'overall_f1': overall_f1,
        'per_field': field_scores,
        'total_evaluated': total,
    }
