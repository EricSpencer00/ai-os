# AuraOS Installation & Setup Guide

**Status:** ✅ **FULLY INTEGRATED INTO auraos.sh**  
**Last Updated:** November 9, 2025

---

## Quick Start (3 Commands)

```bash
# 1. Install all dependencies
./auraos.sh install

# 2. Create AuraOS VM with everything pre-configured
./auraos.sh vm-setup

# 3. Verify system is operational
./auraos.sh health
```

Then open your browser to: **http://localhost:6080/vnc.html**  
Password: **auraos123**

---

## What Gets Installed

### Step 1: System Dependencies (`./auraos.sh install`)

**On macOS:**
- ✅ Homebrew (package manager)
- ✅ Multipass (VM manager)
- ✅ Ollama (local LLM runtime)
- ✅ LLaVA 13B vision model (8GB)
- ✅ Python 3.14 virtual environment
- ✅ All required Python packages

**Prerequisites:**
- macOS 11+ with Apple Silicon (M1/M2/M3)
- 8GB RAM minimum (4GB for VM)
- 30GB free disk space

### Step 2: VM Setup (`./auraos.sh vm-setup`)

**In Ubuntu VM (5 Automated Steps):**

1. **Desktop Environment Installation**
   - ✅ XFCE4 desktop (lightweight, customizable)
   - ✅ XFCE4 extensions and utilities
   - ✅ Applications (firefox, file manager, etc.)

2. **Virtual Display Server**
   - ✅ Xvfb (virtual framebuffer)
   - ✅ Display :1 at 1280x720x24
   - ✅ X11 libraries for GUI apps

3. **VNC Server Setup**
   - ✅ x11vnc (VNC server)
   - ✅ Password authentication (auraos123)
   - ✅ Port 5900 listening
   - ✅ systemd service enabled

4. **Web Interface**
   - ✅ noVNC (web-based VNC)
   - ✅ websockify (websocket proxy)
   - ✅ Port 6080 listening
   - ✅ Browser-accessible

5. **AuraOS Applications** ⭐ NEW
   - ✅ **AuraOS Terminal** - AI-powered command interface
   - ✅ **AuraOS Home Screen** - Custom branded dashboard
   - ✅ **Terminal Launcher** - `auraos-terminal` command
   - ✅ **Home Launcher** - `auraos-home` command

