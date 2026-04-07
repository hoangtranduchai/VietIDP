# -*- coding: utf-8 -*-
"""
OCR Evaluation Metrics
=======================
Character Error Rate (CER) và Word Error Rate (WER).

Nguồn: Phase3_OCR_Engine.py, line 257-306
"""


def compute_cer(reference: str, hypothesis: str) -> float:
    """
    Character Error Rate (CER) = (S + D + I) / N

    S = substitutions, D = deletions, I = insertions, N = reference length.
    Sử dụng Levenshtein edit distance (dynamic programming).

    Args:
        reference: Ground truth text
        hypothesis: OCR output text

    Returns:
        float: CER score (0.0 = perfect, 1.0 = completely wrong)
    """
    ref = list(reference)
    hyp = list(hypothesis)
    n = len(ref)
    m = len(hyp)

    if n == 0:
        return 0.0 if m == 0 else 1.0

    # DP table
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,       # deletion
                d[i][j - 1] + 1,       # insertion
                d[i - 1][j - 1] + cost  # substitution
            )

    return d[n][m] / n


def compute_wer(reference: str, hypothesis: str) -> float:
    """
    Word Error Rate (WER) = (S + D + I) / N

    Giống CER nhưng tính trên từ thay vì ký tự.

    Args:
        reference: Ground truth text
        hypothesis: OCR output text

    Returns:
        float: WER score
    """
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    n = len(ref_words)
    m = len(hyp_words)

    if n == 0:
        return 0.0 if m == 0 else 1.0

    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost
            )

    return d[n][m] / n
