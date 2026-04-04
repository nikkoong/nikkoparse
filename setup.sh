#!/bin/bash

# PDF Extractor Setup Script

echo "Starting PDF Extractor setup..."
echo ""

# Check for Node.js and npm
echo "Checking for Node.js and npm..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed."
    echo "Please install Node.js from: https://nodejs.org"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed."
    echo "Please install npm from: https://nodejs.org"
    exit 1
fi

echo "✓ Node.js version: $(node --version)"
echo "✓ npm version: $(npm --version)"
echo ""

# Install LiteParse globally
echo "Installing LiteParse CLI globally..."
npm install -g @llamaindex/liteparse

if [ $? -ne 0 ]; then
    echo "❌ Failed to install LiteParse."
    echo "Please check your npm configuration and try again."
    exit 1
fi

echo "✓ LiteParse installed"
echo ""

# Check for Python 3.9+
echo "Checking for Python 3.9+..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo "Please install Python 3.9 or higher from: https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo "❌ Python version $PYTHON_VERSION is too old."
    echo "Please install Python 3.9 or higher from: https://python.org"
    exit 1
fi

echo "✓ Python version: $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv .venv

if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment."
    exit 1
fi

echo "✓ Virtual environment created"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies."
    exit 1
fi

echo "✓ Python dependencies installed"
echo ""

# Create data directory
echo "Setting up data directory..."
DATA_DIR="$HOME/Documents/PDFExtractor"

if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    echo "✓ Created directory: $DATA_DIR"
else
    echo "✓ Directory already exists: $DATA_DIR"
fi

# Create projects.json if it doesn't exist
PROJECTS_FILE="$DATA_DIR/projects.json"

if [ ! -f "$PROJECTS_FILE" ]; then
    echo "[]" > "$PROJECTS_FILE"
    echo "✓ Created projects registry: $PROJECTS_FILE"
else
    echo "✓ Projects registry already exists: $PROJECTS_FILE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete!"
echo ""
echo "To start the application, run:"
echo "  ./start.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
