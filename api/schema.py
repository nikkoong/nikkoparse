"""
Schema API Blueprint
Handles schema management and field suggestions
"""

import json
import re
from pathlib import Path
from flask import Blueprint, jsonify, request
from core.storage import get_project, save_project, get_project_dir
from core.suggester import get_suggestions, _extract_text_from_liteparse
from core.regex_generator import generate_regex
from core.ai_export_helper import optimize_samples_for_context_window

schema_bp = Blueprint("schema", __name__)


# AI Prompt Template
AI_PROMPT_TEMPLATE = """I need regex patterns to extract data from parsed documents.

**TASK:** Generate extraction schema with tested regex patterns.

**OUTPUT FORMAT (JSON only, no markdown):**
{
  "fields": [
    {
      "field_id": "account_number",
      "label": "Account Number",
      "regex": "Account:\\\\s*(\\\\d{5}-\\\\d{5}-\\\\d)",
      "value_type": "text",
      "test_results": {"file1.txt": "89613-14560-9"},
      "confidence": "high"
    }
  ]
}

**REQUIREMENTS:**
1. Test each regex on ALL samples
2. Include test_results with extracted values
3. Use double backslashes for JSON (\\\\s not \\s)
4. Capture groups () for values to extract
5. confidence: "high" (all docs), "medium" (80%+), "low" (<80%)
6. value_type: dollar|date|integer|percent|text
7. For multiple matches, prefer FIRST occurrence
8. Make $ optional: \\$?([\\\\d,\\\\.]+)

**VALIDATION:**
✓ Valid regex (no unclosed groups)
✓ All fields have patterns
✓ Test results for 2+ docs
✓ NO markdown code blocks
✓ ONLY JSON output

**SAMPLE DOCUMENTS:**
"""


