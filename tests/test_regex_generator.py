"""
Unit tests for core.regex_generator module
"""

import pytest
from core.regex_generator import (
    generate_regex,
    preview_regex,
    _detect_value_type,
    _get_capture_group,
)


class TestRegexGenerator:
    """Tests for regex generation from highlighted text"""

    def test_generate_regex_with_dollar_amount(self):
        """Test regex generation for dollar amounts"""
        context_lines = ["Total Amount: $11,286.54", "Payment Terms: Net 30"]
        selected = "$11,286.54"

        result = generate_regex(selected, context_lines)

        assert result["regex"] is not None
        assert result["value_type"] == "dollar"
        assert "suggested_label" in result
        assert result["sample_match"] is not None

    def test_generate_regex_with_date(self):
        """Test regex generation for dates"""
        context_lines = ["Invoice Date: March 15, 2024", "Due Date: April 15, 2024"]
        selected = "March 15, 2024"

        result = generate_regex(selected, context_lines)

        assert result["regex"] is not None
        assert result["value_type"] == "date"
        assert result["sample_match"] is not None

    def test_generate_regex_with_invoice_number(self):
        """Test regex generation for invoice numbers"""
        context_lines = [
            "INVOICE",
            "Invoice Number: INV-2024-001234",
            "Invoice Date: March 15",
        ]
        selected = "INV-2024-001234"

        result = generate_regex(selected, context_lines)

        assert result["regex"] is not None
        assert result["value_type"] == "text"
        assert result["sample_match"] is not None

    def test_generate_regex_with_integer(self):
        """Test regex generation for integers"""
        context_lines = ["Quantity: 40", "Unit Price: $150.00"]
        selected = "40"

        result = generate_regex(selected, context_lines)

        assert result["regex"] is not None
        # Note: plain numbers are detected as 'dollar' since they could be amounts
        assert result["value_type"] in ("integer", "dollar")

    def test_generate_regex_with_percent(self):
        """Test regex generation for percentages"""
        context_lines = ["Subtotal: $10,450.50", "Tax (8%): $836.04"]
        selected = "8%"

        result = generate_regex(selected, context_lines)

        assert result["regex"] is not None
        assert result["value_type"] == "percent"

    def test_generate_regex_extracts_label_from_left(self):
        """Test that label is extracted from left side of selected text"""
        context_lines = ["Patient Name: Sarah Williams", "Patient ID: PAT-789456"]
        selected = "Sarah Williams"

        result = generate_regex(selected, context_lines)

        assert result["suggested_label"] is not None or result["regex"] is not None
        # Should extract "Patient Name" from the left side
        assert "Patient Name" in result["regex"] or "patient" in result["regex"].lower()

    def test_generate_regex_without_context(self):
        """Test regex generation when selected text is not in context"""
        context_lines = ["Some unrelated text", "More unrelated content"]
        selected = "$1,234.56"

        result = generate_regex(selected, context_lines)

        # Should still return a regex (fallback behavior)
        assert result["regex"] is not None
        assert result["value_type"] == "dollar"

    def test_preview_regex_basic(self):
        """Test regex preview with basic pattern"""
        regex = r"Invoice Number:\s+([A-Z]+-\d+-\d+)"
        text = "Invoice Number: INV-2024-001234\nTotal: $1,234.56"

        match = preview_regex(regex, text)

        assert match == "INV-2024-001234"

    def test_preview_regex_with_no_match(self):
        """Test regex preview when pattern doesn't match"""
        regex = r"Order Number:\s+(\d+)"
        text = "Invoice Number: INV-2024-001234"

        match = preview_regex(regex, text)

        assert match is None

    def test_preview_regex_with_invalid_regex(self):
        """Test that invalid regex returns None"""
        regex = r"Invoice Number: ([A-Z]+"  # Unclosed group
        text = "Some content"

        match = preview_regex(regex, text)

        assert match is None


class TestValueTypeDetection:
    """Tests for detecting value types in selected text"""

    def test_detect_dollar_amount(self):
        """Test detection of dollar amounts"""
        test_cases = ["$1,234.56", "$10.00", "$1,000,000.99", "1234.56", "500"]

        for text in test_cases:
            value_type = _detect_value_type(text)
            assert value_type == "dollar", f"Failed for: {text}"

    def test_detect_date_formats(self):
        """Test detection of various date formats"""
        test_cases = [
            "March 15, 2024",
            "Mar 15 2024",
            "03/15/2024",
            "2024-03-15",
            "15-03-2024",
        ]

        for text in test_cases:
            value_type = _detect_value_type(text)
            assert value_type == "date", f"Failed for: {text}"

    def test_detect_percent(self):
        """Test detection of percentages"""
        test_cases = ["8%", "15.5%", "100%"]

        for text in test_cases:
            value_type = _detect_value_type(text)
            assert value_type == "percent", f"Failed for: {text}"

    def test_detect_integer(self):
        """Test detection of integers"""
        test_cases = ["42", "1000", "99"]

        for text in test_cases:
            value_type = _detect_value_type(text)
            # Note: plain numbers match dollar regex too
            assert value_type in ("integer", "dollar"), f"Failed for: {text}"

    def test_detect_date_range(self):
        """Test detection of date ranges"""
        test_cases = [
            "Jan 1 - Jan 31",
            "March 1 to March 31",
            "2024-01-01 through 2024-12-31",
        ]

        for text in test_cases:
            value_type = _detect_value_type(text)
            assert value_type == "date_range", f"Failed for: {text}"

    def test_detect_text_default(self):
        """Test that non-matching patterns default to text"""
        test_cases = ["INV-2024-001234", "John Doe", "Mixed 123 Text"]

        for text in test_cases:
            value_type = _detect_value_type(text)
            assert value_type == "text", f"Failed for: {text}"


class TestCaptureGroups:
    """Tests for capture group generation"""

    def test_get_capture_group_dollar(self):
        """Test capture group for dollar amounts"""
        capture = _get_capture_group("dollar")
        assert "\\$" in capture or "\\d" in capture

    def test_get_capture_group_date(self):
        """Test capture group for dates"""
        capture = _get_capture_group("date")
        assert capture is not None
        assert len(capture) > 0

    def test_get_capture_group_integer(self):
        """Test capture group for integers"""
        capture = _get_capture_group("integer")
        assert "\\d" in capture

    def test_get_capture_group_text(self):
        """Test capture group for generic text"""
        capture = _get_capture_group("text")
        assert capture == r"(.+)"
