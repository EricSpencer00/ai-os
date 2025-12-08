# 🧪 Phase 9 Testing Guide

## Quick Test Checklist

### Test 1: Vision Automation Prompt Improvement
**What was fixed:** AI now understands full desktop context and targets other apps instead of Vision window

**To test:**
```bash
# Start the launcher or VM
./auraos.sh launcher

# Or connect to VM via noVNC
open http://192.168.2.50:6080/vnc.html
```

1. Click "Vision" app
2. Enter task: `Open Firefox and search for hello`
3. Click "Auto" (Cluely Automation)
4. Observe:
   - ✓ Should click Firefox icon (not Vision window)
   - ✓ Firefox should open (may show snap error)
   - ✓ Automation should enter search text in Firefox
   - ✓ Should reach "done" status
   - ✗ If typing in Vision's task box → fix didn't work

**Expected Outcome:** Firefox opens, search is performed in browser (not Vision)

---

### Test 2: VM Setup Dependencies
**What was added:** Complete system + Python dependency installation

**To test on fresh VM:**
```bash
# Create fresh Multipass instance
multipass delete auraos-multipass  # if exists
./auraos.sh vm-setup

# Verify packages installed
multipass exec auraos-multipass -- bash -c '
  echo "=== System Packages ==="
  which xdotool && echo "✓ xdotool"
  which python3 && echo "✓ python3"
  python3 -m venv --help >/dev/null && echo "✓ venv"
  
  echo "=== Python Packages ==="
  python3 -c "import requests; print(\"✓ requests\")"
  python3 -c "import flask; print(\"✓ flask\")"
  python3 -c "import pyautogui; print(\"✓ pyautogui\")"
  python3 -c "import PIL; print(\"✓ pillow\")"
  python3 -c "import numpy; print(\"✓ numpy\")"
'
```

**Expected Output:** All packages installed (✓ marks shown)

---

### Test 3: GUI Agent Service
**What was fixed:** Service now has all required dependencies

**To test:**
```bash
# Check service status
multipass exec auraos-multipass -- systemctl status auraos-gui-agent

# Check if running on port 8765
multipass exec auraos-multipass -- netstat -tuln | grep 8765
# OR
curl -s http://192.168.2.50:8765/screenshot | file -

# Check logs for errors
multipass exec auraos-multipass -- tail -20 ~/.auraos/logs/gui_agent.log
```

**Expected:** Service running, port 8765 active, no "ModuleNotFoundError"

---

### Test 4: All 6 Apps End-to-End
**To verify comprehensive functionality:**

```
1. TERMINAL APP ✓
   - Execute: pwd
   - Execute: echo "hello world"
   - Should see output in terminal

2. BROWSER APP ✓ (with workaround)
   - Click "Open Firefox"
   - If snap error: click "Open in Terminal" button
   - Terminal should launch Firefox

3. VISION APP 🟡 (JUST FIXED)
   - Enter task: "Open Firefox"
   - Should click Firefox icon, not Vision window
   - Verify logs show correct clicks

4. FILES APP ❌ (to test)
   - Click "Files"
   - Should show file browser
   - Navigate to /home/auraos

5. SETTINGS APP ❌ (to test)
   - Click "Settings"
   - Should show configuration options

6. UBUNTU APP ❌ (to test)
   - Click "Ubuntu" 
   - Should show fallback desktop
```

---

## 📊 Success Criteria

✅ **Session Complete When:**
1. Vision automation clicks correct windows (not its own control panel)
2. VM setup script installs all dependencies without errors
3. All 6 apps respond to clicks and perform basic operations
4. No "ModuleNotFoundError" or "command not found" errors
5. GUI Agent service running on port 8765

---

## 🔍 Debugging Tips

**If Vision still types in its own box:**
- Check: `auraos_vision.py` lines 356-380 (automation prompt)
- Verify prompt mentions "Do NOT interact with AuraOS Vision window"
- Run: `grep -n "Do NOT interact" auraos_vision.py`

**If packages not installing:**
- Check VM setup script: `scripts/vm.sh` lines 30-45
- Run manually: `multipass exec auraos-multipass -- apt-get install -y xdotool`
- Check: `pip3 install requests flask pyautogui pillow numpy`

**If GUI Agent won't start:**
- Check logs: `multipass exec auraos-multipass -- tail -50 ~/.auraos/logs/gui_agent.log`
- Check python path: `multipass exec auraos-multipass -- which python3`
- Verify service: `multipass exec auraos-multipass -- systemctl status auraos-gui-agent`

---

## 📝 Files Changed This Session

1. **auraos_vision.py** (commit 906769b)
   - Enhanced automation prompt (lines 356-380)
   - Added logging for screenshot dimensions
   - Improved documentation

2. **scripts/vm.sh** (commit fef7865)
   - Added xdotool, python3-venv, python3-dev (line 32-36)
   - Added Python packages (line 144)
   - Added GUI Agent venv setup (lines 151-160)

3. **SESSION_IMPROVEMENTS_PHASE_9.md** (commit 80acea8)
   - Documentation of all changes and testing plan

---

## ⏭️ What's Next

After confirming tests pass:
1. Test remaining apps (Files, Settings, Ubuntu)
2. Create demo video of all 6 apps working
3. Mark as ready for distribution
4. Document any edge cases found during testing
