"""
Extraction API Blueprint
Handles running extraction on all documents
"""

from flask import Blueprint, jsonify
from core.storage import get_project
from core.extractor import run_extraction

extraction_bp = Blueprint("extraction", __name__)


@extraction_bp.route("/projects/<project_id>/extract", methods=["POST"])
def extract(project_id):
    """Run or re-run extraction on all documents"""
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Check if schema exists
        if not project.get("schema"):
            return jsonify(
                {"error": "No schema defined. Please add fields first."}
            ), 400

        # Run extraction
        results = run_extraction(project_id)

        return jsonify({"message": "Extraction completed", "results": results}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
