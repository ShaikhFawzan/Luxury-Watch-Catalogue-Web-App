#!/bin/bash
cd "$(dirname "$0")/.."
echo "========================================"
echo "Watch Cataloging System Build Script"
echo "========================================"
echo ""
echo "Checking and installing dependencies..."
pip install flask
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to install Flask."
    echo "Please ensure Python and pip are installed correctly."
    echo ""
    exit 1
fi
echo ""
echo "Dependencies installed successfully."
echo ""
echo "Starting the application..."
echo "You can access it at http://localhost:5000"
echo "Press Ctrl+C to stop the server."
echo ""
python app.py
