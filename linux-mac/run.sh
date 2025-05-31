#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT" || { echo "Failed to change directory to project root. Exiting."; exit 1; }

VENV_NAME="venv"
PYTHON_CMD="python3" 

if ! command -v $PYTHON_CMD &> /dev/null; then
    echo ======================================
    echo "$PYTHON_CMD could not be found. Trying 'python'."
    echo ======================================

    PYTHON_CMD="python"
    if ! command -v $PYTHON_CMD &> /dev/null; then  
        echo ======================================
        echo "Python (python3 or python) could not be found. Please install Python."
        echo ======================================
        
        exit 1
    fi
fi

echo ======================================
echo "Using Python command: $PYTHON_CMD"
echo ======================================


if [ ! -d "$VENV_NAME/bin" ]; then
    echo ======================================
    echo "Creating virtual environment: $VENV_NAME..."
    echo ======================================
    $PYTHON_CMD -m venv "$VENV_NAME"
    if [ $? -ne 0 ]; then
        echo ======================================
        echo "Failed to create virtual environment."
        echo ======================================
        exit 1
    fi
    echo ======================================
    echo "Virtual environment created."
    echo ======================================
fi

echo ======================================
echo "Activating virtual environment..."
echo ======================================
source "$VENV_NAME/bin/activate"


if [ $? -ne 0 ]; then
    echo ======================================
    echo "Failed to activate virtual environment."
    echo ======================================
    exit 1
fi

echo ======================================
echo "Installing dependencies from requirements.txt..."
echo ======================================

pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo ======================================
    echo "Failed to install dependencies."
    echo ======================================
    deactivate
    exit 1
fi

echo ======================================
echo "Running AutoKeyboard application..."
echo ======================================
$PYTHON_CMD main.py

echo ======================================
echo "Deactivating virtual environment..."
echo ======================================
deactivate

echo ======================================
echo "Done."
echo ======================================