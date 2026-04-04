"""
Regex Generator Module
Generates regex patterns from highlighted text and context
"""

import re
from typing import Dict, List, Optional

from core.field_dictionary import find_by_label


def generate_regex(highlighted_value: str, context_lines: List[str]) -> Dict:
    """
    Generate a regex pattern from highlighted text and surrounding context

    Args:
        highlighted_value: The text the user selected
        context_lines: List of context lines (±2 lines around selection)

    Returns:
        Dictionary with regex, value_type, sample_match, and suggested_label
    """
    # Find the line containing the highlighted value
    containing_line = None
    for line in context_lines:
        if highlighted_value in line:
            containing_line = line
            break

    if not containing_line:
        # Fallback: just return a simple regex for the value
        value_type = _detect_value_type(highlighted_value)
        capture_group = _get_capture_group(value_type)
        return {
            "regex": re.escape(highlighted_value),
            "value_type": value_type,
            "sample_match": highlighted_value,
            "suggested_label": "",
        }

    # Extract text to the LEFT of the highlighted value
    value_index = containing_line.index(highlighted_value)
    label_text = containing_line[:value_index]

    # Clean up label text
    label_text = label_text.strip()

    # Remove trailing punctuation
    label_text = label_text.rstrip(":=-.")

    # Take last 50 characters to avoid overly long anchors
    if len(label_text) > 50:
        label_text = label_text[-50:]

    label_text = label_text.strip()

    # Detect value type
    value_type = _detect_value_type(highlighted_value)

    # Get appropriate capture group
    capture_group = _get_capture_group(value_type)

    # Assemble regex
    if label_text:
        escaped_label = re.escape(label_text)
        regex_pattern = escaped_label + r"[:\s]*" + capture_group
    else:
        # No label found, just match the value pattern
        regex_pattern = capture_group

    # Test the regex on the context
    full_context = "\n".join(context_lines)
    sample_match = None
    try:
        match = re.search(regex_pattern, full_context, re.IGNORECASE)
        if match:
            sample_match = match.group(1) if match.lastindex else match.group(0)
    except re.error:
        pass

    # Look up suggested label from dictionary
    suggested_label = ""
    if label_text:
        dict_entry = find_by_label(label_text)
        if dict_entry:
            suggested_label = dict_entry["label"]

    return {
        "regex": regex_pattern,
        "value_type": value_type,
        "sample_match": sample_match or highlighted_value,
        "suggested_label": suggested_label,
    }


def preview_regex(regex: str, text: str) -> Optional[str]:
    """
    Preview what a regex pattern would capture from text

    Args:
        regex: Regular expression pattern
        text: Text to search in

    Returns:
        Captured value or None if no match
    """
    try:
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            # Return first capture group if available, otherwise full match
            return match.group(1) if match.lastindex else match.group(0)
    except re.error:
        return None

    return None


def _detect_value_type(value: str) -> str:
    """
    Detect the type of value from the highlighted text

    Args:
        value: The highlighted value

    Returns:
        Value type: dollar|date|date_range|percent|integer|text
    """
    value = value.strip()

    # Dollar amount: $123.45 or 123.45
    if re.match(r"^\$?[\d,]+\.?\d{0,2}$", value):
        return "dollar"

    # Percentage: 12.5% or 12%
    if re.match(r"^[\d\.]+%$", value):
        return "percent"

    # Written date: January 15, 2024 or Jan 15 2024
    if re.match(r"^[A-Za-z]+\s+\d{1,2},?\s+\d{4}$", value):
        return "date"

    # Numeric date: 01/15/2024 or 2024-01-15 or 01-15-2024
    if re.match(r"^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$", value) or re.match(
        r"^\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}$", value
    ):
        return "date"

    # Date range: contains ' - ', ' to ', ' through ', ' – '
    if any(sep in value for sep in [" - ", " to ", " through ", " – ", " thru "]):
        return "date_range"

    # Integer only: all digits, no decimal
    if re.match(r"^\d+$", value):
        return "integer"

    # Default to generic text
    return "text"


def _get_capture_group(value_type: str) -> str:
    """
    Get the appropriate regex capture group for a value type

    Args:
        value_type: The detected value type

    Returns:
        Regex capture group pattern
    """
    capture_groups = {
        "dollar": r"\$?([\d,\.]+)",
        "date": r"([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        "date_range": r"(.+?)",
        "percent": r"([\d\.]+%?)",
        "integer": r"(\d+)",
        "text": r"(.+)",
    }

    return capture_groups.get(value_type, r"(.+)")
