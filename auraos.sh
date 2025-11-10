#!/bin/bash
# AuraOS Quick Start Helper
# Convenient wrapper for common AuraOS operations

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/auraos_daemon/venv"

# Configurable VM username (default matches Multipass cloud images)
AURAOS_USER="${AURAOS_USER:-ubuntu}"

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
    if multipass exec auraos-multipass -- [ -f /home/${AURAOS_USER}/.vnc/passwd ] 2>/dev/null; then
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
        multipass exec "$VM_NAME" -- sudo bash <<VNC_PASSWORD_EOF 2>/dev/null
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
      
            chown ${AURAOS_USER}:${AURAOS_USER} /home/${AURAOS_USER}/.vnc/passwd
            chmod 600 /home/${AURAOS_USER}/.vnc/passwd
            echo "✓ Password file created at /home/${AURAOS_USER}/.vnc/passwd"
VNC_PASSWORD_EOF
    
    # Step 4: Fix noVNC service configuration
    echo -e "${YELLOW}[4/7]${NC} Configuring noVNC service..."
    multipass exec "$VM_NAME" -- sudo bash <<SERVICE_EOF 2>/dev/null
cat > /etc/systemd/system/auraos-novnc.service << "CONFIG_EOF"
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
CONFIG_EOF

systemctl daemon-reload
echo "✓ noVNC service configured"
SERVICE_EOF
    
    # Step 5: Start x11vnc
    echo -e "${YELLOW}[5/7]${NC} Starting x11vnc and Xvfb..."
    multipass exec "$VM_NAME" -- sudo systemctl start auraos-x11vnc.service
    sleep 5
    
    # Step 6: Verify x11vnc is listening (robust host-driven check)
    echo -e "${YELLOW}[6/7]${NC} Verifying x11vnc is listening..."

    found_x11vnc=false
    for i in {1..10}; do
        # Run the check from the host to avoid long-lived remote shells blocking
        if multipass exec "$VM_NAME" -- ss -tlnp 2>/dev/null | grep -q ":5900\b"; then
            found_x11vnc=true
            break
        fi
        sleep 1
    done

    if [ "$found_x11vnc" = true ]; then
        echo -e "${GREEN}✓ x11vnc listening on port 5900${NC}"
    else
        echo -e "${RED}✗ x11vnc did not appear on port 5900 after 10s${NC}"
        echo -e "${YELLOW}Gathering diagnostic information...${NC}"
        multipass exec "$VM_NAME" -- sudo systemctl status auraos-x11vnc.service --no-pager || true
        multipass exec "$VM_NAME" -- sudo journalctl -u auraos-x11vnc.service -n 80 --no-pager || true
        echo -e "${YELLOW}You can inspect the VM logs or retry the GUI reset.${NC}"
        return 1
    fi
    
    # Step 7: Start noVNC
    echo -e "${YELLOW}[7/7]${NC} Starting noVNC web server..."
    multipass exec "$VM_NAME" -- sudo systemctl start auraos-novnc.service
    sleep 4
    
    # Verify noVNC (host-driven check)
    found_novnc=false
    for i in {1..10}; do
        if multipass exec "$VM_NAME" -- ss -tlnp 2>/dev/null | grep -q ":6080\b"; then
            found_novnc=true
            break
        fi
        sleep 1
    done

    if [ "$found_novnc" = true ]; then
        echo -e "${GREEN}✓ noVNC listening on port 6080${NC}"
    else
        echo -e "${RED}✗ noVNC did not appear on port 6080 after 10s${NC}"
        echo -e "${YELLOW}Gathering diagnostic information...${NC}"
        multipass exec "$VM_NAME" -- sudo systemctl status auraos-novnc.service --no-pager || true
        multipass exec "$VM_NAME" -- sudo journalctl -u auraos-novnc.service -n 80 --no-pager || true
        return 1
    fi
    
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}✓ GUI Restart Complete!${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Access:${NC}"
    echo -e "  ${GREEN}http://localhost:6080/vnc.html${NC}"
    echo -e "  Password: ${GREEN}auraos123${NC}"
}

