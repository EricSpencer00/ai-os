#!/usr/bin/env bash
set -euo pipefail

# open_vm_gui.sh
# Host helper to open the AuraOS VM GUI and agent from macOS.
# - Ensures your public SSH key is present in the VM
# - Starts SSH tunnels for VNC (host:5901 -> vm:5900) and agent (host:8765 -> vm:8765)
# - Opens the VNC URL on macOS (uses `open`)

INSTANCE="auraos-multipass"
VM_USER="ubuntu"
PUBKEY_FILE="${HOME}/.ssh/id_rsa.pub"
VNC_LOCAL_PORT=5901
VNC_REMOTE_PORT=5900
AGENT_LOCAL_PORT=8765
AGENT_REMOTE_PORT=8765

usage() {
  cat <<EOF
Usage: $(basename "$0") [--no-open] [--no-agent]

Options:
  --no-open    Don't call 'open' to launch the VNC URL (useful for testing)
  --no-agent   Don't create agent tunnel (only VNC)
  -h, --help   Show this help

This script must be run on the host (macOS) where Multipass is installed.
It will:
  - verify the Multipass instance exists
  - copy your public SSH key into the VM if missing
  - start SSH tunnels for VNC and agent (background)
  - open vnc://localhost:${VNC_LOCAL_PORT}

EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

NO_OPEN=0
NO_AGENT=0
for arg in "$@"; do
  case "$arg" in
    --no-open) NO_OPEN=1 ;;
    --no-agent) NO_AGENT=1 ;;
    *) ;;
  esac
done

check_instance() {
  if ! multipass list --format csv | awk -F, '{print $1}' | grep -qx "$INSTANCE"; then
    echo "Multipass instance '$INSTANCE' not found. Start it first (./start_vm_and_bootstrap.sh --gui)." >&2
    exit 2
  fi
}

get_ip() {
  multipass info "$INSTANCE" | awk -F: '/IPv4/ {gsub(/ /, "", $2); print $2; exit}'
}

ensure_pubkey_in_vm() {
  if [[ ! -f "$PUBKEY_FILE" ]]; then
    echo "Public key $PUBKEY_FILE not found. Generate one (ssh-keygen -t rsa) and retry." >&2
    exit 3
  fi

  # read public key (single line)
  PUBKEY_CONTENT=$(sed -n '1p' "$PUBKEY_FILE" | tr -d '\r')

  echo "Checking if public key is installed in VM..."
  if ! multipass exec "$INSTANCE" -- bash -lc "mkdir -p /home/${VM_USER}/.ssh && grep -F -- \"${PUBKEY_CONTENT}\" /home/${VM_USER}/.ssh/authorized_keys >/dev/null 2>&1"; then
    echo "Copying public key to VM..."
    multipass transfer "$PUBKEY_FILE" "$INSTANCE":/tmp/key.pub
    multipass exec "$INSTANCE" -- bash -lc "mkdir -p /home/${VM_USER}/.ssh && cat /tmp/key.pub >> /home/${VM_USER}/.ssh/authorized_keys && chown -R ${VM_USER}:${VM_USER} /home/${VM_USER}/.ssh && chmod 700 /home/${VM_USER}/.ssh && chmod 600 /home/${VM_USER}/.ssh/authorized_keys"
    echo "Public key copied."
  else
    echo "Public key already present in VM."
  fi
}

start_ssh_tunnel() {
  local LOCAL_PORT=$1
  local REMOTE_PORT=$2
  # if a localhost listener exists on LOCAL_PORT, assume tunnel present
  if lsof -iTCP:"${LOCAL_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Local port ${LOCAL_PORT} already listening — skipping tunnel creation."
    return 0
  fi

  echo "Starting SSH tunnel: localhost:${LOCAL_PORT} -> ${INSTANCE}:localhost:${REMOTE_PORT}"
  # Use -o StrictHostKeyChecking=no to avoid prompt on first run; user may prefer manual control
  ssh -f -N -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=no -L ${LOCAL_PORT}:localhost:${REMOTE_PORT} ${VM_USER}@${IP}
  sleep 0.2
  if lsof -iTCP:"${LOCAL_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Tunnel on ${LOCAL_PORT} established."
  else
    echo "Failed to establish tunnel on ${LOCAL_PORT}." >&2
    return 1
  fi
}

