"""
Files API Blueprint
Handles file upload and parsing
"""

from flask import Blueprint, jsonify, request
import os
import logging
from werkzeug.utils import secure_filename
from core.liteparse_runner import process_new_files, check_liteparse_installed
from core.storage import get_project, get_project_dir
from core.suggester import _extract_text_from_liteparse
import json

logger = logging.getLogger(__name__)

files_bp = Blueprint("files", __name__)

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename):
    """Check if file has allowed extension"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@files_bp.route("/projects/<project_id>/files", methods=["POST"])
def upload_files(project_id):
    """Upload and parse PDF files"""
    try:
        logger.info(f"Upload request received for project: {project_id}")

        # Check if LiteParse is installed
        if not check_liteparse_installed():
            logger.error("LiteParse CLI not found")
            return jsonify(
                {"error": "LiteParse CLI not found. Please run setup.sh to install it."}
            ), 500

        # Check if project exists
        project = get_project(project_id)
        if not project:
            logger.error(f"Project not found: {project_id}")
            return jsonify({"error": "Project not found"}), 404

        # Check if files were uploaded
        if "files" not in request.files:
            logger.warning("No files in request")
            return jsonify({"error": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            logger.warning("No files selected")
            return jsonify({"error": "No files selected"}), 400

        logger.info(f"Received {len(files)} files for upload")

        # Save uploaded files to temporary location
        temp_dir = get_project_dir(project_id) / "temp"
        temp_dir.mkdir(exist_ok=True)
        logger.debug(f"Temp directory: {temp_dir}")

        saved_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = temp_dir / filename
                file.save(str(filepath))
                saved_paths.append(str(filepath))
                logger.info(
                    f"Saved uploaded file: {filename} ({os.path.getsize(filepath)} bytes)"
                )
            else:
                logger.warning(f"Skipped non-PDF file: {file.filename}")

        if not saved_paths:
            logger.error("No valid PDF files provided")
            return jsonify({"error": "No valid PDF files provided"}), 400

        logger.info(f"Processing {len(saved_paths)} valid PDF files")

        # Process files with LiteParse
        results = process_new_files(project_id, saved_paths)

        logger.info(f"Processing complete: {results}")

        # Clean up temp directory
        for filepath in saved_paths:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"Removed temp file: {filepath}")
        if temp_dir.exists():
            os.rmdir(str(temp_dir))
            logger.debug("Removed temp directory")

        return jsonify(results), 200

    except FileNotFoundError as e:
        logger.error(f"File not found error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@files_bp.route("/projects/<project_id>/files/<filename>/text", methods=["GET"])
def get_file_text(project_id, filename):
    """Get parsed text for a specific file"""
    try:
        logger.info(f"Text request for file: {filename} in project: {project_id}")

        project = get_project(project_id)
        if not project:
            logger.error(f"Project not found: {project_id}")
            return jsonify({"error": "Project not found"}), 404

        # Check if file exists in project
        file_exists = any(f["filename"] == filename for f in project.get("files", []))
        if not file_exists:
            logger.error(f"File not found in project: {filename}")
            return jsonify({"error": "File not found in project"}), 404

        # Read LiteParse JSON
        project_dir = get_project_dir(project_id)
        base_name = filename.rsplit(".", 1)[0]
        liteparse_file = project_dir / "raw" / f"{base_name}.json"

        logger.debug(f"Looking for LiteParse file: {liteparse_file}")

        if not liteparse_file.exists():
            logger.error(f"Parsed file not found: {liteparse_file}")
            return jsonify({"error": "Parsed file not found"}), 404

        with open(liteparse_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract text
        text = _extract_text_from_liteparse(data)
        logger.info(f"Extracted {len(text)} characters of text from {filename}")

        return jsonify({"filename": filename, "text": text}), 200

    except Exception as e:
        logger.error(f"Error getting file text: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
