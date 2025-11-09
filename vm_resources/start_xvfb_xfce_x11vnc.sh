#!/bin/bash
set -e
USER=ubuntu
export DISPLAY=:1

echo "[$(date)] Starting Xvfb + XFCE + x11vnc..."

# Start Xvfb if not running
if ! pgrep -f "Xvfb :1" >/dev/null 2>&1; then
  echo "Starting Xvfb :1..."
  nohup Xvfb :1 -screen 0 1280x720x24 >/var/log/xvfb.log 2>&1 &
  sleep 2
else
  echo "Xvfb already running"
fi

# Ensure .Xauthority exists
su - $USER -c "xauth generate :1 . trusted 2>/dev/null || xauth list :1 >/dev/null 2>&1 || true"
chown $USER:$USER /home/$USER/.Xauthority 2>/dev/null || true

# Start XFCE session if not running
if ! su - $USER -c "pgrep -u $USER -f xfce4-session >/dev/null 2>&1"; then
  echo "Starting XFCE session for $USER on DISPLAY :1..."
  # Use a more robust startup that waits for the session to be ready
  su - $USER -c "DISPLAY=:1 dbus-launch --exit-with-session startxfce4 >/home/$USER/xfce_start.log 2>&1 &"
  
  # Wait up to 30 seconds for XFCE to fully initialize
  for i in {1..30}; do
    if su - $USER -c "pgrep -u $USER -f 'xfce4-session|xfwm4|xfce4-panel' >/dev/null 2>&1"; then
      echo "XFCE session started (waited ${i}s)"
      # Give panel and window manager a moment to settle
      sleep 2
      break
    fi
    sleep 1
  done
  
  # Verify critical XFCE processes
  if su - $USER -c "pgrep -u $USER -f xfce4-session >/dev/null 2>&1"; then
    echo "XFCE session confirmed running"
  else
    echo "WARNING: XFCE session may not have started properly" >&2
  fi
else
  echo "XFCE session already running"
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
