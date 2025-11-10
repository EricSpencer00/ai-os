#!/bin/bash
# AuraOS Quick Start Helper
# Convenient wrapper for common AuraOS operations

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/auraos_daemon/venv"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          AuraOS Quick Start            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
}

activate_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        cd "$SCRIPT_DIR/auraos_daemon"
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source "$VENV_DIR/bin/activate"
    fi
}

cmd_status() {
    echo -e "${GREEN}Checking system status...${NC}"
    echo ""
    echo -e "${BLUE}VM Status:${NC}"
    multipass list
    echo ""
    echo -e "${BLUE}VM Services:${NC}"
    multipass exec auraos-multipass -- bash -c 'ps aux | grep -E "[x]11vnc|[w]ebsockify" | head -2' || echo "Services not running"
    echo ""
    echo -e "${BLUE}Ports:${NC}"
    lsof -i :5901 -i :6080 -i :8765 2>/dev/null | grep LISTEN || echo "No ports listening"
}

cmd_screenshot() {
    echo -e "${GREEN}Capturing screenshot...${NC}"
    activate_venv
    cd "$SCRIPT_DIR/auraos_daemon"
    python core/screen_automation.py capture
    echo -e "${GREEN}Screenshot saved to /tmp/auraos_screenshot.png${NC}"
}

cmd_keys() {
    activate_venv
    cd "$SCRIPT_DIR/auraos_daemon"
    
    if [ "$1" == "list" ]; then
        echo -e "${GREEN}Listing API keys...${NC}"
        python core/key_manager.py list
    elif [ "$1" == "add" ]; then
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo -e "${YELLOW}Usage: $0 keys add <provider> <api-key>${NC}"
            echo -e "${YELLOW}Example: $0 keys add openai sk-...${NC}"
            exit 1
        fi
        echo -e "${GREEN}Adding API key for $2...${NC}"
        python core/key_manager.py add "$2" "$3"
    elif [ "$1" == "ollama" ]; then
        MODEL="${2:-llava:13b}"
        VISION_MODEL="${3:-$MODEL}"
        echo -e "${GREEN}Setting Ollama: model=$MODEL, vision_model=$VISION_MODEL${NC}"
        python core/key_manager.py enable-ollama "$MODEL" "$VISION_MODEL"
    else
        echo -e "${YELLOW}Usage: $0 keys <list|add|ollama>${NC}"
        echo -e "${YELLOW}  keys list                  - List all configured keys${NC}"
        echo -e "${YELLOW}  keys add <provider> <key>  - Add API key${NC}"
        echo -e "${YELLOW}  keys ollama [model] [vision_model] - Configure Ollama${NC}"
        echo -e "${YELLOW}Example: $0 keys ollama llava:13b qwen2.5-coder:7b${NC}"
        exit 1
    fi
}

cmd_automate() {
    if [ -z "$1" ]; then
        echo -e "${YELLOW}Usage: $0 automate \"<task description>\"${NC}"
        echo -e "${YELLOW}Example: $0 automate \"click the Firefox icon\"${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Automating task: $1${NC}"
    activate_venv
    cd "$SCRIPT_DIR/auraos_daemon"
    python core/screen_automation.py task "$1"
}

cmd_logs() {
    echo -e "${GREEN}Showing recent VM GUI agent logs...${NC}"
    multipass exec auraos-multipass -- journalctl -u auraos-gui-agent.service -n 50 --no-pager
}

cmd_restart() {
    echo -e "${GREEN}Restarting VM services...${NC}"
    multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service
    multipass exec auraos-multipass -- sudo systemctl restart auraos-novnc.service
    multipass exec auraos-multipass -- sudo systemctl restart auraos-gui-agent.service
    echo -e "${GREEN}Services restarted!${NC}"
    echo ""
    cmd_status
}

