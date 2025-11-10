# AuraOS GUI Access - Complete Setup

This guide will help you access the AuraOS desktop via noVNC in your browser.

## Quick Start (One Command)

From the repo root directory:

```bash
./auraos_gui_restart.sh
```

This script will:
1. Stop any running VNC/noVNC services
2. Clean up orphaned processes
3. Set up VNC password authentication
4. Start x11vnc and Xvfb
5. Start noVNC web server
6. Verify everything is running

After it completes (should take ~30 seconds), proceed to **Access the Desktop** below.

---

## Access the Desktop

### Option 1: Browser (Recommended)

1. Open your browser and navigate to:
   ```
   http://localhost:6080/vnc.html
   ```

2. When prompted for a password, enter:
   ```
   auraos123
   ```

3. You should see the XFCE desktop (may be minimal/black initially)

### Option 2: Native VNC Client (if you have one)

```bash
vncviewer localhost:5901
# Password: auraos123
```

---

## Troubleshooting

### I see a directory listing instead of a login prompt

**Problem**: The noVNC web server is serving the wrong files.

**Solution**: 
```bash
# Check if vnc.html exists
multipass exec auraos-multipass -- ls -lh /opt/novnc/vnc.html

# Check noVNC service status
multipass exec auraos-multipass -- systemctl status auraos-novnc.service

# View service configuration
multipass exec auraos-multipass -- cat /etc/systemd/system/auraos-novnc.service
```

The ExecStart line should have:
```
--web /opt/novnc --file-only
```

NOT:
```
--web /opt/novnc/app
```

### Password authentication fails

**Problem**: VNC password file not created or corrupted.

**Solution**:
```bash
# Recreate password file
multipass exec auraos-multipass -- sudo bash -c '
  mkdir -p /home/ubuntu/.vnc
  rm -f /home/ubuntu/.vnc/passwd
  python3 -c "import base64; open(\"/home/ubuntu/.vnc/passwd\", \"wb\").write(base64.b64decode(\"ksvjTTPCvsMAAAAA\"))"
  chown ubuntu:ubuntu /home/ubuntu/.vnc/passwd
  chmod 600 /home/ubuntu/.vnc/passwd
  ls -lh /home/ubuntu/.vnc/passwd
'

# Restart x11vnc
multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service
```

### Cannot connect - nothing on port 6080

**Problem**: noVNC service crashed or didn't start.

**Solution**:
```bash
# Check service status
multipass exec auraos-multipass -- systemctl status auraos-novnc.service --no-pager

# Check logs
multipass exec auraos-multipass -- journalctl -u auraos-novnc.service -n 20 --no-pager

# Manual restart
./auraos_gui_restart.sh
```

### Black/minimal screen after connecting

**Problem**: XFCE desktop is running but rendering minimally.

**Solution**: This is expected behavior - the desktop is running but may not be fully rendered. Try:
```bash
# Take a screenshot to verify XFCE is actually running
./auraos.sh screenshot

# Check if XFCE processes are running
multipass exec auraos-multipass -- ps aux | grep -E 'xfce|Xvfb|x11vnc' | grep -v grep
```

---

## Manual Step-by-Step (if the script doesn't work)

### 1. Stop Services

```bash
multipass exec auraos-multipass -- sudo systemctl stop auraos-x11vnc.service auraos-novnc.service 2>/dev/null || true
```

### 2. Kill Orphaned Processes

```bash
multipass exec auraos-multipass -- bash -c '
  sudo pkill -9 x11vnc 2>/dev/null || true
  sudo pkill -9 Xvfb 2>/dev/null || true
  sudo pkill -9 websockify 2>/dev/null || true
  sudo pkill -9 novnc_proxy 2>/dev/null || true
'
```

### 3. Create VNC Password

```bash
multipass exec auraos-multipass -- sudo bash -c '
  mkdir -p /home/ubuntu/.vnc
  rm -f /home/ubuntu/.vnc/passwd
  python3 -c "import base64; open(\"/home/ubuntu/.vnc/passwd\", \"wb\").write(base64.b64decode(\"ksvjTTPCvsMAAAAA\"))"
  chown ubuntu:ubuntu /home/ubuntu/.vnc/passwd
  chmod 600 /home/ubuntu/.vnc/passwd
'
```

### 4. Start x11vnc + Xvfb

```bash
multipass exec auraos-multipass -- sudo systemctl start auraos-x11vnc.service
sleep 5
```

### 5. Fix and Start noVNC

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
'

multipass exec auraos-multipass -- sudo systemctl daemon-reload
multipass exec auraos-multipass -- sudo systemctl start auraos-novnc.service
sleep 3
```

### 6. Verify Everything

```bash
multipass exec auraos-multipass -- bash -c '
  echo "Checking x11vnc..."
  ss -tlnp 2>/dev/null | grep 5900 || netstat -tlnp 2>/dev/null | grep 5900
  echo ""
  echo "Checking noVNC..."
  ss -tlnp 2>/dev/null | grep 6080 || netstat -tlnp 2>/dev/null | grep 6080
'
```

### 7. Access Browser

Open: http://localhost:6080/vnc.html
Password: auraos123

---

## SSH Tunnels (if needed)

If you're accessing from a remote machine, you may need SSH tunnels:

```bash
# Terminal 1: Tunnel VNC
ssh -L 5901:localhost:5900 ubuntu@192.168.2.9

# Terminal 2: Tunnel noVNC
ssh -L 6080:localhost:6080 ubuntu@192.168.2.9

# Then access: http://localhost:6080/vnc.html
```

---

## Verification Commands

```bash
# Show all running services
multipass exec auraos-multipass -- systemctl status auraos-x11vnc.service auraos-novnc.service --no-pager

# Show ports
multipass exec auraos-multipass -- ss -tlnp 2>/dev/null | grep -E '5900|6080'

# Show XFCE processes
multipass exec auraos-multipass -- ps aux | grep -E 'xfce|Xvfb|x11vnc' | grep -v grep

# Show recent logs
multipass exec auraos-multipass -- journalctl -u auraos-x11vnc.service -u auraos-novnc.service -n 50 --no-pager
```

---

## Key Files

- **Restart Script**: `./auraos_gui_restart.sh`
- **x11vnc Service**: `/etc/systemd/system/auraos-x11vnc.service` (on VM)
- **noVNC Service**: `/etc/systemd/system/auraos-novnc.service` (on VM)
- **VNC Password**: `/home/ubuntu/.vnc/passwd` (on VM)
- **noVNC Web Files**: `/opt/novnc/` (on VM)
- **VNC Log**: `/var/log/x11vnc_manual.log` (on VM)

---

## Next Steps

Once GUI access is working:

1. **Test AI Vision Automation**:
   ```bash
   ./auraos.sh automate "click the file manager icon"
   ```

2. **Take Screenshots**:
   ```bash
   ./auraos.sh screenshot
   ```

3. **Check Status**:
   ```bash
   ./auraos.sh status
   ```

