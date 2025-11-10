# AuraOS Desktop Access Guide

**Status:** ✅ **FULLY OPERATIONAL**  
**Date:** November 9, 2025

---

## Overview

AuraOS now boots directly to the XFCE desktop without requiring login. The system is configured to:
- Automatically start XFCE desktop on boot
- Disable screensaver and lock screens
- Provide immediate VNC access to the desktop environment

---

## Access Methods

### 1. Browser (Recommended)
**URL:** `http://localhost:6080/vnc.html`  
**Password:** `auraos123`

This connects to noVNC, a web-based VNC client that runs in your browser.

**Steps:**
1. Open browser to http://localhost:6080/vnc.html
2. You should see the XFCE desktop immediately
3. No login required - desktop is already running

### 2. Native VNC Client
**Address:** `vnc://localhost:5901`  
**Password:** `auraos123`

Use any VNC client (TightVNC, RealVNC, Remmina, etc.)

**Steps:**
1. Open your VNC client
2. Connect to localhost:5901
3. Enter password: auraos123
4. You'll see the XFCE desktop

---

## System Architecture

```
Your Mac (macOS)
    ├─ Port 5901 (host) → Port 5900 (VM) [Native VNC]
    ├─ Port 6080 (host) → Port 6080 (VM) [noVNC Web]
    └─ Browser: http://localhost:6080/vnc.html
        ↓
    Multipass VM (Ubuntu 22.04)
        ├─ Xvfb Display :1 (1280x720x24)
        │  └─ XFCE Desktop Session
        │     ├─ xfce4-session (window manager)
        │     ├─ xfwm4 (window decorator)
        │     ├─ xfce4-panel (taskbar)
        │     └─ xfdesktop (background/icons)
        ├─ x11vnc Server (port 5900)
        └─ noVNC WebSocket Proxy (port 6080)
```

---

## Desktop Configuration

### Display Server
- **Type:** Xvfb (virtual framebuffer)
- **Display:** :1
- **Resolution:** 1280x720x24
- **Color Depth:** 24-bit

### Desktop Environment
- **Name:** XFCE 4
- **Status:** Auto-starting on boot
- **User:** ubuntu
- **Screensaver:** Disabled
- **Lock Screen:** Disabled
- **Power Management:** Disabled (no auto-blank, no auto-lock)

### VNC Configuration
- **VNC Server:** x11vnc
- **Port (VM):** 5900
- **Port (Host):** 5901 (via forwarder)
- **Authentication:** VNC password (auraos123)
- **Shared Mode:** Enabled (multiple connections allowed)
- **Features:** No damage detection, no wait-for-cursor, no cache

### Web Access
- **Proxy:** noVNC WebSocket proxy (websockify)
- **Port (VM):** 6080
- **Port (Host):** 6080 (via forwarder)
- **Type:** Web browser compatible

---

## Troubleshooting

### "Connection Refused" on Port 5901/6080

**Solution:** Start the port forwarders
```bash
./auraos.sh forward start
```

### Black Screen or No Content

**Solution:** The desktop might have locked. Restart the x11vnc service:
```bash
./auraos.sh gui-reset
```

Or manually inside the VM:
```bash
multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service
```

### Screen Shows Login Prompt

**Solution:** This shouldn't happen with the updated startup script, but if it does:
```bash
./auraos.sh gui-reset
```

This will:
1. Stop all VNC services
2. Kill any lingering XFCE/screensaver processes
3. Reconfigure VNC settings
4. Start fresh XFCE session
5. Restart VNC server

### Need to Log In with SSH

If you need SSH access to the VM:
```bash
# The VM is at 192.168.2.9
ssh ubuntu@192.168.2.9

# Or through Multipass
multipass shell auraos-multipass
```

**SSH Credentials:**
- Username: ubuntu
- Password: auraos123

---

## Key Features

✅ **No Login Required** - Desktop boots directly to XFCE  
✅ **Persistent Desktop** - Desktop stays active across connections  
✅ **Multiple Connections** - Can connect from multiple VNC clients simultaneously  
✅ **Web Access** - No special software needed, works from any browser  
✅ **Native VNC Support** - Full VNC protocol support for all clients  
✅ **Auto-Recovery** - Health check can auto-restart services if needed  

---

## System Information

**VM Details:**
- **Hostname:** auraos-multipass
- **IP Address:** 192.168.2.9
- **OS:** Ubuntu 22.04 LTS
- **Architecture:** ARM64 (compatible with Apple Silicon)

**Desktop Environment:**
- **WM:** Xfwm4 (Xfce window manager)
- **Panel:** xfce4-panel
- **Terminal:** xfce4-terminal
- **File Manager:** Thunar

---

## Next Steps

1. **Access the desktop:**
   ```bash
   # Browser
   http://localhost:6080/vnc.html
   ```

2. **Run automation tasks:**
   ```bash
   ./auraos.sh automate "click on Firefox"
   ```

3. **Capture screenshots:**
   ```bash
   ./auraos.sh screenshot
   ```

4. **Check system health:**
   ```bash
   ./auraos.sh health
   ```

---

## Support Commands

| Task | Command |
|------|---------|
| Start port forwarders | `./auraos.sh forward start` |
| Stop port forwarders | `./auraos.sh forward stop` |
| Check forwarder status | `./auraos.sh forward status` |
| Restart desktop services | `./auraos.sh gui-reset` |
| View system health | `./auraos.sh health` |
| Take screenshot | `./auraos.sh screenshot` |
| View logs | `./auraos.sh logs` |
| SSH into VM | `multipass shell auraos-multipass` |

---

**For more information, see:**
- `README.md` - Main documentation
- `QUICKSTART.md` - Quick start guide
- `SETUP_VERIFICATION.md` - System verification report
