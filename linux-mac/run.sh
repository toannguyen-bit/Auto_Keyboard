#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT" || { echo "Failed to change directory to project root. Exiting."; exit 1; }

VENV_NAME="moitruongao"
PYTHON_CMD="python3" 

if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "$PYTHON_CMD could not be found. Trying 'python'."
    PYTHON_CMD="python"
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo "Python (python3 or python) could not be found. Please install Python."
        exit 1
    fi
fi
echo "Using Python command: $PYTHON_CMD"

if [ ! -d "$VENV_NAME/bin" ]; then
    echo "Creating virtual environment: $VENV_NAME..."
    $PYTHON_CMD -m venv "$VENV_NAME"
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment."
        exit 1
    fi
    echo "Virtual environment created."
fi

echo "Activating virtual environment..."
source "$VENV_NAME/bin/activate"
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment."
    exit 1
fi

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies."
    deactivate
    exit 1
fi

echo "Running AutoKeyboard application..."
$PYTHON_CMD main.py

echo "Deactivating virtual environment..."
deactivate

echo "Done."