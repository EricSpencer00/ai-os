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
    
    # Check 6: Port 6080
    echo -e "${YELLOW}[6/7]${NC} Port 6080 (noVNC)"
    if multipass exec auraos-multipass -- bash -c 'ss -tlnp 2>/dev/null | grep -q 6080' 2>/dev/null; then
        echo -e "${GREEN}✓ Listening on 6080${NC}"
    else
        echo -e "${RED}✗ Not listening on 6080${NC}"
        return 1
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

cmd_help() {
    print_header
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  status             - Show VM and service status"
    echo "  health             - Run system health check"
    echo "  gui-reset          - Complete clean restart of VNC/noVNC"
    echo "  screenshot         - Capture current VM screen"
    echo "  automate \"<task>\" - Run AI automation task"
    echo "  keys list          - List configured API keys"
    echo "  keys add           - Add API key: keys add <provider> <key>"
    echo "  keys ollama        - Configure Ollama models"
    echo "  logs               - Show GUI agent logs"
    echo "  restart            - Restart all VM services"
    echo "  help               - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 health                                    # Check all systems"
    echo "  $0 gui-reset                                 # Reset VNC/noVNC from scratch"
    echo "  $0 screenshot                                # Capture desktop"
    echo "  $0 automate \"click on file manager\"        # AI automation"
    echo "  $0 keys ollama llava:13b qwen2.5-coder:7b  # Switch vision model"
    echo ""
}

# Main command dispatcher
case "$1" in
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
