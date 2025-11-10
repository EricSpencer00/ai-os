# Complete AuraOS GUI Setup - From Scratch

## ✅ Current Status

- ✅ x11vnc running on port 5900 (VNC server)
- ✅ noVNC running on port 6080 (web proxy)
- ✅ VNC password authentication configured
- ✅ Web server serving vnc.html correctly
- ✅ No directory listing issue

## 🚀 How to Access the Desktop

### Step 1: Run the Restart Script (Recommended)

```bash
cd /Users/eric/GitHub/ai-os
./auraos_gui_restart.sh
```

This handles everything automatically.

### Step 2: Open Browser

Navigate to: **http://localhost:6080/vnc.html**

### Step 3: Enter Password

Password: **auraos123**

---

## 📋 What Was Wrong (Root Causes)

| Problem | Cause | Fix |
|---------|-------|-----|
| Directory listing instead of login | noVNC was configured with `--web /opt/novnc/app` but vnc.html is at `/opt/novnc/vnc.html` | Changed to `--web /opt/novnc` |
| Password authentication fails | x11vnc expects password file at `/home/ubuntu/.vnc/passwd` but file was missing or corrupted | Created file with base64-encoded password |
| Multiple websockify processes | Services were restarting repeatedly due to failures | Cleaned up with script before full restart |
| noVNC crashing immediately | Missing vnc.html file (wrong path) | Fixed path in systemd service |

---

## 🔧 The Fix Applied

### 1. Correct VNC Password File

```bash
multipass exec auraos-multipass -- sudo bash -c '
  mkdir -p /home/ubuntu/.vnc
  rm -f /home/ubuntu/.vnc/passwd
  # Create with base64-encoded password "auraos123"
  python3 -c "import base64; open(\"/home/ubuntu/.vnc/passwd\", \"wb\").write(base64.b64decode(\"ksvjTTPCvsMAAAAA\"))"
  chown ubuntu:ubuntu /home/ubuntu/.vnc/passwd
  chmod 600 /home/ubuntu/.vnc/passwd
'
```

### 2. Fixed noVNC Systemd Service

**Correct configuration** (`/etc/systemd/system/auraos-novnc.service`):

```ini
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
```

**Key differences**:
- `--web /opt/novnc` (NOT `/opt/novnc/app`)
- `--file-only` (prevents directory listing)
- Proper format for websockify proxy

### 3. Cleanup Script

The `auraos_gui_restart.sh` script now:
1. Stops services gracefully
2. Kills orphaned processes
3. Sets up authentication
4. Fixes configurations
5. Starts services fresh
6. Verifies connectivity

---

## ✅ Verification Checklist

After running `./auraos_gui_restart.sh`, verify:

```bash
# 1. Check x11vnc is listening
multipass exec auraos-multipass -- ss -tlnp 2>/dev/null | grep 5900
# Expected: LISTEN on 5900

# 2. Check noVNC is listening
multipass exec auraos-multipass -- ss -tlnp 2>/dev/null | grep 6080
# Expected: websockify process on 6080

# 3. Verify VNC password file exists
multipass exec auraos-multipass -- ls -lh /home/ubuntu/.vnc/passwd
# Expected: -rw------- ubuntu:ubuntu 12 bytes

# 4. Test noVNC web server
curl -s http://localhost:6080/vnc.html | grep -q '<title>noVNC</title>'
# Expected: (no output = success)
```

---

## 🐛 Troubleshooting

### See directory listing at http://localhost:6080/vnc.html

Check noVNC configuration:
```bash
multipass exec auraos-multipass -- cat /etc/systemd/system/auraos-novnc.service | grep ExecStart
```

Should have:
```
--web /opt/novnc --file-only
```

NOT:
```
--web /opt/novnc/app
```

### Password still doesn't work

Recreate password file:
```bash
multipass exec auraos-multipass -- sudo bash -c '
  rm -f /home/ubuntu/.vnc/passwd
  python3 -c "import base64; open(\"/home/ubuntu/.vnc/passwd\", \"wb\").write(base64.b64decode(\"ksvjTTPCvsMAAAAA\"))"
  chown ubuntu:ubuntu /home/ubuntu/.vnc/passwd
  chmod 600 /home/ubuntu/.vnc/passwd
'
multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service
```

### Services failing to start

Check logs:
```bash
multipass exec auraos-multipass -- journalctl -u auraos-x11vnc.service -u auraos-novnc.service -n 30 --no-pager
```

Run full restart:
```bash
./auraos_gui_restart.sh
```

---

## 📝 Manual Commands (if script fails)

### Complete Manual Restart:

```bash
# 1. Stop services
multipass exec auraos-multipass -- sudo systemctl stop auraos-x11vnc.service auraos-novnc.service

# 2. Kill processes
multipass exec auraos-multipass -- bash -c '
  sudo pkill -9 x11vnc
  sudo pkill -9 Xvfb
  sudo pkill -9 websockify
  sudo pkill -9 novnc_proxy
'
sleep 3

# 3. Setup password
multipass exec auraos-multipass -- sudo bash -c '
  mkdir -p /home/ubuntu/.vnc
  rm -f /home/ubuntu/.vnc/passwd
  python3 -c "import base64; open(\"/home/ubuntu/.vnc/passwd\", \"wb\").write(base64.b64decode(\"ksvjTTPCvsMAAAAA\"))"
  chown ubuntu:ubuntu /home/ubuntu/.vnc/passwd
  chmod 600 /home/ubuntu/.vnc/passwd
'

# 4. Fix noVNC service config
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
'

# 5. Reload and start
multipass exec auraos-multipass -- sudo systemctl daemon-reload
multipass exec auraos-multipass -- sudo systemctl start auraos-x11vnc.service
sleep 5
multipass exec auraos-multipass -- sudo systemctl start auraos-novnc.service
sleep 3

# 6. Verify
multipass exec auraos-multipass -- ss -tlnp 2>/dev/null | grep -E "5900|6080"
```

---

## 🎯 Next Steps

Once GUI access is confirmed working:

1. **Test AI Vision Integration**:
   ```bash
   ./auraos.sh automate "click on the file manager icon"
   ```

2. **Capture Screenshot**:
   ```bash
   ./auraos.sh screenshot
   ```

3. **Monitor Logs**:
   ```bash
   multipass exec auraos-multipass -- journalctl -u auraos-gui-agent.service -f
   ```

4. **Check System Status**:
   ```bash
   ./auraos.sh status
   ```

---

## 📁 Files Modified

- `/etc/systemd/system/auraos-x11vnc.service` - x11vnc systemd unit
- `/etc/systemd/system/auraos-novnc.service` - noVNC systemd unit (FIXED)
- `/home/ubuntu/.vnc/passwd` - VNC password file (RECREATED)
- `./auraos_gui_restart.sh` - NEW: Complete restart script
- `./GUI_ACCESS.md` - NEW: Detailed access guide

---

## 📞 Support Info

- **Repo**: `/Users/eric/GitHub/ai-os`
- **Restart Script**: `./auraos_gui_restart.sh`
- **Access Guide**: `./GUI_ACCESS.md`
- **Browser URL**: `http://localhost:6080/vnc.html`
- **Password**: `auraos123`
- **VM Name**: `auraos-multipass`
- **VM IP**: `192.168.2.9`

