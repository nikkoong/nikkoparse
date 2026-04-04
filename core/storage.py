"""
Core Storage Module
Handles all file system operations for projects and data
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Constants
BASE_DIR = Path.home() / "Documents" / "NikkoParse_Data"
PROJECTS_FILE = BASE_DIR / "projects.json"


def _ensure_base_dir():
    """Ensure the base directory exists"""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_FILE.exists():
        _save_json(PROJECTS_FILE, [])


def _load_json(file_path: Path) -> any:
    """Load JSON from file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _save_json(file_path: Path, data: any):
    """Save JSON to file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug"""
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    slug = slug.replace(" ", "-")
    # Remove any characters that aren't alphanumeric, hyphens, or underscores
    slug = "".join(c for c in slug if c.isalnum() or c in "-_")
    return slug


def get_projects_list() -> List[Dict]:
    """Get list of all projects"""
    _ensure_base_dir()
    projects = _load_json(PROJECTS_FILE)
    return projects if projects is not None else []


def save_projects_list(projects: List[Dict]):
    """Save projects list"""
    _ensure_base_dir()
    _save_json(PROJECTS_FILE, projects)


def create_project(name: str) -> Dict:
    """
    Create a new project

    Args:
        name: Project name

    Returns:
        Project dictionary with id, name, created_at, doc_count
    """
    _ensure_base_dir()

    # Generate slug
    base_slug = _slugify(name)
    slug = base_slug
    counter = 2

    # Handle collisions
    projects = get_projects_list()
    existing_ids = {p["id"] for p in projects}

    while slug in existing_ids:
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create project structure
    project_dir = BASE_DIR / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "raw").mkdir(exist_ok=True)
    (project_dir / "extracted").mkdir(exist_ok=True)

    # Create project metadata
    now = datetime.utcnow().isoformat() + "Z"
    project = {
        "id": slug,
        "name": name,
        "created_at": now,
        "last_extracted": None,
        "files": [],
        "schema": [],
    }

    # Save project.json
    project_json_path = project_dir / "project.json"
    _save_json(project_json_path, project)

    # Add to projects list
    registry_entry = {"id": slug, "name": name, "created_at": now, "doc_count": 0}
    projects.append(registry_entry)
    save_projects_list(projects)

    return project


def get_project(project_id: str) -> Optional[Dict]:
    """
    Get project details

    Args:
        project_id: Project ID (slug)

    Returns:
        Project dictionary or None if not found
    """
    project_dir = BASE_DIR / "projects" / project_id
    project_json_path = project_dir / "project.json"

    if not project_json_path.exists():
        return None

    return _load_json(project_json_path)


def save_project(project_id: str, data: Dict):
    """
    Save project data

    Args:
        project_id: Project ID (slug)
        data: Project data dictionary
    """
    project_dir = BASE_DIR / "projects" / project_id
    project_json_path = project_dir / "project.json"
    _save_json(project_json_path, data)

    # Update doc_count in registry
    projects = get_projects_list()
    for project in projects:
        if project["id"] == project_id:
            project["doc_count"] = len(data.get("files", []))
            break
    save_projects_list(projects)


def delete_project(project_id: str) -> bool:
    """
    Delete a project and all its files

    Args:
        project_id: Project ID (slug)

    Returns:
        True if deleted, False if not found
    """
    # Remove from projects list
    projects = get_projects_list()
    projects = [p for p in projects if p["id"] != project_id]
    save_projects_list(projects)

    # Delete project directory
    project_dir = BASE_DIR / "projects" / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
        return True

    return False


def rename_project(project_id: str, new_name: str) -> bool:
    """
    Rename a project (updates name but keeps same ID)

    Args:
        project_id: Project ID (slug)
        new_name: New project name

    Returns:
        True if renamed, False if project not found
    """
    # Update project.json
    project = get_project(project_id)
    if not project:
        return False

    project["name"] = new_name
    save_project(project_id, project)

    # Update projects list registry
    projects = get_projects_list()
    for p in projects:
        if p["id"] == project_id:
            p["name"] = new_name
            break
    save_projects_list(projects)

    return True


def get_project_dir(project_id: str) -> Path:
    """Get path to project directory"""
    return BASE_DIR / "projects" / project_id


def ensure_project_dirs(project_id: str):
    """Ensure project subdirectories exist"""
    project_dir = get_project_dir(project_id)
    (project_dir / "raw").mkdir(parents=True, exist_ok=True)
    (project_dir / "extracted").mkdir(parents=True, exist_ok=True)


def get_raw_file_path(project_id: str, filename: str) -> Path:
    """Get path to raw LiteParse JSON file"""
    # LiteParse outputs with .json extension
    base_name = filename.rsplit(".", 1)[0]  # Remove .pdf extension
    return get_project_dir(project_id) / "raw" / f"{base_name}.json"


def get_extracted_file_path(project_id: str, filename: str) -> Path:
    """Get path to extracted data JSON file"""
    base_name = filename.rsplit(".", 1)[0]  # Remove .pdf extension
    return get_project_dir(project_id) / "extracted" / f"{base_name}.extracted.json"
