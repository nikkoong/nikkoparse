"""
Extractor Module
Runs extraction of field values from parsed documents
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.storage import get_project, save_project, get_project_dir
from core.suggester import _extract_text_from_liteparse


def _find_best_match(
    all_matches: List[Dict], field: Dict, filename: str
) -> Optional[Dict]:
    """
    Find the best match from multiple regex matches based on example positions.

    Strategy:
    1. If field has examples with positions, prefer match closest to example position
    2. Otherwise, prefer first occurrence (most likely to be the primary field value)

    Args:
        all_matches: List of match dicts with 'value', 'position', 'line_number'
        field: Field schema dict with optional 'examples' array
        filename: Current file being processed

    Returns:
        Best match dict, or None if no matches
    """
    if not all_matches:
        return None

    if len(all_matches) == 1:
        return all_matches[0]

    # Check if we have an example position for this specific file
    examples = field.get("examples", [])
    target_position = None

    # Look for an example from this specific file
    for example in examples:
        if example.get("file") == filename and example.get("position") is not None:
            target_position = example.get("position")
            break

    # Fall back to legacy example_file/example_value if no examples array
    if target_position is None:
        if field.get("example_file") == filename and field.get("example_value"):
            # We don't have position stored for legacy examples,
            # but we can try to match by value
            example_value = field.get("example_value")
            for match in all_matches:
                if match.get("value") == example_value:
                    return match

    # If we have a target position, find the match closest to it
    if target_position is not None:
        closest_match = min(
            all_matches, key=lambda m: abs(m.get("position", 0) - target_position)
        )
        return closest_match

    # Default: return first match
    return all_matches[0]


def _extract_with_pattern(
    pattern: str, text: str, field: Dict, filename: str
) -> Tuple[Optional[str], bool, List[Dict]]:
    """
    Try to extract a value using a single regex pattern.

    Args:
        pattern: Regex pattern to try
        text: Document text to search
        field: Field schema dict
        filename: Current filename

    Returns:
        Tuple of (value, matched, all_matches)
    """
    value = None
    matched = False
    all_matches = []

    if not pattern:
        return value, matched, all_matches

    try:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))

        if matches:
            matched = True

            for match_obj in matches:
                match_value = (
                    match_obj.group(1) if match_obj.lastindex else match_obj.group(0)
                )
                if match_value:
                    all_matches.append(
                        {
                            "value": match_value.strip(),
                            "position": match_obj.start(),
                            "line_number": text[: match_obj.start()].count("\n") + 1,
                        }
                    )

            if all_matches:
                best_match = _find_best_match(all_matches, field, filename)
                value = best_match["value"] if best_match else all_matches[0]["value"]

    except re.error:
        pass

    return value, matched, all_matches


def _extract_with_cascading_patterns(
    field: Dict, text: str, filename: str
) -> Tuple[Optional[str], bool, List[Dict], Optional[str]]:
    """
    Try multiple regex patterns in order of specificity.

    Strategy:
    1. Try label_anchored patterns first (most specific)
    2. Fall back to value_only patterns if no match
    3. Use primary regex field as last resort

    Args:
        field: Field schema dict with regex and/or regex_patterns
        text: Document text to search
        filename: Current filename

    Returns:
        Tuple of (value, matched, all_matches, matched_pattern_type)
    """
    regex_patterns = field.get("regex_patterns", [])

    # If we have multi-pattern array, try in order of specificity
    if regex_patterns:
        # Sort patterns: label_anchored first, then others, value_only last
        pattern_order = {"label_anchored": 0, "specific": 1, "value_only": 2}
        sorted_patterns = sorted(
            regex_patterns,
            key=lambda p: pattern_order.get(p.get("type", "specific"), 1),
        )

        for pattern_info in sorted_patterns:
            pattern = pattern_info.get("pattern", "")
            pattern_type = pattern_info.get("type", "unknown")

            value, matched, all_matches = _extract_with_pattern(
                pattern, text, field, filename
            )

            if matched and value:
                return value, matched, all_matches, pattern_type

    # Fall back to single regex field
    primary_regex = field.get("regex") or field.get("suggested_regex", "")
    if primary_regex:
        value, matched, all_matches = _extract_with_pattern(
            primary_regex, text, field, filename
        )
        return value, matched, all_matches, "primary"

    return None, False, [], None


def run_extraction(project_id: str) -> Dict:
    """
    Run extraction on all documents in a project

    Args:
        project_id: Project ID (slug)

    Returns:
        Dictionary with extraction summary
    """
    # Load project
    project = get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    schema = project.get("schema", [])
    if not schema:
        return {"extracted": 0, "failed": 0, "fields": 0}

    # Get project directories
    project_dir = get_project_dir(project_id)
    raw_dir = project_dir / "raw"
    extracted_dir = project_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    # Get successfully parsed files
    parsed_files = [
        f
        for f in project.get("files", [])
        if f.get("parsed") and not f.get("parse_failed")
    ]

    extracted_count = 0
    failed_count = 0

    # Extract from each file
    for file_info in parsed_files:
        filename = file_info["filename"]
        base_name = filename.rsplit(".", 1)[0]

        # Read raw LiteParse JSON
        liteparse_file = raw_dir / f"{base_name}.json"
        if not liteparse_file.exists():
            failed_count += 1
            continue

        try:
            with open(liteparse_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract text from LiteParse output
            text = _extract_text_from_liteparse(data)
            if not text:
                failed_count += 1
                continue

            # Load existing extracted file if it exists (to preserve overrides)
            extracted_file = extracted_dir / f"{base_name}.extracted.json"
            existing_data = {}
            if extracted_file.exists():
                try:
                    with open(extracted_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                        existing_data = existing_data.get("extracted", {})
                except (json.JSONDecodeError, IOError):
                    existing_data = {}

            # Extract values for each field in schema
            extracted = {}
            for field in schema:
                field_id = field["field_id"]

                # Check if this field has an override
                if field_id in existing_data and existing_data[field_id].get(
                    "overridden"
                ):
                    # Preserve override
                    extracted[field_id] = existing_data[field_id]
                    continue

                # Run cascading regex extraction (tries label_anchored first, then fallbacks)
                value, matched, all_matches, pattern_type = (
                    _extract_with_cascading_patterns(field, text, filename)
                )

                extracted[field_id] = {
                    "value": value,
                    "matched": matched,
                    "overridden": False,
                    "override_value": None,
                    "all_matches": all_matches if len(all_matches) > 1 else None,
                    "match_count": len(all_matches),
                    "pattern_type": pattern_type,
                }

            # Write extracted data
            output_data = {"filename": filename, "extracted": extracted}

            with open(extracted_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            extracted_count += 1

        except (json.JSONDecodeError, IOError) as e:
            failed_count += 1
            continue

    # Update project last_extracted timestamp
    project["last_extracted"] = datetime.utcnow().isoformat() + "Z"
    save_project(project_id, project)

    return {"extracted": extracted_count, "failed": failed_count, "fields": len(schema)}


def get_extraction_results(project_id: str) -> List[Dict]:
    """
    Get aggregated extraction results for all documents

    Args:
        project_id: Project ID (slug)

    Returns:
        List of rows, each containing filename and field values
    """
    # Load project
    project = get_project(project_id)
    if not project:
        return []

    schema = project.get("schema", [])
    if not schema:
        return []

    # Get project directories
    project_dir = get_project_dir(project_id)
    extracted_dir = project_dir / "extracted"

    # Get successfully parsed files
    parsed_files = [
        f
        for f in project.get("files", [])
        if f.get("parsed") and not f.get("parse_failed")
    ]

    results = []

    for file_info in parsed_files:
        filename = file_info["filename"]
        base_name = filename.rsplit(".", 1)[0]
        extracted_file = extracted_dir / f"{base_name}.extracted.json"

        row = {"filename": filename, "fields": {}}

        # Load extracted data if it exists
        if extracted_file.exists():
            try:
                with open(extracted_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    extracted = data.get("extracted", {})

                # Build row with field values
                for field in schema:
                    field_id = field["field_id"]
                    if field_id in extracted:
                        field_data = extracted[field_id]

                        # Use override_value if overridden, otherwise use value
                        if field_data.get("overridden"):
                            value = field_data.get("override_value")
                        else:
                            value = field_data.get("value")

                        row["fields"][field_id] = {
                            "value": value,
                            "matched": field_data.get("matched", False),
                            "overridden": field_data.get("overridden", False),
                            "all_matches": field_data.get("all_matches"),
                            "match_count": field_data.get("match_count", 0),
                        }
                    else:
                        # Field not in extracted data
                        row["fields"][field_id] = {
                            "value": None,
                            "matched": False,
                            "overridden": False,
                        }
            except (json.JSONDecodeError, IOError):
                # Failed to read extracted file
                for field in schema:
                    row["fields"][field["field_id"]] = {
                        "value": None,
                        "matched": False,
                        "overridden": False,
                    }
        else:
            # No extracted file yet
            for field in schema:
                row["fields"][field["field_id"]] = {
                    "value": None,
                    "matched": False,
                    "overridden": False,
                }

        results.append(row)

    return results


def save_override(
    project_id: str, filename: str, field_id: str, override_value: str
) -> bool:
    """
    Save an override value for a specific field in a specific document

    Args:
        project_id: Project ID (slug)
        filename: Document filename
        field_id: Field ID
        override_value: Override value to save

    Returns:
        True if successful, False otherwise
    """
    project_dir = get_project_dir(project_id)
    extracted_dir = project_dir / "extracted"

    base_name = filename.rsplit(".", 1)[0]
    extracted_file = extracted_dir / f"{base_name}.extracted.json"

    if not extracted_file.exists():
        return False

    try:
        with open(extracted_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        extracted = data.get("extracted", {})

        if field_id not in extracted:
            extracted[field_id] = {
                "value": None,
                "matched": False,
                "overridden": False,
                "override_value": None,
            }

        extracted[field_id]["overridden"] = True
        extracted[field_id]["override_value"] = override_value

        data["extracted"] = extracted

        with open(extracted_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True

    except (json.JSONDecodeError, IOError):
        return False


def clear_override(project_id: str, filename: str, field_id: str) -> bool:
    """
    Clear an override value for a specific field in a specific document

    Args:
        project_id: Project ID (slug)
        filename: Document filename
        field_id: Field ID

    Returns:
        True if successful, False otherwise
    """
    project_dir = get_project_dir(project_id)
    extracted_dir = project_dir / "extracted"

    base_name = filename.rsplit(".", 1)[0]
    extracted_file = extracted_dir / f"{base_name}.extracted.json"

    if not extracted_file.exists():
        return False

    try:
        with open(extracted_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        extracted = data.get("extracted", {})

        if field_id in extracted:
            extracted[field_id]["overridden"] = False
            extracted[field_id]["override_value"] = None

        data["extracted"] = extracted

        with open(extracted_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True

    except (json.JSONDecodeError, IOError):
        return False
