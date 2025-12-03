# AuraOS Application Deployment & Architecture Guide

**Document Purpose**: This guide explains how AuraOS applications are deployed, launched, and why certain architectural decisions were made. Future AI agents should reference this when working on app fixes or enhancements.

**Last Updated**: December 2, 2024 by GitHub Copilot (Claude Haiku 4.5)

---

## 1. System Architecture Overview

### Environment

- **Host Machine**: macOS with Multipass installed
- **Virtual Machine**: Ubuntu 22.04 LTS running in Multipass (`auraos-multipass`)
- **VM Gateway IP**: `192.168.2.1` (accessed from within the VM as the host)
- **Localhost on VM**: Maps to host at `192.168.2.1`
- **VM User**: `auraos` (configured in `auraos.sh` line ~600)
- **Display Server**: Xvfb on port `:99` (accessed via VNC on port `6080`)

### Key Services

| Service | Port (Host) | Port (VM) | Purpose |
|---------|------------|----------|---------|
| Inference Server | `localhost:8081` | `192.168.2.1:8081` | LLM/Vision AI model requests |
| GUI Agent API | `localhost:8765` | `192.168.2.1:8765` | Desktop automation via Flask |
| VNC Server | N/A | `:99` (display) | Virtual desktop at `http://localhost:6080/vnc.html` |

### Critical Environment Detection

**Apps must detect if they're running in VM or locally:**

```python
def get_inference_url():
    """Return the correct inference server URL based on environment"""
    if os.path.exists("/opt/auraos"):  # VM marker
        return "http://192.168.2.1:8081"
    else:
        return "http://localhost:8081"
```

This is implemented in: `auraos_terminal.py`, `auraos_vision.py`, `auraos_browser.py`

---

## 2. Application Architecture

### The Four Main Applications

#### 2.1 AuraOS Terminal (`auraos_terminal.py`)

**Purpose**: Convert English natural language into bash commands and execute them

**Type**: Tkinter GUI (since Phase 7 - all apps are GUI for VM)

**Key Features**:
- English-to-bash conversion via inference server
- Real-time command output display
- Threading to prevent UI freezing during inference calls
- Status bar showing "Ready", "Converting...", "Executing..."

**Entry Point**:
```python
if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSTerminal(root)
    root.mainloop()
```

**Critical Code Pattern**:
```python
def get_inference_url():
    if os.path.exists("/opt/auraos"):
        return "http://192.168.2.1:8081"  # VM uses gateway IP
    return "http://localhost:8081"
```

#### 2.2 AuraOS Browser (`auraos_browser.py`)

**Purpose**: AI-powered web search and Firefox integration

**Type**: Tkinter GUI

**Key Features**:
- Search interface with AI enhancement
- Direct Firefox launch via `subprocess`
- DuckDuckGo or custom search backend
- Status indicators

#### 2.3 AuraOS Vision (`auraos_vision.py`)

**Purpose**: Screenshot-based AI assistant (Cluely-style interface)

**Type**: Tkinter GUI

**Key Features**:
- Screenshot capture via `PIL.ImageGrab` (on display `:99`)
- Base64 encoding for AI transmission
- Image analysis via Ollama `llava:13b` model
- Interaction prompts for AI reasoning

**Critical Import**:
```python
from PIL import ImageGrab  # Requires DISPLAY=:99
```

#### 2.4 AuraOS Launcher (`auraos_launcher.py`)

**Purpose**: Main dashboard that launches other applications

**Type**: Tkinter GUI Dashboard

**Key Features**:
- Buttons for Terminal, Browser, Vision, Settings
- Dynamic app path discovery via `find_app_path()`
- Status bar with launch feedback
- Error handling and fallbacks

---

## 3. Deployment Pipeline

### 3.1 How Apps Get to the VM

```bash
# In auraos.sh (lines 1133-1140):
multipass transfer auraos_terminal.py "$VM_NAME:/tmp/auraos_terminal.py"
multipass transfer auraos_browser.py "$VM_NAME:/tmp/auraos_browser.py"
multipass transfer auraos_vision.py "$VM_NAME:/tmp/auraos_vision.py"
multipass transfer auraos_launcher.py "$VM_NAME:/tmp/auraos_launcher.py"
multipass transfer gui_agent.py "$VM_NAME:/tmp/gui_agent.py"
```

