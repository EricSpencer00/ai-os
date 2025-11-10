#!/usr/bin/env bash
# status.sh - Complete AuraOS status check

echo "╔════════════════════════════════════════════════════════╗"
echo "║              AuraOS Status Report                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo

echo "1. VM & Tunnels"
echo "───────────────"
multipass list | grep auraos || echo "✗ VM not found"
lsof -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1 && echo "✓ Agent tunnel (8765)" || echo "✗ Agent tunnel"
lsof -iTCP:5901 -sTCP:LISTEN >/dev/null 2>&1 && echo "✓ VNC tunnel (5901)" || echo "✗ VNC tunnel"
lsof -iTCP:6080 -sTCP:LISTEN >/dev/null 2>&1 && echo "✓ noVNC tunnel (6080)" || echo "✗ noVNC tunnel"

echo
echo "2. XFCE Processes (in VM)"
echo "───────────────────────────"
for proc in xfce4-session xfwm4 xfce4-panel xfdesktop; do
  if multipass exec auraos-multipass -- pgrep -x "$proc" >/dev/null 2>&1; then
    echo "✓ $proc running"
  else
    echo "✗ $proc NOT running"
  fi
done

echo
echo "3. Screenshot Test"
echo "───────────────────"
SHOT="/tmp/auraos_status_$(date +%s).png"
if curl -sS -m 8 http://localhost:8765/screenshot -o "$SHOT" 2>/dev/null; then
  SIZE=$(wc -c < "$SHOT")
  echo "✓ Screenshot captured: ${SIZE} bytes"
  
  if [ "$SIZE" -lt 15000 ]; then
    echo "⚠️  Screenshot is very small (likely blank/minimal desktop)"
  elif [ "$SIZE" -gt 100000 ]; then
    echo "✓ Screenshot looks good (reasonable size)"
  fi
  
  echo "  File: $SHOT"
else
  echo "✗ Screenshot failed"
fi

echo
echo "4. Access Methods"
echo "──────────────────"
echo "  Browser (noVNC): http://localhost:6080"
echo "                   Password: auraos123"
echo
echo "  VNC Client:      vnc://localhost:5901"
echo "                   Password: auraos123"
echo
echo "  Agent API:       http://localhost:8765"
echo

echo "5. Quick Actions"
echo "─────────────────"
echo "  Open browser:    open http://localhost:6080"
echo "  Restart XFCE:    multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service"
echo "  View logs:       multipass exec auraos-multipass -- sudo journalctl -u auraos-x11vnc.service -n 50"
echo "  Test AI vision:  python3 demo_ai_os.py 'click on the terminal icon'"
echo

read -p "Open noVNC in browser now? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
  open "http://localhost:6080"
  echo "✓ Browser opened - you should see the desktop there"
fi
