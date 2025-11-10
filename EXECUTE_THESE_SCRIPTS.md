# 🚀 START HERE: Complete Script Execution Guide

Run these scripts/commands in order. Each one has a specific purpose.

---

## Step 1: Clean Restart Everything (BEST OPTION)

**This is the recommended way to start from scratch.**

```bash
cd /Users/eric/GitHub/ai-os
./auraos_gui_restart.sh
```

**What it does:**
- Stops VNC services
- Kills orphaned processes
- Sets up VNC password
- Fixes noVNC configuration
- Starts all services
- Verifies everything works

**Time**: ~30 seconds

**Success indicators:**
```
✓ GUI Restart Complete!
✓ x11vnc listening on port 5900
✓ noVNC listening on port 6080
```

---

## Step 2: Open Browser

After Step 1 completes, open your browser and go to:

```
http://localhost:6080/vnc.html
```

---

## Step 3: Enter Password

When prompted by noVNC for a password:

```
auraos123
```

---

## Step 4: Verify You Can See the Desktop

You should see:
- ✅ A login prompt (VNC canvas)
- ✅ XFCE desktop (may be black/minimal)
- ❌ NOT a directory listing
- ❌ NOT an error message

---

## If the Script Fails: Manual Execution

If `./auraos_gui_restart.sh` doesn't work, run these commands one at a time:

### 1. Stop Services

```bash
multipass exec auraos-multipass -- sudo systemctl stop auraos-x11vnc.service auraos-novnc.service 2>/dev/null || true
sleep 2
```

### 2. Kill Processes

```bash
multipass exec auraos-multipass -- bash -c '
  sudo pkill -9 x11vnc 2>/dev/null || true
  sudo pkill -9 Xvfb 2>/dev/null || true
  sudo pkill -9 websockify 2>/dev/null || true
  sudo pkill -9 novnc_proxy 2>/dev/null || true
'
sleep 2
```

### 3. Setup VNC Password

```bash
multipass exec auraos-multipass -- sudo bash -c '
  mkdir -p /home/ubuntu/.vnc
  rm -f /home/ubuntu/.vnc/passwd
  python3 -c "import base64; open(\"/home/ubuntu/.vnc/passwd\", \"wb\").write(base64.b64decode(\"ksvjTTPCvsMAAAAA\"))"
  chown ubuntu:ubuntu /home/ubuntu/.vnc/passwd
  chmod 600 /home/ubuntu/.vnc/passwd
  echo "✓ VNC password file created"
'
```

### 4. Fix noVNC Service

```bash
multipass exec auraos-multipass -- sudo bash -c 'cat > /etc/systemd/system/auraos-novnc.service << "EOF"
[Unit]
Description=AuraOS noVNC web proxy
After=network.target auraos-x11vnc.service

[Service]
Type=simple
User=ubuntu
Environment=HOME=/home/ubuntu
ExecStart=/opt/novnc/utils/novnc_proxy --listen 6080 --vnc localhost:5900 --web /opt/novnc --file-only
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
echo "✓ noVNC service configured"
'
```

### 5. Reload and Start x11vnc

```bash
multipass exec auraos-multipass -- sudo systemctl start auraos-x11vnc.service
sleep 5
echo "✓ x11vnc started"
```

### 6. Reload and Start noVNC

```bash
multipass exec auraos-multipass -- sudo systemctl daemon-reload
multipass exec auraos-multipass -- sudo systemctl start auraos-novnc.service
sleep 3
echo "✓ noVNC started"
```

### 7. Verify Everything

```bash
multipass exec auraos-multipass -- bash -c '
  echo "=== Port Check ==="
  ss -tlnp 2>/dev/null | grep -E "5900|6080"
  echo ""
  echo "=== Service Status ==="
  systemctl status auraos-x11vnc.service auraos-novnc.service --no-pager -l 2>&1 | grep -E "Active:|ExecStart:" | head -4
'
```

Then proceed to **Step 2: Open Browser** above.

---

## 🔍 Verification Checklist

After setup, verify each of these works:

### ✅ x11vnc is listening
```bash
multipass exec auraos-multipass -- ss -tlnp 2>/dev/null | grep 5900
# Should show: LISTEN on port 5900
```

### ✅ noVNC is listening
```bash
multipass exec auraos-multipass -- ss -tlnp 2>/dev/null | grep 6080
# Should show: websockify on port 6080
```

### ✅ VNC password file exists
```bash
multipass exec auraos-multipass -- ls -lh /home/ubuntu/.vnc/passwd
# Should show: -rw------- 1 ubuntu ubuntu 12 bytes
```

### ✅ noVNC serves vnc.html correctly
```bash
curl -s http://localhost:6080/vnc.html | grep -q '<title>noVNC</title>'
# If this returns nothing, noVNC is working correctly
```

### ✅ Browser access works
```
Open: http://localhost:6080/vnc.html
Password: auraos123
Expected: VNC login canvas (not directory listing)
```

---

## 🆘 Common Issues & Fixes

### Issue: Directory listing instead of login prompt

**Root cause**: noVNC web path is wrong

**Quick fix**:
```bash
multipass exec auraos-multipass -- systemctl cat auraos-novnc.service | grep 'ExecStart'
# Should have: --web /opt/novnc
# If it says: --web /opt/novnc/app (WRONG!)
# Run step 4 above to fix it
```

### Issue: Password "auraos123" doesn't work

**Root cause**: VNC password file missing or corrupted

**Quick fix**:
```bash
# Run step 3 above to recreate password
# Then restart x11vnc:
multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service
# Wait 5 seconds and try again
```

### Issue: Can't connect to http://localhost:6080/vnc.html

**Root cause**: noVNC service crashed

**Quick fix**:
```bash
# Check status
multipass exec auraos-multipass -- systemctl status auraos-novnc.service

# Check logs
multipass exec auraos-multipass -- journalctl -u auraos-novnc.service -n 20 --no-pager

# Restart everything
./auraos_gui_restart.sh
```

### Issue: Black screen after connecting

**This is expected** - XFCE is running but may not render much on Xvfb

**Verify it's working**:
```bash
./auraos.sh screenshot
# This captures what XFCE is actually showing
```

---

## 📊 Success Metrics

When everything works:

| Component | Status | How to Check |
|-----------|--------|-------------|
| x11vnc | ✅ Running | `ss -tlnp \| grep 5900` shows port open |
| noVNC | ✅ Running | `ss -tlnp \| grep 6080` shows port open |
| VNC Auth | ✅ Configured | VNC password file exists (12 bytes) |
| Browser | ✅ Accessible | `http://localhost:6080/vnc.html` loads |
| XFCE | ✅ Running | Screenshot shows desktop content |

---

## 📞 Documentation Files

All detailed info is in these files:

- **`GUI_SETUP_SUMMARY.md`** - Detailed explanation of what was wrong and how it was fixed
- **`GUI_ACCESS.md`** - Comprehensive troubleshooting and reference guide
- **`auraos_gui_restart.sh`** - The automated restart script

---

## ✨ You're Done!

Once you can see the desktop in your browser:

1. **Take a screenshot**:
   ```bash
   ./auraos.sh screenshot
   ```

2. **Test AI automation**:
   ```bash
   ./auraos.sh automate "click on the file manager"
   ```

3. **Check system status**:
   ```bash
   ./auraos.sh status
   ```