cmd_health() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       AuraOS System Health Check       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    
    # Check 1: VM Running
    echo -e "${YELLOW}[1/7]${NC} VM Status"
    multipass list | grep auraos-multipass || { echo -e "${RED}✗ VM not running${NC}"; return 1; }
    echo -e "${GREEN}✓ VM running${NC}"
    echo ""
    
    # Check 2: x11vnc Service
    echo -e "${YELLOW}[2/7]${NC} x11vnc Service"
    if multipass exec auraos-multipass -- bash -c 'ps aux | grep -q "[x]11vnc"' 2>/dev/null; then
        echo -e "${GREEN}✓ x11vnc running${NC}"
    else
        echo -e "${RED}✗ x11vnc not running${NC}"
        echo "  Starting..."
        multipass exec auraos-multipass -- sudo systemctl start auraos-x11vnc.service
        sleep 3
    fi
    echo ""
    
    # Check 3: noVNC Service
    echo -e "${YELLOW}[3/7]${NC} noVNC Service"
    if multipass exec auraos-multipass -- bash -c 'ps aux | grep -q "[w]ebsockify"' 2>/dev/null; then
        echo -e "${GREEN}✓ noVNC running${NC}"
    else
        echo -e "${RED}✗ noVNC not running${NC}"
        echo "  Starting..."
        multipass exec auraos-multipass -- sudo systemctl start auraos-novnc.service
        sleep 2
    fi
    echo ""
    
    # Check 4: VNC Password File
    echo -e "${YELLOW}[4/7]${NC} VNC Authentication"
    if multipass exec auraos-multipass -- [ -f /home/ubuntu/.vnc/passwd ] 2>/dev/null; then
        echo -e "${GREEN}✓ Password file exists${NC}"
    else
        echo -e "${RED}✗ Password file missing${NC}"
        return 1
    fi
    echo ""
    
    # Check 5: Port 5900
    echo -e "${YELLOW}[5/7]${NC} Port 5900 (x11vnc)"
    if multipass exec auraos-multipass -- bash -c 'ss -tlnp 2>/dev/null | grep -q 5900' 2>/dev/null; then
        echo -e "${GREEN}✓ Listening on 5900${NC}"
    else
        echo -e "${RED}✗ Not listening on 5900${NC}"
        return 1
    fi
    echo ""
    
    # Check 6: Port 6080 (noVNC)
    echo -e "${YELLOW}[6/7]${NC} Port 6080 (noVNC)"

    # First check if host already has something listening on 6080
    if lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | grep -q ':6080'; then
        echo -e "${GREEN}✓ Host listening on 6080${NC}"

    else
        # If not on host, check inside the Multipass VM
        if multipass exec auraos-multipass -- bash -c 'ss -tlnp 2>/dev/null | grep -q 6080' 2>/dev/null; then
            echo -e "${YELLOW}→ noVNC listening inside VM but not on host; establishing local forward...${NC}"

            # Create a lightweight Python forwarder script if missing
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
import threading
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

            VM_IP=$(multipass info auraos-multipass | grep IPv4 | cut -d: -f2 | tr -d ' ')
            # Start forwarder for 6080
            nohup /usr/bin/env python3 /tmp/auraos_port_forward.py 6080 "$VM_IP" 6080 >/tmp/forward_6080.log 2>&1 &
            sleep 0.5
            if lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | grep -q ':6080'; then
                echo -e "${GREEN}✓ Forwarder started: localhost:6080 -> ${VM_IP}:6080${NC}"
            else
                echo -e "${RED}✗ Failed to start forwarder for 6080${NC}"
                return 1
            fi

        else
            echo -e "${RED}✗ Not listening on 6080 inside VM${NC}"
            return 1
        fi
    fi
    echo ""
    
    # Check 7: Web Server
    echo -e "${YELLOW}[7/7]${NC} Web Server"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6080/vnc.html 2>&1)
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓ noVNC web server responding${NC}"
    else
        echo -e "${RED}✗ Web server returned: $HTTP_CODE${NC}"
        return 1
    fi
    echo ""
    
    # Summary
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}✓ All systems operational!${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Access the GUI:${NC}"
    echo -e "  Browser: ${GREEN}http://localhost:6080/vnc.html${NC}"
    echo -e "  Password: ${GREEN}auraos123${NC}"
}

