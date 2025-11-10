#!/usr/bin/env bash
# quick_check.sh - Quick status check and screenshot viewer

echo "=== AuraOS Status Check ==="
echo

# Check if noVNC/agent tunnels are active
if lsof -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "✓ Agent tunnel active (port 8765)"
else
  echo "✗ Agent tunnel NOT active - run ./open_vm_gui.sh"
fi

if lsof -iTCP:6080 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "✓ noVNC tunnel active (port 6080)"
else
  echo "✗ noVNC tunnel NOT active"
fi

# Check XFCE in VM
echo
echo "Checking XFCE processes in VM..."
if multipass exec auraos-multipass -- pgrep -x xfce4-session >/dev/null 2>&1; then
  echo "✓ XFCE session running"
else
  echo "✗ XFCE session NOT running"
fi

# Capture and display screenshot
echo
echo "Capturing current screenshot..."
if curl -sS -m 8 http://localhost:8765/screenshot -o /tmp/current_screen.png 2>/dev/null; then
  SIZE=$(wc -c < /tmp/current_screen.png)
  echo "✓ Screenshot captured: ${SIZE} bytes"
  echo
  echo "Opening screenshot..."
  open /tmp/current_screen.png
  echo
  echo "What do you see?"
  echo "  - If it's a blue noVNC login screen: enter password 'auraos123' in browser"
  echo "  - If it's the XFCE desktop: ready for AI automation!"
  echo "  - If it's black: run './ubuntu_vm.sh ensure-desktop' to restart XFCE"
else
  echo "✗ Screenshot failed"
fi

echo
echo "noVNC URL: http://localhost:6080"
