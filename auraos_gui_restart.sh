#!/bin/bash
# AuraOS GUI Complete Clean Restart
# Brings VNC and noVNC up cleanly from scratch
# Usage: ./auraos_gui_restart.sh

set -e

VM_NAME="auraos-multipass"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   AuraOS GUI Complete Clean Restart      ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Stop services
echo -e "${YELLOW}[1/7]${NC} Stopping VNC services..."
multipass exec "$VM_NAME" -- bash -c 'sudo systemctl stop auraos-x11vnc.service auraos-novnc.service 2>/dev/null || true' &
STOP_PID=$!
sleep 3
wait $STOP_PID 2>/dev/null || true

# Step 2: Kill orphaned processes
echo -e "${YELLOW}[2/7]${NC} Cleaning up orphaned processes..."
multipass exec "$VM_NAME" -- bash -c '
  sudo pkill -9 x11vnc 2>/dev/null || true
  sudo pkill -9 Xvfb 2>/dev/null || true
  sudo pkill -9 websockify 2>/dev/null || true
  sudo pkill -9 novnc_proxy 2>/dev/null || true
' &
CLEAN_PID=$!
sleep 3
wait $CLEAN_PID 2>/dev/null || true

# Step 3: Setup VNC password
# Step 3: Setup VNC password
echo -e "${YELLOW}[3/7]${NC} Setting up VNC authentication..."
multipass exec "$VM_NAME" -- sudo bash << 'VNC_PASSWORD_EOF'
  mkdir -p /home/ubuntu/.vnc
  rm -f /home/ubuntu/.vnc/passwd

  # Use expect to create password non-interactively with x11vnc
  expect << 'EXPECT_EOF'
    set timeout 5
    spawn x11vnc -storepasswd /home/ubuntu/.vnc/passwd
    expect "Enter VNC password:"
    send "auraos123\r"
    expect "Verify password:"
    send "auraos123\r"
    expect "Write password"
    send "y\r"
    expect eof
EXPECT_EOF
  
  chown ubuntu:ubuntu /home/ubuntu/.vnc/passwd
  chmod 600 /home/ubuntu/.vnc/passwd
  echo "✓ Password file created at /home/ubuntu/.vnc/passwd"
VNC_PASSWORD_EOF


# Step 4: Fix noVNC service configuration
echo -e "${YELLOW}[4/7]${NC} Configuring noVNC service..."
multipass exec "$VM_NAME" -- bash -c 'sudo bash << SERVICE_EOF
cat > /etc/systemd/system/auraos-novnc.service << "CONFIG_EOF"
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
CONFIG_EOF

systemctl daemon-reload
echo "✓ noVNC service configured"
SERVICE_EOF
'

# Step 5: Start x11vnc
echo -e "${YELLOW}[5/7]${NC} Starting x11vnc and Xvfb..."
multipass exec "$VM_NAME" -- sudo systemctl start auraos-x11vnc.service
sleep 5

# Step 6: Verify x11vnc is listening
echo -e "${YELLOW}[6/7]${NC} Verifying x11vnc is listening..."
multipass exec "$VM_NAME" -- bash -c '
  for i in {1..10}; do
    ss -tlnp 2>/dev/null | grep -q 5900 && break
    echo "Waiting for x11vnc to start... ($i/10)"
    sleep 1
  done
  ss -tlnp 2>/dev/null | grep 5900 || netstat -tlnp 2>/dev/null | grep 5900
' | grep -q 5900
echo -e "${GREEN}✓ x11vnc listening on port 5900${NC}"

# Step 7: Start noVNC
echo -e "${YELLOW}[7/7]${NC} Starting noVNC web server..."
multipass exec "$VM_NAME" -- sudo systemctl start auraos-novnc.service
sleep 4

# Verify noVNC
multipass exec "$VM_NAME" -- bash -c '
  for i in {1..10}; do
    ss -tlnp 2>/dev/null | grep -q 6080 && break
    echo "Waiting for noVNC to start... ($i/10)"
    sleep 1
  done
  ss -tlnp 2>/dev/null | grep 6080 || netstat -tlnp 2>/dev/null | grep 6080
' | grep -q 6080
echo -e "${GREEN}✓ noVNC listening on port 6080${NC}"

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}✓ GUI Restart Complete!${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Connection Details:${NC}"
echo ""
echo "  Browser URL:"
echo -e "    ${GREEN}http://localhost:6080/vnc.html${NC}"
echo ""
echo "  Password:"
echo -e "    ${GREEN}auraos123${NC}"
echo ""
echo -e "${YELLOW}Expected Display:${NC}"
echo "  - NOT a directory listing"
echo "  - NOT an error page"
echo "  - Should show XFCE desktop (black/minimal for now)"
echo ""
echo -e "${YELLOW}If you see a directory listing:${NC}"
echo "  The noVNC web path is wrong. Check:"
echo "  multipass exec $VM_NAME -- ls -la /opt/novnc/vnc.html"
echo ""