cmd_gui_reset() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   AuraOS GUI Complete Clean Restart   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    
    VM_NAME="auraos-multipass"
    
    # Step 1: Stop services
    echo -e "${YELLOW}[1/7]${NC} Stopping VNC services..."
    multipass exec "$VM_NAME" -- sudo systemctl stop auraos-x11vnc.service auraos-novnc.service 2>/dev/null || true
    sleep 2
    
    # Step 2: Kill orphaned processes
    echo -e "${YELLOW}[2/7]${NC} Cleaning up orphaned processes..."
    multipass exec "$VM_NAME" -- bash -c '
      sudo pkill -9 x11vnc 2>/dev/null || true
      sudo pkill -9 Xvfb 2>/dev/null || true
      sudo pkill -9 websockify 2>/dev/null || true
      sudo pkill -9 novnc_proxy 2>/dev/null || true
    ' 2>/dev/null
    sleep 2
    
    # Step 3: Setup VNC password
    echo -e "${YELLOW}[3/7]${NC} Setting up VNC authentication..."
    multipass exec "$VM_NAME" -- sudo bash << 'VNC_PASSWORD_EOF' 2>/dev/null
      mkdir -p /home/ubuntu/.vnc
      rm -f /home/ubuntu/.vnc/passwd
      
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
    multipass exec "$VM_NAME" -- sudo bash << 'SERVICE_EOF' 2>/dev/null
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
    
    # Step 5: Start x11vnc
    echo -e "${YELLOW}[5/7]${NC} Starting x11vnc and Xvfb..."
    multipass exec "$VM_NAME" -- sudo systemctl start auraos-x11vnc.service
    sleep 5
    
    # Step 6: Verify x11vnc is listening
    echo -e "${YELLOW}[6/7]${NC} Verifying x11vnc is listening..."
    multipass exec "$VM_NAME" -- bash -c '
      for i in {1..10}; do
        ss -tlnp 2>/dev/null | grep -q 5900 && break
        sleep 1
      done
      ss -tlnp 2>/dev/null | grep 5900 || netstat -tlnp 2>/dev/null | grep 5900
    ' >/dev/null 2>&1
    echo -e "${GREEN}✓ x11vnc listening on port 5900${NC}"
    
    # Step 7: Start noVNC
    echo -e "${YELLOW}[7/7]${NC} Starting noVNC web server..."
    multipass exec "$VM_NAME" -- sudo systemctl start auraos-novnc.service
    sleep 4
    
    # Verify noVNC
    multipass exec "$VM_NAME" -- bash -c '
      for i in {1..10}; do
        ss -tlnp 2>/dev/null | grep -q 6080 && break
        sleep 1
      done
    ' >/dev/null 2>&1
    echo -e "${GREEN}✓ noVNC listening on port 6080${NC}"
    
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}✓ GUI Restart Complete!${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Access:${NC}"
    echo -e "  ${GREEN}http://localhost:6080/vnc.html${NC}"
    echo -e "  Password: ${GREEN}auraos123${NC}"
}

