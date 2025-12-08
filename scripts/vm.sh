#!/usr/bin/env bash
# VM related commands for AuraOS
# This script is intended to be sourced by ./auraos.sh via load_script vm
set -e

# Ensure helper variables from auraos.sh are available
SCRIPT_DIR="${SCRIPT_DIR:-$(pwd)}"
AURAOS_USER="${AURAOS_USER:-ubuntu}"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
RED='\033[0;31m'

cmd_vm_setup() {
    echo -e "${BLUE}Starting VM setup (modular script)...${NC}"
    VM_NAME="auraos-multipass"

    if multipass list 2>/dev/null | grep -q "$VM_NAME"; then
        echo -e "${YELLOW}VM $VM_NAME already exists. Skipping creation.${NC}"
    else
        multipass launch 22.04 --name "$VM_NAME" --cpus 2 --memory 4G --disk 20G
        echo -e "${GREEN}✓ VM created${NC}"
    fi

    echo -e "${YELLOW}Installing desktop packages...${NC}"
    multipass exec "$VM_NAME" -- sudo bash -c '
        apt-get update -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
            xfce4 xfce4-goodies xvfb x11vnc python3-pip expect curl wget git \
            xdotool python3-venv python3-dev python3-tk \
            portaudio19-dev firefox
    '
    echo -e "${GREEN}✓ Desktop installed${NC}"

    echo -e "${YELLOW}Installing noVNC...${NC}"
    multipass exec "$VM_NAME" -- sudo bash -c '
        cd /opt
        if [ ! -d /opt/novnc ]; then
            git clone https://github.com/novnc/noVNC.git novnc >/dev/null 2>&1 || true
            git clone https://github.com/novnc/websockify.git /opt/novnc/utils/websockify >/dev/null 2>&1 || true
        fi
    '
    echo -e "${GREEN}✓ noVNC installed${NC}"

    echo -e "${YELLOW}Configuring services...${NC}"
    multipass exec "$VM_NAME" -- sudo bash <<'SERVICE_SETUP'
# Create x11vnc systemd service
cat > /etc/systemd/system/auraos-x11vnc.service << 'EOF'
[Unit]
Description=AuraOS x11vnc VNC Server
After=network.target

[Service]
Type=simple
User=${AURAOS_USER}
Environment=DISPLAY=:99
Environment=HOME=/home/${AURAOS_USER}
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp &
ExecStart=/usr/bin/x11vnc -display :99 -forever -shared -rfbauth /home/${AURAOS_USER}/.vnc/passwd -rfbport 5900
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create noVNC systemd service
cat > /etc/systemd/system/auraos-novnc.service << 'EOF'
[Unit]
Description=AuraOS noVNC web proxy
After=network.target auraos-x11vnc.service

[Service]
Type=simple
User=${AURAOS_USER}
Environment=HOME=/home/${AURAOS_USER}
ExecStart=/opt/novnc/utils/novnc_proxy --listen 6080 --vnc localhost:5900 --web /opt/novnc --file-only
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create GUI agent service (placeholder)
cat > /etc/systemd/system/auraos-gui-agent.service << 'EOF'
[Unit]
Description=AuraOS GUI Automation Agent
After=network.target auraos-x11vnc.service

[Service]
Type=simple
User=${AURAOS_USER}
Environment=DISPLAY=:99
Environment=HOME=/home/${AURAOS_USER}
WorkingDirectory=/home/${AURAOS_USER}
ExecStart=/usr/bin/python3 /home/${AURAOS_USER}/gui_agent.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
SERVICE_SETUP
    echo -e "${GREEN}✓ Services configured${NC}"

    echo -e "${YELLOW}Setting up VNC password and starting services...${NC}"
    multipass exec "$VM_NAME" -- sudo bash <<'VNC_START'
# Create VNC password
mkdir -p /home/${AURAOS_USER}/.vnc
rm -f /home/${AURAOS_USER}/.vnc/passwd

expect << 'EXPECT_EOF'
set timeout 5
spawn x11vnc -storepasswd /home/${AURAOS_USER}/.vnc/passwd
expect "Enter VNC password:"
send "auraos123\r"
expect "Verify password:"
send "auraos123\r"
expect "Write password"
send "y\r"
expect eof
EXPECT_EOF

chown -R ${AURAOS_USER}:${AURAOS_USER} /home/${AURAOS_USER}/.vnc
chmod 600 /home/${AURAOS_USER}/.vnc/passwd

# Start services
systemctl enable auraos-x11vnc.service auraos-novnc.service || true
systemctl start auraos-x11vnc.service || true
sleep 2
systemctl start auraos-novnc.service || true
VNC_START

    echo -e "${YELLOW}Installing Python dependencies and AuraOS applications...${NC}"
    multipass exec "$VM_NAME" -- sudo bash -c '
        apt-get update -qq
        apt-get install -y -qq python3-tk python3-pip portaudio19-dev firefox >/dev/null 2>&1 || true
        pip3 install --quiet speech_recognition pyaudio requests flask pyautogui pillow numpy || true
    '
    
    echo -e "${YELLOW}Setting up GUI Agent environment...${NC}"
    multipass exec "$VM_NAME" -- bash -c '
        # Create GUI Agent directory
        mkdir -p ~/gui_agent_env
        
        # Create virtual environment for GUI Agent
        python3 -m venv ~/gui_agent_env
        
        # Activate and install GUI Agent dependencies
        source ~/gui_agent_env/bin/activate
        pip install --quiet requests flask pyautogui pillow numpy || true
        deactivate
    '
    
    echo -e "${GREEN}✓ VM setup complete. Access via http://localhost:6080/vnc.html (password: auraos123)${NC}"
}

