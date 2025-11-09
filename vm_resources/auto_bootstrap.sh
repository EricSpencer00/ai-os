#!/usr/bin/env bash
# Auto-bootstrap helper: waits for SSH on localhost:2222, then SCPs and runs bootstrap.sh inside the VM.
# Usage: ./vm_resources/auto_bootstrap.sh
# It will prompt for the 'auraos' user's password when scp/ssh runs (unless you have key-based auth).

set -euo pipefail

SSH_PORT=2222
SSH_USER="auraos"
HOST="localhost"
LOCAL_BOOTSTRAP_PATH="$(pwd)/vm_resources/bootstrap.sh"
REMOTE_BOOTSTRAP_PATH="/tmp/bootstrap.sh"
TIMEOUT=600
INTERVAL=2

if [ ! -f "$LOCAL_BOOTSTRAP_PATH" ]; then
  echo "Local bootstrap script not found: $LOCAL_BOOTSTRAP_PATH"
  echo "Run this from the repository root."
  exit 1
fi

echo "Waiting up to $TIMEOUT seconds for SSH on $HOST:$SSH_PORT..."
elapsed=0
while ! nc -z "$HOST" "$SSH_PORT"; do
  sleep $INTERVAL
  elapsed=$((elapsed + INTERVAL))
  printf '.'
  if [ $elapsed -ge $TIMEOUT ]; then
    echo "\nTimed out waiting for SSH on $HOST:$SSH_PORT"
    exit 2
  fi
done

echo "\nSSH is reachable — copying bootstrap script to VM..."

# Copy file (will prompt for password if required)
scp -P "$SSH_PORT" "$LOCAL_BOOTSTRAP_PATH" "$SSH_USER"@"$HOST":"$REMOTE_BOOTSTRAP_PATH"

echo "Running bootstrap inside VM (this will prompt for sudo password)..."
ssh -p "$SSH_PORT" "$SSH_USER"@"$HOST" "sudo bash $REMOTE_BOOTSTRAP_PATH"

echo "Bootstrap finished (if the script succeeded)."
exit 0
