# VM GUI Fix Summary

## Issue
- Black/tiled screen in VNC viewer due to client-side caching and broken systemd unit
- XFCE desktop session wasn't starting reliably before x11vnc

## Root Causes
1. **Malformed systemd unit** - ExecStart had duplicate/unbalanced quotes causing shell parsing errors
2. **x11vnc pixel-cache** - Client-side caching (-ncache 10) showed stale tile buffers
3. **Missing XFCE session** - startxfce4 wasn't being called or was failing silently

## Solution Implemented

### Files Created

**1. `/opt/auraos/start_xvfb_xfce_x11vnc.sh`** - Idempotent startup script
```bash
#!/bin/bash
set -e
USER=ubuntu
export DISPLAY=:1

# Start Xvfb if not running
if ! pgrep -f "Xvfb :1" >/dev/null 2>&1; then
  nohup Xvfb :1 -screen 0 1280x720x24 >/var/log/xvfb.log 2>&1 &
  sleep 1
fi

# Ensure .Xauthority exists and owned by ubuntu
su - $USER -c "xauth generate :1 . trusted || true"
chown $USER:$USER /home/$USER/.Xauthority || true

# Start XFCE session if not running
if ! su - $USER -c "pgrep -u $USER -f xfce4-session >/dev/null 2>&1"; then
  su - $USER -c "DISPLAY=:1 dbus-launch --exit-with-session startxfce4 >/home/$USER/xfce_start.log 2>&1 &"
  for i in {1..20}; do
    if su - $USER -c "pgrep -u $USER -f xfce4-session >/dev/null 2>&1"; then
      break
    fi
    sleep 1
  done
fi

# Start x11vnc with client-side caching disabled
exec /usr/bin/x11vnc -auth /home/$USER/.Xauthority -display :1 -rfbport 5900 \
  -rfbauth /home/$USER/.vnc/passwd -forever -shared -noxdamage -nowf -ncache 0 \
  -o /var/log/x11vnc_manual.log
```

**2. `/etc/systemd/system/auraos-x11vnc.service`** - Clean systemd unit
```ini
[Unit]
Description=AuraOS Xvfb + x11vnc virtual desktop
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/auraos/start_xvfb_xfce_x11vnc.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Key Changes
- **Disabled client-side caching**: `-ncache 0` (was `-ncache 10`)
- **Idempotent checks**: Script checks if Xvfb/XFCE are running before starting
- **Proper wait logic**: Waits up to 20s for XFCE session to initialize
- **Clean systemd unit**: Simple ExecStart pointing to script (no complex inline bash)
- **Proper logging**: x11vnc logs to `/var/log/x11vnc_manual.log`, XFCE to `/home/ubuntu/xfce_start.log`

## Current Status
✅ **Service Active**: `auraos-x11vnc.service` running and enabled  
✅ **Xvfb Running**: Display :1 at 1280x720x24  
✅ **x11vnc Running**: Port 5900, client-side caching disabled  
✅ **XFCE Running**: xfce4-session, xfwm4, xfce4-panel all active  
✅ **Screenshot Verified**: 222KB PNG captured via agent (real desktop content)

## Verification Commands
```bash
# Check service status
multipass exec auraos-multipass -- sudo systemctl status auraos-x11vnc.service

# Check running processes
multipass exec auraos-multipass -- ps aux | egrep 'Xvfb|x11vnc|xfce4-session|xfwm4|xfce4-panel' | grep -v grep

# Check logs
multipass exec auraos-multipass -- sudo tail -n 100 /var/log/x11vnc_manual.log
multipass exec auraos-multipass -- sudo tail -n 100 /home/ubuntu/xfce_start.log

# Capture screenshot
curl -sS http://localhost:8765/screenshot -o /tmp/test_screenshot.png
```

## Access Methods
1. **VNC Direct**: `vnc://localhost:5901` (password: `auraos123`)
2. **noVNC Browser**: `http://localhost:6080/vnc.html`
3. **Agent API**: `http://localhost:8765/screenshot`

## Troubleshooting

### If service fails to start
```bash
# Check logs
multipass exec auraos-multipass -- sudo journalctl -u auraos-x11vnc.service -n 100 --no-pager

# Kill any manual processes
multipass exec auraos-multipass -- sudo pkill -9 x11vnc
multipass exec auraos-multipass -- sudo pkill -9 Xvfb

# Restart service
multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service
```

### If XFCE session missing
```bash
# Manually start XFCE
multipass exec auraos-multipass -- sudo -u ubuntu bash -c "DISPLAY=:1 dbus-launch --exit-with-session startxfce4 >/home/ubuntu/xfce_start.log 2>&1 &"

# Wait 5s and verify
sleep 5
multipass exec auraos-multipass -- ps aux | grep xfce4-session
```

### If black screen persists
1. Press Alt+Alt+Alt (three times) in VNC viewer to force x11vnc repaint
2. Resize VNC viewer window to trigger refresh
3. Check if client-side caching is re-enabled (should be `-ncache 0`)

## Notes
- The script is idempotent - safe to run multiple times
- XFCE will refuse to start if already running (expected behavior)
- x11vnc will fail if port 5900 is in use (kill existing instance first)
- Service survives VM reboots (enabled via systemd)
