#!/bin/bash
# ensure_desktop.sh - Ensure XFCE desktop session is running on DISPLAY :1
# Can be run manually or via cron/systemd timer

set -e
USER=ubuntu
DISPLAY=:1

echo "[$(date)] Checking XFCE desktop session..."

# Check if XFCE session is running (use -x for exact match to avoid matching xfconfd)
if pgrep -x -u $USER xfce4-session >/dev/null 2>&1 && \
   pgrep -x -u $USER xfwm4 >/dev/null 2>&1 && \
   pgrep -x -u $USER xfce4-panel >/dev/null 2>&1; then
  echo "✓ XFCE session is running"
  ps aux | grep -E 'xfce4-session|xfwm4|xfce4-panel' | grep -v grep || true
  exit 0
fi

echo "✗ XFCE session not found - starting it now..."

# Clean up stale processes
pkill -u $USER -x xfce4-session || true
pkill -u $USER -x xfwm4 || true
pkill -u $USER -x xfce4-panel || true
sleep 1

# Ensure Xvfb is running first
if ! pgrep -f "Xvfb :1" >/dev/null 2>&1; then
  echo "Starting Xvfb :1..."
  nohup Xvfb :1 -screen 0 1280x720x24 >/var/log/xvfb.log 2>&1 &
  sleep 2
fi

# Ensure .Xauthority
su - $USER -c "xauth generate :1 . trusted 2>/dev/null || xauth list :1 >/dev/null 2>&1 || true"
chown $USER:$USER /home/$USER/.Xauthority 2>/dev/null || true

# Start XFCE
echo "Launching XFCE session..."
su - $USER -c "DISPLAY=:1 dbus-launch --exit-with-session startxfce4 >/home/$USER/xfce_start.log 2>&1 &"

# Wait for session
for i in {1..30}; do
  if pgrep -x -u $USER xfce4-session >/dev/null 2>&1 && \
     pgrep -x -u $USER xfwm4 >/dev/null 2>&1 && \
     pgrep -x -u $USER xfce4-panel >/dev/null 2>&1; then
    echo "✓ XFCE session started (waited ${i}s)"
    sleep 1
    ps aux | grep -E 'xfce4-session|xfwm4|xfce4-panel' | grep -v grep || true
    exit 0
  fi
  sleep 1
done

echo "✗ XFCE session failed to start after 30s" >&2
echo "Check logs: tail -n 50 /home/$USER/xfce_start.log" >&2
exit 1
