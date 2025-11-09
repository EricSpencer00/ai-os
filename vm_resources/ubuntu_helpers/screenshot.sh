#!/bin/bash
# screenshot.sh - Capture screenshot from DISPLAY :1
# Usage: ./screenshot.sh [output_file.png]

USER=ubuntu
DISPLAY=:1
OUTPUT="${1:-/tmp/screenshot_$(date +%Y%m%d_%H%M%S).png}"

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

# Take screenshot
if command -v import >/dev/null 2>&1; then
  # ImageMagick
  import -window root "$OUTPUT"
elif command -v xwd >/dev/null 2>&1 && command -v convert >/dev/null 2>&1; then
  # xwd + convert
  xwd -root -out /tmp/screenshot.xwd && convert /tmp/screenshot.xwd "$OUTPUT" && rm -f /tmp/screenshot.xwd
else
  echo "Error: No screenshot tool available (install imagemagick)" >&2
  exit 1
fi

if [ -f "$OUTPUT" ]; then
  echo "Screenshot saved: $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
  file "$OUTPUT"
else
  echo "Error: Screenshot failed" >&2
  exit 1
fi
