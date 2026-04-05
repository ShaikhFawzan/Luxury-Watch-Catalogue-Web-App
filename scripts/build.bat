@echo off
cd /d "%~dp0.."
echo ========================================
echo Watch Cataloging System Build Script
echo ========================================
echo.
echo Checking and installing dependencies...
pip install flask
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install Flask.
    echo Please ensure Python and pip are installed correctly.
    echo.
    pause
    exit /b 1
)
echo.
echo Dependencies installed successfully.
echo.
echo Starting the application...
echo You can access it at http://localhost:5000
echo Press Ctrl+C to stop the server.
echo.
python app.py