### 3.2 How Apps Get Installed on VM

**In auraos.sh (lines 1155-1180)**, inside the `AURAOS_APPS` heredoc:

```bash
# Copy from /tmp to final location
if [ -f /tmp/auraos_terminal.py ]; then
    cp /tmp/auraos_terminal.py /opt/auraos/bin/auraos_terminal.py
    chmod +x /opt/auraos/bin/auraos_terminal.py
fi
# ... (similar for browser, vision, launcher)
```

**Result**: `/opt/auraos/bin/` contains all executable app files

### 3.3 How Apps Are Launched from Launcher

In `auraos_launcher.py`:

```python
def find_app_path(app_name):
    """Find app in order of preference"""
    search_paths = [
        os.path.join(script_dir, app_name),        # Same dir as launcher
        os.path.join("/opt/auraos/bin", app_name), # VM install location
        os.path.join(os.path.expanduser("~"), "auraos", app_name),
    ]
    for path in search_paths:
        if os.path.exists(path):
            return path
    return None

def launch_terminal(self):
    terminal_path = find_app_path("auraos_terminal.py")
    if terminal_path:
        subprocess.Popen(
            [sys.executable, terminal_path],
            env=os.environ.copy(),
            start_new_session=True
        )
```

**Key Point**: Terminal is launched as a **GUI app with subprocess.Popen**, NOT in a terminal emulator!

---

## 4. Critical Issues & Solutions

### Issue 1: Python Cache Stale Code

**Problem**: Old `.pyc` files in `__pycache__` directories prevent new code from loading

**Solution**: 
```bash
# Clear all caches after deployment
find /opt/auraos -type d -name __pycache__ -exec rm -rf {} +
find /opt/auraos -type f -name "*.pyc" -delete
```

**Prevention**:
```bash
# In auraos.sh or deployment scripts:
export PYTHONDONTWRITEBYTECODE=1
```

### Issue 2: Permissions Denied on /opt/auraos/bin

**Problem**: Files copied as root can't be modified by auraos user

**Solution**:
```bash
multipass exec auraos-multipass -- sudo bash <<'EOF'
chmod -R 755 /opt/auraos/bin
chown -R auraos:auraos /opt/auraos/bin
EOF
```

### Issue 3: Wrong URL in VM Apps

**Problem**: Apps tried to use `localhost:8081` from within VM, but host is at `192.168.2.1`

**Solution**: 
```python
if os.path.exists("/opt/auraos"):  # Running in VM
    url = "http://192.168.2.1:8081"
else:
    url = "http://localhost:8081"
```

**Why**: Multipass VMs access host services via the gateway IP, not localhost

### Issue 4: Terminal Launching in Wrong Mode

**Problem**: The launcher was trying to launch Terminal with `xfce4-terminal -e python3 app.py`
- This expected a CLI app
- But the new Terminal is a GUI app
- This caused the old cached CLI version to run instead

**Solution**: 
Change launcher to use `subprocess.Popen([sys.executable, app.py])` like Browser and Vision

**File**: `auraos_launcher.py` lines 101-120

**Commit**: Changed from terminal emulator flag `-e` to direct Python subprocess execution

---

## 5. How to Deploy App Changes

### Quick Deploy (for development)

```bash
#!/bin/bash
# From /Users/eric/GitHub/ai-os

# 1. Transfer files
multipass transfer auraos_terminal.py auraos-multipass:/tmp/
multipass transfer auraos_browser.py auraos-multipass:/tmp/
multipass transfer auraos_vision.py auraos-multipass:/tmp/
multipass transfer auraos_launcher.py auraos-multipass:/tmp/

# 2. Copy and clear cache
multipass exec auraos-multipass -- sudo bash <<'EOF'
cp /tmp/auraos_*.py /opt/auraos/bin/
chmod +x /opt/auraos/bin/auraos_*.py
find /opt/auraos -type d -name __pycache__ -exec rm -rf {} +
find /opt/auraos -type f -name "*.pyc" -delete
EOF

# 3. Test
multipass exec auraos-multipass -- bash <<'EOF'
export PYTHONDONTWRITEBYTECODE=1
python3 -c "import sys; sys.path.insert(0, '/opt/auraos/bin'); import auraos_terminal"
echo "✅ Deployment successful"
EOF
```

