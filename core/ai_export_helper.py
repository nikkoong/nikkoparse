"""
AI Export Helper Module
Optimizes document samples for AI context window limitations
"""

import re
from typing import List, Dict, Tuple


def smart_truncate_text(text: str, max_chars: int = 3000) -> str:
    """
    Intelligently truncate text to fit context window while preserving structure

    Strategy:
    1. Keep first 1000 chars (usually header/account info)
    2. Sample middle sections (field data)
    3. Keep last 500 chars (usually footer/totals)
    """
    if len(text) <= max_chars:
        return text

    # Take first 1000 chars (header section)
    header = text[:1000]

    # Take last 500 chars (footer/summary)
    footer = text[-500:]

    # Sample middle - take every Nth line to stay under budget
    middle_start = 1000
    middle_end = len(text) - 500
    middle_text = text[middle_start:middle_end]

    remaining_budget = max_chars - 1000 - 500 - 100  # 100 for markers

    if len(middle_text) <= remaining_budget:
        middle_sample = middle_text
    else:
        # Sample every Nth line
        lines = middle_text.split("\n")
        sample_ratio = len(middle_text) / remaining_budget
        step = max(1, int(len(lines) / (len(lines) / sample_ratio)))
        sampled_lines = lines[::step]
        middle_sample = "\n".join(
            sampled_lines[: int(remaining_budget / 50)]
        )  # ~50 chars per line

    # Combine with markers
    truncated = (
        header
        + "\n...\n[MIDDLE SECTION SAMPLED - Original length: {} chars]\n...\n".format(
            len(middle_text)
        )
        + middle_sample
        + "\n...\n[FOOTER SECTION]\n"
        + footer
    )

    return truncated[:max_chars]


def extract_key_value_pairs(text: str, max_pairs: int = 30) -> List[Tuple[str, str]]:
    """
    Extract key-value pairs from text for pattern learning

    Returns list of (label, value) tuples that AI can use for pattern generation
    """
    pairs = []

    # Common patterns for label: value or label value
    patterns = [
        r"([A-Z][A-Za-z\s]{2,30}):\s*(\$?[\d,\.-]+\w*)",  # Label: $123.45
        r"([A-Z][A-Za-z\s]{2,30})\s+(\$[\d,\.]+)",  # Label $123.45
        r"([A-Z][A-Za-z\s]{2,30})\s+(\d{1,2}/\d{1,2}/\d{2,4})",  # Label 01/26/26
        r"([A-Z][A-Za-z\s]{2,30}):\s*([A-Z0-9][A-Za-z0-9\s-]{3,50})",  # Label: Text Value
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            label = match.group(1).strip()
            value = match.group(2).strip()

            # Filter out common false positives
            if len(label) > 3 and len(value) > 0:
                if label not in ["Page", "Total", "Date", "Account"]:  # Too generic
                    pairs.append((label, value))

            if len(pairs) >= max_pairs:
                break

        if len(pairs) >= max_pairs:
            break

    return pairs[:max_pairs]


def create_compact_sample(text: str, filename: str, max_chars: int = 3000) -> Dict:
    """
    Create a compact document sample optimized for AI context window

    Returns structured sample with key-value pairs and truncated full text
    """
    # Extract key-value pairs for structured learning
    kv_pairs = extract_key_value_pairs(text)

    # Create compact representation
    compact = {
        "filename": filename,
        "length": len(text),
        "key_value_examples": [
            {"label": label, "value": value}
            for label, value in kv_pairs[:15]  # Limit to 15 most relevant
        ],
        "excerpt": smart_truncate_text(text, max_chars),
    }

    return compact


def estimate_token_count(text: str) -> int:
    """
    Rough estimation of token count (1 token ≈ 4 chars for English)
    """
    return len(text) // 4


def optimize_samples_for_context_window(
    documents: List[Dict], max_total_tokens: int = 8000
) -> List[Dict]:
    """
    Optimize document samples to fit within AI context window

    Strategy:
    - Include 2-3 full samples if documents are small
    - Use compact samples for larger documents
    - Ensure total stays under max_total_tokens

    Args:
        documents: List of {filename, text} dicts
        max_total_tokens: Maximum tokens to use (default 8000 for ~32k window)

    Returns:
        Optimized list of document samples
    """
    optimized = []
    total_tokens = 0

    # Reserve tokens for prompt template (~2000 tokens)
    available_tokens = max_total_tokens - 2000

    # Sort by size (smaller first)
    sorted_docs = sorted(documents, key=lambda d: len(d.get("text", "")))

    for doc in sorted_docs:
        text = doc.get("text", "")
        filename = doc.get("filename", "unknown")

        # Estimate if we can include full or need to compact
        doc_tokens = estimate_token_count(text)

        if total_tokens + doc_tokens < available_tokens:
            # Can include more detail
            if doc_tokens < 2000:  # Small doc, include full
                optimized.append(
                    {"filename": filename, "full_text": text, "length": len(text)}
                )
                total_tokens += doc_tokens
            else:  # Large doc, use compact
                compact = create_compact_sample(text, filename, max_chars=3000)
                optimized.append(compact)
                total_tokens += estimate_token_count(compact["excerpt"])
        else:
            # Running out of space, use minimal sample
            if len(optimized) < 2:  # Always include at least 2 samples
                minimal = create_compact_sample(text, filename, max_chars=1500)
                optimized.append(minimal)
                total_tokens += estimate_token_count(minimal["excerpt"])
            else:
                break

    return optimized
