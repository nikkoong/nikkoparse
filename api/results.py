"""
Results API Blueprint
Handles extraction results and overrides
"""

from flask import Blueprint, jsonify, request
from core.storage import get_project
from core.extractor import get_extraction_results, save_override, clear_override

results_bp = Blueprint("results", __name__)


@results_bp.route("/projects/<project_id>/results", methods=["GET"])
def get_results(project_id):
    """Get aggregated extraction results table"""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        results = get_extraction_results(project_id)

        return jsonify({"schema": project.get("schema", []), "results": results}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@results_bp.route(
    "/projects/<project_id>/results/<filename>/<field_id>", methods=["PUT"]
)
def save_cell_override(project_id, filename, field_id):
    """Save override value for a specific cell"""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        data = request.get_json()

        if not data or "override_value" not in data:
            return jsonify({"error": "override_value is required"}), 400

        override_value = data["override_value"]

        success = save_override(project_id, filename, field_id, override_value)

        if not success:
            return jsonify({"error": "Failed to save override"}), 500

        return jsonify({"message": "Override saved successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@results_bp.route(
    "/projects/<project_id>/results/<filename>/<field_id>", methods=["DELETE"]
)
def clear_cell_override(project_id, filename, field_id):
    """Clear override value for a specific cell"""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        success = clear_override(project_id, filename, field_id)

        if not success:
            return jsonify({"error": "Failed to clear override"}), 500

        return jsonify({"message": "Override cleared successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
