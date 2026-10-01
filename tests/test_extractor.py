"""
Tests for the pure extraction helpers in core/extractor.py

Covers single-pattern extraction, the label-anchored -> value-only -> primary
pattern cascade, and best-match selection across multiple hits. Fixtures are
small inline document strings; the project/storage layer is never touched.
"""

from core.extractor import (
    _extract_with_cascading_patterns,
    _extract_with_pattern,
    _find_best_match,
)


def _match(value, position, line_number=1):
    return {"value": value, "position": position, "line_number": line_number}


class TestFindBestMatch:
    def test_empty_match_list_returns_none(self):
        assert _find_best_match([], {}, "doc.pdf") is None

    def test_single_match_is_returned(self):
        only = _match("42.50", 10)
        assert _find_best_match([only], {}, "doc.pdf") == only

    def test_defaults_to_first_match_without_examples(self):
        matches = [_match("first", 10), _match("second", 90)]
        assert _find_best_match(matches, {}, "doc.pdf")["value"] == "first"

    def test_prefers_match_closest_to_example_position(self):
        matches = [_match("far", 10), _match("near", 90)]
        field = {"examples": [{"file": "doc.pdf", "position": 100}]}
        assert _find_best_match(matches, field, "doc.pdf")["value"] == "near"

    def test_example_from_another_file_is_ignored(self):
        matches = [_match("first", 10), _match("second", 90)]
        field = {"examples": [{"file": "other.pdf", "position": 90}]}
        assert _find_best_match(matches, field, "doc.pdf")["value"] == "first"

    def test_legacy_example_matches_by_value(self):
        matches = [_match("A", 10), _match("B", 90)]
        field = {"example_file": "doc.pdf", "example_value": "B"}
        assert _find_best_match(matches, field, "doc.pdf")["value"] == "B"


class TestExtractWithPattern:
    def test_extracts_capture_group_value(self):
        value, matched, all_matches = _extract_with_pattern(
            r"Total Amount[:\s]*\$?([\d,\.]+)",
            "Total Amount: $42.50\nPlease pay within 30 days",
            {},
            "doc.pdf",
        )
        assert value == "42.50"
        assert matched is True
        assert len(all_matches) == 1

    def test_match_records_position_and_line_number(self):
        text = "Header line\nID: 777\nFooter line"
        _, matched, all_matches = _extract_with_pattern(
            r"ID[:\s]*(\d+)", text, {}, "doc.pdf"
        )
        assert matched is True
        assert all_matches[0]["value"] == "777"
        assert all_matches[0]["line_number"] == 2
        assert all_matches[0]["position"] == text.index("ID")

    def test_pattern_without_group_returns_full_match(self):
        value, matched, _ = _extract_with_pattern(
            r"\b\d{4}\b", "Year: 2024", {}, "doc.pdf"
        )
        assert value == "2024"
        assert matched is True

    def test_no_match(self):
        result = _extract_with_pattern(
            r"Missing[:\s]*(\d+)", "nothing here", {}, "doc.pdf"
        )
        assert result == (None, False, [])

    def test_empty_pattern(self):
        result = _extract_with_pattern("", "some text", {}, "doc.pdf")
        assert result == (None, False, [])

    def test_invalid_pattern(self):
        result = _extract_with_pattern("([", "some text", {}, "doc.pdf")
        assert result == (None, False, [])


class TestCascadingPatterns:
    TEXT = "Discount: $9.99\nTotal: $42.50"

    def test_label_anchored_wins_over_value_only(self):
        field = {
            "regex_patterns": [
                {"type": "value_only", "pattern": r"\$([\d,\.]+)"},
                {
                    "type": "label_anchored",
                    "pattern": r"Total[:\s]*\$?([\d,\.]+)",
                },
            ]
        }
        value, matched, _, pattern_type = _extract_with_cascading_patterns(
            field, self.TEXT, "doc.pdf"
        )
        assert value == "42.50"
        assert matched is True
        assert pattern_type == "label_anchored"

    def test_falls_back_to_value_only_when_anchor_misses(self):
        field = {
            "regex_patterns": [
                {
                    "type": "label_anchored",
                    "pattern": r"Nonexistent[:\s]*\$?([\d,\.]+)",
                },
                {"type": "value_only", "pattern": r"\$([\d,\.]+)"},
            ]
        }
        value, matched, _, pattern_type = _extract_with_cascading_patterns(
            field, "Amount: $17.25", "doc.pdf"
        )
        assert value == "17.25"
        assert matched is True
        assert pattern_type == "value_only"

    def test_falls_back_to_primary_regex_field(self):
        field = {"regex": r"Total[:\s]*\$?([\d,\.]+)"}
        value, matched, _, pattern_type = _extract_with_cascading_patterns(
            field, "Total: $42.50", "doc.pdf"
        )
        assert value == "42.50"
        assert matched is True
        assert pattern_type == "primary"

    def test_no_pattern_matches(self):
        field = {"regex": r"Nope[:\s]*(\d+)"}
        result = _extract_with_cascading_patterns(field, "irrelevant text", "doc.pdf")
        assert result == (None, False, [], "primary")

    def test_empty_field(self):
        result = _extract_with_cascading_patterns({}, "irrelevant text", "doc.pdf")
        assert result == (None, False, [], None)
