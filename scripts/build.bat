@echo off
cd /d "%~dp0.."
echo ========================================
echo Watch Cataloging System Build Script
echo ========================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Please create a .env file with your Supabase credentials:
    echo   - SUPABASE_URL
    echo   - SUPABASE_KEY
    echo   - SECRET_KEY
    echo.
    echo See README.md for configuration details.
    echo.
    pause
)

echo Checking and installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies.
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
