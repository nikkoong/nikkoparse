# AGENTS.md - Development Guide for Coding Agents

This document provides essential information for AI coding agents working in the nikkoparse codebase.

## Project Overview

nikkoparse is a Python Flask application for PDF document extraction and parsing. It uses LiteParse CLI for OCR and provides a RESTful API with a vanilla JavaScript frontend.

**Tech Stack:** Python 3.9+, Flask, pytest, LiteParse CLI, vanilla JavaScript (ES6+)

**Storage:** File-based (JSON files, no database)

## Build, Test, and Run Commands

### Setup
```bash
# Install dependencies (LiteParse CLI + Python packages)
./setup.sh

# Or manually:
npm install -g @llamaindex/liteparse
pip install -r requirements.txt
```

### Running the Application
```bash
# Start Flask server (localhost:5001)
./start.sh

# Or manually:
source venv/bin/activate  # If using venv
python app.py
```

### Testing
```bash
# Run all tests
pytest

# Run all tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_storage.py
pytest tests/test_suggester.py
pytest tests/test_regex_generator.py

# Run specific test class
pytest tests/test_storage.py::TestProjectDirectory

# Run specific test method
pytest tests/test_storage.py::TestProjectDirectory::test_get_project_dir_returns_path

# Run with print statements visible
pytest -s

# Run integration test (requires Flask server running separately)
python test_ai_workflow.py
```

### Linting/Formatting
**Note:** No linting or formatting tools are currently configured. Follow the code style patterns below.

## Project Structure

```
nikkoparse/
├── app.py                      # Flask application entry point
├── requirements.txt            # Python dependencies
├── liteparse.config.json       # LiteParse configuration
├── README.md                   # User documentation
├── AUTO_GENERATE.md            # Auto-generate schema technical docs
├── AGENTS.md                   # This file - developer guide
├── api/                        # Flask API blueprints (REST endpoints)
│   ├── projects.py            # Project CRUD endpoints
│   ├── files.py               # File upload/parsing endpoints
│   ├── schema.py              # Schema management & AI export
│   ├── extraction.py          # Extraction endpoints
│   ├── results.py             # Results and overrides
│   └── regex_preview.py       # Regex preview endpoint
├── core/                       # Core business logic (no Flask dependencies)
│   ├── storage.py             # File system operations
│   ├── extractor.py           # Extraction engine
│   ├── suggester.py           # Field suggestion algorithm
│   ├── regex_generator.py     # Regex auto-generation (legacy)
│   ├── liteparse_runner.py    # LiteParse subprocess wrapper
│   ├── field_dictionary.py    # Master field dictionary
│   └── ai_export_helper.py    # AI context window optimization
├── tests/                      # Test suite (pytest)
├── static/                     # Frontend (HTML/CSS/JS, no build step)
│   ├── css/app.css            # All styles including extraction table
│   ├── js/
│   │   ├── api.js             # API wrapper functions
│   │   ├── home.js            # Home page logic
│   │   └── project.js         # Project page + auto-generate schema
│   ├── home.html              # Landing page
│   └── project.html           # Main project interface
└── staging/                    # Temporary staging for LiteParse
```

**Key Separation:** `/api/` contains Flask-specific code; `/core/` contains pure business logic; `/static/js/` contains frontend logic including auto-generate schema algorithm.

## Code Style Guidelines

### Python Version
Use Python 3.9+ features. Type hints are required.

### Imports
Organize imports in three groups with blank lines between:
```python
# 1. Standard library
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 2. Third-party
from flask import Flask, jsonify, request

# 3. Internal (absolute imports from project root)
from core.storage import get_project, save_project
from core.extractor import run_extraction
```

### Naming Conventions
- **Files:** `lowercase_with_underscores.py`
- **Functions:** `lowercase_with_underscores()`
- **Private functions:** `_leading_underscore()`
- **Variables:** `lowercase_with_underscores`
- **Constants:** `UPPERCASE_WITH_UNDERSCORES`
- **Test files:** `test_*.py`
- **Test classes:** `TestClassName`
- **Test methods:** `test_method_name()`
- **API endpoints:** `/api/kebab-case-urls`
- **JSON keys:** `snake_case`

