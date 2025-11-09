#!/usr/bin/env bash
# Start an Ubuntu VM using multipass (preferred on macOS M1) and run the existing bootstrap inside it.
# This is a fallback that is far more reliable on macOS than raw QEMU/cloud-image quirks.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BOOTSTRAP="$SCRIPT_DIR/vm_resources/bootstrap.sh"
NAME="auraos-multipass"
MEM=8192
CPUS=4
DISK=20G
IMAGE="jammy" # Ubuntu 22.04 LTS

function die(){ echo "$*" >&2; exit 1; }

if [ ! -f "$BOOTSTRAP" ]; then
  die "bootstrap not found at $BOOTSTRAP"
fi

if ! command -v multipass >/dev/null 2>&1; then
  die "multipass not installed. Install via Homebrew: brew install --cask multipass"
fi

if multipass list | grep -q "^$NAME\b"; then
  echo "Existing instance $NAME found — deleting to recreate"
  multipass delete -p "$NAME"
fi

# Create a cloud-init that writes the bootstrap and runs it
USER_DATA=$(mktemp -t auraos-cloudinit.XXXX)
cat > "$USER_DATA" <<'YAML'
#cloud-config
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: users, admin
    shell: /bin/bash
    lock_passwd: false
write_files:
  - path: /tmp/bootstrap.sh
    permissions: '0755'
    owner: root:root
    content: |
YAML

# Append bootstrap content, indenting by two spaces
sed 's/^/      /' "$BOOTSTRAP" >> "$USER_DATA"

cat >> "$USER_DATA" <<'YAML'

runcmd:
  - [ bash, -lc, "chmod +x /tmp/bootstrap.sh && sudo bash /tmp/bootstrap.sh" ]
YAML

echo "Launching multipass instance $NAME (this may take a minute)..."
multipass launch --name "$NAME" --mem "$MEM" --disk "$DISK" --cpus "$CPUS" --cloud-init "$USER_DATA" "$IMAGE"

echo "Waiting for instance to be ready..."
multipass exec "$NAME" -- sudo cloud-init status --wait

echo "Bootstrap should have run. You can shell into the VM with:"
echo "  multipass shell $NAME"
echo "Or SSH (multipass info $NAME will show the IPv4 address)."

rm -f "$USER_DATA"
echo "Done."
exit 0