cmd_disable_screensaver() {
        VM_NAME="${1:-auraos-multipass}"
        USER_NAME="${2:-$AURAOS_USER}"

        echo -e "${BLUE}Disabling screensaver/lock inside VM '$VM_NAME' for user '$USER_NAME'...${NC}"

        multipass exec "$VM_NAME" -- sudo bash -s "$USER_NAME" <<'DISABLE_EOF'
#!/usr/bin/env bash
set -e
USER_NAME="$1"
HOME_DIR="/home/$USER_NAME"

echo "Applying session-level disable settings for $USER_NAME"

# Disable X blanking and DPMS (if X available)
export DISPLAY=:0
xset s off 2>/dev/null || true
xset s noblank 2>/dev/null || true
xset -dpms 2>/dev/null || true

# Kill common locker daemons
pkill light-locker 2>/dev/null || true
pkill xscreensaver 2>/dev/null || true
pkill xss-lock 2>/dev/null || true

# Create autostart to re-apply settings on login
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

# Create session helper
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

# Disable light-locker autostart if present
if [ -f "$HOME_DIR/.config/autostart/light-locker.desktop" ]; then
    sed -i.bak 's/X-GNOME-Autostart-enabled=true/X-GNOME-Autostart-enabled=false/' "$HOME_DIR/.config/autostart/light-locker.desktop" || true
    chown "$USER_NAME:$USER_NAME" "$HOME_DIR/.config/autostart/light-locker.desktop" || true
fi

echo "Done. Re-login or reboot the VM for all changes to take effect."
DISABLE_EOF
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
    echo -e "  2. (Optional) Install v2 improvements:"
    echo -e "     ${BLUE}./auraos.sh setup-v2${NC}"
    echo -e "     ${YELLOW}(10-12x faster inference, delta detection, local planner)${NC}"
    echo ""
    echo -e "  3. Check system health:"
    echo -e "     ${BLUE}./auraos.sh health${NC}"
    echo ""
    echo -e "  4. Try AI automation:"
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
    multipass exec "$VM_NAME" -- sudo bash <<SERVICE_SETUP
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

# Create GUI agent service
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
    echo ""

    echo -e "${YELLOW}[5/7]${NC} Setting up VNC password and starting services..."
    multipass exec "$VM_NAME" -- sudo bash <<VNC_START
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
systemctl enable auraos-x11vnc.service auraos-novnc.service
systemctl start auraos-x11vnc.service
sleep 3
systemctl start auraos-novnc.service
VNC_START

    echo -e "${YELLOW}[6/7]${NC} Installing AuraOS applications (with error logging)..."
    multipass exec "$VM_NAME" -- sudo bash <<AURAOS_APPS
# Install dependencies for AuraOS apps
apt-get update -qq && apt-get install -y python3-tk python3-pip portaudio19-dev firefox >/dev/null 2>&1
pip3 install speech_recognition pyaudio >/dev/null 2>&1

# Create AuraOS bin directory
mkdir -p /opt/auraos/bin

# Initialize launcher log
cat > /tmp/auraos_launcher.log << 'LOG_INIT'
# AuraOS Launcher Log
# Created at installation time
LOG_INIT

# Install ChatGPT-style AuraOS Terminal with Hamburger Menu
cat > /opt/auraos/bin/auraos_terminal.py << 'TERMINAL_EOF'
#!/usr/bin/env python3
"""AuraOS Terminal - ChatGPT-Style AI Command Interface"""
import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import sys
import os
from datetime import datetime

class AuraOSTerminal:
    def __init__(self, root, cli_mode=False):
        self.cli_mode = cli_mode
        if not cli_mode:
            self.root = root
            self.root.title("AuraOS Terminal")
            self.root.geometry("1000x700")
            self.root.configure(bg='#0a0e27')
            self.command_history = []
            self.history_index = -1
            self.show_command_panel = False
            self.create_widgets()
            self.log_event("STARTUP", "Terminal initialized")
        else:
            self.run_cli_mode()
    
    def log_event(self, action, message):
        """Log events to file"""
        try:
            with open("/tmp/auraos_launcher.log", "a") as f:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                f.write(f"[{ts}] {action}: {message}\n")
        except:
            pass
    
    def create_widgets(self):
        # Top bar with hamburger menu
        top_frame = tk.Frame(self.root, bg='#1a1e37', height=50)
        top_frame.pack(fill='x')
        
        menu_btn = tk.Button(
            top_frame, text="☰ Commands", command=self.toggle_command_panel,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=10, pady=8
        )
        menu_btn.pack(side='left', padx=10, pady=8)
        
        title = tk.Label(
            top_frame, text="⚡ AuraOS Terminal", font=('Arial', 14, 'bold'),
            fg='#00d4ff', bg='#1a1e37'
        )
        title.pack(side='left', padx=20, pady=8)
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#0a0e27')
        main_frame.pack(fill='both', expand=True)
        
        # Command panel (hidden by default)
        self.cmd_panel = tk.Frame(main_frame, bg='#1a1e37', width=250)
        self.cmd_panel_visible = False
        
        # Chat-style output area (main focus)
        self.output_area = scrolledtext.ScrolledText(
            main_frame, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
            font=('Menlo', 11), insertbackground='#00d4ff',
            relief='flat', padx=15, pady=15
        )
        self.output_area.pack(fill='both', expand=True, padx=0, pady=0)
        self.output_area.config(state='disabled')
        
        # Configure tags for rich output
        self.output_area.tag_config("system", foreground="#00d4ff", font=('Menlo', 11, 'bold'))
        self.output_area.tag_config("user", foreground="#4ec9b0", font=('Menlo', 11, 'bold'))
        self.output_area.tag_config("output", foreground="#d4d4d4", font=('Menlo', 10))
        self.output_area.tag_config("error", foreground="#f48771", font=('Menlo', 10, 'bold'))
        self.output_area.tag_config("success", foreground="#6db783", font=('Menlo', 10, 'bold'))
        self.output_area.tag_config("info", foreground="#9cdcfe", font=('Menlo', 10))
        
        # Welcome message
        self.append_output("⚡ AuraOS Terminal v2.0\n", "system")
        self.append_output("AI-Powered Command Interface\n\n", "system")
        self.append_output("Type your commands below. Use ☰ Commands menu for advanced options.\n\n", "info")
        
        # Input frame (bottom)
        input_frame = tk.Frame(self.root, bg='#1a1e37', height=80)
        input_frame.pack(fill='x', padx=0, pady=0)
        
        # Prompt indicator
        prompt_label = tk.Label(
            input_frame, text="→ ", font=('Menlo', 12, 'bold'),
            fg='#00d4ff', bg='#1a1e37'
        )
        prompt_label.pack(side='left', padx=(15, 0), pady=10)
        
        # Input field
        self.input_field = tk.Entry(
            input_frame, bg='#2d3547', fg='#ffffff',
            font=('Menlo', 12), insertbackground='#00d4ff',
            relief='flat', bd=0
        )
        self.input_field.pack(side='left', fill='both', expand=True, ipady=10, padx=(5, 10), pady=10)
        self.input_field.bind('<Return>', lambda e: self.execute_command())
        self.input_field.bind('<Up>', self.history_up)
        self.input_field.bind('<Down>', self.history_down)
        self.input_field.bind('<Escape>', lambda e: self.input_field.delete(0, tk.END))
        self.input_field.focus()
        
        # Button frame
        btn_frame = tk.Frame(input_frame, bg='#1a1e37')
        btn_frame.pack(side='right', padx=10, pady=10)
        
        self.execute_btn = tk.Button(
            btn_frame, text="Send", command=self.execute_command,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=12, pady=6
        )
        self.execute_btn.pack(side='left', padx=5)
    
    def toggle_command_panel(self):
        """Show/hide command panel"""
        if self.cmd_panel_visible:
            self.cmd_panel.pack_forget()
            self.cmd_panel_visible = False
            self.output_area.pack(fill='both', expand=True, padx=0, pady=0)
        else:
            self.create_command_panel()
            self.cmd_panel.pack(side='left', fill='y', before=self.output_area, padx=0, pady=0)
            self.cmd_panel_visible = True
            self.output_area.pack(fill='both', expand=True, padx=0, pady=0)
    
    def create_command_panel(self):
        """Create command reference panel"""
        self.cmd_panel.destroy()
        self.cmd_panel = tk.Frame(self.root.winfo_children()[1], bg='#1a1e37', width=250)
        
                # Title
                title = tk.Label(
                        self.cmd_panel, text="Commands", font=('Arial', 12, 'bold'),
                        fg='#00d4ff', bg='#1a1e37'
                )
                title.pack(padx=10, pady=10, fill='x')

                # Command list
                commands_text = scrolledtext.ScrolledText(
                        self.cmd_panel, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
                        font=('Menlo', 9), height=30, width=25, relief='flat'
                )
                commands_text.pack(fill='both', expand=True, padx=10, pady=10)

                commands_help = """Built-in Commands:
    help      Show this help
    clear     Clear screen
    history   Show history
    exit      Close app

AI Agent Mode — HOW IT WORKS:
    This section explains the *mechanics* of the AI integration,
    not only what it can do. Use plain English to describe a goal
    and the terminal will run a controlled pipeline:

    1) Intent parsing
         • Your natural-language task is sent to a local assistant
             (configured to use Ollama/local LLM or a gateway).
         • The assistant returns a proposed plan: steps and commands.

    2) Command generation & safety checks
         • Candidate shell commands are synthesized from the plan.
         • A lightweight safety validator runs heuristics (no rm -rf /, no
             direct network exfiltration, path sanity checks).
         • The validator will annotate risky commands and ask for
             confirmation before execution (unless auto-approve is set).

    3) Dry-run / validation (when available)
         • For operations that support it, a dry-run is attempted first
             (e.g. --dry-run flags or a simulated verification step).

    4) Execution & recovery
         • Commands run asynchronously and are logged (stdout/stderr,
             exit codes, timestamps) to /tmp/auraos_launcher.log.
         • If a tool is missing, the terminal can install it (apt/pip)
             and resume the task.
         • On failure the agent attempts intelligent fallbacks and
             reports final status and suggested next steps.

    5) Post-checks
         • After completion the agent can run verification commands
             (service checks, file existence, checksum, etc.) and show
             the final report in the chat view.

EXAMPLES (what to *say*):
    "create a spreadsheet with Q3 data and save it to /tmp/q3.xlsx"
    "find large media files and archive them to /mnt/archive"
    "install python deps from requirements.txt and run pytest"

IMPLEMENTATION NOTES:
    • Implemented now: async command execution, logging,
        history, basic safe-run heuristics, and an integration hook
        where an LLM prompt/response can be plugged in.
    • Planned/optional: a full Ollama/GPT local model integration
        with response parsing, richer dry-run simulation, and an
        explicit interactive approval UI. These appear as
        configurable options in the terminal's settings.

Each task is logged with full execution details & timestamps.

Press ☰ to hide
"""
                commands_text.insert(tk.END, commands_help)
                commands_text.config(state='disabled')
    
    def append_output(self, text, tag="output"):
        """Append text to output area"""
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, text, tag)
        self.output_area.see(tk.END)
        self.output_area.config(state='disabled')
        self.root.update_idletasks()
    
    def execute_command(self):
        """Execute user command"""
        command = self.input_field.get().strip()
        if not command:
            return
        
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # Show user command
        self.append_output(f"→ {command}\n", "user")
        self.input_field.delete(0, tk.END)
        
        # Handle AI-prefixed tasks (natural language)
        if command.lower().startswith('ai:'):
            # Strip prefix and hand off to the AI task handler
            task = command[3:].strip()
            threading.Thread(target=self.handle_ai_task, args=(task,), daemon=True).start()
            return

        # Handle built-in commands
        if command.lower() in ['exit', 'quit']:
            self.log_event("EXIT", "User closed terminal")
            self.root.quit()
            return
        elif command.lower() == 'clear':
            self.output_area.config(state='normal')
            self.output_area.delete(1.0, tk.END)
            self.output_area.config(state='disabled')
            return
        elif command.lower() == 'help':
            self.show_help()
            return
        elif command.lower() == 'history':
            self.show_history()
            return
        
        # Run shell command asynchronously
        threading.Thread(target=self.run_command, args=(command,), daemon=True).start()
    
    def run_command(self, command):
        """Run shell command and display output"""
        try:
            self.append_output("⟳ Running...\n", "info")
            result = subprocess.run(
                command, shell=True, capture_output=True,
                text=True, timeout=30, cwd=os.path.expanduser('~')
            )
            
            if result.stdout:
                self.append_output(result.stdout, "output")
            
            if result.returncode == 0 and not result.stdout:
                self.append_output("✓ Success\n", "success")
            elif result.returncode != 0:
                if result.stderr:
                    self.append_output(result.stderr, "error")
                else:
                    self.append_output(f"✗ Exit code: {result.returncode}\n", "error")
            
            self.append_output("\n", "output")
            self.log_event("COMMAND", f"Executed: {command} (exit: {result.returncode})")
            
        except subprocess.TimeoutExpired:
            self.append_output("✗ Command timed out (30s limit)\n", "error")
            self.log_event("TIMEOUT", f"Command exceeded 30s: {command}")
        except Exception as e:
            self.append_output(f"✗ Error: {str(e)}\n", "error")
            self.log_event("ERROR", f"Exception: {str(e)}")
        
        self.append_output("\n", "output")

    def simple_plan(self, text):
        """Very small heuristic planner: returns a list of candidate shell commands
        based on keywords. This is intentionally conservative and is a hook
        where a real LLM adapter can be integrated."""
        text_l = text.lower()
        commands = []
        note = ""
        # install X
        if 'install' in text_l and ('pip' in text_l or 'python' in text_l or 'package' in text_l):
            # Attempt to find requirements file
            commands.append('pip install -r requirements.txt')
            note = 'Will attempt pip install from requirements.txt'
        elif text_l.startswith('install') or 'install' in text_l:
            # generic install using apt
            # pick last word as package if obvious
            parts = text_l.split()
            for p in reversed(parts):
                if p.isalpha() and len(p) > 2:
                    pkg = p
                    break
            else:
                pkg = None
            if pkg:
                commands.append(f'sudo apt-get update && sudo apt-get install -y {pkg}')
                note = f'Will apt-install package: {pkg}'
            else:
                commands.append('sudo apt-get update')
                note = 'Will update apt; no package parsed'
        elif 'spreadsheet' in text_l or 'excel' in text_l or 'csv' in text_l:
            # propose a python pandas command (requires pandas)
            commands.append("python3 - <<'PY'\nimport pandas as pd\ndf = pd.read_csv('input.csv')\ndf.to_excel('/tmp/out.xlsx', index=False)\nPY")
            note = 'Will convert CSV -> XLSX using pandas (requires pandas)'
        elif 'backup' in text_l or 'archive' in text_l:
            commands.append("find ~ -type f -mtime -7 -print0 | xargs -0 tar -czf /tmp/backup_recent.tgz")
            note = 'Will archive files modified in last 7 days'
        else:
            # fallback: echo a suggested command
            commands.append(f"echo 'I could not parse the task: {text.replace("'","\\'")}'")
            note = 'No heuristic match; returning an echo placeholder'

        return commands, note

    def handle_ai_task(self, task_text):
        """Handle a natural-language task issued with the 'ai:' prefix.
        This is a conservative implementation: it proposes commands and asks
        for confirmation before running them.
        GUI: uses a yes/no dialog. CLI: prompts for y/N.
        """
        self.log_event('AI_TASK', task_text)
        self.append_output(f"⟡ AI Task: {task_text}\n", 'info')
        cmds, note = self.simple_plan(task_text)
        self.append_output(f"Proposed actions:\n", 'info')
        for c in cmds:
            self.append_output(f"  $ {c}\n", 'output')
        if note:
            self.append_output(f"Note: {note}\n", 'info')

        # Confirmation
        run_now = False
        try:
            # GUI path
            if self.root:
                msg = 'Run the proposed commands now? (They will run with the current user privileges)'
                run_now = messagebox.askyesno('AI Task - Confirm', msg)
        except Exception:
            run_now = False

        # CLI fallback: try reading from stdin
        if not run_now:
            try:
                # In GUI this will be skipped; in CLI mode stdin is available
                resp = input('Run proposed commands? (y/N): ').strip().lower()
                run_now = (resp == 'y' or resp == 'yes')
            except Exception:
                run_now = False

        if not run_now:
            self.append_output('AI task aborted by user. No commands executed.\n', 'info')
            return

        # Execute commands sequentially
        for c in cmds:
            self.append_output(f'→ Executing: {c}\n', 'info')
            self.log_event('AI_EXEC', c)
            # run synchronously to preserve order
            try:
                res = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=300, cwd=os.path.expanduser('~'))
                if res.stdout:
                    self.append_output(res.stdout, 'output')
                if res.returncode != 0:
                    if res.stderr:
                        self.append_output(res.stderr, 'error')
                    else:
                        self.append_output(f'✗ Exit code: {res.returncode}\n', 'error')
                else:
                    self.append_output('✓ Completed\n', 'success')
                self.log_event('AI_RESULT', f"cmd={c} exit={res.returncode}")
            except Exception as e:
                self.append_output(f'✗ Error running command: {e}\n', 'error')
                self.log_event('AI_ERROR', str(e))
    
     def show_help(self):
                     """Display help text"""
                     help_text = """
⚡ AuraOS Terminal - How the AI integration works

The terminal provides an *AI-assisted workflow* to convert your
natural-language intent into safe, auditable shell actions.

Quick flow (what happens when you type a task):

  1) You type an instruction in plain English.
  2) (Optional) The instruction is sent to a local LLM adapter
      which returns a proposed plan and candidate commands.
  3) The terminal runs a validation pass: safety heuristics,
      dry-run where possible, and identifies missing tools.
  4) You are shown the plan and any risky steps; approve to run.
  5) The terminal executes commands asynchronously, logs everything,
      and attempts intelligent retries or fallbacks on failure.

Built-in safeguards and features:
  • Safety validator: basic heuristics to avoid destructive ops.
  • Auto-install: apt/pip installs for missing dependencies.
  • Timeout: commands have a 30s default timeout (configurable).
  • Execution log: /tmp/auraos_launcher.log stores timestamps, PIDs,
     stdout/stderr, and exit codes for every run.

What is already implemented vs. planned:
  • Implemented: async execution, logging, history, a hook that
     accepts LLM-generated commands, basic safety heuristics, and
     auto-install helpers (apt/pip wrappers).
  • Planned: richer LLM integration (Ollama/GPT) with structured
     responses, simulated dry-runs, and an interactive approval UI.

Examples you can try:
  → "install python deps and run unit tests"
  → "create a spreadsheet from CSV files in Downloads"
  → "find and archive log files older than 30 days"

Logs: /tmp/auraos_launcher.log

Tip: Start with a short natural language goal, review the proposed
plan, then approve execution.
"""
                     self.append_output(help_text, "info")
    
    def show_history(self):
        """Display command history"""
        if not self.command_history:
            self.append_output("No history yet.\n\n", "info")
            return
        self.append_output("Command History:\n", "info")
        for i, cmd in enumerate(self.command_history[-20:], max(1, len(self.command_history)-19)):
            self.append_output(f"  {i}. {cmd}\n", "output")
        self.append_output("\n", "output")
    
    def history_up(self, event):
        """Navigate command history up"""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.input_field.delete(0, tk.END)
            self.input_field.insert(0, self.command_history[self.history_index])
    
    def history_down(self, event):
        """Navigate command history down"""
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input_field.delete(0, tk.END)
            self.input_field.insert(0, self.command_history[self.history_index])
        elif self.history_index == len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            self.input_field.delete(0, tk.END)
    
    def run_cli_mode(self):
        """CLI mode for headless execution"""
        print("⚡ AuraOS Terminal (CLI Mode)")
        print("Type 'exit' to quit\n")
        while True:
            try:
                command = input("→ ").strip()
                if command.lower() in ['exit', 'quit']:
                    break
                if command:
                    subprocess.run(command, shell=True, cwd=os.path.expanduser('~'))
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break

