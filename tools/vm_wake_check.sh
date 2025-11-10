#!/usr/bin/env bash
# VM Wake Resilience Check — runs on host after sleep/wake
# Detects VM health and automatically remediates common issues
# 
# Usage:
#   ./tools/vm_wake_check.sh
#
# Or run automatically via launchd (macOS) / systemd (Linux) sleep hooks

set -euo pipefail

# Configuration
REPO_ROOT="${REPO_ROOT:-.}"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/vm_wake_check.log"
QEMU_PID_FILE="$LOG_DIR/qemu.pid"
BOOTSTRAP_LOG="$LOG_DIR/bootstrap.log"
BOOTSTRAP_DONE_MARKER="$LOG_DIR/bootstrap_done"
BOOTSTRAP_TIMEOUT_MARKER="$LOG_DIR/bootstrap_timed_out"

SSH_PORT=2222
VM_USER="auraos"
VM_PASS="auraos123"
MAX_RETRIES=3
HEALTH_CHECK_TIMEOUT=5

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function log() {
  local level=$1
  shift
  local msg="$@"
  local timestamp=$(date -u "+%Y-%m-%d %H:%M:%S UTC")
  echo -e "[${timestamp}] [${level}] ${msg}" | tee -a "$LOG_FILE"
}

function log_info() { log "INFO" "$@"; }
function log_warn() { log "WARN" "$@"; }
function log_error() { log "ERROR" "$@"; }
function log_success() { log "SUCCESS" "$@"; }

# Cleanup on exit
trap 'log_info "Wake check completed"' EXIT

log_info "===== VM Wake Check Started ====="

# Check 1: Is QEMU process running?
if [ -f "$QEMU_PID_FILE" ]; then
  QEMU_PID=$(cat "$QEMU_PID_FILE" 2>/dev/null || echo "")
  if [ -n "$QEMU_PID" ] && ps -p "$QEMU_PID" >/dev/null 2>&1; then
    log_success "QEMU process $QEMU_PID is running"
  else
    log_error "QEMU process $QEMU_PID not found — VM may have crashed"
    log_warn "Consider restarting VM with: ./run_and_bootstrap_vm.sh &"
    exit 1
  fi
else
  log_warn "No QEMU PID file found at $QEMU_PID_FILE"
  log_info "Assuming VM may be running; proceeding with SSH checks"
fi

# Check 2: Is SSH port open?
log_info "Checking SSH port $SSH_PORT..."
if command -v nc >/dev/null; then
  if nc -z -w 2 localhost $SSH_PORT 2>/dev/null; then
    log_success "SSH port $SSH_PORT is open"
  else
    log_warn "SSH port $SSH_PORT not responding — guest may not be ready or network interrupted"
    exit 1
  fi
else
  log_warn "nc (netcat) not found — skipping TCP check"
fi

# Check 3: Can we authenticate via SSH?
log_info "Testing SSH authentication..."
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=yes -o ConnectTimeout=$HEALTH_CHECK_TIMEOUT"

if timeout $HEALTH_CHECK_TIMEOUT ssh -p $SSH_PORT $SSH_OPTS $VM_USER@localhost 'echo AUTH_OK' >/dev/null 2>&1; then
  log_success "SSH authentication successful"
  SSH_OK=true
else
  log_warn "SSH authentication failed — cloud-init may still be running or bootstrap incomplete"
  SSH_OK=false
fi

# Check 4: Has bootstrap completed?
if [ "$SSH_OK" = true ]; then
  log_info "Checking bootstrap status..."
  
  # Check for a bootstrap-done marker file (optional, set by bootstrap script)
  if ssh -p $SSH_PORT $SSH_OPTS $VM_USER@localhost "test -f /var/log/auraos/bootstrap_done" >/dev/null 2>&1; then
    log_success "Bootstrap completed successfully (marker found)"
    rm -f "$BOOTSTRAP_TIMEOUT_MARKER" 2>/dev/null || true
    touch "$BOOTSTRAP_DONE_MARKER"
  else
    log_info "Bootstrap done marker not found — attempting to verify via service check"
    
    # Try to check if critical services are running
    if ssh -p $SSH_PORT $SSH_OPTS $VM_USER@localhost "systemctl is-active auraos-x11vnc >/dev/null 2>&1" >/dev/null 2>&1; then
      log_success "AuraOS services running (x11vnc detected)"
      touch "$BOOTSTRAP_DONE_MARKER"
    else
      log_warn "AuraOS services not fully running yet — may need bootstrap retry"
    fi
  fi
