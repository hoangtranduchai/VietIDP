# -*- coding: utf-8 -*-
"""Strict field-level extraction metrics for VietIDP benchmark evaluation."""

from __future__ import annotations

from collections import Counter

from src.evaluation.normalization import normalize_extraction_value

STANDARD_FIELDS = [
    "loai_van_ban",
    "so_hieu",
    "ngay_ban_hanh",
    "co_quan_ban_hanh",
    "trich_yeu",
    "nguoi_ky",
]
DATE_FIELDS = {"ngay_ban_hanh"}



def _stringify(value) -> str:
    if value is None:
        return ""
    return str(value)



def _is_empty(value: str) -> bool:
    return not value.strip()



def _token_f1(prediction: str, reference: str) -> float:
    pred_tokens = prediction.split()
    ref_tokens = reference.split()

    if not pred_tokens and not ref_tokens:
        return 1.0
    if not pred_tokens or not ref_tokens:
        return 0.0

    pred_counter = Counter(pred_tokens)
    ref_counter = Counter(ref_tokens)
    overlap = sum((pred_counter & ref_counter).values())
    if overlap == 0:
        return 0.0

    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)



def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous_row = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current_row = [i]
        for j, right_char in enumerate(right, start=1):
            insertions = current_row[j - 1] + 1
            deletions = previous_row[j] + 1
            substitutions = previous_row[j - 1] + (left_char != right_char)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]



def _character_similarity(prediction: str, reference: str) -> float:
    if not prediction and not reference:
        return 1.0
    if not prediction or not reference:
        return 0.0
    distance = _edit_distance(prediction, reference)
    return max(0.0, 1.0 - (distance / max(len(reference), len(prediction), 1)))



def _field_status(raw_pred: str, raw_gt: str, normalized_match: bool) -> str:
    pred_empty = _is_empty(raw_pred)
    gt_empty = _is_empty(raw_gt)
    if pred_empty and gt_empty:
        return "both_empty"
    if pred_empty and not gt_empty:
        return "missed"
    if not pred_empty and gt_empty:
        return "extra"
    return "correct" if normalized_match else "wrong"



def compute_field_metrics(predicted: dict | None, ground_truth: dict | None) -> dict:
    predicted = predicted or {}
    ground_truth = ground_truth or {}

    fields = {}
    totals = {
        "strict_exact_match": 0.0,
        "normalized_exact_match": 0.0,
        "accent_insensitive_exact_match": 0.0,
        "token_f1": 0.0,
        "character_similarity": 0.0,
    }
    status_counts = {status: 0 for status in ["correct", "wrong", "missed", "extra", "both_empty"]}

    for field in STANDARD_FIELDS:
        raw_pred = _stringify(predicted.get(field, ""))
        raw_gt = _stringify(ground_truth.get(field, ""))
        is_date_field = field in DATE_FIELDS

        strict_exact_match = raw_pred == raw_gt
        normalized_pred = normalize_extraction_value(raw_pred, date_field=is_date_field)
        normalized_gt = normalize_extraction_value(raw_gt, date_field=is_date_field)
        accent_pred = normalize_extraction_value(raw_pred, accent_insensitive=True, date_field=is_date_field)
        accent_gt = normalize_extraction_value(raw_gt, accent_insensitive=True, date_field=is_date_field)

        normalized_exact_match = normalized_pred == normalized_gt
        accent_exact_match = accent_pred == accent_gt
        token_f1 = _token_f1(normalized_pred, normalized_gt)
        character_similarity = _character_similarity(normalized_pred, normalized_gt)
        status = _field_status(raw_pred, raw_gt, normalized_exact_match)

        field_metrics = {
            "status": status,
            "strict_exact_match": strict_exact_match,
            "normalized_exact_match": normalized_exact_match,
            "accent_insensitive_exact_match": accent_exact_match,
            "token_f1": round(token_f1, 4),
            "character_similarity": round(character_similarity, 4),
            "predicted": raw_pred,
            "ground_truth": raw_gt,
            "normalized_predicted": normalized_pred,
            "normalized_ground_truth": normalized_gt,
            "accent_insensitive_predicted": accent_pred,
            "accent_insensitive_ground_truth": accent_gt,
        }
        fields[field] = field_metrics

        totals["strict_exact_match"] += float(strict_exact_match)
        totals["normalized_exact_match"] += float(normalized_exact_match)
        totals["accent_insensitive_exact_match"] += float(accent_exact_match)
        totals["token_f1"] += token_f1
        totals["character_similarity"] += character_similarity
        status_counts[status] += 1

    denominator = max(len(STANDARD_FIELDS), 1)
    macro = {name: round(total / denominator, 4) for name, total in totals.items()}

    return {
        "fields": fields,
        "macro": macro,
        "status_counts": status_counts,
        "field_count": len(STANDARD_FIELDS),
    }
