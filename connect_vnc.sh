#!/usr/bin/env bash
# connect_vnc.sh - Simple VNC connection helper

set -euo pipefail

echo "=== VNC Connection Helper ==="
echo

# Check tunnel
if ! lsof -iTCP:5901 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: No SSH tunnel on port 5901. Run ./open_vm_gui.sh first." >&2
  exit 1
fi
echo "✓ SSH tunnel active on port 5901"

# Test connection
if nc -zv localhost 5901 2>&1 | grep -q succeeded; then
  echo "✓ Port 5901 is accessible"
else
  echo "✗ Cannot connect to port 5901" >&2
  exit 1
fi

echo
echo "VNC Connection Options:"
echo
echo "1. Browser (noVNC - recommended, no password needed):"
echo "   http://localhost:6080"
echo
echo "2. TigerVNC Viewer:"
echo "   Host: localhost:5901"
echo "   Password: auraos123"
echo
echo "3. macOS Screen Sharing (built-in):"
echo "   Host: vnc://localhost:5901"
echo "   Password: auraos123"
echo
echo "4. Command line test:"
echo "   vncviewer localhost:5901"
echo

read -p "Open noVNC in browser now? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
  open "http://localhost:6080" || echo "Browser open failed - visit manually: http://localhost:6080"
fi