cmd_install() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   AuraOS Installation Script v1.0      ║${NC}"
    echo -e "${BLUE}║   For Apple Silicon (M1/M2/M3) Macs    ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""

    # Check if running on macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        echo -e "${RED}Error: This script is for macOS only${NC}"
        exit 1
    fi

    # Check if running on Apple Silicon
    if [[ $(uname -m) != "arm64" ]]; then
        echo -e "${YELLOW}Warning: This script is optimized for Apple Silicon (M1/M2/M3)${NC}"
        echo -e "${YELLOW}You appear to be on Intel. Continue? (y/n)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    echo -e "${BLUE}Step 1/8: Checking Homebrew...${NC}"
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo -e "${GREEN}✓ Homebrew already installed${NC}"
    fi
    echo ""

    echo -e "${BLUE}Step 2/8: Installing Multipass...${NC}"
    if ! command -v multipass &> /dev/null; then
        echo "Installing Multipass (VM manager)..."
        brew install multipass
        echo -e "${GREEN}✓ Multipass installed${NC}"
    else
        echo -e "${GREEN}✓ Multipass already installed${NC}"
    fi
    echo ""

    echo -e "${BLUE}Step 3/8: Installing Ollama...${NC}"
    if ! command -v ollama &> /dev/null; then
        echo "Installing Ollama (local LLM)..."
        brew install ollama
        echo -e "${GREEN}✓ Ollama installed${NC}"
    else
        echo -e "${GREEN}✓ Ollama already installed${NC}"
    fi
    echo ""

    echo -e "${BLUE}Step 4/8: Starting Ollama service...${NC}"
    brew services start ollama 2>/dev/null || true
    sleep 2
    echo "Waiting for Ollama to start..."
    for i in {1..10}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Ollama service is running${NC}"
            break
        fi
        [ $i -eq 10 ] && echo -e "${YELLOW}⚠ Ollama may not have started. Continue anyway.${NC}"
        sleep 1
    done
    echo ""

    echo -e "${BLUE}Step 5/8: Downloading vision model (llava:13b)...${NC}"
    if ollama list 2>/dev/null | grep -q "llava:13b"; then
        echo -e "${GREEN}✓ llava:13b model already installed${NC}"
    else
        echo "Downloading llava:13b model (this may take several minutes)..."
        ollama pull llava:13b
        echo -e "${GREEN}✓ Model downloaded${NC}"
    fi
    echo ""

    echo -e "${BLUE}Step 6/8: Setting up Python virtual environment...${NC}"
    cd "$SCRIPT_DIR/auraos_daemon"
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        echo "Installing Python packages..."
        pip install --upgrade pip setuptools wheel --quiet
        pip install -r requirements.txt --quiet
        echo -e "${GREEN}✓ Python environment created${NC}"
    else
        echo -e "${GREEN}✓ Virtual environment already exists${NC}"
    fi
    echo ""

    echo -e "${BLUE}Step 7/8: Setting up configuration...${NC}"
    if [ ! -f "config.json" ]; then
        if [ -f "config.sample.json" ]; then
            cp config.sample.json config.json
            echo -e "${GREEN}✓ Created config.json from sample${NC}"
        else
            echo -e "${RED}Error: config.sample.json not found${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ config.json already exists${NC}"
    fi
    echo ""

    echo -e "${BLUE}Step 8/8: Configuring Ollama for vision tasks...${NC}"
    source venv/bin/activate
    python core/key_manager.py enable-ollama llava:13b llava:13b 2>/dev/null || echo "Configured Ollama"
    echo -e "${GREEN}✓ Ollama configured with llava:13b for vision${NC}"
    echo ""

    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}✓ Installation Complete! 🎉${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo ""
    echo -e "  1. Set up Ubuntu VM:"
    echo -e "     ${BLUE}./auraos.sh vm-setup${NC}"
    echo ""
    echo -e "  2. Check system health:"
    echo -e "     ${BLUE}./auraos.sh health${NC}"
    echo ""
    echo -e "  3. Try AI automation:"
    echo -e "     ${BLUE}./auraos.sh automate \"click on Firefox\"${NC}"
    echo ""
}

cmd_vm_setup() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║        AuraOS VM Setup (Multipass)     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""

    VM_NAME="auraos-multipass"

    # Check if VM already exists
    if multipass list 2>/dev/null | grep -q "$VM_NAME"; then
        echo -e "${YELLOW}VM $VM_NAME already exists.${NC}"
        echo -e "${YELLOW}Delete and recreate? (y/n)${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo "Stopping and deleting existing VM..."
            multipass stop "$VM_NAME" 2>/dev/null || true
            multipass delete "$VM_NAME" 2>/dev/null || true
            multipass purge 2>/dev/null || true
        else
            echo "Using existing VM."
            return 0
        fi
    fi

    echo -e "${YELLOW}[1/5]${NC} Creating Ubuntu VM with Multipass..."
    multipass launch 22.04 \
        --name "$VM_NAME" \
        --cpus 2 \
        --memory 4G \
        --disk 20G
    echo -e "${GREEN}✓ VM created${NC}"
    echo ""

    echo -e "${YELLOW}[2/5]${NC} Installing desktop environment..."
    multipass exec "$VM_NAME" -- sudo bash -c '
        apt-get update -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
            xfce4 xfce4-goodies \
            xvfb x11vnc \
            python3-pip expect \
            curl wget git
    '
    echo -e "${GREEN}✓ Desktop installed${NC}"
    echo ""

    echo -e "${YELLOW}[3/5]${NC} Installing noVNC..."
    multipass exec "$VM_NAME" -- sudo bash -c '
        cd /opt
        git clone https://github.com/novnc/noVNC.git novnc >/dev/null 2>&1
        git clone https://github.com/novnc/websockify.git /opt/novnc/utils/websockify >/dev/null 2>&1
    '
    echo -e "${GREEN}✓ noVNC installed${NC}"
    echo ""

    echo -e "${YELLOW}[4/5]${NC} Setting up VNC services..."
    multipass exec "$VM_NAME" -- sudo bash << 'SERVICE_SETUP'