### Full Deploy (use auraos.sh)

```bash
cd /Users/eric/GitHub/ai-os
./auraos.sh setup  # Runs full setup including app transfer and deployment
```

---

## 6. File Locations Reference

| File | Host Location | VM Location | Purpose |
|------|---|---|---|
| Terminal App | `/Users/eric/GitHub/ai-os/auraos_terminal.py` | `/opt/auraos/bin/auraos_terminal.py` | English→Bash GUI |
| Browser App | `/Users/eric/GitHub/ai-os/auraos_browser.py` | `/opt/auraos/bin/auraos_browser.py` | AI Search GUI |
| Vision App | `/Users/eric/GitHub/ai-os/auraos_vision.py` | `/opt/auraos/bin/auraos_vision.py` | Screenshot AI GUI |
| Launcher | `/Users/eric/GitHub/ai-os/auraos_launcher.py` | `/opt/auraos/bin/auraos_launcher.py` | Main Dashboard |
| Deploy Script | `/Users/eric/GitHub/ai-os/auraos.sh` | N/A (runs on host) | Orchestration |
| GUI Agent | `/Users/eric/GitHub/ai-os/gui_agent.py` | `/opt/auraos/gui_agent/agent.py` | Desktop automation |
| Config | `/Users/eric/GitHub/ai-os/auraos_daemon/config.json` | `/opt/auraos/daemon/config.json` | Settings |

---

## 7. Debugging Common Issues

### Apps Show Old UI/Behavior

**Cause**: Python bytecode cache

**Fix**:
```bash
multipass exec auraos-multipass -- sudo bash <<'EOF'
find /opt/auraos -type d -name __pycache__ -exec rm -rf {} +
find /opt/auraos -type f -name "*.pyc" -delete
EOF
```

### "Module not found" Errors

**Cause**: Missing dependencies in VM

**Fix**:
```bash
multipass exec auraos-multipass -- bash <<'EOF'
pip3 install requests pillow numpy pyautogui --upgrade
EOF
```

### Inference Server Connection Failed

**Cause**: Wrong URL or server not running

**Fix**:
```bash
# On host, check if server is running
curl http://localhost:8081/health

# If not, start it:
ollama serve &

# From VM, verify you can reach host:
multipass exec auraos-multipass -- bash <<'EOF'
curl http://192.168.2.1:8081/health
EOF
```

### Apps Won't Launch from Launcher

**Cause**: Path not found or permissions

**Fix**:
```bash
# Check files exist
multipass exec auraos-multipass -- ls -lh /opt/auraos/bin/auraos_*.py

# Check executable bit
multipass exec auraos-multipass -- bash <<'EOF'
chmod +x /opt/auraos/bin/auraos_*.py
EOF

# Test import
multipass exec auraos-multipass -- bash <<'EOF'
export PYTHONDONTWRITEBYTECODE=1
python3 -c "import sys; sys.path.insert(0, '/opt/auraos/bin'); import auraos_terminal"
EOF
```

### Display/GUI Not Showing

**Cause**: DISPLAY variable not set or Xvfb not running

**Check**:
```bash
multipass exec auraos-multipass -- bash <<'EOF'
echo "DISPLAY is: $DISPLAY"
ps aux | grep -i xvfb | grep -v grep
ps aux | grep -i vnc | grep -v grep
EOF
```

---

## 8. Testing Checklist for Future Agents

When you modify any app:

