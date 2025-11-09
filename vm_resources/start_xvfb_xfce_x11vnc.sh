#!/bin/bash
set -e
USER=ubuntu
export DISPLAY=:1

echo "[$(date)] Starting Xvfb + XFCE + x11vnc..."

# Start Xvfb if not running
if ! pgrep -x "Xvfb" >/dev/null 2>&1; then
  echo "Starting Xvfb :1..."
  nohup Xvfb :1 -screen 0 1280x720x24 >/var/log/xvfb.log 2>&1 &
  sleep 2
else
  echo "Xvfb already running"
fi

# Ensure .Xauthority exists
su - $USER -c "xauth generate :1 . trusted 2>/dev/null || xauth list :1 >/dev/null 2>&1 || true"
chown $USER:$USER /home/$USER/.Xauthority 2>/dev/null || true

# Check if XFCE session is actually running (use -x for exact match to avoid matching xfconfd)
XFCE_RUNNING=0
if pgrep -x -u $USER xfce4-session >/dev/null 2>&1; then
  # Double check that key XFCE processes exist
  if pgrep -x -u $USER xfwm4 >/dev/null 2>&1 && pgrep -x -u $USER xfce4-panel >/dev/null 2>&1; then
    echo "XFCE session already running (xfce4-session, xfwm4, xfce4-panel all present)"
    XFCE_RUNNING=1
  else
    echo "WARNING: xfce4-session found but xfwm4/panel missing - will restart XFCE" >&2
    # Kill incomplete session
    pkill -u $USER -x xfce4-session || true
    sleep 1
  fi
fi

if [ $XFCE_RUNNING -eq 0 ]; then
  echo "Starting XFCE session for $USER on DISPLAY :1..."
  
  # Clean up any stale XFCE processes first
  pkill -u $USER -x xfce4-session || true
  pkill -u $USER -x xfwm4 || true
  pkill -u $USER -x xfce4-panel || true
  pkill -u $USER -x xfdesktop || true
  pkill -u $USER -x xfce4-screensaver || true
  sleep 1
  
  # Start fresh XFCE session
  su - $USER -c "DISPLAY=:1 dbus-launch --exit-with-session startxfce4 >/home/$USER/xfce_start.log 2>&1 &"
  
  # Wait up to 30 seconds for XFCE to fully initialize
  for i in {1..30}; do
    if pgrep -x -u $USER xfce4-session >/dev/null 2>&1 && \
       pgrep -x -u $USER xfwm4 >/dev/null 2>&1 && \
       pgrep -x -u $USER xfce4-panel >/dev/null 2>&1; then
      echo "XFCE session started successfully (waited ${i}s)"
      # Give it a moment to settle
      sleep 2
      break
    fi
    sleep 1
  done
  
  # Final verification
  if pgrep -x -u $USER xfce4-session >/dev/null 2>&1; then
    echo "XFCE session confirmed running"
  else
    echo "ERROR: XFCE session failed to start - check /home/$USER/xfce_start.log" >&2
  fi
fi

# Final check before starting x11vnc
if ! su - $USER -c "DISPLAY=:1 xdpyinfo >/dev/null 2>&1"; then
  echo "WARNING: Cannot connect to X display :1" >&2
  sleep 2
fi

echo "Starting x11vnc on port 5900..."
exec /usr/bin/x11vnc -auth /home/$USER/.Xauthority -display :1 -rfbport 5900 \
  -rfbauth /home/$USER/.vnc/passwd -forever -shared -noxdamage -nowf -ncache 0 \
  -o /var/log/x11vnc_manual.log
