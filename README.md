# NikkoParse

A local macOS tool for extracting structured data from PDF documents using intelligent regex pattern generation.

![Version](https://img.shields.io/badge/version-1.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Features

- 📄 **PDF Parsing with OCR** - Powered by LiteParse CLI
- 🎯 **Interactive Field Definition** - Click text to create extraction patterns
- ⚡ **Auto-Generate Schema** - Instant, deterministic pattern generation from user-provided examples
- 🤖 **AI-Assisted Import** - Optional AI workflow for complex documents; automatically creates prompt to paste into an AI for schema generation
- 📊 **Intelligent Field Suggestions** - Master dictionary of 1000+ common fields
- 🔍 **Multi-Pattern Regex Cascading** - Robust extraction with fallback patterns
- 📋 **Export to TSV** - Copy results directly to Excel/Google Sheets
- 💾 **File-Based Storage** - No database needed, all data in JSON files
- 🎨 **Modern UI** - Clean interface with progress tracking and live preview

---

## Quick Start

### Prerequisites

- macOS (tested on macOS 12+)
- Python 3.9 or higher
- Node.js 16+ (for LiteParse CLI)
- npm (comes with Node.js)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nikkoong/nikkoparse.git
   cd nikkoparse
   ```

2. **Run setup script**
   ```bash
   ./setup.sh
   ```
   
   This will:
   - Check for Node.js and npm
   - Install LiteParse CLI globally
   - Create Python virtual environment
   - Install Python dependencies
   - Create data directory at `~/Documents/NikkoParse_Data`

3. **Launch the app**
   ```bash
   ./start.sh
   ```
   
   The app will:
   - Activate virtual environment
   - Start Flask server on port 5001
   - Auto-open browser to http://localhost:5001

---

## Usage

### 1. Create a Project

Click "New Project" card on the home page and give your project a name (e.g., "Payslips 2026").

### 2. Upload PDFs

Click "Add Files" to upload PDF documents. Each file will be:
- Uploaded and parsed with LiteParse (includes OCR)
- Converted to searchable text
- Displayed in the document preview panel

The first uploaded document opens automatically.

### 3. Define Extraction Fields
This section allows you to define the fields you want to extract from your documents. You can create extraction patterns in three ways: quick automatic generation, AI-assisted schema creation, or manual regex pattern definition.

**Quick Method (Recommended):**
1. Select text values in the document preview to select them
2. Enter a field label (e.g., "Net Pay", "Date Range")
3. Press Enter or click "Add Field"
4. Click "Auto-Generate Schema" button
5. Patterns are generated and extraction runs automatically

**AI-Assisted Method (For Complex Documents):**
1. After selecting example values for the fields you want to extract, click "Export for AI" button
2. Copy the generated prompt
3. Paste into Claude, ChatGPT, or Gemini (any AI chatbot)
4. Wait 30-60 seconds for AI to generate schema
5. Click "Import AI Schema" and paste the JSON response
6. Extraction runs automatically

### 4. Review & Edit Results

- View extracted data in the table view
- Click kebab menu (⋮) on any cell to:
  - Override value manually
  - Remove override
  - Navigate to value in document
- Click column headers to cycle through documents
- Results update across all documents in real-time

### 5. Export Data

Click "Copy TSV" button to copy the extraction results table, then paste directly into:
- Microsoft Excel
- Google Sheets
- Any spreadsheet application

---

## Project Structure

```
nikkoparse/
├── app.py                    # Flask application entry point
├── setup.sh                  # Environment setup script
├── start.sh                  # Launch script
├── requirements.txt          # Python dependencies
├── liteparse.config.json     # LiteParse configuration
├── api/                      # Flask REST API endpoints
├── core/                     # Core business logic
├── static/                   # Frontend (HTML/CSS/JS)
└── tests/                    # Test suite (pytest)
```

**Data Storage:**
```
~/Documents/NikkoParse_Data/
├── projects.json             # Project registry
└── projects/
    └── {project-id}/
        ├── project.json      # Metadata & schema
        ├── raw/              # LiteParse outputs
        └── extracted/        # Extraction results
```

---

## Auto-Generate Schema Feature

The **Auto-Generate Schema** feature is the fastest, most reliable way to create extraction patterns. It uses deterministic algorithms to analyze your example selections and generate flexible, context-aware regex patterns.

### How It Works

1. **Select Examples** - Click values in your documents to create field examples
   - Select a few examples of each field from different documents
   - The system tracks the value and surrounding context

2. **Click Auto-Generate** - The algorithm:
   - Analyzes context around each example value
   - Detects field labels and distinctive keywords
   - Identifies column separators and skip patterns
   - Generates flexible patterns that handle variations
   - Creates fallback patterns for robustness

3. **Instant Results** - Patterns are applied and extraction runs automatically
   - No AI cost or latency
   - Deterministic and predictable
   - Works offline

### Pattern Generation Strategy

The algorithm creates **flexible, context-aware patterns** by:

**Label Detection:**
- Identifies row labels (e.g., "401(k) Basic Contribution", "Supply therms @")
- Escapes regex special characters (parentheses, periods, etc.)
- Replaces specific numbers with flexible patterns (e.g., "2.00" → `\d+(?:\.\d+)?`)
- Keeps distinctive words exact (e.g., "therms" not `[a-zA-Z]+`)

**Skip Patterns:**
- Detects and skips date columns between label and value
- Identifies number columns to skip (hours, quantities)
- Excludes numbers that are part of labels (e.g., "401" in "401(k)")

**Value Patterns:**
- **Money**: Preserves units like "kWh" or "¢/therm" to avoid cross-matching
- **Numbers**: Detects dashes for account numbers (e.g., "89613-14560-9")
- **Dates**: Handles both single dates and date ranges with optional second date
- **Text**: Captures alphanumeric with spaces

**Multi-Pattern Cascade:**
Each field gets 3 patterns tried in order:
1. **Specific** - Label + skip columns + value (most precise)
2. **Medium** - Label + greedy skip + value (handles spacing variations)
3. **Fallback** - Value-only pattern (catches edge cases)

### Smart Example Selection

When you have multiple examples for a field, the system automatically picks the best one:
- **Date fields**: Prefers date ranges over single dates
- **Other fields**: Prefers longer/more complex values with more context

This ensures patterns are as flexible as possible from the start.

### Benefits

- **Speed**: Instant pattern generation (vs 30-60 seconds for AI)
- **Cost**: Free, no API calls required
- **Reliability**: Deterministic results, no AI variability
- **Offline**: Works without internet connection
- **Flexibility**: Patterns handle variations in amounts, dates, formatting

### Example Workflow

**Scenario:** Extracting from payslips with varying amounts

1. Click "Net Pay: $2,450.67" in document 1 → Label field "Net Pay"
2. Click "Net Pay: $3,120.89" in document 2 → System adds as second example
3. Click "Auto-Generate Schema"
4. Generated pattern: `Net Pay:?\s+(\$[\d,\.]+)` matches any dollar amount
5. Extraction runs across all 13 payslips successfully

**Result:** 10 fields extracted in ~30 seconds vs 45 minutes manually

---

## AI-Assisted Schema Builder (Optional)

For complex documents where patterns are harder to identify, you can use AI assistance:

### How It Works

1. **Export** - NikkoParse generates an optimized prompt containing:
   - Sample excerpts from your documents
   - Instructions for the AI
   - Output format specification
   - Examples of good regex patterns

2. **AI Processing** - Claude/ChatGPT/OpenCode:
   - Analyzes document structure
   - Identifies common fields
   - Generates regex patterns with capture groups
   - Tests patterns against samples
   - Returns validated JSON schema

3. **Import** - NikkoParse:
   - Validates JSON syntax (auto-fixes common issues)
   - Tests patterns against your documents
   - Saves schema
   - Runs extraction automatically

### When to Use AI vs Auto-Generate

**Use Auto-Generate when:**
- Documents have consistent structure
- You can click 2-3 examples of each field
- You want instant, free results

**Use AI when:**
- Document structure is complex or varies widely
- You're not sure what fields to extract
- You want AI to discover patterns you might miss

---

## Technical Details

### Tech Stack

- **Backend:** Python 3.9+, Flask 3.0+
- **Frontend:** Vanilla JavaScript (ES6+), no build step
- **Parsing:** LiteParse CLI (`@llamaindex/liteparse`)
- **Storage:** JSON files (no database)
- **Testing:** pytest (38 passing tests)

### Key Features

**Multi-Pattern Regex Cascading:**
Each field has multiple regex patterns tried in priority order:
1. `specific` - Label-anchored pattern with context (most precise)
2. `medium` - Label with greedy skip to value (handles spacing variations)
3. `value_only` - Value format only (fallback for edge cases)

This provides robust extraction with graceful degradation.

**Intelligent Field Suggestions:**
- Master dictionary of 1000+ fields across 16 categories
- Keyword-based scoring algorithm
- Suggests top 10 most relevant fields
- Includes sample values from your documents

**Smart Data Type Detection:**
Automatically detects and applies:
- Money (`$106.79`, `$1,234.56`, `130.00 kWh`, `58.500¢/therm`)
- Date (`01/26/26`, `2026-01-26`, `Jan 26, 2026`, `01/04/2026 - 01/17/2026`)
- Number (`1234`, `1,234.56`, `89613-14560-9`)
- Text (everything else)

Colored badges in UI help identify field types at a glance.

**Auto-Generate Schema:**
Deterministic pattern generation from example selections:
- Analyzes context around selected values
- Creates flexible patterns (handles variations in amounts/dates)
- Generates multi-pattern cascade for robustness
- Smart example selection (prefers ranges, complex values)
- Instant results, no AI required

See the [Auto-Generate Schema](#auto-generate-schema-feature) section for details.

---

## Development

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_storage.py
```

### Code Style

- Python: Type hints required, Google-style docstrings
- JavaScript: Vanilla ES6+, no TypeScript
- Follow patterns in DEVELOPMENT.md

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Troubleshooting

### LiteParse not found
```bash
npm install -g @llamaindex/liteparse
```

### Port 5001 already in use
Edit `app.py` and change:
```python
app.run(debug=True, port=5001)  # Change to another port
```

---

## Roadmap

- [x] Auto-generate schema from field examples
- [x] Multi-pattern regex cascading
- [x] Smart example selection (date ranges, complex values)
- [x] Flexible pattern generation (handle variations)
- [x] Horizontal scroll with frozen first column
- [x] Enter key to submit field labels
- [ ] Windows/Linux support
- [ ] Package as native macOS app
- [ ] Support for more document formats (DOCX, images)
- [ ] Visual regex pattern debugger
- [ ] Export to CSV/JSON formats
- [ ] Multi-user project collaboration
- [ ] Cloud backup integration

---

## License

MIT License - see LICENSE file for details


---