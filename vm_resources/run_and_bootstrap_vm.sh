#!/usr/bin/env bash
# One-shot helper: prepare ARM Ubuntu cloud VM, start QEMU, wait for SSH, and run bootstrap.sh inside the VM.
# Usage: ./vm_resources/run_and_bootstrap_vm.sh
# Intended to run on host (macOS M1 or Linux). It will NOT run the VM in a GUI; it runs headless with -nographic

set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
IMAGES_DIR="$REPO_ROOT/images"
mkdir -p "$IMAGES_DIR"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"

# Config — adjust as needed
IMG_URL="https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-arm64.img"
BASE_IMG="$IMAGES_DIR/ubuntu-jammy-arm64-base.img"
VM_DISK="$IMAGES_DIR/auraos-vm.qcow2"
VM_DISK_SIZE="20G"
USER_DATA_FILE="$IMAGES_DIR/user-data"
META_DATA_FILE="$IMAGES_DIR/meta-data"
SEED_ISO="$IMAGES_DIR/seed.iso"
SSH_PORT=2222
VM_RAM=16384
VM_CPUS=6
QEMU_LOG="$LOG_DIR/qemu.log"
SERIAL_LOG="$LOG_DIR/qemu_serial.log"
BOOTSTRAP_LOCAL="$REPO_ROOT/vm_resources/bootstrap.sh"
REMOTE_BOOTSTRAP="/tmp/bootstrap.sh"

# Helpers
function die(){ echo "$*" >&2; exit 1; }
function has(){ command -v "$1" >/dev/null 2>&1; }

# Function to display a progress bar
function progress_bar() {
  local progress=$1
  local total=$2
  local width=50
  local percent=$((progress * 100 / total))
  local filled=$((progress * width / total))
  local empty=$((width - filled))

  printf "\r["
  for ((i = 0; i < filled; i++)); do printf "#"; done
  for ((i = 0; i < empty; i++)); do printf "-"; done
  printf "] %d%%" "$percent"
}

# Update progress bar at each step
steps=8
current_step=0

echo "[1/8] Checking required tools..."
has qemu-system-aarch64 || die "qemu-system-aarch64 not found. Install QEMU (brew install qemu)"
has qemu-img || die "qemu-img not found. Install QEMU (brew install qemu)"

ISO_TOOL=""
if has genisoimage; then ISO_TOOL=genisoimage
elif has mkisofs; then ISO_TOOL=mkisofs
fi
IS_DARWIN=false
if [[ "$(uname -s)" == "Darwin" ]]; then IS_DARWIN=true; fi

if [ "$IS_DARWIN" = true ] && [ -z "$ISO_TOOL" ]; then
  # macOS will use hdiutil fallback later
  echo "macOS detected; will use hdiutil if genisoimage/mkisofs are absent"
fi

if [ ! -f "$BOOTSTRAP_LOCAL" ]; then
  die "bootstrap.sh not found at $BOOTSTRAP_LOCAL — put your bootstrap script there"
fi

# Choose the best available accelerator for QEMU to reduce hiccups.
# On macOS use HVF, on Linux prefer KVM if /dev/kvm exists, otherwise fall back to TCG.
ACCEL_ARG=""
if [ "$IS_DARWIN" = true ]; then
  ACCEL_ARG="-accel hvf"
else
  if [ -c /dev/kvm ] || [ -w /dev/kvm ] 2>/dev/null; then
    ACCEL_ARG="-accel kvm"
  else
    ACCEL_ARG="-accel tcg"
  fi
fi

current_step=$((current_step + 1))
progress_bar $current_step $steps

echo "[2/8] Downloading base cloud image (if missing)..."
if [ ! -f "$BASE_IMG" ]; then
  curl -L --progress-bar -o "$BASE_IMG" "$IMG_URL" || die "failed to download base image"
else
  echo "Base image already exists: $BASE_IMG"
fi

current_step=$((current_step + 1))
progress_bar $current_step $steps

