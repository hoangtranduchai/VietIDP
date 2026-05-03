# -*- coding: utf-8 -*-
"""Unit tests for normalization and extraction metrics modules."""

import pytest

from src.evaluation.normalization import (
    normalize_unicode_nfc,
    collapse_whitespace,
    cleanup_basic_punctuation,
    case_fold_text,
    remove_accents,
    normalize_text,
    normalize_vietnamese_administrative_date,
    normalize_extraction_value,
)
from src.evaluation.extraction_metrics import (
    compute_field_metrics,
    _token_f1,
    _character_similarity,
    _edit_distance,
    STANDARD_FIELDS,
)


# ═══════════════════════════════════════════════════════════════════════
# Normalization Tests
# ═══════════════════════════════════════════════════════════════════════


class TestNormalizeUnicodeNFC:
    def test_none_returns_empty(self):
        assert normalize_unicode_nfc(None) == ""

    def test_normal_text(self):
        assert normalize_unicode_nfc("Việt Nam") == "Việt Nam"

    def test_nfd_to_nfc(self):
        # NFD: "ệ" as "e" + combining circumflex + combining dot below
        nfd = "Vi\u0065\u0302\u0323t"
        result = normalize_unicode_nfc(nfd)
        assert "ệ" in result or result == "Việt"


class TestCollapseWhitespace:
    def test_multiple_spaces(self):
        assert collapse_whitespace("hello   world") == "hello world"

    def test_tabs_and_newlines(self):
        assert collapse_whitespace("hello\t\n  world") == "hello world"

    def test_leading_trailing(self):
        assert collapse_whitespace("  hello  ") == "hello"

    def test_none(self):
        assert collapse_whitespace(None) == ""


class TestCleanupBasicPunctuation:
    def test_curly_quotes_to_straight(self):
        result = cleanup_basic_punctuation("\u201CHello\u201D")
        assert '"' in result

    def test_em_dash_to_hyphen(self):
        result = cleanup_basic_punctuation("2023\u20142024")
        assert "-" in result

    def test_fullwidth_to_ascii(self):
        result = cleanup_basic_punctuation("Hello\uff0c World")
        assert "," in result


class TestCaseFold:
    def test_uppercase(self):
        assert case_fold_text("HELLO") == "hello"

    def test_vietnamese(self):
        result = case_fold_text("QUYẾT ĐỊNH")
        assert result == "quyết định"


class TestRemoveAccents:
    def test_vietnamese_accents(self):
        result = remove_accents("Việt Nam")
        assert result == "Viet Nam"

    def test_diacritics(self):
        result = remove_accents("Đại học Bách Khoa")
        assert result == "Dai hoc Bach Khoa"

    def test_no_accents(self):
        assert remove_accents("Hello") == "Hello"


class TestNormalizeText:
    def test_basic(self):
        result = normalize_text("  HELLO   World  ")
        assert result == "hello world"

    def test_accent_insensitive(self):
        result = normalize_text("Đại học", accent_insensitive=True)
        assert result == "dai hoc"

    def test_accent_sensitive(self):
        result = normalize_text("Đại học", accent_insensitive=False)
        assert "đại" in result


class TestNormalizeVietnameseDate:
    def test_slash_format(self):
        assert normalize_vietnamese_administrative_date("15/03/2024") == "2024-03-15"

    def test_dash_format(self):
        assert normalize_vietnamese_administrative_date("15-03-2024") == "2024-03-15"

    def test_vietnamese_format(self):
        result = normalize_vietnamese_administrative_date("ngày 15 tháng 03 năm 2024")
        assert result == "2024-03-15"

    def test_invalid_date(self):
        result = normalize_vietnamese_administrative_date("32/13/2024")
        assert result is None

    def test_empty(self):
        assert normalize_vietnamese_administrative_date("") is None
        assert normalize_vietnamese_administrative_date(None) is None

    def test_non_date_text(self):
        assert normalize_vietnamese_administrative_date("not a date") is None


class TestNormalizeExtractionValue:
    def test_regular_text(self):
        result = normalize_extraction_value("  HELLO  World  ")
        assert result == "hello world"

    def test_date_field(self):
        result = normalize_extraction_value("15/03/2024", date_field=True)
        assert result == "2024-03-15"

    def test_date_field_non_date(self):
        # When date normalization fails, falls back to text normalization
        result = normalize_extraction_value("not a date", date_field=True)
        assert result == "not a date"


# ═══════════════════════════════════════════════════════════════════════
# Extraction Metrics Tests
# ═══════════════════════════════════════════════════════════════════════


