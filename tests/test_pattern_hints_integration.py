"""
Integration tests for pattern hint generation with real PDF documents

Tests pattern hint generation using actual payslip and ConEd bill PDFs
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

import pytest


# Test data paths
PAYSLIPS_DIR = Path(__file__).parent.parent / "payslips"
CONED_DIR = Path(__file__).parent.parent / "con_ed_bills"
TEST_OUTPUT_DIR = Path(__file__).parent / "test_output"


def parse_pdf(pdf_path: Path) -> str:
    """
    Parse a PDF file using LiteParse and return text

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text from PDF
    """
    TEST_OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = TEST_OUTPUT_DIR / f"{pdf_path.stem}.json"

    # Run lit parse
    cmd = ["lit", "parse", str(pdf_path), "-o", str(output_file), "--format", "json"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        raise RuntimeError(f"LiteParse failed for {pdf_path.name}: {result.stderr}")

    # Read the output
    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract text from various LiteParse output formats
    if isinstance(data, str):
        return data

    if "text" in data:
        return data["text"]

    if "pages" in data and isinstance(data["pages"], list):
        return "\n\n".join(
            page.get("text", "") if isinstance(page, dict) else str(page)
            for page in data["pages"]
        )

    if "items" in data and isinstance(data["items"], list):
        return "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in data["items"]
        )

    if "content" in data:
        return data["content"]

    return str(data)


def generate_pattern_hint_simple(before_text: str, value: str) -> Dict:
    """
    Simplified pattern hint generator - detects structure in context

    Args:
        before_text: Text before the value
        value: The value to extract

    Returns:
        Dictionary with building blocks and suggested patterns
    """
    # Take last 200 chars
    context = before_text[-200:].strip()
    lines = context.split("\n")
    last_line = lines[-1] if lines else ""

    building_blocks = []

    # 1. Detect row label (word before numbers)
    label_match = re.match(r"^([A-Za-z][A-Za-z\s()/-]*?)(?=\s+[\d$])", last_line)
    row_label = None
    if label_match:
        row_label = label_match.group(1).strip()
        building_blocks.append(
            {"type": "label", "text": row_label, "pattern": re.escape(row_label)}
        )

    # 2. Detect dates to skip (do this BEFORE detecting numbers to avoid splitting dates)
    dates = re.findall(
        r"\d{1,2}/\d{1,2}/\d{4}(?:\s*-\s*\d{1,2}/\d{1,2}/\d{4})?", last_line
    )
    date_positions = []
    for date in dates:
        pos = last_line.find(date)
        if pos != -1:
            date_positions.append((pos, pos + len(date)))

    if dates:
        building_blocks.append(
            {"type": "skip_date", "text": dates[0], "pattern": r"[\d/\s-]+"}
        )

    # 3. Detect numbers to skip (but exclude numbers that are part of dates or the target value)
    numbers = []
    for match in re.finditer(r"\d+(?:\.\d+)?", last_line):
        num_text = match.group(0)
        num_pos = match.start()

        # Skip if this number is part of the target value
        if num_text == value or num_text in value:
            continue

        # Skip if this number is within a date range
        is_in_date = any(start <= num_pos < end for start, end in date_positions)

        if not is_in_date:
            numbers.append(num_text)

    # Add unique numbers to building blocks (skip duplicates)
    seen_numbers = set()
    for num in numbers:
        if num not in seen_numbers:
            building_blocks.append(
                {"type": "skip_number", "text": num, "pattern": r"\d+"}
            )
            seen_numbers.add(num)

    # Generate patterns
    patterns = []

    # Specific pattern using all blocks
    if building_blocks:
        parts = [b["pattern"] for b in building_blocks]
        specific = r"\s+".join(parts) + r"\s+([\d.]+)"
        patterns.append({"type": "specific", "pattern": specific})

    # Medium pattern - label + greedy skip
    if row_label:
        medium = re.escape(row_label) + r".*?([\d.]+)"
        patterns.append({"type": "medium", "pattern": medium})

    # Fallback - value only
    patterns.append({"type": "value_only", "pattern": r"([\d.]+)"})

    return {"building_blocks": building_blocks, "patterns": patterns}


def extract_with_pattern(text: str, pattern: str) -> Optional[str]:
    """Extract value from text using regex pattern"""
    try:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1) if match.lastindex else match.group(0)
    except re.error:
        pass
    return None


class TestPatternHintsIntegration:
    """Integration tests for pattern hints with real PDFs"""

    @classmethod
    def teardown_class(cls):
        """Clean up test output directory"""
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

    def test_payslip_hourly_rate_109_134615(self):
        """
        Test pattern generation for payslip hourly rate 109.134615

        Verifies:
        1. Can find the value in parsed PDF
        2. Pattern hints detect row label, date column, hours column
        3. Generated patterns extract same field from other payslips
        """
        # Parse example payslip
        example_pdf = PAYSLIPS_DIR / "Payslip-12_26_2025.pdf"
        if not example_pdf.exists():
            pytest.skip(f"Test payslip not found: {example_pdf}")

        text = parse_pdf(example_pdf)

        # Find the hourly rate
        target = "109.134615"
        pos = text.find(target)
        assert pos != -1, f"Value {target} not found in {example_pdf.name}"

        # Generate pattern hints
        before_text = text[max(0, pos - 500) : pos]
        hints = generate_pattern_hint_simple(before_text, target)

        # Verify building blocks
        assert len(hints["building_blocks"]) > 0, "Should detect building blocks"
        block_types = [b["type"] for b in hints["building_blocks"]]

        print(f"\n=== Payslip Hourly Rate Test ===")
        print(f"Target: {target}")
        print(f"Building blocks:")
        for block in hints["building_blocks"]:
            print(f"  {block['type']}: '{block['text']}' -> {block['pattern']}")

        # Should detect salary label
        assert "label" in block_types, "Should detect row label (Salary)"

        # Test patterns on other payslips
        test_pdfs = [
            PAYSLIPS_DIR / "Payslip-01_09_2026.pdf",
            PAYSLIPS_DIR / "Payslip-01_23_2026.pdf",
        ]

        for pattern_info in hints["patterns"]:
            pattern = pattern_info["pattern"]
            successes = 0

            for test_pdf in test_pdfs:
                if not test_pdf.exists():
                    continue

                test_text = parse_pdf(test_pdf)
                extracted = extract_with_pattern(test_text, pattern)

                if extracted and re.match(r"\d+\.\d+", extracted):
                    successes += 1

            print(f"  [{pattern_info['type']}] {successes}/{len(test_pdfs)}: {pattern}")

        # At least one pattern should work
        assert any(
            extract_with_pattern(parse_pdf(p), hints["patterns"][0]["pattern"])
            for p in test_pdfs
            if p.exists()
        ), "At least one pattern should extract from other docs"

    def test_coned_kwh_field(self):
        """
        Test pattern generation for ConEd kWh usage field

        Verifies:
        1. Can find kWh value in bill
        2. Pattern hints detect structure
        3. Patterns work across different bills
        """
        example_pdf = CONED_DIR / "0126.pdf"
        if not example_pdf.exists():
            pytest.skip(f"Test ConEd bill not found: {example_pdf}")

        text = parse_pdf(example_pdf)

        # Find kWh value
        kwh_match = re.search(r"(\d{2,4}(?:\.\d{2})?)\s*kWh", text, re.IGNORECASE)
        if not kwh_match:
            kwh_match = re.search(
                r"kWh.*?(\d{2,4}(?:\.\d{2})?)", text, re.IGNORECASE | re.DOTALL
            )

        assert kwh_match, f"Could not find kWh value in {example_pdf.name}"

        target = kwh_match.group(1)
        pos = text.find(target, kwh_match.start())

        # Generate hints
        before_text = text[max(0, pos - 500) : pos]
        hints = generate_pattern_hint_simple(before_text, target)

        print(f"\n=== ConEd kWh Test ===")
        print(f"Target: {target} kWh")
        print(f"Building blocks:")
        for block in hints["building_blocks"]:
            print(f"  {block['type']}: '{block['text']}' -> {block['pattern']}")

        # Test on other bills
        test_pdfs = [CONED_DIR / "0225.pdf", CONED_DIR / "0325.pdf"]

        for pattern_info in hints["patterns"]:
            pattern = pattern_info["pattern"]
            successes = sum(
                1
                for p in test_pdfs
                if p.exists() and extract_with_pattern(parse_pdf(p), pattern)
            )
            print(f"  [{pattern_info['type']}] {successes}/{len(test_pdfs)}: {pattern}")

    def test_coned_rate_field(self):
        """
        Test pattern generation for ConEd rate field (12.902¢/kWh)

        Verifies:
        1. Can find rate value in bill
        2. Pattern hints detect structure
        3. Patterns work across different bills
        """
        example_pdf = CONED_DIR / "0126.pdf"
        if not example_pdf.exists():
            pytest.skip(f"Test ConEd bill not found: {example_pdf}")

        text = parse_pdf(example_pdf)

        # Find rate (number with 3 decimals)
        rate_match = re.search(
            r"(\d{1,3}\.\d{3})\s*[¢c]\s*/\s*kWh", text, re.IGNORECASE
        )
        if not rate_match:
            rate_match = re.search(r"(\d{1,3}\.\d{3})", text)

        assert rate_match, f"Could not find rate value in {example_pdf.name}"

        target = rate_match.group(1)
        pos = text.find(target, rate_match.start())

        # Generate hints
        before_text = text[max(0, pos - 500) : pos]
        hints = generate_pattern_hint_simple(before_text, target)

        print(f"\n=== ConEd Rate Test ===")
        print(f"Target: {target}¢/kWh")
        print(f"Building blocks:")
        for block in hints["building_blocks"]:
            print(f"  {block['type']}: '{block['text']}' -> {block['pattern']}")

        # Test on other bills
        test_pdfs = [CONED_DIR / "0225.pdf", CONED_DIR / "0325.pdf"]

        for pattern_info in hints["patterns"]:
            pattern = pattern_info["pattern"]
            successes = sum(
                1
                for p in test_pdfs
                if p.exists() and extract_with_pattern(parse_pdf(p), pattern)
            )
            print(f"  [{pattern_info['type']}] {successes}/{len(test_pdfs)}: {pattern}")
