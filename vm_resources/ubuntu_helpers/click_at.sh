#!/bin/bash
# click_at.sh - Click at specific coordinates on DISPLAY :1
# Usage: ./click_at.sh X Y [button]
#   X, Y: pixel coordinates
#   button: 1 (left, default), 2 (middle), 3 (right)

USER=ubuntu
DISPLAY=:1

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 X Y [button]" >&2
  echo "  X, Y: pixel coordinates" >&2
  echo "  button: 1 (left), 2 (middle), 3 (right) - default 1" >&2
  exit 1
fi

X=$1
Y=$2
BUTTON=${3:-1}

# Ensure running as the correct user
if [ "$EUID" -eq 0 ] && [ "$(whoami)" != "$USER" ]; then
  exec su - $USER -c "DISPLAY=$DISPLAY $0 $*"
fi

export DISPLAY

# Check if X is accessible
if ! xdpyinfo >/dev/null 2>&1; then
  echo "Error: Cannot connect to DISPLAY $DISPLAY" >&2
  exit 1
fi

# Perform click
echo "Clicking at ($X, $Y) with button $BUTTON on $DISPLAY"
xdotool mousemove "$X" "$Y"
sleep 0.1
xdotool click "$BUTTON"

echo "✓ Click executed at ($X, $Y)"