echo "[3/8] Creating VM disk (qcow2) with $VM_DISK_SIZE..."
ABS_BASE_IMG="$BASE_IMG"
ABS_VM_DISK="$VM_DISK"
if [ -f "$ABS_VM_DISK" ]; then
  echo "VM disk already exists: $ABS_VM_DISK"
else
  echo "Detecting backing file format for $ABS_BASE_IMG..."
  backing_fmt="qcow2"
  if qemu-img info "$ABS_BASE_IMG" >/dev/null 2>&1; then
    detected=$(qemu-img info "$ABS_BASE_IMG" 2>/dev/null | awk -F': ' '/file format|format:/{print $2; exit}') || true
    if [ -n "$detected" ]; then backing_fmt="$detected"; fi
  fi
  echo "Using backing format: $backing_fmt"
  qemu-img create -f qcow2 -b "$ABS_BASE_IMG" -F "$backing_fmt" "$ABS_VM_DISK" "$VM_DISK_SIZE"
  echo "Created $ABS_VM_DISK (backed by $ABS_BASE_IMG)"
fi

current_step=$((current_step + 1))
progress_bar $current_step $steps

echo "[4/8] Preparing cloud-init user-data/meta-data..."
# If the host has an SSH public key, inject it into cloud-init for passwordless login
SSH_PUB="$HOME/.ssh/id_rsa.pub"
if [ -f "$SSH_PUB" ]; then
  SSH_KEY_CONTENT=$(sed -n '1p' "$SSH_PUB")
else
  SSH_KEY_CONTENT=""
fi
## Generate a SHA512 password hash for cloud-init. Prefer openssl on macOS/Linux.
PASS_HASH=""
if has openssl; then
  # generate a short random salt
  SALT=$(openssl rand -hex 6)
  PASS_HASH=$(openssl passwd -6 -salt "$SALT" "auraos123") || PASS_HASH=""
else
  # Fallback to python crypt if available
  if python3 -c "import crypt" >/dev/null 2>&1; then
    PASS_HASH=$(python3 -c "import crypt; print(crypt.crypt('auraos123', crypt.mksalt(crypt.METHOD_SHA512)))")
  else
    PASS_HASH=""
  fi
fi

cat > "$USER_DATA_FILE" <<EOF
#cloud-config
users:
  - name: auraos
    gecos: AuraOS User
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: users, admin
    lock_passwd: false
    passwd: "${PASS_HASH}"
ssh_pwauth: true
chpasswd:
  list: |
    auraos:auraos123
  expire: False
ssh_authorized_keys:
EOF
if [ -n "$SSH_KEY_CONTENT" ]; then
  printf "  - %s\n" "$SSH_KEY_CONTENT" >> "$USER_DATA_FILE"
fi

# Include the bootstrap script in cloud-init so it runs on first boot. This
# avoids SCP races where SSH is up but user provisioning isn't complete yet.
cat >> "$USER_DATA_FILE" <<'EOF'
package_update: false
package_upgrade: false
write_files:
  - path: /tmp/bootstrap.sh
    permissions: '0755'
    owner: root:root
    content: |
EOF
# Append the bootstrap.sh content, indenting by 6 spaces to fit under YAML block
while IFS= read -r _line; do
  # If the last line is empty this preserves empty lines too
  printf '      %s\n' "$_line" >> "$USER_DATA_FILE"
done < "$BOOTSTRAP_LOCAL"

cat >> "$USER_DATA_FILE" <<'EOF'

runcmd:
  # Make sure the bootstrap is executable and run it as root
  - [ bash, -lc, "chmod +x /tmp/bootstrap.sh && /tmp/bootstrap.sh" ]
EOF

cat > "$META_DATA_FILE" <<EOF
instance-id: auraos-vm
local-hostname: auraos-vm
EOF

current_step=$((current_step + 1))
progress_bar $current_step $steps

echo "[5/8] Building seed ISO ($SEED_ISO)..."
ABS_SEED_ISO="$SEED_ISO"
if [ -f "$ABS_SEED_ISO" ]; then
  echo "Seed ISO already exists: $ABS_SEED_ISO"
