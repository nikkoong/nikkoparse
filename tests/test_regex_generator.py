"""
Tests for core/regex_generator.py

Covers the pure pattern-generation logic: value-type detection, capture-group
selection, label-anchored regex generation from highlighted text, and regex
previewing. All fixtures are small inline strings — no PDFs or OCR involved.
"""

import re

import pytest

from core.regex_generator import (
    _detect_value_type,
    _get_capture_group,
    generate_regex,
    preview_regex,
)


class TestDetectValueType:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("$1,234.56", "dollar"),
            ("1234.56", "dollar"),
            ("12.5%", "percent"),
            ("January 15, 2024", "date"),
            ("Jan 15 2024", "date"),
            ("01/15/2024", "date"),
            ("2024-01-15", "date"),
            ("January 1, 2024 - January 31, 2024", "date_range"),
            ("some free text", "text"),
        ],
    )
    def test_detects_value_types(self, value, expected):
        assert _detect_value_type(value) == expected

    def test_surrounding_whitespace_is_ignored(self):
        assert _detect_value_type("  $50.00  ") == "dollar"


class TestGetCaptureGroup:
    @pytest.mark.parametrize(
        "value_type,expected",
        [
            ("dollar", r"\$?([\d,\.]+)"),
            ("percent", r"([\d\.]+%?)"),
            ("integer", r"(\d+)"),
            ("text", r"(.+)"),
            ("date_range", r"(.+?)"),
        ],
    )
    def test_known_types(self, value_type, expected):
        assert _get_capture_group(value_type) == expected

    def test_unknown_type_falls_back_to_generic(self):
        assert _get_capture_group("not-a-type") == r"(.+)"

    def test_dollar_group_captures_amount(self):
        match = re.search(_get_capture_group("dollar"), "Total: $99.95")
        assert match.group(1) == "99.95"

    def test_date_group_captures_numeric_date(self):
        match = re.search(_get_capture_group("date"), "Dated: 01/15/2024")
        assert match.group(1) == "01/15/2024"


class TestGenerateRegex:
    def test_label_anchored_dollar_amount(self):
        context = ["Invoice #1042", "Total Amount Due: $1,234.56", "Thank you"]
        result = generate_regex("$1,234.56", context)

        assert result["value_type"] == "dollar"
        assert result["sample_match"] == "1,234.56"
        # "Total Amount Due" is an exact entry in the field dictionary
        assert result["suggested_label"] == "Total Amount Due"

    def test_generated_regex_generalizes_to_other_amounts(self):
        context = ["Total Amount Due: $1,234.56"]
        result = generate_regex("$1,234.56", context)

        captured = preview_regex(result["regex"], "Total Amount Due: $2,000.00")
        assert captured == "2,000.00"

    def test_date_value_with_label(self):
        result = generate_regex("01/15/2024", ["Invoice Date: 01/15/2024"])

        assert result["value_type"] == "date"
        assert result["sample_match"] == "01/15/2024"

    def test_percent_value_with_label(self):
        result = generate_regex("8.25%", ["Tax Rate: 8.25%"])

        assert result["value_type"] == "percent"
        assert result["sample_match"] == "8.25%"

    def test_unlabeled_value_uses_capture_group_only(self):
        result = generate_regex("$450.00", ["$450.00"])

        assert result["value_type"] == "dollar"
        assert result["sample_match"] == "450.00"
        assert result["suggested_label"] == ""

    def test_value_missing_from_context_falls_back_to_literal(self):
        result = generate_regex("$99.99", ["Unrelated line", "Another line"])

        assert result["value_type"] == "dollar"
        assert result["sample_match"] == "$99.99"
        assert result["suggested_label"] == ""
        # Fallback regex matches the literal value in new text
        assert preview_regex(result["regex"], "Amount owed: $99.99") == "$99.99"


class TestPreviewRegex:
    def test_returns_first_capture_group(self):
        assert preview_regex(r"Total[:\s]*\$?([\d,\.]+)", "Total: $42.50") == "42.50"

    def test_returns_full_match_when_no_group(self):
        assert preview_regex(r"\d{4}", "Year: 2024") == "2024"

    def test_no_match_returns_none(self):
        assert preview_regex(r"Phone[:\s]*(\d+)", "No phone listed") is None

    def test_invalid_regex_returns_none(self):
        assert preview_regex("([", "any text") is None

    def test_matching_is_case_insensitive(self):
        assert preview_regex(r"total[:\s]*\$?([\d,\.]+)", "TOTAL: $7.25") == "7.25"