### Type Hints
Always use type hints for function parameters and return values:
```python
def get_project(project_id: str) -> Optional[Dict]:
    """Get project by ID"""
    pass

def get_suggestions(project_id: str, max_suggestions: int = 10) -> List[Dict]:
    """Get field suggestions"""
    pass

def extract_pairs(text: str) -> List[Tuple[str, str]]:
    """Extract key-value pairs"""
    pass
```

Use `Path` from `pathlib` for file paths, not strings.

### Docstrings
Use Google-style docstrings for all public functions:
```python
def function_name(param: str, count: int = 5) -> Dict:
    """
    Brief description of function
    
    Args:
        param: Description of param
        count: Description of count (default: 5)
        
    Returns:
        Description of return value
    """
```

Module-level docstrings at the top of each file:
```python
"""
Module Name
Brief description of module purpose
"""
```

### String Formatting
Use f-strings exclusively:
```python
message = f"Project {project_id} not found"
logger.info(f"✓ Successfully parsed: {filename}")
```

### Error Handling
Use specific exceptions, not bare `except`:
```python
try:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
except FileNotFoundError:
    return None
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON: {e}")
    return None
```

For API endpoints, return proper error responses:
```python
@bp.route("/projects/<project_id>", methods=["GET"])
def get_project_endpoint(project_id):
    try:
        project = get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(project), 200
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        return jsonify({"error": str(e)}), 500
```

### Logging
Use Python's logging module with appropriate levels:
```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed debugging information")
logger.info(f"✓ Successfully processed {count} items")
logger.warning(f"Skipping invalid file: {filename}")
logger.error(f"Failed to process: {e}")
```

### File Operations
Use `pathlib.Path` for all file operations:
```python
from pathlib import Path

project_dir = Path.home() / "Documents" / "PDFExtractor" / "projects" / project_id
project_file = project_dir / "project.json"

# Create directories
project_dir.mkdir(parents=True, exist_ok=True)

# Check existence
if project_file.exists():
    # read file
```

### JSON Operations
Pattern for loading/saving JSON:
```python
def _load_json(file_path: Path) -> Optional[Dict]:
    """Load JSON from file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def _save_json(file_path: Path, data: Dict) -> None:
    """Save JSON to file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

### Flask Blueprint Pattern
Each API domain should be a separate Blueprint:
```python
# In api/domain.py
from flask import Blueprint, jsonify, request

domain_bp = Blueprint("domain", __name__)

@domain_bp.route("/endpoint", methods=["GET"])
def handler():
    """Endpoint handler"""
    pass

# In app.py
from api.domain import domain_bp
app.register_blueprint(domain_bp, url_prefix="/api")
```

## Testing Guidelines

- Write tests for all core business logic in `/core/`
- Test files go in `/tests/` with `test_` prefix
- Use pytest fixtures sparingly; prefer actual project data for integration tests
- Test both success and error cases
- Use descriptive test method names that explain what is being tested

## Common Patterns

### Validation Pattern
```python
if not data or "required_field" not in data:
    return jsonify({"error": "Required field is missing"}), 400

if not value.strip():
    return jsonify({"error": "Value cannot be empty"}), 400
```

### Regex Pattern
```python
try:
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    for match in matches:
        value = match.group(1) if match.lastindex else match.group(0)
        # process match
except re.error as e:
    logger.warning(f"Invalid regex pattern: {e}")
```

### Subprocess Pattern (LiteParse)
```python
import subprocess

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=300
)
if result.returncode != 0:
    raise RuntimeError(f"Command failed: {result.stderr}")