else
  if [ -n "$ISO_TOOL" ]; then
    echo "Using $ISO_TOOL to build ISO"
    $ISO_TOOL -output "$ABS_SEED_ISO" -volid cidata -joliet -rock "$USER_DATA_FILE" "$META_DATA_FILE"
  elif [ "$IS_DARWIN" = true ]; then
    echo "Using macOS hdiutil to build ISO"
    TMPDIR=$(mktemp -d)
    mkdir -p "$TMPDIR/cidata"
    cp "$USER_DATA_FILE" "$TMPDIR/cidata/user-data"
    cp "$META_DATA_FILE" "$TMPDIR/cidata/meta-data"
    (cd "$TMPDIR" && hdiutil makehybrid -o "$ABS_SEED_ISO" -iso -joliet -default-volume-name cidata cidata)
    rm -rf "$TMPDIR"
  else
    die "No ISO creation tool found. Please install genisoimage (brew install cdrtools) or mkisofs."
  fi
  echo "Created seed ISO: $ABS_SEED_ISO"
fi

current_step=$((current_step + 1))
progress_bar $current_step $steps

# Ensure log file exists
: > "$QEMU_LOG"
# Ensure serial log file exists too (QEMU will write to it). Creating it here
# makes it clear to the user and ensures predictable ownership/permissions.
: > "$SERIAL_LOG"

echo "[6/8] Starting QEMU (background) — logs: $QEMU_LOG"
# Start QEMU in background and redirect stdout/stderr to log. Use setsid so it keeps running when this script exits.
QEMU_CMD=(qemu-system-aarch64
  -machine virt,highmem=on
  -cpu cortex-a72
  ${ACCEL_ARG}
  -m $VM_RAM
  -smp $VM_CPUS
  -drive if=virtio,file="$ABS_VM_DISK",discard=unmap,cache=writeback
  # Attach the cloud-init seed ISO as a virtio-backed block device (cidata)
  -drive if=none,file="$ABS_SEED_ISO",id=cidata,format=raw
  -device virtio-blk-device,drive=cidata
  -netdev user,id=net0,hostfwd=tcp::${SSH_PORT}-:22
  -device virtio-net-device,netdev=net0
  # Serial handling: use file logging by default, but support DEBUG mode which
  # attaches the serial/monitor to the terminal (easier for interactive debugging).
  
  # SERIAL_ARG will be expanded into the QEMU command below
  
  -overcommit mem-lock=off
)

# Decide how to attach the serial port
if [ "${DEBUG:-}" = "1" ] || [ "${DEBUG:-}" = "true" ]; then
  # In DEBUG mode write the serial console to the serial log file and expose
  # the QEMU monitor on a local telnet port so we don't steal the controlling
  # terminal. This avoids QEMU holding the terminal's stdio (which happened
  # under sudo/nohup) while still providing an interactive monitor.
  SERIAL_ARG=( -serial "file:$SERIAL_LOG" -monitor telnet:127.0.0.1:4444,server,nowait -nographic )
else
  SERIAL_ARG=( -serial "file:$SERIAL_LOG" )
fi

# Insert SERIAL_ARG into command (replace placeholder if present)
QEMU_CMD+=( "${SERIAL_ARG[@]}" )

# Start QEMU. In DEBUG mode we run it in foreground so the VM console is visible.
if [ "${DEBUG:-}" = "1" ] || [ "${DEBUG:-}" = "true" ]; then
  "${QEMU_CMD[@]}" 2>&1 | tee -a "$QEMU_LOG"
  QEMU_PID=$!
else
  # Start QEMU in background, prefer nohup on macOS where setsid may be absent
  if has nohup; then
    nohup "${QEMU_CMD[@]}" > "$QEMU_LOG" 2>&1 &
    QEMU_PID=$!
  else
    "${QEMU_CMD[@]}" > "$QEMU_LOG" 2>&1 &
    QEMU_PID=$!
  fi
