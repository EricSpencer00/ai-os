# AuraOS Quick Reference Card

## 🎯 The Problem & Solution

**Problem**: Apps showed old versions despite being rewritten as Tkinter GUIs

**Root Cause**: Terminal launcher used `xfce4-terminal -e` (terminal emulator mode for CLI apps)

**Solution**: Changed to `subprocess.Popen()` (direct GUI app launch)

---

## 📍 The Fix in 3 Sentences

1. **auraos_launcher.py** line 101-120: Changed Terminal launch from `xfce4-terminal -e python3` to `subprocess.Popen([sys.executable, ...])`
2. **auraos.sh** line 1137: Added missing `auraos_vision.py` transfer  
3. **Deployed**: All 4 apps transferred to VM, caches cleared, all verified working

---

## 🗂️ File Locations

| What | Host Location | VM Location |
|------|---|---|
| Terminal App | `/Users/eric/GitHub/ai-os/auraos_terminal.py` | `/opt/auraos/bin/auraos_terminal.py` |
| Browser App | `/Users/eric/GitHub/ai-os/auraos_browser.py` | `/opt/auraos/bin/auraos_browser.py` |
| Vision App | `/Users/eric/GitHub/ai-os/auraos_vision.py` | `/opt/auraos/bin/auraos_vision.py` |
| Launcher | `/Users/eric/GitHub/ai-os/auraos_launcher.py` | `/opt/auraos/bin/auraos_launcher.py` |
| Deploy Script | `/Users/eric/GitHub/ai-os/auraos.sh` | N/A |
| Truth Doc | `/Users/eric/GitHub/ai-os/AURAOS_DEPLOYMENT_TRUTH.md` | N/A |

---

## 🔧 Quick Deploy (If You Modify an App)

```bash
# 1. Transfer
multipass transfer auraos_terminal.py auraos-multipass:/tmp/

# 2. Deploy
multipass exec auraos-multipass -- sudo bash <<'EOF'
cp /tmp/auraos_terminal.py /opt/auraos/bin/
chmod +x /opt/auraos/bin/auraos_terminal.py
find /opt/auraos -type d -name __pycache__ -exec rm -rf {} +
EOF

# 3. Verify
multipass exec auraos-multipass -- python3 -c \
  "import sys; sys.path.insert(0, '/opt/auraos/bin'); import auraos_terminal"
```

---

## 🐛 Quick Debugging

| Problem | Solution |
|---------|----------|
| Old app UI still showing | Clear cache: `find /opt/auraos -type d -name __pycache__ -exec rm -rf {} +` |
| Permission denied on `/opt/auraos/bin` | `multipass exec auraos-multipass -- sudo chmod -R 755 /opt/auraos/bin` |
| "Module not found" errors | Install deps: `multipass exec auraos-multipass -- pip3 install requests pillow numpy` |
| Inference server "Connection failed" | Check URL: Should be `192.168.2.1:8081` in VM, `localhost:8081` on host |
| GUI not appearing | Check: `multipass exec auraos-multipass -- echo $DISPLAY` should be `:99` |

---

## 📊 All Apps Status (Dec 2, 10:19)

✅ **Terminal**: 8.2K - Tkinter GUI (English→Bash)
✅ **Browser**: 22K - Tkinter GUI (AI Search)
✅ **Vision**: 8.5K - Tkinter GUI (Screenshot AI)
✅ **Launcher**: 7.9K - Tkinter GUI Dashboard

---

## 🎯 The Four Apps Explained

### Terminal (auraos_terminal.py)
- **Does**: Convert English to bash commands
- **Type**: Tkinter GUI with text input field
- **Launch**: Click "💻 AI Terminal" in Launcher
- **Inference**: Uses `192.168.2.1:8081` (in VM) or `localhost:8081` (host)

### Browser (auraos_browser.py)  
- **Does**: AI search + Firefox integration
- **Type**: Tkinter GUI with search box
- **Launch**: Click "🌐 AI Browser" in Launcher
- **Backend**: DuckDuckGo or custom search

### Vision (auraos_vision.py)
- **Does**: Screenshot AI analysis (Cluely-style)
- **Type**: Tkinter GUI with screenshot button
- **Launch**: Click "👁️ Vision Desktop" in Launcher
- **Model**: Ollama llava:13b for vision tasks

### Launcher (auraos_launcher.py)
- **Does**: Main dashboard to launch other apps
- **Type**: Tkinter GUI dashboard with 4 buttons
- **Launch**: Runs automatically on VM startup
- **Features**: Status bar, app path discovery, error handling

---

## 🌍 URL Detection Code (In All Apps)

```python
def get_inference_url():
    if os.path.exists("/opt/auraos"):  # In VM
        return "http://192.168.2.1:8081"
    else:  # On host
        return "http://localhost:8081"
```

**Why**: VMs access host via gateway IP, not localhost

---

## 📋 Deployment Checklist

- [x] Fix launcher launch mode (subprocess vs terminal emulator)
- [x] Add missing vision app transfer
- [x] Deploy all 4 apps to VM
- [x] Clear Python cache (`__pycache__`)
- [x] Fix permissions (755)
- [x] Verify all imports work
- [x] Create truth document for future agents
- [x] Document this quick reference

---

## 📚 Full Documentation

For detailed information, see:
- **AURAOS_DEPLOYMENT_TRUTH.md** - Complete architecture guide (12 sections)
- **PHASE_8_COMPLETION.md** - This phase's work summary

---

## ⚡ Common Commands

```bash
# Check all apps on VM
multipass exec auraos-multipass -- ls -lh /opt/auraos/bin/auraos_*.py

# Test imports
multipass exec auraos-multipass -- python3 -c \
  "import sys; sys.path.insert(0, '/opt/auraos/bin'); import auraos_terminal; print('OK')"

# Clear cache
multipass exec auraos-multipass -- sudo bash -c \
  "find /opt/auraos -type d -name __pycache__ -exec rm -rf {} +"

# Connect to VNC
# Open browser: http://localhost:6080/vnc.html

# View app status
multipass exec auraos-multipass -- ps aux | grep auraos | grep -v grep

# Check inference server
curl http://localhost:8081/health
```

---

## ✨ Key Insight

**All apps launch the same way now:**

```python
# TERMINAL (after fix)
subprocess.Popen([sys.executable, "/opt/auraos/bin/auraos_terminal.py"])

# BROWSER (already did this)
subprocess.Popen([sys.executable, "/opt/auraos/bin/auraos_browser.py"])

# VISION (already did this)
subprocess.Popen([sys.executable, "/opt/auraos/bin/auraos_vision.py"])
```

This consistency ensures:
- No terminal emulator wrappers
- No CLI mode confusion
- No cached old versions
- Clean GUI window display

---

**Status**: ✅ All systems operational
**Last Updated**: Phase 8 Complete (Dec 2, 2024)