- [ ] Modify the app file on host (`/Users/eric/GitHub/ai-os/auraos_*.py`)
- [ ] Test syntax: `python3 -m py_compile auraos_terminal.py`
- [ ] Transfer to VM: `multipass transfer auraos_terminal.py auraos-multipass:/tmp/`
- [ ] Deploy to final location: `multipass exec auraos-multipass -- sudo bash -c "cp /tmp/auraos_terminal.py /opt/auraos/bin/ && chmod +x /opt/auraos/bin/auraos_terminal.py"`
- [ ] Clear cache: `multipass exec auraos-multipass -- sudo bash -c "find /opt/auraos -type d -name __pycache__ -exec rm -rf {} +"`
- [ ] Test import: `multipass exec auraos-multipass -- python3 -c "import sys; sys.path.insert(0, '/opt/auraos/bin'); import auraos_terminal"`
- [ ] Connect VNC and test in GUI
- [ ] Click app button in Launcher
- [ ] Verify new UI/behavior appears

---

## 9. Architecture Decisions & Rationale

### Why All Apps Are Tkinter GUI

**Reason**: Apps run inside a VM with a display server. CLI apps would require terminal emulators, making them harder to launch and control from the Launcher dashboard. Tkinter provides:
- Cross-platform GUI framework
- No heavy dependencies
- Easy subprocess launch
- Direct window display on `:99`

### Why Three-Location App Search

```python
search_paths = [
    os.path.join(script_dir, app_name),              # Dev/testing
    os.path.join("/opt/auraos/bin", app_name),      # Installed
    os.path.join(os.path.expanduser("~"), "auraos", app_name),  # User
]
```

**Reason**: Flexibility for different deployment scenarios:
- **Same dir**: Developer running launcher directly from `/Users/eric/GitHub/ai-os/`
- **Installed**: Production deployment from `/opt/auraos/bin/`
- **User home**: User-customized apps in `~/auraos/`

### Why Multipass + VNC

**Reason**: 
- Multipass provides lightweight VM isolation
- Xvfb + VNC allows remote GUI access
- Doesn't require full desktop environment like KVM
- Easy transfer of files between host and VM
- Can be accessed from web browser

---

## 10. Recent Fixes (Phase 7-8)

### Fixed in Phase 7

1. **Tkinter Conversion**: All apps converted from CLI/custom to full Tkinter GUI
2. **Launcher Update**: Modified `launch_vision_os()` to launch app directly
3. **Cache Clearing**: Implemented systematic cache clearing after deployment

### Fixed in Phase 8 (Current)

1. **Terminal Launch Mode**: Changed from terminal emulator (`xfce4-terminal -e`) to direct GUI subprocess launch
2. **Vision Transfer**: Added missing `auraos_vision.py` transfer in `auraos.sh`
3. **Vision Installation**: Added vision.py copy logic in AURAOS_APPS section
4. **Root Cause**: Terminal was being launched as CLI in terminal emulator, which used cached old version

**Result**: All apps now launch as proper Tkinter GUI windows directly from launcher

---

## 11. Quick Reference for Future AI Agents

**You are working on AuraOS. Here's what you need to know:**

1. **Four apps**: Terminal, Browser, Vision, Launcher (all Tkinter GUI)
2. **Two URLs**: Host uses `localhost:8081`, VM uses `192.168.2.1:8081` (use `/opt/auraos` check)
3. **Two locations**: Host dev files in `/Users/eric/GitHub/ai-os/`, VM files in `/opt/auraos/bin/`
4. **Two enemies**: Python cache (`__pycache__`) and permissions (use `sudo`)
5. **Two modes**: Transfer to `/tmp/`, then copy to `/opt/auraos/bin/` with sudo

**When apps don't work:**
1. Check if it's cache (clear it)
2. Check if it's permissions (chmod 755)
3. Check if it's URL (verify `/opt/auraos` exists)
4. Check if it's launcher mode (should be subprocess, not terminal)

**When deploying changes:**
- Transfer file → sudo copy to /opt/auraos/bin → clear cache → test import

---

## 12. Contact Information

**Last Fixed By**: GitHub Copilot (Claude Haiku 4.5)

**If you break anything**: 
- Check the deployment pipeline section (3.1-3.3)
- Follow the testing checklist (section 8)
- Reference the debugging section (section 7)
- The most common issue is Python cache - clear it first
- The second most common issue is launcher launch mode - check if using subprocess vs terminal emulator
