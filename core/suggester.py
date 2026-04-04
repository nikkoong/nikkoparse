"""
Suggester Module
Implements field suggestion scoring algorithm
"""

import json
import random
import re
from pathlib import Path
from typing import List, Dict, Optional

from core.field_dictionary import get_dictionary
from core.storage import get_project, get_project_dir


def get_suggestions(project_id: str, max_suggestions: int = 10) -> List[Dict]:
    """
    Generate field suggestions based on document content

    Args:
        project_id: Project ID (slug)
        max_suggestions: Maximum number of suggestions to return (default: 10)

    Returns:
        List of suggested fields with sample values and match counts
    """
    # Load project
    project = get_project(project_id)
    if not project:
        return []

    # Get successfully parsed files
    parsed_files = [
        f
        for f in project.get("files", [])
        if f.get("parsed") and not f.get("parse_failed")
    ]

    if not parsed_files:
        return []

    # Sample up to 5 random documents
    sample_size = min(5, len(parsed_files))
    sampled_files = random.sample(parsed_files, sample_size)

    # Load parsed text from sampled documents
    project_dir = get_project_dir(project_id)
    raw_dir = project_dir / "raw"

    sampled_docs = []
    for file_info in sampled_files:
        filename = file_info["filename"]
        base_name = filename.rsplit(".", 1)[0]
        liteparse_file = raw_dir / f"{base_name}.json"

        if liteparse_file.exists():
            try:
                with open(liteparse_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Extract text from LiteParse JSON structure
                    text = _extract_text_from_liteparse(data)
                    if text:
                        sampled_docs.append({"filename": filename, "text": text})
            except (json.JSONDecodeError, IOError):
                continue

    if not sampled_docs:
        return []

    # Score all dictionary entries
    dictionary = get_dictionary()
    scored_entries = []

    for entry in dictionary:
        score = 0

        # Check each sampled document
        for doc in sampled_docs:
            text_lower = doc["text"].lower()

            # Check if any keyword appears in the text
            for keyword in entry["keywords"]:
                if keyword.lower() in text_lower:
                    score += 1
                    break  # Count at most 1 per document

        if score > 0:
            scored_entries.append({"entry": entry, "score": score})

    # Sort by score descending
    scored_entries.sort(key=lambda x: x["score"], reverse=True)

    # Take top N
    top_entries = scored_entries[:max_suggestions]

    # For each suggested field, find sample value and context
    suggestions = []
    for item in top_entries:
        entry = item["entry"]
        score = item["score"]

        # Try to find a sample value by running the regex
        sample_value = None
        sample_context = None

        try:
            regex_pattern = entry["suggested_regex"]

            for doc in sampled_docs:
                match = re.search(regex_pattern, doc["text"], re.IGNORECASE)
                if match:
                    # Get the captured value
                    sample_value = match.group(1) if match.lastindex else match.group(0)

                    # Get context (±50 chars around the match)
                    start = max(0, match.start() - 50)
                    end = min(len(doc["text"]), match.end() + 50)
                    sample_context = doc["text"][start:end].strip()
                    break
        except re.error:
            # Invalid regex, skip
            pass

        suggestions.append(
            {
                "field_id": entry["field_id"],
                "label": entry["label"],
                "suggested_regex": entry["suggested_regex"],
                "sample_value": sample_value,
                "sample_context": sample_context,
                "match_count": score,
                "suggested": True,
                "confirmed": False,
            }
        )

    return suggestions


def _extract_text_from_liteparse(data: dict) -> str:
    """
    Extract text content from LiteParse JSON output

    Args:
        data: Parsed LiteParse JSON data

    Returns:
        Extracted text string
    """
    # LiteParse JSON structure varies, but typically has a 'text' field
    # or 'pages' array with text content

    if isinstance(data, dict):
        # Try direct text field
        if "text" in data:
            return str(data["text"])

        # Try pages array
        if "pages" in data and isinstance(data["pages"], list):
            texts = []
            for page in data["pages"]:
                if isinstance(page, dict) and "text" in page:
                    texts.append(str(page["text"]))
            return "\n".join(texts)

        # Try items/elements array
        if "items" in data and isinstance(data["items"], list):
            texts = []
            for item in data["items"]:
                if isinstance(item, dict) and "text" in item:
                    texts.append(str(item["text"]))
            return " ".join(texts)

        # Fallback: try to extract any text-like fields
        text_parts = []
        for key, value in data.items():
            if key in ["text", "content", "body", "markdown"]:
                text_parts.append(str(value))

        if text_parts:
            return "\n".join(text_parts)

    # If data is a string, return it
    if isinstance(data, str):
        return data

    return ""
