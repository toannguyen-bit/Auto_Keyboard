@echo off
set SCRIPT_DIR=%~dp0
cd /D "%SCRIPT_DIR%.."


set VENV_NAME=moitruongao


python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python.
    pause
    exit /b 1
)


if not exist "%VENV_NAME%\Scripts\activate.bat" (
    echo Creating virtual environment: %VENV_NAME%...
    python -m venv %VENV_NAME%
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created.
)

echo Activating virtual environment...
call "%VENV_NAME%\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo Running AutoKeyboard application...
python main.py

echo Deactivating virtual environment (script will exit)...

echo Done.
