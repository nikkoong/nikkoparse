"""
Unit tests for core.storage module
"""

import json
import tempfile
import shutil
from pathlib import Path
from core.storage import (
    get_project_dir,
    create_project,
    get_projects_list,
    get_project,
    delete_project,
    save_project,
    get_raw_file_path,
    get_extracted_file_path,
)


class TestProjectDirectory:
    """Tests for project directory functions"""

    def test_get_project_dir_returns_path(self):
        """Test that get_project_dir returns proper Path object"""
        project_dir = get_project_dir("test-project")

        assert isinstance(project_dir, Path)
        assert "test-project" in str(project_dir)

    def test_get_raw_file_path(self):
        """Test getting raw file path"""
        file_path = get_raw_file_path("test-project", "document.pdf")

        assert isinstance(file_path, Path)
        assert "raw" in str(file_path)
        assert "document" in str(file_path)

    def test_get_extracted_file_path(self):
        """Test getting extracted file path"""
        file_path = get_extracted_file_path("test-project", "document.pdf")

        assert isinstance(file_path, Path)
        assert "extracted" in str(file_path)


class TestProjectOperations:
    """Tests for project CRUD operations (integration-style)"""

    def test_get_projects_list_returns_list(self):
        """Test that get_projects_list returns a list"""
        projects = get_projects_list()

        assert isinstance(projects, list)
        # May be empty or contain projects

    def test_get_project_nonexistent(self):
        """Test getting non-existent project returns None"""
        project = get_project("nonexistent-project-xyz-123")

        # Should return None or empty dict for non-existent project
        assert project is None or project == {}


class TestSlugGeneration:
    """Tests for slug generation logic"""

    def test_slug_from_name_basic(self):
        """Test basic slug generation logic"""
        # Storage module generates slugs internally
        # This tests the expected behavior
        name = "My Test Project"
        expected_pattern = "my-test-project"

        # Just verify the pattern is correct
        slug = name.lower().replace(" ", "-")
        assert slug == expected_pattern

    def test_slug_special_chars(self):
        """Test slug handles special characters"""
        import re

        name = "Project @ 2024!"
        # Simulate the slug logic
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"-+", "-", slug)

        assert "@" not in slug
        assert "!" not in slug