########
# Main
########
check_instance
IP=$(get_ip)
if [[ -z "$IP" ]]; then
  echo "Could not determine IP for $INSTANCE" >&2
  multipass info "$INSTANCE" || true
  exit 4
fi

echo "Found instance $INSTANCE with IP: $IP"

ensure_pubkey_in_vm

# Ensure VNC password exists inside the VM (non-interactive)
ensure_vnc_password_in_vm() {
  echo "Ensuring VNC password exists in VM..."
  # If the passwd file is missing or empty, create it using expect (non-interactive)
  multipass exec "$INSTANCE" -- bash -lc "if [ ! -s /home/${VM_USER}/.vnc/passwd ]; then echo 'creating VNC passwd inside VM'; sudo apt-get update -y >/dev/null 2>&1 || true; sudo apt-get install -y expect >/dev/null 2>&1 || true; mkdir -p /home/${VM_USER}/.vnc; rm -f /home/${VM_USER}/.vnc/passwd; expect -c 'spawn x11vnc -storepasswd /home/${VM_USER}/.vnc/passwd; expect \"Enter VNC password:\"; send \"auraos123\\r\"; expect \"Verify password:\"; send \"auraos123\\r\"; expect -re \"Write password to.*\\[y\\]/n\"; send \"y\\r\"; expect eof' && chown ${VM_USER}:${VM_USER} /home/${VM_USER}/.vnc/passwd && chmod 600 /home/${VM_USER}/.vnc/passwd; else echo 'VNC passwd exists'; fi"
  # restart service to pick up the file
  multipass exec "$INSTANCE" -- sudo systemctl restart auraos-x11vnc.service || true
}

ensure_vnc_password_in_vm

# Start VNC tunnel
start_ssh_tunnel ${VNC_LOCAL_PORT} ${VNC_REMOTE_PORT}

if [[ "$NO_AGENT" -eq 0 ]]; then
  start_ssh_tunnel ${AGENT_LOCAL_PORT} ${AGENT_REMOTE_PORT}
fi

echo "VNC available at vnc://localhost:${VNC_LOCAL_PORT} (password: auraos123)"
if [[ "$NO_AGENT" -eq 0 ]]; then
  echo "Agent API available at http://localhost:${AGENT_LOCAL_PORT} (tunneled)"
fi

if [[ "$NO_OPEN" -eq 0 ]]; then
  echo "Opening VNC client..."
  # Prefer TigerVNC viewer if installed (try a few common app names), otherwise fall back to macOS Screen Sharing
  # Try specific app bundle name the user provided first
  if [ -d "/Applications/TigerVNC Viewer 1.15.0.app" ]; then
    open -a "TigerVNC Viewer 1.15.0.app" --args localhost:${VNC_LOCAL_PORT} || true
  elif open -a "TigerVNC Viewer" --args localhost:${VNC_LOCAL_PORT} >/dev/null 2>&1; then
    open -a "TigerVNC Viewer" --args localhost:${VNC_LOCAL_PORT} || true
  elif open -a "TigerVNC Viewer.app" --args localhost:${VNC_LOCAL_PORT} >/dev/null 2>&1; then
    open -a "TigerVNC Viewer.app" --args localhost:${VNC_LOCAL_PORT} || true
  else
    # fallback to default vnc: URL handler (Screen Sharing)
    open "vnc://localhost:${VNC_LOCAL_PORT}" || echo "Use your VNC client to connect to vnc://localhost:${VNC_LOCAL_PORT}";
  fi
fi

exit 0
