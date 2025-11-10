#!/usr/bin/env bash
# Helper to activate the venv and start the AuraOS daemon
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/venv"

if [ ! -d "$VENV" ]; then
  echo "Virtualenv not found at $VENV. Creating..."
  python3 -m venv "$VENV"
  source "$VENV/bin/activate"
  pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
  if [ -f "$HERE/requirements.txt" ]; then
    pip install -r "$HERE/requirements.txt"
  fi
  deactivate || true
fi

# Activate and run
# shellcheck disable=SC1091
source "$VENV/bin/activate"
cd "$HERE"
echo "Starting AuraOS daemon with $(which python)" 
python main.py

# If the script exits, deactivate
deactivate || true