6. **AuraOS Branding Configuration** ⭐ NEW
   - ✅ Hostname set to "auraos"
   - ✅ Dark blue AuraOS theme (#0a0e27)
   - ✅ Cyan accent color (#00d4ff)
   - ✅ Screensaver disabled
   - ✅ Lock screen disabled
   - ✅ Custom desktop background
   - ✅ Desktop shortcuts
   - ✅ Autostart home screen

---

## Detailed Installation Flow

### `./auraos.sh install` Flow

```
✓ Check for macOS
  ↓
✓ Verify Homebrew installed
  ↓
✓ Install Multipass VM manager
  ↓
✓ Install Ollama local LLM
  ↓
✓ Start Ollama service
  ↓
✓ Download llava:13b model (8GB)
  ↓
✓ Create Python 3.14 virtual environment
  ↓
✓ Install Python dependencies
  ↓
✓ Configure Ollama for vision tasks
  ↓
[COMPLETE] Ready for ./auraos.sh vm-setup
```

**Time:** ~10-15 minutes (mostly model download)

### `./auraos.sh vm-setup` Flow

```
✓ Create Ubuntu 22.04 VM
  • 2 CPUs, 4GB RAM, 20GB disk
  ↓
✓ Install desktop environment
  • XFCE4, X11, applications
  ↓
✓ Install VNC server
  • Xvfb, x11vnc, authentication
  ↓
✓ Install noVNC web interface
  • Clone noVNC repository
  • Setup websockify proxy
  ↓
✓ Configure systemd services [STEP 4/7] ⭐ UPDATED
  • auraos-x11vnc.service
  • auraos-novnc.service
  • auraos-gui-agent.service
  ↓
✓ Setup VNC authentication [STEP 5/7]
  • Password: auraos123
  ↓
✓ Install AuraOS applications [STEP 6/7] ⭐ NEW
  • Install Python3-tk (GUI framework)
  • Install speech_recognition & pyaudio
  • Create /opt/auraos/bin/ directory
  • Install auraos-terminal.py
  • Install auraos-homescreen.py
  • Create command launchers
  ↓
✓ Configure AuraOS branding [STEP 7/7] ⭐ NEW
  • Set hostname to "auraos"
  • Configure XFCE desktop
  • Disable screensaver/lock
  • Set dark blue background
  • Create desktop shortcuts
  • Setup autostart
  ↓
✓ Start all services
  ↓
✓ Setup port forwarding
  • localhost:5901 → VM:5900
  • localhost:6080 → VM:6080
  ↓
[COMPLETE] Desktop ready at localhost:6080
```

**Time:** ~5-10 minutes

---

## Command Reference

### Installation & Setup

```bash
# First-time setup (full installation)
./auraos.sh install

# Create/setup VM
./auraos.sh vm-setup

# Verify all systems working
./auraos.sh health
```

### Port Forwarding Management

```bash
# Start port forwarders (if not running)
./auraos.sh forward start

# Stop all forwarders
./auraos.sh forward stop

# Check forwarder status
./auraos.sh forward status
```

### System Management

```bash
# Show VM and service status
./auraos.sh status

# Complete desktop restart
./auraos.sh gui-reset

# View GUI agent logs
./auraos.sh logs

# Restart all VM services
./auraos.sh restart
```

### Applications

```bash
# Launch AuraOS Terminal (inside VM)
multipass shell auraos-multipass
auraos-terminal

# Launch Home Screen (inside VM)
auraos-home

# Launch Terminal in CLI mode
auraos-terminal --cli
```

---

## What You Get

### On Your Mac (Host)

| Component | Purpose | Command |
|-----------|---------|---------|
| auraos.sh | Main control script | `./auraos.sh <command>` |
| Virtual Env | Python packages | `source auraos_daemon/venv/bin/activate` |
| Port Forwarders | Network tunneling | Started automatically by health check |

### In the VM

| Component | Purpose | Access |
|-----------|---------|--------|
| XFCE Desktop | Desktop environment | VNC/Browser |
| x11vnc | VNC server | Port 5900 |
| noVNC | Web interface | Port 6080 |
| **AuraOS Terminal** ⭐ | AI command interface | `auraos-terminal` command |
| **AuraOS Home** ⭐ | Dashboard launcher | `auraos-home` or auto-launch |
| Ollama | Local LLM | Auto-started |
| LLaVA 13B | Vision model | Integrated with terminal |

---

## Access Your AuraOS Desktop

### Browser Access (Recommended)

```
URL:      http://localhost:6080/vnc.html
Password: auraos123
```

**Features:**
- Works in any web browser
- No software installation needed
- Keyboard and mouse support
- Copy/paste support

### Native VNC Client

```
Address:  vnc://localhost:5901
Password: auraos123
```

**Supported clients:**
- TightVNC (Windows, macOS, Linux)
- RealVNC Viewer (Windows, macOS, Linux)
- Remmina (Linux)
- Built-in VNC (macOS)
- Others

### SSH Access (Advanced)

```bash
# Get VM IP
multipass list

# SSH into VM
ssh ubuntu@<VM_IP>
# or
multipass shell auraos-multipass
```

---

## Desktop Experience

### On First Launch

1. **Browser opens** → noVNC loads
2. **AuraOS Home Screen appears** → Custom dashboard with quick actions
3. **Four main buttons:**
   - 🖥️ **Terminal** - Launch AuraOS Terminal
   - 📁 **Files** - Open file manager
   - 🌐 **Browser** - Open Firefox
   - ⚙️ **Settings** - System configuration

### Desktop Features

✅ **AuraOS Branding**
- Hostname: "auraos"
- Dark blue background (#0a0e27)
- Cyan accents (#00d4ff)

✅ **Applications**
- AuraOS Terminal (AI-powered)
- File manager (Thunar)
- Web browser (Firefox)
- Settings manager (XFCE4)

✅ **No Login Required**
- Boots directly to desktop
- Screensaver disabled
- Auto-launches home screen

✅ **Desktop Shortcuts**
- AuraOS Terminal
- AuraOS Home
- Standard XFCE shortcuts

---

## Verification Checklist

After running the setup, verify everything works:

```bash
# 1. Check installation
./auraos.sh install
# ✓ All tools installed
# ✓ Python venv created
# ✓ Model downloaded

# 2. Check VM creation
./auraos.sh vm-setup
# ✓ VM running
# ✓ All services started
# ✓ Desktop accessible

# 3. Check system health
./auraos.sh health
# ✓ All 7 checks passing
# ✓ Web server responding
# ✓ VNC server listening

# 4. Access desktop
# http://localhost:6080/vnc.html
# ✓ AuraOS Home Screen visible
# ✓ Buttons responsive
# ✓ Terminal launches
```

---

## Troubleshooting

### "Installation failed to install Multipass"

```bash
# Install manually
brew install multipass

# Try again
./auraos.sh install
```

### "VM not creating"

```bash
# Check Multipass status
multipass list

# Ensure enough disk space
df -h

# Free up space and retry
./auraos.sh vm-setup
```

### "Desktop shows Ubuntu instead of AuraOS"

```bash
# Restart VM services
./auraos.sh gui-reset

# Or manually restart
multipass restart auraos-multipass
```

### "Port forwarding not working"

```bash
# Start forwarders manually
./auraos.sh forward start

# Check status
./auraos.sh forward status

# If still failing, restart health check
./auraos.sh health
```

### "VNC password not working"

Password is **auraos123** (lowercase)
- ✓ Correct: `auraos123`
- ✗ Wrong: `auraos` (missing number)
- ✗ Wrong: `Auraos123` (wrong case)

---

## Reproducibility

### For Clean Setup on New Machine

```bash
# Clone repository
git clone https://github.com/EricSpencer00/ai-os.git
cd ai-os

# Make script executable
chmod +x auraos.sh

# Follow 3-step setup
./auraos.sh install    # ~15 mins
./auraos.sh vm-setup   # ~10 mins
./auraos.sh health     # Verify

# Open browser
# http://localhost:6080/vnc.html
```

### For Resetting/Reinstalling

```bash
# Complete clean restart
multipass delete -p auraos-multipass
./auraos.sh vm-setup

# Or just restart services
./auraos.sh gui-reset
```

---

## System Architecture

```
┌─────────────────────────────────────┐
│          Your Mac (macOS)           │
├─────────────────────────────────────┤
│  ./auraos.sh (control script)       │
│  Python 3.14 venv                   │
│  Ollama (LLM runtime)               │
│  Port Forwarders                    │
│    5901 ──→ VM:5900 (VNC)          │
│    6080 ──→ VM:6080 (noVNC)        │
│    8765 ──→ VM:8765 (GUI Agent)    │
└────────────┬────────────────────────┘
             │ Multipass VM
┌────────────▼────────────────────────┐
│  Ubuntu 22.04 LTS VM (192.168.2.9)  │
├─────────────────────────────────────┤
│  Desktop Environment (XFCE4)        │
│    • Xvfb :1 (1280x720x24)         │
│    • x11vnc (port 5900)             │
│    • noVNC (port 6080)              │
│  AuraOS Applications ⭐             │
│    • auraos-terminal                │
│    • auraos-homescreen              │
│  Ollama + LLaVA 13B                │
│  GUI Automation Agent               │
└─────────────────────────────────────┘
```

---

## Integration Points

All components are fully integrated:

✅ **auraos.sh** - Single entry point for all operations  
✅ **Installation** - Automatic dependency installation  
✅ **VM Setup** - Automated desktop and app installation  
✅ **Health Check** - Verifies all systems operational  
✅ **Port Forwarding** - Automatic network setup  
✅ **Terminal App** - Pre-installed in VM  
✅ **Home Screen** - Auto-launches on login  
✅ **Branding** - Complete AuraOS theming  
✅ **Documentation** - Comprehensive guides included  

---

## Next Steps

After setup completes:

1. **Access the desktop**
   ```
   http://localhost:6080/vnc.html
   Password: auraos123
   ```

2. **Click "Terminal" button** to launch AuraOS Terminal

3. **Try a command**
   ```
   $ ls
   $ pwd
   $ whoami
   ```

4. **Try an automation task**
   ```bash
   ./auraos.sh automate "click on the file manager"
   ```

5. **Check AI vision capabilities**
   ```bash
   ./auraos.sh screenshot
   ./auraos.sh automate "describe what's on screen"
   ```

---

**Everything is automated and reproducible via `./auraos.sh`**

For questions or issues, see documentation:
- Main: `README.md`
- Terminal: `AURAOS_TERMINAL.md`
- Home Screen: `AURAOS_HOMESCREEN.md`
- Desktop: `DESKTOP_ACCESS.md`
- Verification: `SETUP_VERIFICATION.md`
