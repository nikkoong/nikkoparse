"""
Regex Preview API Blueprint
Handles live regex preview testing
"""

from flask import Blueprint, jsonify, request
from core.regex_generator import preview_regex

regex_preview_bp = Blueprint("regex_preview", __name__)


@regex_preview_bp.route("/regex-preview", methods=["POST"])
def preview_regex_endpoint():
    """Test a regex against text and return the match"""
    try:
        data = request.get_json()

        if not data or "regex" not in data or "text" not in data:
            return jsonify({"error": "regex and text are required"}), 400

        regex = data["regex"]
        text = data["text"]

        match = preview_regex(regex, text)

        return jsonify({"match": match}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
