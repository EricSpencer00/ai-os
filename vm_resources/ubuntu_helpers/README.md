# Ubuntu VM Helper Scripts

Collection of shell scripts for automating the AuraOS Ubuntu VM desktop environment.

## Scripts

### Desktop Management

**`ensure_desktop.sh`** - Ensure XFCE desktop session is running
```bash
sudo ./ensure_desktop.sh
```
- Checks if XFCE session is running
- Starts Xvfb and XFCE if needed
- Can be run via cron or systemd timer for auto-recovery

**`start_xvfb_xfce_x11vnc.sh`** - Main startup script (used by systemd)
```bash
sudo ./start_xvfb_xfce_x11vnc.sh
```
- Starts Xvfb on DISPLAY :1
- Ensures XFCE session is running
- Starts x11vnc server
- Used by `auraos-x11vnc.service`

### Screen Automation

**`screenshot.sh`** - Capture screenshot
```bash
./screenshot.sh [output.png]
```
- Captures screenshot from DISPLAY :1
- Auto-generates filename if not provided
- Requires ImageMagick

**`click_at.sh`** - Click at coordinates
```bash
./click_at.sh X Y [button]
```
- X, Y: pixel coordinates
- button: 1 (left), 2 (middle), 3 (right)
- Uses xdotool

**`type_text.sh`** - Type text
```bash
./type_text.sh "Hello, world!"
```
- Types text with keyboard simulation
- 100ms delay between characters

### Setup

**`install_packages.sh`** - Install automation tools
```bash
sudo ./install_packages.sh
```
- Installs automation tools (xdotool, imagemagick, etc.)
- Installs browsers (Firefox, Chromium)
- Installs Python packages for vision/OCR

## Installation

Copy to VM:
```bash
multipass transfer vm_resources/ubuntu_helpers/* auraos-multipass:/tmp/
multipass exec auraos-multipass -- sudo mkdir -p /opt/auraos/bin
multipass exec auraos-multipass -- sudo mv /tmp/*.sh /opt/auraos/bin/
multipass exec auraos-multipass -- sudo chmod +x /opt/auraos/bin/*.sh
```

## Integration with Host

From the host (macOS), you can run these via multipass:

```bash
# Ensure desktop is running
multipass exec auraos-multipass -- sudo /opt/auraos/bin/ensure_desktop.sh

# Take screenshot
multipass exec auraos-multipass -- /opt/auraos/bin/screenshot.sh /tmp/screen.png
multipass exec auraos-multipass -- cat /tmp/screen.png > /tmp/vm_screenshot.png

# Click at coordinates
multipass exec auraos-multipass -- /opt/auraos/bin/click_at.sh 640 360

# Type text
multipass exec auraos-multipass -- /opt/auraos/bin/type_text.sh "Hello from host"
```

## Systemd Integration

Create a timer to ensure desktop stays alive:

```bash
# /etc/systemd/system/auraos-desktop-check.service
[Unit]
Description=Check and restart XFCE desktop if needed
After=auraos-x11vnc.service

[Service]
Type=oneshot
ExecStart=/opt/auraos/bin/ensure_desktop.sh

# /etc/systemd/system/auraos-desktop-check.timer
[Unit]
Description=Check XFCE desktop every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now auraos-desktop-check.timer
```

## API Integration

The Flask GUI agent at `http://localhost:8765` provides REST endpoints that use these scripts internally:

- `GET /health` - Check if agent is running
- `GET /screenshot` - Capture screenshot (PNG)
- `POST /click` - Click at coordinates
- `POST /type` - Type text

See `/opt/auraos/gui_agent/agent.py` for implementation details.
