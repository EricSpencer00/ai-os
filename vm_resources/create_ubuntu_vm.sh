#!/usr/bin/env bash
# Create an Ubuntu ARM64 QEMU VM (cloud image) and a cloud-init seed ISO
# Intended to run on macOS (M1) or Linux hosts. This script does NOT boot the VM;
# it prepares the disk (qcow2) and the cloud-init ISO (seed.iso). After running
# it will print a recommended qemu-system-aarch64 command to start the VM.

set -euo pipefail

# Config
IMG_URL="https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-arm64.img"
BASE_IMG="images/ubuntu-jammy-arm64-base.img"
VM_IMG_DIR="images"
VM_DISK="images/auraos-vm.qcow2"
VM_DISK_SIZE="20G"
SEED_ISO="images/seed.iso"
USER_DATA_FILE="images/user-data"
META_DATA_FILE="images/meta-data"
HTTP_SERVE_DIR="."  # directory to serve files from if using http bootstrap
SSH_PUB_KEY_FILE="$HOME/.ssh/id_rsa.pub"

mkdir -p "$VM_IMG_DIR"

echo "[1/6] Checking for required tools..."
command -v qemu-system-aarch64 >/dev/null 2>&1 || { echo "qemu-system-aarch64 not found; please install QEMU (brew install qemu)"; exit 1; }
command -v qemu-img >/dev/null 2>&1 || { echo "qemu-img not found; please install QEMU (brew install qemu)"; exit 1; }

# genisoimage / mkisofs (cdrtools) preferred for creating the seed ISO
if command -v genisoimage >/dev/null 2>&1; then
    ISO_TOOL="genisoimage"
elif command -v mkisofs >/dev/null 2>&1; then
    ISO_TOOL="mkisofs"
else
    ISO_TOOL=""
fi

# macOS hdiutil fallback
IS_DARWIN=false
if [[ "$(uname -s)" == "Darwin" ]]; then
    IS_DARWIN=true
fi

echo "[2/6] Downloading base cloud image (if missing)..."
if [ ! -f "$BASE_IMG" ]; then
    echo "Downloading $IMG_URL -> $BASE_IMG"
    curl -L --progress-bar -o "$BASE_IMG" "$IMG_URL"
else
    echo "Base image already exists: $BASE_IMG"
fi

echo "[3/6] Creating VM disk (qcow2) with $VM_DISK_SIZE..."
## Use absolute paths for backing file and target disk so qemu-img resolves them correctly
ABS_BASE_IMG="$(cd "$VM_IMG_DIR" && pwd)/$(basename "$BASE_IMG")"
ABS_VM_DISK="$(cd "$VM_IMG_DIR" && pwd)/$(basename "$VM_DISK")"

if [ -f "$ABS_VM_DISK" ]; then
    echo "VM disk already exists: $ABS_VM_DISK"
else
  echo "Detecting backing file format for $ABS_BASE_IMG..."
  backing_fmt="qcow2"
  if qemu-img info "$ABS_BASE_IMG" >/dev/null 2>&1; then
    detected=$(qemu-img info "$ABS_BASE_IMG" 2>/dev/null | awk -F': ' '/file format|format:/{print $2; exit}') || true
    if [ -n "$detected" ]; then
      backing_fmt="$detected"
    fi
  fi

  echo "Using backing format: $backing_fmt"
  qemu-img create -f qcow2 -b "$ABS_BASE_IMG" -F "$backing_fmt" "$ABS_VM_DISK" "$VM_DISK_SIZE"
  echo "Created $ABS_VM_DISK (backed by $ABS_BASE_IMG)"
fi

echo "[4/6] Preparing cloud-init user-data/meta-data..."
# Default user-data: create user 'auraos' with password auraos123, enable ssh password auth
cat > "$USER_DATA_FILE" <<'EOF'
#cloud-config
users:
  - name: auraos
    gecos: AuraOS User
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: users, admin
    lock_passwd: false
    passwd: "$6$rounds=4096$saltsaltsalt$placeholderhash"
ssh_pwauth: true
chpasswd:
  list: |
    auraos:auraos123
  expire: False
ssh_authorized_keys: []
package_update: true
package_upgrade: true
runcmd:
  - [ bash, -lc, "echo 'Bootstrap placeholder: you can serve bootstrap.sh from host and curl it here' ]
EOF

# meta-data (minimal)
cat > "$META_DATA_FILE" <<EOF
instance-id: auraos-vm
local-hostname: auraos-vm
EOF

# Create seed ISO
echo "[5/6] Building seed ISO ($SEED_ISO)..."
# Resolve absolute path for seed ISO so helpers write to correct location
ABS_SEED_ISO="$(cd "$VM_IMG_DIR" && pwd)/$(basename "$SEED_ISO")"
if [ -f "$ABS_SEED_ISO" ]; then
  echo "Seed ISO already exists: $ABS_SEED_ISO"
else
  if [ -n "$ISO_TOOL" ]; then
    echo "Using $ISO_TOOL to build ISO"
    $ISO_TOOL -output "$ABS_SEED_ISO" -volid cidata -joliet -rock "$USER_DATA_FILE" "$META_DATA_FILE"
  elif [ "$IS_DARWIN" = true ]; then
    echo "Using macOS hdiutil to build ISO"
    # hdiutil expects a single source directory; create a temporary 'cidata' folder
    TMPDIR=$(mktemp -d)
    mkdir -p "$TMPDIR/cidata"
    cp "$USER_DATA_FILE" "$TMPDIR/cidata/user-data"
    cp "$META_DATA_FILE" "$TMPDIR/cidata/meta-data"
    (cd "$TMPDIR" && hdiutil makehybrid -o "$ABS_SEED_ISO" -iso -joliet -default-volume-name cidata cidata)
    rm -rf "$TMPDIR"
  else
    echo "No ISO creation tool found. Please install genisoimage (brew install cdrtools) or mkisofs."
    exit 1
  fi
  echo "Created seed ISO: $ABS_SEED_ISO"
  # Update the SEED_ISO variable used later for printing
  SEED_ISO="$ABS_SEED_ISO"
fi

echo "[6/6] Done. Next steps: start the VM with QEMU."

# Recommend qemu command depending on OS
if [ "$IS_DARWIN" = true ]; then
    ACCEL_OPTS='-accel hvf'
else
    ACCEL_OPTS='-accel tcg'
fi

cat <<EOF
To boot the VM (headless, with SSH port forwarded to host port 2222):

qemu-system-aarch64 \
  -machine virt,highmem=on \
  -cpu cortex-a72 \
  $ACCEL_OPTS \
  -m 4096 \
  -nographic \
  -smp 2 \
    -drive if=virtio,file=$ABS_VM_DISK,discard=unmap,cache=writeback \
    -drive if=none,file=$SEED_ISO,id=cidata,format=raw \
  -device virtio-blk-device,drive=cidata \
  -netdev user,id=net0,hostfwd=tcp::2222-:22 \
  -device virtio-net-device,netdev=net0

Then SSH in once the VM boots and cloud-init finishes (may take a minute):

ssh -p 2222 auraos@localhost
Password: auraos123

Notes:
- If you want the VM to have a graphical console, remove '-nographic' and add
  a virtio-gpu/display device. For initial bootstrap SSH access is easiest.
- To serve your local bootstrap.sh to the VM during first boot, run a simple HTTP server
  in the directory containing bootstrap.sh, e.g.:

  python3 -m http.server 8000

  And add a runcmd entry in user-data to curl http://<host-ip>:8000/bootstrap.sh and run it.

EOF

exit 0