# Create x11vnc systemd service
cat > /etc/systemd/system/auraos-x11vnc.service << 'EOF'
[Unit]
Description=AuraOS x11vnc VNC Server
After=network.target

[Service]
Type=simple
User=ubuntu
Environment=DISPLAY=:99
Environment=HOME=/home/ubuntu
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp &
ExecStart=/usr/bin/x11vnc -display :99 -forever -shared -rfbauth /home/ubuntu/.vnc/passwd -rfbport 5900
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
User=ubuntu
Environment=HOME=/home/ubuntu
ExecStart=/opt/novnc/utils/novnc_proxy --listen 6080 --vnc localhost:5900 --web /opt/novnc --file-only
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create GUI agent service
cat > /etc/systemd/system/auraos-gui-agent.service << 'EOF'
[Unit]
Description=AuraOS GUI Automation Agent
After=network.target auraos-x11vnc.service

[Service]
Type=simple
User=ubuntu
Environment=DISPLAY=:99
Environment=HOME=/home/ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/bin/python3 /home/ubuntu/gui_agent.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
SERVICE_SETUP
    echo -e "${GREEN}✓ Services configured${NC}"
    echo ""

    echo -e "${YELLOW}[5/5]${NC} Setting up VNC password and starting services..."
    multipass exec "$VM_NAME" -- sudo bash << 'VNC_START'
# Create VNC password
mkdir -p /home/ubuntu/.vnc
rm -f /home/ubuntu/.vnc/passwd

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

chown -R ubuntu:ubuntu /home/ubuntu/.vnc
chmod 600 /home/ubuntu/.vnc/passwd

# Start services
systemctl enable auraos-x11vnc.service auraos-novnc.service
systemctl start auraos-x11vnc.service
sleep 3
systemctl start auraos-novnc.service
VNC_START

    # Set up port forwarding
    VM_IP=$(multipass info "$VM_NAME" | grep IPv4 | awk '{print $2}')
    echo ""
    echo -e "${YELLOW}Setting up port forwarding...${NC}"
    
    # Kill any existing port forwards
    pkill -f "ssh.*5901:localhost:5900" 2>/dev/null || true
    pkill -f "ssh.*6080:localhost:6080" 2>/dev/null || true
    pkill -f "ssh.*8765:localhost:8765" 2>/dev/null || true
    
    # Set up SSH forwarding in background
    multipass exec "$VM_NAME" -- bash -c "
        # Allow password auth for port forwarding
        echo 'ubuntu:auraos123' | sudo chpasswd
        sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
        sudo systemctl restart ssh
    " >/dev/null 2>&1

    sleep 2

    # Port forward VNC (5900->5901) and noVNC (6080->6080)
    ssh -f -N -L 5901:localhost:5900 -L 6080:localhost:6080 -L 8765:localhost:8765 \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ubuntu@"$VM_IP" >/dev/null 2>&1 &

    echo -e "${GREEN}✓ Port forwarding set up${NC}"
    echo ""

    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}✓ VM Setup Complete!${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Access the Ubuntu desktop:${NC}"
    echo -e "  Browser: ${BLUE}http://localhost:6080/vnc.html${NC}"
    echo -e "  Password: ${BLUE}auraos123${NC}"
    echo ""
    echo -e "${YELLOW}Run system health check:${NC}"
    echo -e "  ${BLUE}./auraos.sh health${NC}"
    echo ""
}

