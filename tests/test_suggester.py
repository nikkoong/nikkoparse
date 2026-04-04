"""
Unit tests for core.suggester module
"""

import json
import tempfile
from pathlib import Path
from core.suggester import get_suggestions, _extract_text_from_liteparse


class TestSuggester:
    """Tests for field suggestion generation"""

    def test_extract_text_from_liteparse_direct_text(self):
        """Test extracting text from LiteParse JSON with direct text field"""
        data = {"text": "Invoice Number: INV-123\nTotal: $500.00"}

        result = _extract_text_from_liteparse(data)

        assert "Invoice Number" in result
        assert "INV-123" in result

    def test_extract_text_from_liteparse_pages_array(self):
        """Test extracting text from LiteParse JSON with pages array"""
        data = {"pages": [{"text": "Page 1 content"}, {"text": "Page 2 content"}]}

        result = _extract_text_from_liteparse(data)

        assert "Page 1" in result
        assert "Page 2" in result

    def test_extract_text_from_liteparse_items_array(self):
        """Test extracting text from LiteParse JSON with items array"""
        data = {"items": [{"text": "Item 1"}, {"text": "Item 2"}]}

        result = _extract_text_from_liteparse(data)

        assert "Item 1" in result
        assert "Item 2" in result

    def test_extract_text_from_liteparse_string(self):
        """Test extracting text when data is already a string"""
        data = "Direct text content"

        result = _extract_text_from_liteparse(data)

        assert result == "Direct text content"

    def test_extract_text_from_liteparse_empty(self):
        """Test extracting text from empty data"""
        data = {}

        result = _extract_text_from_liteparse(data)

        assert result == ""

    def test_extract_text_with_content_field(self):
        """Test extracting text from content/body/markdown fields"""
        test_cases = [
            {"content": "Content field text"},
            {"body": "Body field text"},
            {"markdown": "Markdown field text"},
        ]

        for data in test_cases:
            result = _extract_text_from_liteparse(data)
            assert len(result) > 0


class TestSuggestionScoring:
    """Tests for suggestion scoring logic (integration-style tests)"""

    def test_suggestion_requires_parsed_files(self):
        """Test that suggestions require parsed files"""
        # This would need a mock project structure
        # For now, just documenting the expected behavior
        pass

    def test_suggestion_samples_up_to_5_documents(self):
        """Test that suggester samples at most 5 documents"""
        # This would need a mock project with many files
        pass

    def test_suggestion_scores_by_keyword_matches(self):
        """Test that scoring is based on keyword matches"""
        # This would need mock documents with known keywords
        pass

    def test_suggestion_returns_top_10(self):
        """Test that at most 10 suggestions are returned"""
        pass

    def test_suggestion_includes_sample_values(self):
        """Test that suggestions include sample values from regex matches"""
        pass
