#!/bin/bash
# type_text.sh - Type text on DISPLAY :1
# Usage: ./type_text.sh "text to type"

AURAOS_USER="${AURAOS_USER:-ubuntu}"
USER="$AURAOS_USER"
DISPLAY=:1

if [ -z "$1" ]; then
  echo "Usage: $0 \"text to type\"" >&2
  exit 1
fi

TEXT="$1"

# Ensure running as the correct user
if [ "$EUID" -eq 0 ] && [ "$(whoami)" != "$USER" ]; then
  exec su - $USER -c "DISPLAY=$DISPLAY $0 '$TEXT'"
fi

export DISPLAY

# Check if X is accessible
if ! xdpyinfo >/dev/null 2>&1; then
  echo "Error: Cannot connect to DISPLAY $DISPLAY" >&2
  exit 1
fi

# Type text
echo "Typing: $TEXT"
xdotool type --delay 100 "$TEXT"

echo "✓ Text typed successfully"