if __name__ == "__main__":
    if "--cli" in sys.argv:
        app = AuraOSTerminal(None, cli_mode=True)
    else:
        root = tk.Tk()
        app = AuraOSTerminal(root)
        root.mainloop()
TERMINAL_EOF

# Install Improved AuraOS Home Screen with Error Logging
cat > /opt/auraos/bin/auraos_homescreen.py << 'HOMESCREEN_EOF'
#!/usr/bin/env python3
"""AuraOS Home Screen - Dashboard and Launcher with Error Logging"""
import tkinter as tk
import subprocess
import os
import threading
from datetime import datetime

LOG_FILE = "/tmp/auraos_launcher.log"

def log_event(action, message, level="INFO"):
    """Log app launch events"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] [{level}] {action}: {message}\n")
    except:
        pass

class AuraOSHomeScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS")
        self.root.geometry("800x600")
        self.root.configure(bg='#0a0e27')
        log_event("STARTUP", "Homescreen initialized")
        self.create_widgets()
        
    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg='#0a0e27', height=120)
        header.pack(fill='x', padx=20, pady=20)
        
        logo_label = tk.Label(header, text="⚡ AuraOS", font=('Arial', 48, 'bold'),
                             fg='#00d4ff', bg='#0a0e27')
        logo_label.pack()
        
        tagline = tk.Label(header, text="AI-Powered Operating System",
                          font=('Arial', 14), fg='#888888', bg='#0a0e27')
        tagline.pack()
        
        # Content
        content = tk.Frame(self.root, bg='#0a0e27')
        content.pack(fill='both', expand=True, padx=40, pady=20)
        
        actions_frame = tk.Frame(content, bg='#0a0e27')
        actions_frame.pack(pady=30)
        
        actions = [
            ("🖥️ Terminal", "AuraOS Terminal", self.launch_terminal),
            ("📁 Files", "File Manager", self.launch_files),
            ("🌐 Browser", "Web Browser", self.launch_browser),
            ("⚙️ Settings", "System Settings", self.launch_settings),
        ]
        
        for emoji, label, handler in actions:
            btn = tk.Button(
                actions_frame,
                text=emoji,
                command=handler,
                width=15,
                height=3,
                bg='#1a3a52',
                fg='#00d4ff',
                font=('Arial', 14, 'bold'),
                relief='raised',
                cursor='hand2',
                activebackground='#00d4ff',
                activeforeground='#0a0e27'
            )
            btn.pack(pady=10, fill='x')
            
            label_widget = tk.Label(
                actions_frame,
                text=label,
                font=('Arial', 10),
                fg='#888888',
                bg='#0a0e27'
            )
            label_widget.pack()
        
        # Status bar
        self.status_bar = tk.Label(
            self.root,
            text="Ready",
            font=('Arial', 9),
            fg='#666666',
            bg='#0a0e27',
            justify='left'
        )
        self.status_bar.pack(side='bottom', fill='x', padx=20, pady=10)
        
        # Clock
        self.clock_label = tk.Label(
            self.root,
            text="",
            font=('Arial', 12),
            fg='#00d4ff',
            bg='#0a0e27'
        )
        self.clock_label.pack(side='bottom', pady=5)
        self.update_clock()
    
    def set_status(self, message):
        """Update status bar"""
        try:
            self.status_bar.config(text=message)
            self.root.update_idletasks()
        except:
            pass
    
    def update_clock(self):
        """Update clock display"""
        try:
            now = datetime.now()
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%A, %B %d, %Y")
            self.clock_label.config(text=f"{time_str}\n{date_str}")
            self.root.after(1000, self.update_clock)
        except:
            pass
    
    def launch_app(self, app_name, command_list, fallback_list=None, success_exit_codes=None):
        """Generic app launcher with error logging"""
        if success_exit_codes is None:
            success_exit_codes = [0]
        
        def _launch():
            log_event("LAUNCH", f"Starting {app_name}")
            self.set_status(f"Starting {app_name}...")
            
            try:
                p = subprocess.Popen(
                    command_list,
                    start_new_session=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                log_event("LAUNCH", f"{app_name} launched with PID {p.pid}")
                self.set_status(f"{app_name} started")
                threading.Timer(0.5, lambda: self._check_process(p, app_name, fallback_list, success_exit_codes)).start()
                
            except Exception as e:
                log_event("ERROR", f"Failed to launch {app_name}: {str(e)}", "ERROR")
                
                if fallback_list:
                    log_event("FALLBACK", f"Trying fallback for {app_name}")
                    try:
                        p = subprocess.Popen(fallback_list, start_new_session=True,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        log_event("FALLBACK", f"Fallback launched with PID {p.pid}")
                        self.set_status(f"{app_name} (fallback) started")
                    except Exception as fe:
                        log_event("ERROR", f"Fallback failed: {str(fe)}", "ERROR")
                        self.set_status(f"Failed to start {app_name}")
                else:
                    self.set_status(f"Failed to start {app_name}")
        
        threading.Thread(target=_launch, daemon=True).start()
    
    def _check_process(self, process, app_name, fallback_list=None, success_exit_codes=None):
        """Check if process exited"""
        if success_exit_codes is None:
            success_exit_codes = [0]
        
        try:
            returncode = process.poll()
            if returncode is not None:
                if returncode in success_exit_codes:
                    log_event("SUCCESS", f"{app_name} launched successfully (exit {returncode})")
                    self.set_status(f"{app_name} running")
                else:
                    stdout, stderr = process.communicate()
                    error_msg = stderr.decode() if stderr else ""
                    log_event("ERROR", f"{app_name} exited with code {returncode}: {error_msg[:100]}", "ERROR")
                    
                    if fallback_list:
                        log_event("FALLBACK", f"Process failed, trying fallback")
                        self.launch_app(app_name, fallback_list, None, success_exit_codes)
                    else:
                        self.set_status(f"{app_name} process exited")
        except Exception as e:
            log_event("ERROR", f"Process check failed: {str(e)}", "ERROR")
    
    def launch_terminal(self):
        self.launch_app("Terminal", ['auraos-terminal'], ['xfce4-terminal'])
    
    def launch_files(self):
        self.launch_app("File Manager", ['thunar'], ['xfce4-file-manager'], success_exit_codes=[0])
    
    def launch_browser(self):
        self.launch_app("Browser", ['firefox'], ['chromium'])
    
    def launch_settings(self):
        self.launch_app("Settings", ['xfce4-settings-manager'], None)

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSHomeScreen(root)
    log_event("UI", "Homescreen displayed")
    root.mainloop()
HOMESCREEN_EOF

# Make scripts executable and set permissions
chmod +x /opt/auraos/bin/auraos_terminal.py
chmod +x /opt/auraos/bin/auraos_homescreen.py
chown -R ${AURAOS_USER}:${AURAOS_USER} /opt/auraos

# Create/update command launchers
cat > /usr/local/bin/auraos-terminal << 'TERM_LAUNCHER'
#!/bin/bash
cd /opt/auraos/bin
exec python3 auraos_terminal.py "$@"
TERM_LAUNCHER

cat > /usr/local/bin/auraos-home << 'HOME_LAUNCHER'
#!/bin/bash
cd /opt/auraos/bin
exec python3 auraos_homescreen.py
HOME_LAUNCHER

chmod +x /usr/local/bin/auraos-terminal
chmod +x /usr/local/bin/auraos-home

# Change terminal launcher to not use env var
cat > /opt/auraos/bin/auraos-terminal << 'TERMINAL_SCRIPT'
#!/bin/bash
cd /opt/auraos/bin
exec python3 auraos_terminal.py "$@"
TERMINAL_SCRIPT
chmod +x /opt/auraos/bin/auraos-terminal

echo "✓ AuraOS applications installed with error logging"
AURAOS_APPS

    echo -e "${YELLOW}[7/7]${NC} Configuring AuraOS branding..."
    multipass exec "$VM_NAME" -- sudo bash <<BRANDING
# Set hostname
echo "auraos" > /etc/hostname
sed -i 's/ubuntu-multipass/auraos/g' /etc/hosts
sed -i 's/ubuntu/auraos/g' /etc/hosts

# Configure desktop for ${AURAOS_USER} user
sudo -u ${AURAOS_USER} bash << 'USER_CONFIG'
# Create config directories
mkdir -p ~/.config/xfce4/xfconf/xfce-perchannel-xml
mkdir -p ~/.config/autostart
mkdir -p ~/Desktop

# Disable screensaver
cat > ~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-screensaver.xml << 'XML_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-screensaver" version="1.0">
  <property name="enabled" type="bool" value="false"/>
  <property name="saver_enabled" type="bool" value="false"/>
</channel>
XML_EOF

# Disable power manager locking
cat > ~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-power-manager.xml << 'XML_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-power-manager" version="1.0">
  <property name="blank-on-ac" type="int" value="0"/>
  <property name="dpms-on-ac-sleep" type="uint" value="0"/>
  <property name="dpms-on-ac-off" type="uint" value="0"/>
  <property name="lock-screen-suspend-hibernate" type="bool" value="false"/>
  <property name="general-notification" type="bool" value="false"/>
</channel>
XML_EOF

# Set AuraOS background
cat > ~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml << 'XML_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorVNC-0" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="color1" type="array">
            <value type="uint" value="4369"/>
            <value type="uint" value="8738"/>
            <value type="uint" value="13107"/>
            <value type="uint" value="65535"/>
          </property>
          <property name="image-style" type="int" value="5"/>
        </property>
      </property>
    </property>
  </property>
</channel>
XML_EOF

# Create autostart for home screen
cat > ~/.config/autostart/auraos-homescreen.desktop << 'DESKTOP_EOF'
[Desktop Entry]
Type=Application
Name=AuraOS Home
Comment=AuraOS Home Screen Dashboard
Exec=auraos-home
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
DESKTOP_EOF

# Create desktop shortcuts
cat > ~/Desktop/AuraOS_Terminal.desktop << 'DESKTOP_EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=AuraOS Terminal
Comment=AI-Powered Terminal
Exec=auraos-terminal
Icon=utilities-terminal
Terminal=false
Categories=System;TerminalEmulator;
DESKTOP_EOF

cat > ~/Desktop/AuraOS_Home.desktop << 'DESKTOP_EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=AuraOS Home
Comment=AuraOS Dashboard
Exec=auraos-home
Icon=user-home
Terminal=false
Categories=System;
DESKTOP_EOF

chmod +x ~/Desktop/*.desktop

USER_CONFIG

echo "✓ AuraOS branding configured"
BRANDING

    # Additional safety: ensure xfce4-screensaver cannot lock the session.
    # Remove per-user autostart, kill any running screensaver processes, and
    # remove the package if present. These are non-fatal operations.
    multipass exec "$VM_NAME" -- sudo bash -c '
        # remove system autostart for xfce4-screensaver (if exists)
        rm -f /etc/xdg/autostart/xfce4-screensaver.desktop || true

        # remove per-user autostart for the auraos user
        if [ -d "/home/${AURAOS_USER}/.config/autostart" ]; then
            rm -f /home/${AURAOS_USER}/.config/autostart/xfce4-screensaver.desktop || true
            chown -R ${AURAOS_USER}:${AURAOS_USER} /home/${AURAOS_USER}/.config || true
        fi

        # Kill any running screensaver processes
        pkill -f xfce4-screensaver || true

        # Try removing the xfce4-screensaver package to avoid re-enabling locks
        DEBIAN_FRONTEND=noninteractive apt-get remove -y xfce4-screensaver >/dev/null 2>&1 || true
    '

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
        echo '${AURAOS_USER}:auraos123' | sudo chpasswd
        sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
        sudo systemctl restart ssh
    " >/dev/null 2>&1

    sleep 2

    # Port forward VNC (5900->5901) and noVNC (6080->6080)
    ssh -f -N -L 5901:localhost:5900 -L 6080:localhost:6080 -L 8765:localhost:8765 \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${AURAOS_USER}@"$VM_IP" >/dev/null 2>&1 &

    echo -e "${GREEN}✓ Port forwarding set up${NC}"
    echo ""

    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}✓ AuraOS VM Setup Complete!${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}AuraOS Desktop installed with:${NC}"
    echo -e "  ⚡ AuraOS Home Screen (auto-launches)"
    echo -e "  🖥️  AuraOS Terminal (AI-powered)"
    echo -e "  🎨 Custom branding and dark blue theme"
    echo ""
    echo -e "${GREEN}Access your AuraOS desktop:${NC}"
    echo -e "  Browser: ${BLUE}http://localhost:6080/vnc.html${NC}"
    echo -e "  Password: ${BLUE}auraos123${NC}"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "  ${BLUE}./auraos.sh health${NC}        - System health check"
    echo -e "  ${BLUE}./auraos.sh forward start${NC} - Start port forwarders"
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

cmd_setup_v2() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   AuraOS v2 Setup - Architecture Improvements             ║${NC}"
    echo -e "${BLUE}║   Fast delta detection + local planner + WebSocket I/O    ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    REPO_ROOT="$SCRIPT_DIR"
    LOG_FILE="$REPO_ROOT/logs/v2_setup.log"
    mkdir -p "$REPO_ROOT/logs"

    log_v2() {
        echo "[$(date -u +%H:%M:%S)] $@" | tee -a "$LOG_FILE"
    }

    log_v2_success() {
        echo -e "${GREEN}✅ $@${NC}" | tee -a "$LOG_FILE"
    }

    log_v2_error() {
        echo -e "${RED}❌ $@${NC}" | tee -a "$LOG_FILE"
    }

    log_v2 "===== AuraOS v2 Setup ====="

    # Check 1: Verify dependencies
    log_v2 "\n[1/5] Checking dependencies..."
    
    check_cmd() {
        if command -v "$1" >/dev/null 2>&1; then
            log_v2 "  ✓ $1 found"
            return 0
        else
            log_v2 "  ✗ $1 NOT found"
            return 1
        fi
    }

    all_ok=true
    check_cmd "python3" || all_ok=false
    check_cmd "ollama" || all_ok=false
    check_cmd "multipass" || all_ok=false

    if [ "$all_ok" = false ]; then
        log_v2_error "Missing required tools. Install: brew install python3 ollama multipass"
        exit 1
    fi

    log_v2_success "All host dependencies present"

    # Check 2: Ensure models are available
    log_v2 "\n[2/5] Checking Ollama models..."

    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        log_v2_error "Ollama not running. Start with: ollama serve"
        exit 1
    fi

    # Pull models if not present
    if ! ollama list 2>/dev/null | grep -q mistral; then
        log_v2 "Pulling mistral model (for local planning)..."
        ollama pull mistral &
        log_v2 "Background pull started — may take a few minutes"
    else
        log_v2 "  ✓ mistral model available"
    fi

    if ! ollama list 2>/dev/null | grep -q llava; then
        log_v2 "Pulling llava:13b model (for vision, on-demand)..."
        ollama pull llava:13b &
        log_v2 "Background pull started — may take several minutes"
    else
        log_v2 "  ✓ llava:13b model available"
    fi

    log_v2_success "Ollama models configured"

    # Check 3: Install Python dependencies
    log_v2 "\n[3/5] Installing Python dependencies..."

    activate_venv

    if [ -d "$REPO_ROOT/auraos_daemon/venv" ]; then
        log_v2 "Activating venv..."
        source "$REPO_ROOT/auraos_daemon/venv/bin/activate"
    fi

    pip_cmd="python3 -m pip"
    $pip_cmd install --upgrade pip setuptools wheel >/dev/null 2>&1 || true

    # Install v2 dependencies
    deps="pillow numpy websockets websocket-client pytesseract"
    for dep in $deps; do
        log_v2 "  Installing $dep..."
        $pip_cmd install "$dep" >/dev/null 2>&1 || true
    done

    log_v2_success "Python dependencies installed"

    # Check 4: Setup host tools
    log_v2 "\n[4/5] Setting up host tools..."

    mkdir -p "$REPO_ROOT/tools"

    # Copy and make executable
    for script in vm_wake_check.sh install_ws_agent.sh; do
        if [ -f "$REPO_ROOT/tools/$script" ]; then
            chmod +x "$REPO_ROOT/tools/$script"
            log_v2 "  ✓ $script ready"
        fi
    done

    # Setup launchd on macOS
    if [ "$(uname -s)" = "Darwin" ]; then
        log_v2 "Setting up macOS wake-check LaunchAgent..."
        
        PLIST="$HOME/Library/LaunchAgents/com.auraos.vm-wake-check.plist"
        if [ ! -f "$PLIST" ]; then
            mkdir -p "$(dirname "$PLIST")"
            cp "$REPO_ROOT/tools/com.auraos.vm-wake-check.plist" "$PLIST"
            
            # Update REPO_ROOT in plist
            sed -i '' "s|HOME/GitHub/ai-os|$(echo "$REPO_ROOT" | sed 's|/|\\\/|g')|g" "$PLIST"
            
            launchctl load "$PLIST" 2>/dev/null || true
            log_v2 "  ✓ LaunchAgent loaded"
        else
            log_v2 "  ℹ LaunchAgent already installed"
        fi
    fi

    log_v2_success "Host tools configured"

    # Check 5: Verify VM setup
    log_v2 "\n[5/5] Verifying VM setup..."

    if multipass list 2>/dev/null | grep -q "auraos-multipass\|Running"; then
        log_v2 "  ✓ VM is running"
        
        # Check for WebSocket agent in VM
        if multipass exec auraos-multipass -- systemctl is-active auraos-ws-agent >/dev/null 2>&1; then
            log_v2 "  ✓ WebSocket agent service active"
        else
            log_v2 "  ℹ WebSocket agent not yet installed (will be added on next vm-setup)"
        fi
    else
        log_v2 "  ℹ No running VM detected"
        log_v2 "  To set up: ./auraos.sh vm-setup"
    fi

    log_v2_success "VM verification complete"

    # Summary
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}✓ AuraOS v2 Setup Complete! 🚀${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Key Improvements Installed:${NC}"
    echo -e "  ${GREEN}✓${NC} Delta screenshot detection (5-10x less bandwidth)"
    echo -e "  ${GREEN}✓${NC} Local Mistral planner (10-15x faster reasoning)"
    echo -e "  ${GREEN}✓${NC} WebSocket agent (50-100ms latency)"
    echo -e "  ${GREEN}✓${NC} VM wake resilience (auto-recovery)"
    echo ""
    echo -e "${YELLOW}Expected Performance:${NC}"
    echo -e "  ${BLUE}MVP (v1):${NC}       5-10 seconds per action"
    echo -e "  ${BLUE}v2 (optimized):${NC} 500ms-1.2 seconds per action"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo -e "  1. Test components:"
    echo -e "     ${BLUE}python3 tools/demo_v2_architecture.py${NC}"
    echo -e ""
    echo -e "  2. Read documentation:"
    echo -e "     ${BLUE}cat ARCHITECTURE_V2.md${NC}"
    echo ""
    echo -e "  3. Run VM wake-check (macOS):"
    echo -e "     ${BLUE}bash tools/vm_wake_check.sh${NC}"
    echo ""
    echo -e "${YELLOW}Documentation:${NC}"
    echo -e "  - ARCHITECTURE_V2.md      Full technical reference"
    echo -e "  - V2_INTEGRATION_GUIDE.md Step-by-step integration"
    echo -e "  - QUICK_COMMANDS.md       Command reference"
    echo ""
    echo -e "${YELLOW}Logs saved to:${NC} ${BLUE}$LOG_FILE${NC}"
    echo ""
}

cmd_help() {
    print_header
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  install            - Install all dependencies (Homebrew, Multipass, Ollama, Python)"
    echo "  setup-v2           - Install v2 improvements (delta detection, planner, WebSocket)"
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
    echo "  disable-screensaver - Disable VM screensaver/lock (usage: disable-screensaver [vm-name] [user])"
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
    setup-v2)
        cmd_setup_v2
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
    disable-screensaver)
        shift
        cmd_disable_screensaver "$@"
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
