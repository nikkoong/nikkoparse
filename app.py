"""
PDF Extractor - Flask Application
Main entry point for the web server
"""

from flask import Flask, send_from_directory, jsonify
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max file size

# Register API blueprints
from api.projects import projects_bp
from api.files import files_bp
from api.schema import schema_bp
from api.extraction import extraction_bp
from api.results import results_bp
from api.regex_preview import regex_preview_bp

app.register_blueprint(projects_bp, url_prefix="/api")
app.register_blueprint(files_bp, url_prefix="/api")
app.register_blueprint(schema_bp, url_prefix="/api")
app.register_blueprint(extraction_bp, url_prefix="/api")
app.register_blueprint(results_bp, url_prefix="/api")
app.register_blueprint(regex_preview_bp, url_prefix="/api")


@app.route("/")
def index():
    """Serve the home page"""
    return send_from_directory("static", "index.html")


@app.route("/project/<project_id>")
def project(project_id):
    """Serve the project page"""
    return send_from_directory("static", "project.html")


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🚀 PDF Extractor Starting...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")
    print("Server running at: http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("")

    app.run(host="localhost", port=5001, debug=True)
