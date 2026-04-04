"""
Projects API Blueprint
Handles project CRUD operations
"""

from flask import Blueprint, jsonify, request
from core.storage import (
    get_projects_list,
    create_project,
    get_project,
    delete_project,
    rename_project,
)

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/projects", methods=["GET"])
def list_projects():
    """Get list of all projects"""
    try:
        projects = get_projects_list()
        return jsonify(projects), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@projects_bp.route("/projects", methods=["POST"])
def create_new_project():
    """Create a new project"""
    try:
        data = request.get_json()

        if not data or "name" not in data:
            return jsonify({"error": "Project name is required"}), 400

        name = data["name"].strip()
        if not name:
            return jsonify({"error": "Project name cannot be empty"}), 400

        project = create_project(name)
        return jsonify(project), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@projects_bp.route("/projects/<project_id>", methods=["GET"])
def get_project_details(project_id):
    """Get project details including schema"""
    try:
        project = get_project(project_id)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        return jsonify(project), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@projects_bp.route("/projects/<project_id>", methods=["DELETE"])
def delete_project_endpoint(project_id):
    """Delete a project and all its files"""
    try:
        success = delete_project(project_id)

        if not success:
            return jsonify({"error": "Project not found"}), 404

        return jsonify({"message": "Project deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@projects_bp.route("/projects/<project_id>/rename", methods=["PUT"])
def rename_project_endpoint(project_id):
    """Rename a project"""
    try:
        data = request.get_json()

        if not data or "name" not in data:
            return jsonify({"error": "New project name is required"}), 400

        new_name = data["name"].strip()
        if not new_name:
            return jsonify({"error": "Project name cannot be empty"}), 400

        success = rename_project(project_id, new_name)

        if not success:
            return jsonify({"error": "Project not found"}), 404

        return jsonify(
            {"message": "Project renamed successfully", "name": new_name}
        ), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
