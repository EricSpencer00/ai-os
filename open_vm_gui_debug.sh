#!/usr/bin/env bash
set -euo pipefail

# open_vm_gui_debug.sh
# Host-side helper to (1) create tunnels, (2) verify agent and screenshots, (3) open noVNC/VNC,
# and (4) if the screen is black, print relevant VM logs to help debug.

INSTANCE="auraos-multipass"
VM_USER="ubuntu"
VNC_LOCAL=5901
VNC_REMOTE=5900
NOVNC_LOCAL=6080
NOVNC_REMOTE=6080
AGENT_LOCAL=8765
AGENT_REMOTE=8765

usage(){
  cat <<EOF
Usage: $(basename "$0") [--no-open]

--no-open    Don't automatically open browser/VNC client. Useful when debugging.
EOF
}

NO_OPEN=0
if [[ "${1:-}" == "--no-open" ]]; then
  NO_OPEN=1
fi

# helpers
get_ip(){
  multipass info "$INSTANCE" | awk -F: '/IPv4/ {gsub(/ /, "", $2); print $2; exit}'
}

start_tunnel(){
  local lport=$1
  local rport=$2
  local ip=$3
  if lsof -iTCP:"${lport}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Local port ${lport} already listening - skipping tunnel"
    return 0
  fi
  echo "Starting SSH tunnel: localhost:${lport} -> ${ip}:localhost:${rport}"
  ssh -f -N -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=no -L ${lport}:localhost:${rport} ${VM_USER}@${ip} || {
    echo "Failed to create SSH tunnel to ${VM_USER}@${ip}. Ensure you can SSH (public key) or run open_vm_gui.sh first." >&2
    return 1
  }
  sleep 0.2
}

wait_for_agent(){
  local retries=10
  local i=0
  while (( i < retries )); do
    if curl -sSf -m 3 "http://localhost:${AGENT_LOCAL}/health" >/dev/null 2>&1; then
      echo "Agent is healthy"
      return 0
    fi
    i=$((i+1))
    sleep 1
  done
  echo "Agent did not respond after ${retries}s"
  return 1
}

fetch_screenshot(){
  local out=$1
  if ! curl -sS -m 8 "http://localhost:${AGENT_LOCAL}/screenshot" -o "${out}"; then
    return 1
  fi
  # basic sanity: non-empty
  if [[ ! -s "${out}" ]]; then
    return 1
  fi
  return 0
}

# Main
if ! multipass list --format csv | awk -F, '{print $1}' | grep -qx "$INSTANCE"; then
  echo "Multipass instance '$INSTANCE' not found. Start it first (./start_vm_and_bootstrap.sh --gui)." >&2
  exit 2
fi
IP=$(get_ip)
if [[ -z "$IP" ]]; then
  echo "Could not determine IP for $INSTANCE" >&2
  multipass info "$INSTANCE" || true
  exit 3
fi

echo "Found instance $INSTANCE at $IP"

# start tunnels
start_tunnel ${VNC_LOCAL} ${VNC_REMOTE} ${IP} || true
start_tunnel ${NOVNC_LOCAL} ${NOVNC_REMOTE} ${IP} || true
start_tunnel ${AGENT_LOCAL} ${AGENT_REMOTE} ${IP} || true

# Wait for agent and try to fetch screenshot
if wait_for_agent; then
  OUT="/tmp/auraos_debug_$(date +%s).png"
  if fetch_screenshot "${OUT}"; then
    echo "Screenshot saved to ${OUT} (size: $(wc -c <"${OUT}") bytes)"
    if [[ ${NO_OPEN} -eq 0 ]]; then
      open "${OUT}" || echo "Open failed - view ${OUT} manually"
    fi
  else
    echo "Failed to fetch screenshot from agent. Will attempt to restart auraos-x11vnc.service on VM and retry once."
    multipass exec "$INSTANCE" -- sudo systemctl restart auraos-x11vnc.service || true
    sleep 2
    if fetch_screenshot "/tmp/auraos_debug_retry.png"; then
      echo "Screenshot after restart saved to /tmp/auraos_debug_retry.png"
      if [[ ${NO_OPEN} -eq 0 ]]; then
        open "/tmp/auraos_debug_retry.png" || true
      fi
    else
      echo "Screenshot still failing after restart. Collecting VM logs for diagnosis..." >&2
      echo "--- last 200 lines of auraos-x11vnc.service journal ---"
      multipass exec "$INSTANCE" -- sudo journalctl -u auraos-x11vnc.service -n 200 --no-pager || true
      echo
      echo "--- /var/log/x11vnc_manual.log (tail 200) ---"
      multipass exec "$INSTANCE" -- sudo sh -c 'test -f /var/log/x11vnc_manual.log && tail -n 200 /var/log/x11vnc_manual.log || echo "no x11vnc_manual.log"' || true
      echo
      echo "--- /home/ubuntu/xfce_start.log (tail 200) ---"
      multipass exec "$INSTANCE" -- sudo sh -c 'test -f /home/ubuntu/xfce_start.log && tail -n 200 /home/ubuntu/xfce_start.log || echo "no xfce_start.log"' || true
      echo
      echo "If logs show 'black' or tile-cache messages, try: multipass exec $INSTANCE -- sudo systemctl restart auraos-x11vnc.service" >&2
    fi
  fi
else
  echo "Agent unavailable - cannot capture screenshot. Try running ./open_vm_gui.sh to set up tunnels and keys, or check multipass/SSH connectivity." >&2
fi

# Open noVNC and vnc handler if requested
if [[ ${NO_OPEN} -eq 0 ]]; then
  echo "Opening noVNC in browser: http://localhost:${NOVNC_LOCAL}"
  open "http://localhost:${NOVNC_LOCAL}" || true
  echo "Opening vnc://localhost:${VNC_LOCAL} (if your VNC client handles vnc: urls)"
  open "vnc://localhost:${VNC_LOCAL}" || true
fi

echo "Done. If you still see a black screen, reply with the output above or run this script with --no-open and paste the logs."