fi
sleep 1
if ! ps -p "$QEMU_PID" >/dev/null 2>&1; then
  die "QEMU failed to start (pid $QFEMU_PID). Check $QEMU_LOG"
fi

echo "QEMU started with PID $QEMU_PID"

current_step=$((current_step + 1))
progress_bar $current_step $steps

# Wait until SSH authentication works (not just TCP open).
# TCP open can occur before cloud-init sets up users/keys; test auth by running a harmless command.
echo "[7/8] Waiting for SSH on localhost:$SSH_PORT..." | tee -a "$LOG_DIR/bootstrap.log"
# wait up to 600s
timeout=600
elapsed=0
while true; do
  # First check TCP quick, to avoid heavy SSH attempts when port closed
  if ! nc -z localhost $SSH_PORT; then
    printf '.'
    sleep 2
    elapsed=$((elapsed+2))
  else
    # Try authenticating using key-based auth (non-interactive). If the host key is unknown
    # we previously set StrictHostKeyChecking=no so this should not block.
    ssh -o BatchMode=yes -o ConnectTimeout=5 -p $SSH_PORT auraos@localhost 'echo AUTH_OK' >/dev/null 2>&1 && break || true
    # If key auth fails, try password auth non-interactively is tricky; at least try to detect
    # whether SSH will accept a password by forcing password auth (this will still fail here
    # without an automated password tool, but will reveal whether server is closing immediately).
    ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o ConnectTimeout=5 -p $SSH_PORT auraos@localhost 'echo AUTH_OK' >/dev/null 2>&1 && break || true

    # Not yet ready — sleep and retry.
    printf '.'
    sleep 2
    elapsed=$((elapsed+2))
  fi

  if [ $elapsed -ge $timeout ]; then
    echo "\nTimed out waiting for SSH authentication. Check $QEMU_LOG and $LOG_DIR/bootstrap.log"
    exit 2
  fi
done

echo "\nSSH authenticated — copying bootstrap and running it inside VM" | tee -a "$LOG_DIR/bootstrap.log"
# Copy and execute bootstrap
if ! nc -z localhost $SSH_PORT; then
  echo "Failed to connect to SSH on localhost:$SSH_PORT" >> "$LOG_DIR/bootstrap.log"
  exit 2
fi

# Use SSH options to bypass host key verification and enable password-based auth
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=yes"

echo "Copying bootstrap script..." | tee -a "$LOG_DIR/bootstrap.log"
# Attempt scp with a few retries to avoid racing with late cloud-init restarts
max_retries=6
attempt=1
while true; do
  echo "Attempt $attempt: copying bootstrap script..." | tee -a "$LOG_DIR/bootstrap.log"
  scp -P $SSH_PORT $SSH_OPTS "$BOOTSTRAP_LOCAL" auraos@localhost:"$REMOTE_BOOTSTRAP" 2>&1 | tee -a "$LOG_DIR/bootstrap.log"
  scp_rc=${PIPESTATUS[0]}
  if [ $scp_rc -eq 0 ]; then
    break
  fi
  if [ $attempt -ge $max_retries ]; then
    echo "Failed to copy bootstrap script to VM after $attempt attempts" >> "$LOG_DIR/bootstrap.log"
    exit 2
  fi
  attempt=$((attempt+1))
  sleep 3
done

echo "Running bootstrap script on VM..." | tee -a "$LOG_DIR/bootstrap.log"
ssh -p $SSH_PORT $SSH_OPTS auraos@localhost "sudo bash $REMOTE_BOOTSTRAP" 2>&1 | tee -a "$LOG_DIR/bootstrap.log"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "Failed to execute bootstrap script inside VM" >> "$LOG_DIR/bootstrap.log"
  exit 2
fi

current_step=$((current_step + 1))
progress_bar $current_step $steps

echo "[8/8] Bootstrap run completed. Tail the QEMU log to watch the VM console if needed:"
echo "  tail -f $QEMU_LOG"

echo "Done."
exit 0