else
  log_warn "SSH not available — cannot verify bootstrap completion"
fi

# Check 5: Test GUI agent health endpoint
if [ "$SSH_OK" = true ]; then
  log_info "Checking GUI agent health..."
  
  if timeout 3 ssh -p $SSH_PORT $SSH_OPTS $VM_USER@localhost 'curl -s --max-time 2 http://127.0.0.1:8765/health' >/dev/null 2>&1; then
    log_success "GUI agent is responding on port 8765"
  else
    log_warn "GUI agent not responding — may need restart (systemctl restart auraos-gui-agent in VM)"
  fi
fi

# Check 6: Port forwarding status
log_info "Checking host port forwarders..."
# If using multipass, verify port forwarding rules are in place (this is automatic with multipass)
# If using SSH, verify SSH tunnel is still active
if command -v multipass >/dev/null; then
  log_info "Multipass detected — port forwarding managed automatically"
fi

# Remediation: Retry bootstrap if it timed out
if [ -f "$BOOTSTRAP_TIMEOUT_MARKER" ] && [ "$SSH_OK" = true ]; then
  log_warn "Previous bootstrap timed out — attempting retry..."
  
  # Check how many times we've already retried
  RETRY_COUNT=0
  if [ -f "$LOG_DIR/bootstrap_retries" ]; then
    RETRY_COUNT=$(cat "$LOG_DIR/bootstrap_retries")
  fi
  
  if [ "$RETRY_COUNT" -lt "$MAX_RETRIES" ]; then
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "$RETRY_COUNT" > "$LOG_DIR/bootstrap_retries"
    
    log_info "Bootstrap retry $RETRY_COUNT/$MAX_RETRIES..."
    
    # Attempt to re-run bootstrap on the guest
    BOOTSTRAP_SCRIPT="/tmp/bootstrap_guest_retry.sh"
    cat > "$BOOTSTRAP_SCRIPT" <<'RETRY_SCRIPT'
#!/bin/bash
# Lightweight bootstrap retry — checks if key services are up and starts them if needed
echo "Bootstrap retry: checking services..."

# Ensure auraos-x11vnc service is running
if ! systemctl is-active auraos-x11vnc >/dev/null 2>&1; then
  echo "Starting auraos-x11vnc service..."
  systemctl start auraos-x11vnc || systemctl restart auraos-x11vnc || true
fi

# Ensure auraos-novnc service is running
if ! systemctl is-active auraos-novnc >/dev/null 2>&1; then
  echo "Starting auraos-novnc service..."
  systemctl start auraos-novnc || systemctl restart auraos-novnc || true
fi

# Ensure auraos-gui-agent service is running
if ! systemctl is-active auraos-gui-agent >/dev/null 2>&1; then
  echo "Starting auraos-gui-agent service..."
  systemctl start auraos-gui-agent || systemctl restart auraos-gui-agent || true
fi

# Mark bootstrap as done
mkdir -p /var/log/auraos
touch /var/log/auraos/bootstrap_done
echo "Bootstrap retry completed"
RETRY_SCRIPT
    
    chmod +x "$BOOTSTRAP_SCRIPT"
    
    # Transfer and execute
    if scp -P $SSH_PORT $SSH_OPTS "$BOOTSTRAP_SCRIPT" $VM_USER@localhost:/tmp/bootstrap_retry.sh >/dev/null 2>&1; then
      if ssh -p $SSH_PORT $SSH_OPTS $VM_USER@localhost 'sudo bash /tmp/bootstrap_retry.sh' 2>&1 | tee -a "$BOOTSTRAP_LOG"; then
        log_success "Bootstrap retry successful"
        rm -f "$BOOTSTRAP_TIMEOUT_MARKER"
        touch "$BOOTSTRAP_DONE_MARKER"
      else
        log_warn "Bootstrap retry failed"
      fi
    else
      log_error "Failed to transfer bootstrap retry script"
    fi
    
    rm -f "$BOOTSTRAP_SCRIPT"
  else
    log_error "Bootstrap retry limit ($MAX_RETRIES) exceeded — manual intervention required"
  fi
fi

# Summary
log_info "===== Wake Check Summary ====="
if [ "$SSH_OK" = true ] && [ -f "$BOOTSTRAP_DONE_MARKER" ]; then
  log_success "VM is healthy and ready"
  exit 0
elif [ "$SSH_OK" = true ]; then
  log_warn "VM is partially responsive but bootstrap may be incomplete"
  exit 1
else
  log_error "VM is not responsive to SSH"
  exit 2
fi