```

## Important Notes

- **No database:** All data is stored in JSON files under `~/Documents/NikkoParse_Data/`
- **No frontend build process:** JavaScript is vanilla ES6+ with no bundler
- **LiteParse dependency:** The `liteparse` CLI must be installed globally via npm
- **File size limit:** Flask configured for 100MB max upload size
- **OCR enabled:** LiteParse config has OCR enabled with English language

## Auto-Generate Schema Feature

The Auto-Generate Schema feature is implemented entirely in JavaScript (`static/js/project.js`). It provides deterministic, instant pattern generation from user-selected field examples.

### Key Components

**Main Function:** `autoGenerateSchema()` at line 1150
- Orchestrates the entire pattern generation process
- Implements smart example selection (date ranges over singles, longer over shorter)
- Loads file texts, generates patterns, saves schema, runs extraction

**Core Algorithm:** `generatePatternHint()` at line 908
- Analyzes context around example values (750 chars before value)
- Detects row labels and creates flexible patterns
- Identifies skip patterns (dates, numbers not part of label)
- Assembles 3-tier pattern cascade (specific, medium, fallback)

**Value Patterns:** `getValuePattern()` at line 1095
- Creates type-specific capture patterns
- Money: Preserves specific units (`kWh`, `therms`, `¢/therm`)
- Numbers: Detects dashes for account numbers
- Dates: Handles optional date ranges `(?:...)?`
- Text: Captures alphanumeric with spaces

### Pattern Generation Philosophy

1. **Flexible over rigid** - Replace specific numbers with `\d+(?:\.\d+)?` patterns
2. **Context-aware over value-only** - Use distinctive labels and keywords
3. **Specific units over generic** - Use "therms" not `[a-zA-Z]+`
4. **Multi-pattern cascade** - 3 patterns per field for robustness

### Key Bug Fixes

**Bug #1: Numbers in Labels** (line 1013-1016)
- Problem: "401" in "401(k)" was treated as skip pattern
- Fix: Check if number position < label end position

**Bug #2: Over-Specific Amounts** (line 948-953)
- Problem: "2.00" was escaped literally, only matched exact amount
- Fix: Two-step process: escape regex chars, then replace numbers with patterns

**Bug #3: Account Numbers** (line 1119-1121)
- Problem: Pattern `(\d+)` lost dashes in "89613-14560-9"
- Fix: Detect dashes in value, generate `([\d-]+)`

**Bug #4: Money Units** (line 1111-1115)
- Problem: Pattern captured "130.00" instead of "130.00 kWh"
- Fix: Extract specific unit from value, include in pattern

**Bug #5: Date Ranges** (line 1131-1134, 1221-1226)
- Problem: Range pattern didn't match single dates
- Fix 1: Make second date optional with `(?:...)?`
- Fix 2: Smart selection prefers range examples for date fields

### Code Locations

| Feature | File | Lines |
|---------|------|-------|
| Auto-generate orchestration | `static/js/project.js` | 1150-1299 |
| Pattern hint generation | `static/js/project.js` | 908-1086 |
| Value pattern creation | `static/js/project.js` | 1095-1144 |
| Label detection | `static/js/project.js` | 922-961 |
| Skip pattern detection | `static/js/project.js` | 963-1030 |
| Pattern assembly | `static/js/project.js` | 1032-1083 |
| Smart example selection | `static/js/project.js` | 1212-1232 |

### Testing Auto-Generate

When modifying auto-generate logic:
1. Test with varying amounts (1.00 vs 2.00 vs 3.50)
2. Test with date ranges and single dates
3. Test with labels containing numbers ("401(k)")
4. Test with units that shouldn't cross-match (kWh vs therms)
5. Test with account numbers containing dashes

See [AUTO_GENERATE.md](AUTO_GENERATE.md) for comprehensive technical documentation.

### JavaScript Code Style

**Functions:**
- Use descriptive names: `generatePatternHint()`, `getValuePattern()`
- Document parameters with JSDoc comments
- Return structured objects with clear property names

**Regex Escaping:**
```javascript
// CORRECT: Two-step process
let escaped = label.replace(/[()[\]{}.*+?^$|\\]/g, '\\$&');  // Escape first
let flexible = escaped.replace(/\d+(?:\\\.\d+)?/g, '\\d+(?:\\.\\d+)?');  // Then replace

// WRONG: One step (numbers get double-escaped)
let pattern = label.replace(/[()[\]{}.*+?^$|\\.0-9]/g, '\\$&');
```

**Pattern Testing:**
```javascript
// Test patterns during development
const testValue = "Supply 2.00 therms @";
const pattern = generatePatternHint(context, testValue, 'money');
console.log('Generated pattern:', pattern.suggestedPatterns[0].pattern);
// Expected: Supply \\d+(?:\\.\\d+)? therms @
```