cmd_forward() {
    VM_NAME="auraos-multipass"
    echo -e "${BLUE}Starting/Managing port forwarders for $VM_NAME...${NC}"
    VM_IP=$(multipass info "$VM_NAME" 2>/dev/null | grep IPv4 | cut -d: -f2 | tr -d ' ')
    if [ -z "$VM_IP" ]; then
        echo -e "${RED}Could not find VM IP${NC}"
        return 1
    fi
    # Create forwarder script if missing
    if [ ! -f /tmp/auraos_port_forward.py ]; then
        cat > /tmp/auraos_port_forward.py <<'PY'
#!/usr/bin/env python3
import sys, socket, threading
if len(sys.argv)<4:
    print('Usage: auraos_port_forward.py <local_port> <remote_host> <remote_port>')
    sys.exit(1)
local_port=int(sys.argv[1]); remote_host=sys.argv[2]; remote_port=int(sys.argv[3])
server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', local_port))
server.listen(5)
def handle(client_sock):
    try:
        remote=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect((remote_host, remote_port))
    except Exception:
        client_sock.close(); return
    def forward(src,dst):
        try:
            while True:
                data=src.recv(4096)
                if not data: break
                dst.sendall(data)
        except Exception:
            pass
        try: dst.shutdown(socket.SHUT_RDWR)
        except Exception: pass
    t1=threading.Thread(target=forward, args=(client_sock,remote), daemon=True)
    t2=threading.Thread(target=forward, args=(remote,client_sock), daemon=True)
    t1.start(); t2.start(); t1.join(); t2.join()
    client_sock.close(); remote.close()
try:
    while True:
        client,addr=server.accept()
        t=threading.Thread(target=handle, args=(client,), daemon=True)
        t.start()
except KeyboardInterrupt:
    server.close()
PY
        chmod +x /tmp/auraos_port_forward.py
    fi

    for PORT in 5901 6080 8765; do
        nohup /usr/bin/env python3 /tmp/auraos_port_forward.py $PORT "$VM_IP" $PORT >/tmp/forward_$PORT.log 2>&1 &
    done
    echo -e "${GREEN}✓ Forwarders started${NC}"
}

