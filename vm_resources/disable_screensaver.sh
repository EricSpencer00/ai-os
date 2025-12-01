#!/usr/bin/env bash
set -e

# Usage: sudo ./disable_screensaver.sh [username]
USER_NAME="${1:-ubuntu}"
HOME_DIR="/home/$USER_NAME"

echo "Disabling screensaver / lock for user: $USER_NAME"

# 1) Disable X server blanking and DPMS for the active display via xset (if X running)
if command -v xset >/dev/null 2>&1; then
  echo "Applying xset settings (session)"
  export DISPLAY=:0
  xset s off || true
  xset s noblank || true
  xset -dpms || true
fi

# 2) Kill and disable common locker daemons (light-locker, xscreensaver, xss-lock)
if command -v pkill >/dev/null 2>&1; then
  echo "Stopping locker daemons if present"
  pkill light-locker || true
  pkill xscreensaver || true
  pkill xss-lock || true
fi

# 3) Create an autostart entry to apply xset at session start
AUTOSTART_DIR="$HOME_DIR/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/disable-screensaver.desktop" <<'DESK'
[Desktop Entry]
Type=Application
Name=Disable Screensaver
Exec=/usr/local/bin/disable-screensaver-session.sh
X-GNOME-Autostart-enabled=true
NoDisplay=true
DESK

# 4) Create the session helper script
cat > /usr/local/bin/disable-screensaver-session.sh <<'SH'
#!/usr/bin/env bash
# Run in user session to disable blanking and DPMS
export DISPLAY=:0
xset s off 2>/dev/null || true
xset s noblank 2>/dev/null || true
xset -dpms 2>/dev/null || true
pkill light-locker 2>/dev/null || true
pkill xscreensaver 2>/dev/null || true
SH

chmod +x /usr/local/bin/disable-screensaver-session.sh || true

# 5) Ensure ownership of autostart files
chown -R "$USER_NAME:$USER_NAME" "$AUTOSTART_DIR" || true
chown root:root /usr/local/bin/disable-screensaver-session.sh || true

# 6) Try to apply settings now for the current session (may require running as user)
if [ "$EUID" -eq 0 ]; then
  # try to su to user and run xset if possible
  if command -v su >/dev/null 2>&1; then
    su - "$USER_NAME" -c "export DISPLAY=:0; xset s off || true; xset s noblank || true; xset -dpms || true" || true
  fi
fi

# 7) Disable light-locker autostart if present
if [ -f "$HOME_DIR/.config/autostart/light-locker.desktop" ]; then
  echo "Disabling light-locker autostart"
  sed -i.bak 's/X-GNOME-Autostart-enabled=true/X-GNOME-Autostart-enabled=false/' "$HOME_DIR/.config/autostart/light-locker.desktop" || true
  chown "$USER_NAME:$USER_NAME" "$HOME_DIR/.config/autostart/light-locker.desktop" || true
fi

echo "Screensaver/lock disabling steps applied. Re-login or reboot may be required for some changes to take effect."