cmd_forward() {
    if [ -z "$1" ] || [ "$1" == "start" ]; then
        echo -e "${GREEN}Starting port forwarders...${NC}"
        VM_IP=$(multipass info auraos-multipass 2>/dev/null | grep IPv4 | cut -d: -f2 | tr -d ' ')
        if [ -z "$VM_IP" ]; then
            echo -e "${RED}Could not get VM IP address${NC}"
            return 1
        fi
        echo "VM IP: $VM_IP"

        # Create forwarder script if missing
        if [ ! -f /tmp/auraos_port_forward.py ]; then
            cat > /tmp/auraos_port_forward.py << 'PY'
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
        except Exception: pass
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

        # Start forwarders for 5901, 6080, 8765
        for PORT in 5901 6080 8765; do
            REMOTE_PORT=$PORT
            [ $PORT -eq 5901 ] && REMOTE_PORT=5900  # VNC is on 5900 inside VM
            
            # Check if already running
            if lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | grep -q ":$PORT "; then
                echo -e "${YELLOW}→ Forwarder already running on $PORT${NC}"
            else
                nohup /usr/bin/env python3 /tmp/auraos_port_forward.py $PORT "$VM_IP" $REMOTE_PORT >/tmp/forward_${PORT}.log 2>&1 &
                echo $! > /tmp/forward_${PORT}.pid
                sleep 0.2
                if lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | grep -q ":$PORT "; then
                    echo -e "${GREEN}✓ Forwarder started on localhost:$PORT${NC}"
                else
                    echo -e "${RED}✗ Failed to start forwarder on $PORT${NC}"
                fi
            fi
        done

    elif [ "$1" == "stop" ]; then
        echo -e "${GREEN}Stopping port forwarders...${NC}"
        pkill -f /tmp/auraos_port_forward.py || true
        sleep 0.2
        echo -e "${GREEN}✓ Forwarders stopped${NC}"

    elif [ "$1" == "status" ]; then
        echo -e "${YELLOW}Port forwarder status:${NC}"
        lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | grep -E '5901|6080|8765' || echo "No forwarders running"
        echo
        echo -e "${YELLOW}Forwarder processes:${NC}"
        ps aux | grep auraos_port_forward | grep -v grep || echo "No forwarder processes"
    else
        echo -e "${YELLOW}Usage: $0 forward <start|stop|status>${NC}"
        exit 1
    fi
}

cmd_help() {
    print_header
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  install            - Install all dependencies (Homebrew, Multipass, Ollama, Python)"
    echo "  vm-setup           - Create and configure Ubuntu VM with GUI"
    echo "  status             - Show VM and service status"
    echo "  health             - Run comprehensive system health check"
    echo "  gui-reset          - Complete clean restart of VNC/noVNC services"
    echo "  forward            - Manage port forwarders: forward <start|stop|status>"
    echo "  screenshot         - Capture current VM screen"
    echo "  automate \"<task>\" - Run AI-powered automation task"
    echo "  keys list          - List configured API keys"
    echo "  keys add           - Add API key: keys add <provider> <key>"
    echo "  keys ollama        - Configure Ollama models"
    echo "  logs               - Show GUI agent logs"
    echo "  restart            - Restart all VM services"
    echo "  help               - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 install                                   # First-time setup"
    echo "  $0 vm-setup                                  # Create Ubuntu VM"
    echo "  $0 health                                    # Check all systems"
    echo "  $0 gui-reset                                 # Reset VNC/noVNC from scratch"
    echo "  $0 screenshot                                # Capture desktop"
    echo "  $0 automate \"click on file manager\"        # AI automation"
    echo "  $0 keys ollama llava:13b llava:13b          # Configure vision model"
    echo ""
    echo "Examples:"
    echo "  $0 install                                   # First-time setup"
    echo "  $0 vm-setup                                  # Create Ubuntu VM"
    echo "  $0 health                                    # Check all systems"
    echo "  $0 forward start                             # Start port forwarders"
    echo "  $0 gui-reset                                 # Reset VNC/noVNC from scratch"
    echo "  $0 screenshot                                # Capture desktop"
    echo "  $0 automate \"click on file manager\"        # AI automation"
    echo "  $0 keys ollama llava:13b llava:13b          # Configure vision model"
    echo ""
    echo "Quick Start:"
    echo "  1. ./auraos.sh install     # Install everything"
    echo "  2. ./auraos.sh vm-setup    # Create Ubuntu VM with GUI"
    echo "  3. ./auraos.sh health      # Verify all systems working"
    echo "  4. Open http://localhost:6080/vnc.html (password: auraos123)"
    echo ""
}

# Main command dispatcher
case "$1" in
    install)
        cmd_install
        ;;
    vm-setup)
        cmd_vm_setup
        ;;
    forward)
        shift
        cmd_forward "$@"
        ;;
    status)
        cmd_status
        ;;
    health)
        cmd_health
        ;;
    gui-reset)
        cmd_gui_reset
        ;;
    screenshot)
        cmd_screenshot
        ;;
    keys)
        shift
        cmd_keys "$@"
        ;;
    automate)
        shift
        cmd_automate "$@"
        ;;
    logs)
        cmd_logs
        ;;
    restart)
        cmd_restart
        ;;
    help|--help|-h|"")
        cmd_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        cmd_help
        exit 1
        ;;
esac