cmd_gui_reset() {
    VM_NAME="auraos-multipass"
    echo -e "${BLUE}Performing GUI reset in VM $VM_NAME...${NC}"

    # Preconditions: multipass installed and VM running
    if ! command -v multipass >/dev/null 2>&1; then
        echo -e "${RED}multipass is not installed or not in PATH. Aborting.${NC}"
        return 2
    fi

    if ! multipass list 2>/dev/null | grep -q "^${VM_NAME}\b"; then
        echo -e "${YELLOW}VM ${VM_NAME} not found. Create it with: ./auraos.sh vm-setup${NC}"
        return 2
    fi

    STATE=$(multipass info "$VM_NAME" 2>/dev/null | awk -F: '/State:/{gsub(/^[ \t]+|[ \t]+$/,"",$2); print $2}')

    if [ "$STATE" != "Running" ]; then
        echo -e "${YELLOW}VM ${VM_NAME} is not running (state=${STATE}). Attempting to start it...${NC}"
        multipass start "$VM_NAME" || { echo -e "${RED}Failed to start VM ${VM_NAME}${NC}"; return 2; }
    fi

    # Wait for multipass SSH to become available (retry loop)
    wait_for_ssh()
    {
        local vm="$1"
        local timeout=${2:-30}
        local elapsed=0
        local interval=2
        while [ $elapsed -lt $timeout ]; do
            if multipass exec "$vm" -- echo ready >/dev/null 2>&1; then
                return 0
            fi
            sleep $interval
            elapsed=$((elapsed + interval))
        done
        return 1
    }

    echo "Waiting for VM SSH to become available (timeout 30s)..."
    if ! wait_for_ssh "$VM_NAME" 30; then
        echo -e "${RED}exec failed: SSH into VM timed out after 30s. See diagnostics below.${NC}"
        echo "--- multipass list ---"
        multipass list || true
        echo "--- multipass info $VM_NAME ---"
        multipass info "$VM_NAME" || true
        echo "If the VM is running but SSH times out, try: multipass restart $VM_NAME" 
        return 1
    fi

    echo "Running GUI reset commands inside VM (this may take a few seconds)..."
    if ! multipass exec "$VM_NAME" -- sudo bash -c '
        set -e
        systemctl stop auraos-x11vnc.service auraos-novnc.service || true
        pkill -9 x11vnc 2>/dev/null || true
        pkill -9 Xvfb 2>/dev/null || true
        pkill -9 websockify 2>/dev/null || true
        systemctl start auraos-x11vnc.service || true
        sleep 2
        systemctl start auraos-novnc.service || true
    ' ; then
        echo -e "${RED}GUI reset inside VM failed or timed out.${NC}"
        echo "You can inspect VM logs with: multipass exec $VM_NAME -- sudo journalctl -u auraos-x11vnc.service -n 80 --no-pager"
        return 1
    fi

    echo -e "${GREEN}✓ GUI reset attempted${NC}"
}

cmd_disable_screensaver() {
    VM_NAME="${1:-auraos-multipass}"
    USER_NAME="${2:-$AURAOS_USER}"
    echo -e "${BLUE}Disabling screensaver inside $VM_NAME for $USER_NAME...${NC}"
    multipass exec "$VM_NAME" -- sudo bash -s "$USER_NAME" <<'DISABLE_EOF'
#!/usr/bin/env bash
USER_NAME="$1"
HOME_DIR="/home/$USER_NAME"
export DISPLAY=:0
xset s off 2>/dev/null || true
xset s noblank 2>/dev/null || true
xset -dpms 2>/dev/null || true
pkill light-locker 2>/dev/null || true
pkill xscreensaver 2>/dev/null || true
pkill xss-lock 2>/dev/null || true
AUTOSTART_DIR="$HOME_DIR/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/disable-screensaver.desktop" <<'DESK'
[Desktop Entry]
Type=Application
Name=Disable Screensaver
Exec=/usr/local/bin/disable-screensaver-session.sh
X-GNOME-Autostart-enabled=true
NoDisplay=true
DESK
cat > /usr/local/bin/disable-screensaver-session.sh <<'SH'
#!/usr/bin/env bash
export DISPLAY=:0
xset s off 2>/dev/null || true
xset s noblank 2>/dev/null || true
xset -dpms 2>/dev/null || true
pkill light-locker 2>/dev/null || true
pkill xscreensaver 2>/dev/null || true
SH
chmod +x /usr/local/bin/disable-screensaver-session.sh || true
chown -R "$USER_NAME:$USER_NAME" "$AUTOSTART_DIR" || true
chown root:root /usr/local/bin/disable-screensaver-session.sh || true
if [ -f "$HOME_DIR/.config/autostart/light-locker.desktop" ]; then
  sed -i.bak 's/X-GNOME-Autostart-enabled=true/X-GNOME-Autostart-enabled=false/' "$HOME_DIR/.config/autostart/light-locker.desktop" || true
  chown "$USER_NAME:$USER_NAME" "$HOME_DIR/.config/autostart/light-locker.desktop" || true
fi
echo "Screensaver disable applied"
DISABLE_EOF
}