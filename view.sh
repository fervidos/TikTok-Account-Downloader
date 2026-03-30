#!/bin/bash
# TikTok Account Downloader Viewer - Start Script
# Runs the FastAPI application on 0.0.0.0:54321

# Change to the directory of the script
cd "$(dirname "$0")" || exit

# Determine python command
if command -v python3 &> /dev/null; then
    PY_CMD="python3"
elif command -v python &> /dev/null; then
    PY_CMD="python"
else
    echo "Python is not installed or not in PATH."
    exit 1
fi

# Install dependencies if needed
echo "Installing dependencies..."
"$PY_CMD" -m pip install fastapi uvicorn -q

# Start the server
echo
echo "Starting TikTok Account Downloader Viewer..."
echo "Server will be available at: http://localhost:54321"
echo
"$PY_CMD" -m uvicorn viewer:app --host 0.0.0.0 --port 54321 --reload

read -p "Press any key to continue..."
