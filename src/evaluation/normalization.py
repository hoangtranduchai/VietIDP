# -*- coding: utf-8 -*-
"""Normalization helpers for publication-grade extraction evaluation."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

WHITESPACE_RE = re.compile(r"\s+")
PUNCT_SPACE_BEFORE_RE = re.compile(r"\s+([,.;:!?/\-])")
PUNCT_SPACE_AFTER_RE = re.compile(r"([(/\-])\s+")
DATE_SLASH_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
DATE_VI_RE = re.compile(
    r"\bng[aà]y\s+(\d{1,2})\s+th[aá]ng\s+(\d{1,2})\s+n[aă]m\s+(\d{4})\b",
    flags=re.IGNORECASE,
)

PUNCT_TRANSLATION = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "„": '"',
        "‟": '"',
        "'": "'",
        "'": "'",
        "‚": "'",
        "‛": "'",
        "–": "-",
        "—": "-",
        "−": "-",
        "…": "...",
        "，": ",",
        "：": ":",
        "；": ";",
        "！": "!",
        "？": "?",
        "（": "(",
        "）": ")",
        "／": "/",
    }
)


def normalize_unicode_nfc(text: str | None) -> str:
    if text is None:
        return ""
    return unicodedata.normalize("NFC", str(text))



def collapse_whitespace(text: str | None) -> str:
    normalized = normalize_unicode_nfc(text)
    return WHITESPACE_RE.sub(" ", normalized).strip()



def cleanup_basic_punctuation(text: str | None) -> str:
    cleaned = collapse_whitespace(text).translate(PUNCT_TRANSLATION)
    cleaned = PUNCT_SPACE_BEFORE_RE.sub(r"\1", cleaned)
    cleaned = PUNCT_SPACE_AFTER_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"([,.;:!?])(?!\s|$)", r"\1 ", cleaned)
    return collapse_whitespace(cleaned)



def case_fold_text(text: str | None) -> str:
    return cleanup_basic_punctuation(text).casefold()



def remove_accents(text: str | None) -> str:
    normalized = normalize_unicode_nfc(text)
    decomposed = unicodedata.normalize("NFD", normalized)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    stripped = stripped.replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFC", stripped)



def normalize_text(text: str | None, *, accent_insensitive: bool = False) -> str:
    normalized = case_fold_text(text)
    if accent_insensitive:
        normalized = remove_accents(normalized)
        normalized = collapse_whitespace(normalized)
    return normalized



def _format_iso_date(day: int, month: int, year: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None



def normalize_vietnamese_administrative_date(text: str | None) -> str | None:
    normalized = case_fold_text(text)
    if not normalized:
        return None

    match = DATE_SLASH_RE.fullmatch(normalized)
    if match:
        day, month, year = (int(part) for part in match.groups())
        return _format_iso_date(day, month, year)

    match = DATE_VI_RE.fullmatch(normalized)
    if match:
        day, month, year = (int(part) for part in match.groups())
        return _format_iso_date(day, month, year)

    return None



def normalize_extraction_value(
    text: str | None,
    *,
    accent_insensitive: bool = False,
    date_field: bool = False,
) -> str:
    normalized = normalize_text(text, accent_insensitive=accent_insensitive)
    if date_field:
        return normalize_vietnamese_administrative_date(normalized) or normalized
    return normalized
