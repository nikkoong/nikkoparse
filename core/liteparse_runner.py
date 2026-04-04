"""
LiteParse Runner Module
Handles subprocess execution of LiteParse CLI for PDF parsing
"""

import subprocess
import shutil
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from core.storage import get_project, save_project, get_project_dir

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
STAGING_DIR = PROJECT_ROOT / "staging"
CONFIG_FILE = PROJECT_ROOT / "liteparse.config.json"


def check_liteparse_installed() -> bool:
    """
    Check if LiteParse CLI is installed

    Returns:
        True if installed, False otherwise
    """
    try:
        logger.info("Checking if LiteParse CLI is installed...")
        result = subprocess.run(
            ["lit", "--version"], capture_output=True, text=True, timeout=5
        )
        installed = result.returncode == 0
        if installed:
            logger.info(f"LiteParse CLI found: {result.stdout.strip()}")
        else:
            logger.error("LiteParse CLI not found or returned error")
        return installed
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.error(f"LiteParse CLI check failed: {e}")
        return False


def run_batch_parse(project_id: str, pdf_paths: List[str]) -> Dict:
    """
    Run LiteParse batch parsing on PDF files

    Args:
        project_id: Project ID (slug)
        pdf_paths: List of paths to PDF files to parse

    Returns:
        Dictionary with 'success' and 'failed' lists
    """
    logger.info(
        f"Starting batch parse for project {project_id} with {len(pdf_paths)} files"
    )

    # Ensure staging directory exists
    STAGING_DIR.mkdir(exist_ok=True)
    logger.debug(f"Staging directory: {STAGING_DIR}")

    # Copy PDFs to staging
    staged_files = []
    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        dest_path = STAGING_DIR / filename
        logger.debug(f"Copying {pdf_path} to {dest_path}")
        shutil.copy2(pdf_path, dest_path)
        staged_files.append(filename)

    logger.info(f"Staged {len(staged_files)} files: {staged_files}")

    # Get output directory
    project_dir = get_project_dir(project_id)
    raw_dir = project_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Output directory: {raw_dir}")

    # Run LiteParse batch-parse
    try:
        cmd = [
            "lit",
            "batch-parse",
            str(STAGING_DIR),
            str(raw_dir),
            "--format",
            "json",
            "--config",
            str(CONFIG_FILE),
            "--extension",
            ".pdf",
        ]

        logger.info(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
        )

        logger.info(f"LiteParse completed with return code: {result.returncode}")
        logger.debug(f"STDOUT: {result.stdout}")
        if result.stderr:
            logger.warning(f"STDERR: {result.stderr}")

        # Parse output to determine success/failure
        success = []
        failed = []

        # Check which files were successfully parsed
        for filename in staged_files:
            base_name = filename.rsplit(".", 1)[0]
            # LiteParse creates files with .json extension, not .liteparse.json
            output_file = raw_dir / f"{base_name}.json"

            logger.debug(f"Checking output file: {output_file}")

            if output_file.exists():
                # Check if file has content
                file_size = output_file.stat().st_size
                logger.debug(
                    f"Output file {filename} exists with size {file_size} bytes"
                )
                if file_size > 0:
                    success.append(filename)
                    logger.info(f"✓ Successfully parsed: {filename}")
                else:
                    failed.append({"filename": filename, "error": "Empty output file"})
                    logger.error(f"✗ Empty output file for: {filename}")
            else:
                # Try to extract error from stderr
                error_msg = "Parse failed"
                stderr_lower = result.stderr.lower() if result.stderr else ""

                if "password" in stderr_lower or "encrypted" in stderr_lower:
                    error_msg = "Password protected"
                elif "corrupt" in stderr_lower:
                    error_msg = "Corrupted file"
                elif "invalid" in stderr_lower:
                    error_msg = "Invalid PDF format"

                failed.append({"filename": filename, "error": error_msg})
                logger.error(f"✗ Failed to parse {filename}: {error_msg}")

        logger.info(
            f"Batch parse complete: {len(success)} success, {len(failed)} failed"
        )
        return {"success": success, "failed": failed}

    except subprocess.TimeoutExpired:
        # If timeout, mark all as failed
        logger.error(f"Parse timeout after 300 seconds for {len(staged_files)} files")
        return {
            "success": [],
            "failed": [{"filename": f, "error": "Parse timeout"} for f in staged_files],
        }

    except FileNotFoundError as e:
        logger.error(f"LiteParse CLI not found: {e}")
        raise FileNotFoundError(
            "LiteParse CLI not found. Please run setup.sh to install it."
        )

    except Exception as e:
        logger.error(f"Unexpected error during batch parse: {e}", exc_info=True)
        raise

    finally:
        # Clean up staging directory
        logger.debug("Cleaning up staging directory")
        for file in STAGING_DIR.glob("*"):
            if file.is_file():
                file.unlink()
                logger.debug(f"Removed staged file: {file}")


def process_new_files(project_id: str, file_paths: List[str]) -> Dict:
    """
    Process new PDF files for a project

    Args:
        project_id: Project ID (slug)
        file_paths: List of file paths to process

    Returns:
        Dictionary with summary of processed/skipped/failed files
    """
    logger.info(f"Processing {len(file_paths)} files for project {project_id}")

    # Load existing project
    project = get_project(project_id)
    if not project:
        logger.error(f"Project {project_id} not found")
        raise ValueError(f"Project {project_id} not found")

    # Filter out already-present filenames
    existing_files = {f["filename"] for f in project.get("files", [])}
    new_files = []
    skipped_files = []

    for file_path in file_paths:
        filename = os.path.basename(file_path)
        if filename in existing_files:
            skipped_files.append(filename)
            logger.info(f"Skipping duplicate file: {filename}")
        else:
            new_files.append((file_path, filename))
            logger.debug(f"New file to process: {filename}")

    if not new_files:
        logger.info("No new files to process")
        return {"new": 0, "skipped": len(skipped_files), "success": [], "failed": []}

    logger.info(
        f"Processing {len(new_files)} new files, skipped {len(skipped_files)} duplicates"
    )

    # Run batch parse on new files only
    new_file_paths = [path for path, _ in new_files]
    parse_results = run_batch_parse(project_id, new_file_paths)

    # Update project.json with new file entries
    now = datetime.utcnow().isoformat() + "Z"

    for filename in parse_results["success"]:
        # Find original path
        original_path = next(path for path, name in new_files if name == filename)

        project["files"].append(
            {
                "filename": filename,
                "original_path": original_path,
                "parsed": True,
                "parse_date": now,
                "parse_failed": False,
                "parse_error": None,
            }
        )
        logger.info(f"Added successfully parsed file to project: {filename}")

    for failure in parse_results["failed"]:
        filename = failure["filename"]
        # Find original path
        original_path = next(path for path, name in new_files if name == filename)

        project["files"].append(
            {
                "filename": filename,
                "original_path": original_path,
                "parsed": False,
                "parse_date": now,
                "parse_failed": True,
                "parse_error": failure["error"],
            }
        )
        logger.warning(f"Added failed file to project: {filename} - {failure['error']}")

    # Save updated project
    save_project(project_id, project)
    logger.info(
        f"Updated project.json with {len(parse_results['success'])} success and {len(parse_results['failed'])} failed"
    )

    return {
        "new": len(new_files),
        "skipped": len(skipped_files),
        "success": parse_results["success"],
        "failed": parse_results["failed"],
    }
