#!/usr/bin/env bash
set -euo pipefail

# test_vm_gui.sh - Quick test to verify VM GUI is working

echo "=== AuraOS VM GUI Test ==="
echo

echo "1. Checking if XFCE processes are running in VM..."
if multipass exec auraos-multipass -- pgrep -x -u ubuntu xfce4-session >/dev/null 2>&1; then
  echo "✓ xfce4-session running"
else
  echo "✗ xfce4-session NOT running" >&2
  exit 1
fi

if multipass exec auraos-multipass -- pgrep -x -u ubuntu xfwm4 >/dev/null 2>&1; then
  echo "✓ xfwm4 running"
else
  echo "✗ xfwm4 NOT running" >&2
  exit 1
fi

if multipass exec auraos-multipass -- pgrep -x -u ubuntu xfce4-panel >/dev/null 2>&1; then
  echo "✓ xfce4-panel running"
else
  echo "✗ xfce4-panel NOT running" >&2
  exit 1
fi

echo
echo "2. Checking agent health..."
if curl -sSf -m 3 http://localhost:8765/health >/dev/null 2>&1; then
  echo "✓ Agent responding on http://localhost:8765"
else
  echo "✗ Agent not responding. Run ./open_vm_gui.sh to create tunnels." >&2
  exit 1
fi

echo
echo "3. Capturing screenshot..."
SCREENSHOT="/tmp/auraos_test_$(date +%s).png"
if curl -sS -m 8 http://localhost:8765/screenshot -o "$SCREENSHOT"; then
  SIZE=$(wc -c < "$SCREENSHOT")
  if [ "$SIZE" -gt 10000 ]; then
    echo "✓ Screenshot captured: $SCREENSHOT (${SIZE} bytes)"
    echo "  Opening screenshot..."
    open "$SCREENSHOT" || echo "  (open failed - view manually: $SCREENSHOT)"
  else
    echo "✗ Screenshot too small (${SIZE} bytes) - likely black screen" >&2
    exit 1
  fi
else
  echo "✗ Screenshot capture failed" >&2
  exit 1
fi

echo
echo "4. Checking systemd service status..."
if multipass exec auraos-multipass -- sudo systemctl is-active --quiet auraos-x11vnc.service; then
  echo "✓ auraos-x11vnc.service is active"
else
  echo "✗ auraos-x11vnc.service not active" >&2
  multipass exec auraos-multipass -- sudo systemctl status auraos-x11vnc.service --no-pager || true
  exit 1
fi

echo
echo "=== All tests passed! ==="
echo
echo "Next steps:"
echo "  - Open VNC: open vnc://localhost:5901 (password: auraos123)"
echo "  - Open noVNC: open http://localhost:6080"
echo "  - Or run: ./open_vm_gui.sh"
echo
