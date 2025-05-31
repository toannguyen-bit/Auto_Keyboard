@echo off
set SCRIPT_DIR=%~dp0
cd /D "%SCRIPT_DIR%.."


set VENV_NAME=venv


python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python.
    pause
    exit /b 1
)


if not exist "%VENV_NAME%\Scripts\activate.bat" (
    echo ==============================
    echo Creating virtual environment: %VENV_NAME%...
    echo ==============================
    python -m venv %VENV_NAME%
    if %errorlevel% neq 0 (
        echo =============================================
        echo Failed to create virtual environment.
        echo =============================================
        pause
        exit /b 1
    )
    echo ==============================
    echo Virtual environment created.
    echo ==============================
)
echo ======================================
echo Activating virtual environment...
echo ======================================

call "%VENV_NAME%\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo ======================================
    echo Failed to activate virtual environment.
    echo ======================================

    pause
    exit /b 1
)

echo ======================================
echo Installing dependencies from requirements.txt...
echo ======================================

pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ======================================
    echo Failed to install dependencies.
    echo ======================================

    pause
    exit /b 1
)

echo ======================================
echo Running AutoKeyboard application...
echo ======================================


python main.py

echo ======================================
echo Deactivating virtual environment (script will exit)...
echo ======================================

echo ==============================
echo done
echo ==============================
