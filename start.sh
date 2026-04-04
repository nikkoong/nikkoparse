#!/bin/bash

# PDF Extractor Start Script

echo "Starting PDF Extractor..."

# Kill any existing Flask servers on port 5001
echo "Checking for existing servers..."
lsof -ti:5001 | xargs kill -9 2>/dev/null
if [ $? -eq 0 ]; then
  echo "✓ Stopped existing server on port 5001"
  sleep 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
  source venv/bin/activate
elif [ -d ".venv" ]; then
  source .venv/bin/activate
else
  echo "❌ Error: Virtual environment not found (venv or .venv)"
  exit 1
fi

# Start Flask app
python app.py &
FLASK_PID=$!

# Wait for Flask to start
echo "Waiting for server to start..."
sleep 3

# Check if server is running
if ! lsof -i:5001 >/dev/null 2>&1; then
  echo "❌ Error: Server failed to start"
  exit 1
fi

# Open browser
open http://localhost:5001

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ PDF Extractor is running!"
echo ""
echo "Access the app at: http://localhost:5001"
echo ""
echo "To stop the server, press Ctrl+C"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Wait for Flask process
wait $FLASK_PID
