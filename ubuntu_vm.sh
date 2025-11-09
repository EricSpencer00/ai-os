#!/usr/bin/env bash
# ubuntu_vm.sh - Host-side wrapper for Ubuntu VM automation
# Usage: ./ubuntu_vm.sh <command> [args...]

set -euo pipefail

INSTANCE="auraos-multipass"
AGENT_PORT=8765

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [args...]

Commands:
  screenshot [file]     - Capture screenshot (via agent API)
  click X Y [button]    - Click at coordinates
  type "text"           - Type text
  ensure-desktop        - Ensure XFCE session is running
  install-packages      - Install automation tools in VM
  exec <cmd>            - Execute command in VM
  shell                 - Open shell in VM
  
Examples:
  $(basename "$0") screenshot /tmp/screen.png
  $(basename "$0") click 640 360
  $(basename "$0") type "Hello, world!"
  $(basename "$0") ensure-desktop
  $(basename "$0") exec ps aux | grep xfce

EOF
}

if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  usage
  exit 0
fi

COMMAND="$1"
shift

case "$COMMAND" in
  screenshot)
    OUTPUT="${1:-/tmp/vm_screenshot_$(date +%Y%m%d_%H%M%S).png}"
    echo "Capturing screenshot via agent API..."
    if curl -sS -m 10 "http://localhost:${AGENT_PORT}/screenshot" -o "$OUTPUT"; then
      echo "✓ Screenshot saved: $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
      file "$OUTPUT"
    else
      echo "✗ Screenshot failed. Is the agent running? Try: ./open_vm_gui.sh" >&2
      exit 1
    fi
    ;;
    
  click)
    if [[ $# -lt 2 ]]; then
      echo "Usage: $0 click X Y [button]" >&2
      exit 1
    fi
    X="$1"
    Y="$2"
    BUTTON="${3:-1}"
    echo "Clicking at ($X, $Y) button $BUTTON..."
    if curl -sS -m 5 "http://localhost:${AGENT_PORT}/click" \
         -H "Content-Type: application/json" \
         -d "{\"x\": $X, \"y\": $Y, \"button\": $BUTTON}" | grep -q success; then
      echo "✓ Click executed"
    else
      echo "✗ Click failed" >&2
      exit 1
    fi
    ;;
    
  type)
    if [[ $# -lt 1 ]]; then
      echo "Usage: $0 type \"text\"" >&2
      exit 1
    fi
    TEXT="$1"
    echo "Typing: $TEXT"
    multipass exec "$INSTANCE" -- /opt/auraos/bin/type_text.sh "$TEXT"
    ;;
    
  ensure-desktop)
    echo "Ensuring XFCE desktop is running..."
    multipass exec "$INSTANCE" -- sudo /opt/auraos/bin/ensure_desktop.sh
    ;;
    
  install-packages)
    echo "Installing automation packages in VM..."
    multipass exec "$INSTANCE" -- sudo /opt/auraos/bin/install_packages.sh
    ;;
    
  exec)
    multipass exec "$INSTANCE" -- "$@"
    ;;
    
  shell)
    multipass shell "$INSTANCE"
    ;;
    
  *)
    echo "Unknown command: $COMMAND" >&2
    usage
    exit 1
    ;;
esac
