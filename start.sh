#!/bin/bash
# Start AuraOS Launcher

# Ensure we are in the script directory
cd "$(dirname "$0")"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

# Check for Tkinter
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: python3-tk is not installed."
    echo "Please install it (e.g., brew install python-tk or sudo apt install python3-tk)"
    exit 1
fi

# Launch
echo "Starting AuraOS..."
python3 auraos_launcher.py
