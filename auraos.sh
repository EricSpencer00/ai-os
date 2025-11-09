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

cmd_test() {
    echo -e "${GREEN}Running MVP test suite...${NC}"
    cd "$SCRIPT_DIR"
    python3 test_mvp.py
}

cmd_status() {
    echo -e "${GREEN}Checking system status...${NC}"
    echo ""
    echo -e "${BLUE}VM Status:${NC}"
    multipass list
    echo ""
    echo -e "${BLUE}VM Services:${NC}"
    multipass exec auraos-multipass -- systemctl status auraos-x11vnc.service --no-pager -l | head -n 4
    multipass exec auraos-multipass -- systemctl status auraos-novnc.service --no-pager -l | head -n 4
    multipass exec auraos-multipass -- systemctl status auraos-gui-agent.service --no-pager -l | head -n 4
    echo ""
    echo -e "${BLUE}Tunnels:${NC}"
    lsof -i :5901 -i :6080 -i :8765 | grep -v "COMMAND" || echo "No tunnels active"
}

cmd_gui() {
    echo -e "${GREEN}Opening VM GUI...${NC}"
    cd "$SCRIPT_DIR"
    ./open_vm_gui.sh
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
        echo -e "${GREEN}Enabling local Ollama...${NC}"
        python core/key_manager.py enable-ollama
    else
        echo -e "${YELLOW}Usage: $0 keys <list|add|ollama>${NC}"
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

cmd_help() {
    print_header
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  test              - Run comprehensive MVP test suite"
    echo "  status            - Show VM and service status"
    echo "  gui               - Open VM GUI (VNC + noVNC)"
    echo "  screenshot        - Capture current VM screen"
    echo "  keys list         - List configured API keys"
    echo "  keys add          - Add API key: keys add <provider> <key>"
    echo "  keys ollama       - Enable local Ollama"
    echo "  automate \"<task>\" - Run AI automation task"
    echo "  logs              - Show GUI agent logs"
    echo "  restart           - Restart all VM services"
    echo "  help              - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 test"
    echo "  $0 status"
    echo "  $0 screenshot"
    echo "  $0 keys add openai sk-proj-..."
    echo "  $0 automate \"click the terminal icon\""
    echo ""
}

# Main command dispatcher
case "$1" in
    test)
        cmd_test
        ;;
    status)
        cmd_status
        ;;
    gui)
        cmd_gui
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