class TestTokenF1:
    def test_perfect_match(self):
        assert _token_f1("hello world", "hello world") == 1.0

    def test_no_overlap(self):
        assert _token_f1("foo bar", "baz qux") == 0.0

    def test_partial_overlap(self):
        f1 = _token_f1("hello world foo", "hello world bar")
        assert 0.0 < f1 < 1.0

    def test_both_empty(self):
        assert _token_f1("", "") == 1.0

    def test_one_empty(self):
        assert _token_f1("", "hello") == 0.0
        assert _token_f1("hello", "") == 0.0


class TestEditDistance:
    def test_same(self):
        assert _edit_distance("hello", "hello") == 0

    def test_one_insert(self):
        assert _edit_distance("hell", "hello") == 1

    def test_one_delete(self):
        assert _edit_distance("hello", "hell") == 1

    def test_one_substitute(self):
        assert _edit_distance("hello", "hella") == 1

    def test_empty(self):
        assert _edit_distance("", "abc") == 3
        assert _edit_distance("abc", "") == 3


class TestCharacterSimilarity:
    def test_identical(self):
        assert _character_similarity("hello", "hello") == 1.0

    def test_completely_different(self):
        sim = _character_similarity("abc", "xyz")
        assert sim == 0.0

    def test_both_empty(self):
        assert _character_similarity("", "") == 1.0

    def test_one_empty(self):
        assert _character_similarity("", "hello") == 0.0

    def test_partial(self):
        sim = _character_similarity("hello", "helo")
        assert 0.5 < sim < 1.0


class TestComputeFieldMetrics:
    def test_perfect_match(self):
        data = {
            "loai_van_ban": "Quyết định",
            "so_hieu": "123/QĐ-UBND",
            "ngay_ban_hanh": "15/03/2024",
            "co_quan_ban_hanh": "UBND TP.HCM",
            "trich_yeu": "Về việc phê duyệt",
            "nguoi_ky": "Nguyễn Văn A",
        }
        result = compute_field_metrics(data, data)
        assert result["macro"]["strict_exact_match"] == 1.0
        assert result["macro"]["normalized_exact_match"] == 1.0
        assert result["status_counts"]["correct"] == len(STANDARD_FIELDS)

    def test_all_wrong(self):
        pred = {f: "wrong" for f in STANDARD_FIELDS}
        gt = {f: "correct" for f in STANDARD_FIELDS}
        result = compute_field_metrics(pred, gt)
        assert result["macro"]["strict_exact_match"] == 0.0
        assert result["status_counts"]["wrong"] == len(STANDARD_FIELDS)

    def test_missing_prediction(self):
        gt = {"loai_van_ban": "Quyết định", "so_hieu": "123"}
        result = compute_field_metrics({}, gt)
        assert result["status_counts"]["missed"] >= 2

    def test_extra_prediction(self):
        pred = {"loai_van_ban": "Quyết định"}
        result = compute_field_metrics(pred, {})
        assert result["status_counts"]["extra"] >= 1

    def test_both_empty(self):
        result = compute_field_metrics({}, {})
        assert result["status_counts"]["both_empty"] == len(STANDARD_FIELDS)

    def test_none_inputs(self):
        result = compute_field_metrics(None, None)
        assert result["field_count"] == len(STANDARD_FIELDS)

    def test_normalized_match_case_difference(self):
        pred = {"loai_van_ban": "QUYẾT ĐỊNH"}
        gt = {"loai_van_ban": "quyết định"}
        result = compute_field_metrics(pred, gt)
        field = result["fields"]["loai_van_ban"]
        assert field["strict_exact_match"] is False
        assert field["normalized_exact_match"] is True

    def test_date_normalization(self):
        pred = {"ngay_ban_hanh": "15/03/2024"}
        gt = {"ngay_ban_hanh": "ngày 15 tháng 03 năm 2024"}
        result = compute_field_metrics(pred, gt)
        field = result["fields"]["ngay_ban_hanh"]
        # Both should normalize to 2024-03-15
        assert field["normalized_exact_match"] is True

    def test_signer_not_agency(self):
        """Ensure nguoi_ky and co_quan_ban_hanh are evaluated independently."""
        pred = {"nguoi_ky": "UBND TP.HCM", "co_quan_ban_hanh": "Nguyễn Văn A"}
        gt = {"nguoi_ky": "Nguyễn Văn A", "co_quan_ban_hanh": "UBND TP.HCM"}
        result = compute_field_metrics(pred, gt)
        assert result["fields"]["nguoi_ky"]["status"] == "wrong"
        assert result["fields"]["co_quan_ban_hanh"]["status"] == "wrong"

    def test_motto_not_agency(self):
        """National motto should not be confused with issuing agency."""
        pred = {"co_quan_ban_hanh": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"}
        gt = {"co_quan_ban_hanh": "UBND TỈNH BÌNH DƯƠNG"}
        result = compute_field_metrics(pred, gt)
        assert result["fields"]["co_quan_ban_hanh"]["status"] == "wrong"
