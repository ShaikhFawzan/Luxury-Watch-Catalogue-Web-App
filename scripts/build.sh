#!/bin/bash
cd "$(dirname "$0")\.."
echo "========================================"
echo "Watch Cataloging System Build Script"
echo "========================================"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Please create a .env file with your Supabase credentials:"
    echo "  - SUPABASE_URL"
    echo "  - SUPABASE_KEY"
    echo "  - SECRET_KEY"
    echo ""
    echo "See README.md for configuration details."
    echo ""
fi

echo "Checking and installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to install dependencies."
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