@schema_bp.route("/projects/<project_id>/suggestions", methods=["GET"])
def get_field_suggestions(project_id):
    """Get top-10 field suggestions based on document content"""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        suggestions = get_suggestions(project_id)

        return jsonify({"suggestions": suggestions, "count": len(suggestions)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@schema_bp.route("/projects/<project_id>/schema", methods=["PUT"])
def save_schema(project_id):
    """Save project schema"""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        data = request.get_json()

        if not data or "schema" not in data:
            return jsonify({"error": "Schema is required"}), 400

        schema = data["schema"]

        # Validate schema structure
        if not isinstance(schema, list):
            return jsonify({"error": "Schema must be an array"}), 400

        for field in schema:
            if "field_id" not in field or "label" not in field:
                return jsonify(
                    {"error": "Each field must have field_id and label"}
                ), 400

        # Update project schema
        project["schema"] = schema
        save_project(project_id, project)

        return jsonify({"message": "Schema saved successfully", "schema": schema}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@schema_bp.route("/projects/<project_id>/schema/generate-regex", methods=["POST"])
def generate_regex_endpoint(project_id):
    """Generate regex from highlighted text and context"""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        data = request.get_json()

        if not data or "highlighted_value" not in data or "context_lines" not in data:
            return jsonify(
                {"error": "highlighted_value and context_lines are required"}
            ), 400

        highlighted_value = data["highlighted_value"]
        context_lines = data["context_lines"]

        if not isinstance(context_lines, list):
            return jsonify({"error": "context_lines must be an array"}), 400

        result = generate_regex(highlighted_value, context_lines)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@schema_bp.route("/projects/<project_id>/export-for-ai", methods=["GET"])
def export_for_ai_schema(project_id):
    """Export project data optimized for AI schema generation"""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Get parsed files
        parsed_files = [
            f
            for f in project.get("files", [])
            if f.get("parsed") and not f.get("parse_failed")
        ]

        if not parsed_files:
            return jsonify({"error": "No parsed files in project"}), 400

        # Load document texts
        project_dir = get_project_dir(project_id)
        raw_dir = project_dir / "raw"

        documents = []
        for file_info in parsed_files:
            filename = file_info["filename"]
            base_name = filename.rsplit(".", 1)[0]
            liteparse_file = raw_dir / f"{base_name}.json"

            if liteparse_file.exists():
                try:
                    with open(liteparse_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    text = _extract_text_from_liteparse(data)
                    if text:
                        documents.append({"filename": filename, "text": text})
                except (json.JSONDecodeError, IOError):
                    continue

        if not documents:
            return jsonify({"error": "Could not load document texts"}), 400

        # Optimize samples for context window (max ~8000 tokens)
        optimized_samples = optimize_samples_for_context_window(
            documents, max_total_tokens=8000
        )

        # Build the complete AI prompt with embedded samples
        samples_text = ""
        for idx, sample in enumerate(optimized_samples, 1):
            samples_text += f"\n\n--- Document {idx}: {sample['filename']} ---\n"
            if "key_value_examples" in sample:
                samples_text += "Key fields detected:\n"
                for kv in sample["key_value_examples"][:10]:
                    samples_text += f"  {kv['label']}: {kv['value']}\n"
                samples_text += "\n"
            if "excerpt" in sample:
                samples_text += sample["excerpt"]
            elif "text" in sample:
                # Full text included
                samples_text += sample["text"][:5000]  # Limit to 5000 chars per doc

        complete_prompt = AI_PROMPT_TEMPLATE + samples_text

        # Build export data
        export_data = {
            "project_id": project_id,
            "project_name": project.get("name", "Unnamed Project"),
            "document_count": len(parsed_files),
            "samples_included": len(optimized_samples),
            "sample_documents": optimized_samples,
            "suggested_fields": [
                "Account Number",
                "Date",
                "Total Amount",
                "Reference Number",
                "Description",
            ],
            "ai_prompt": complete_prompt,
        }

        return jsonify(export_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@schema_bp.route("/projects/<project_id>/import-ai-schema", methods=["POST"])
def import_ai_schema(project_id):
    """Import and validate AI-generated schema"""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        data = request.get_json()

        # Accept both "schema" and "fields" for backwards compatibility
        ai_schema = data.get("schema") or data.get("fields")

        if not ai_schema:
            return jsonify({"error": "schema or fields array is required"}), 400

        if not isinstance(ai_schema, list):
            return jsonify({"error": "schema must be an array"}), 400

        # Validate and process each field
        validated_schema = []
        validation_errors = []

        for idx, field in enumerate(ai_schema):
            # Check required fields
            required = ["field_id", "label", "regex", "value_type"]
            missing = [f for f in required if f not in field]
            if missing:
                validation_errors.append(
                    f"Field {idx + 1}: Missing required fields: {', '.join(missing)}"
                )
                continue

            # Validate regex
            try:
                re.compile(field["regex"])
            except re.error as e:
                validation_errors.append(
                    f"Field '{field.get('label', idx + 1)}': Invalid regex - {str(e)}"
                )
                continue

            # Build validated field
            validated_field = {
                "field_id": field["field_id"],
                "label": field["label"],
                "regex": field["regex"],
                "value_type": field.get("value_type", "text"),
                "confirmed": True,
                "suggested": False,
                "ai_generated": True,
                "confidence": field.get("confidence", "unknown"),
                "test_results": field.get("test_results", {}),
            }

            validated_schema.append(validated_field)

        if validation_errors:
            return jsonify(
                {
                    "error": "Schema validation failed",
                    "validation_errors": validation_errors,
                    "valid_fields": len(validated_schema),
                    "invalid_fields": len(validation_errors),
                }
            ), 400

        # Option to merge or replace
        merge_mode = data.get("merge", False)

        if merge_mode and project.get("schema"):
            # Merge: Add new fields, update existing by field_id
            existing_ids = {f["field_id"]: f for f in project["schema"]}
            for field in validated_schema:
                existing_ids[field["field_id"]] = field
            final_schema = list(existing_ids.values())
        else:
            # Replace mode (default)
            final_schema = validated_schema

        # Save to project
        project["schema"] = final_schema
        save_project(project_id, project)

        return jsonify(
            {
                "success": True,
                "message": "Schema imported successfully",
                "imported_count": len(validated_schema),
                "total_fields": len(final_schema),
                "merge_mode": merge_mode,
                "schema": final_schema,
            }
        ), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
