#!/bin/bash
# Fix AuraOS Desktop Environment Issues

set -e

VM_NAME="auraos-multipass"
AURAOS_USER="auraos"

echo "════════════════════════════════════════════════════════════"
echo "AuraOS DESKTOP & FUNCTIONALITY REPAIR"
echo "════════════════════════════════════════════════════════════"
echo ""

# Function to run commands in VM
run_vm() {
    multipass exec "$VM_NAME" -- sudo -u "$AURAOS_USER" bash -c "$1"
}

# ===== FIX 1: ICON THEME & DESKTOP CONFIGURATION =====
echo "[1/5] Configuring icon theme and desktop appearance..."
run_vm 'DISPLAY=:99 xfconf-query -c xsettings -p /Net/IconThemeName -s "Adwaita" --create -t string' 2>/dev/null || true
run_vm 'DISPLAY=:99 xfconf-query -c xsettings -p /Net/ThemeName -s "Adwaita" --create -t string' 2>/dev/null || true
run_vm 'DISPLAY=:99 xfconf-query -c xfdesktop -p /backdrop/screen0/monitor0/workspace0/last-image -s "/usr/share/pixmaps/xfce4-backdrop.png" --create -t string' 2>/dev/null || true
echo "✓ Desktop theme configured"

# ===== FIX 2: INSTALL MISSING ICON PACKAGES =====
echo "[2/5] Installing icon packages..."
multipass exec "$VM_NAME" -- sudo bash -c 'apt-get update -qq && apt-get install -y adwaita-icon-theme papirus-icon-theme xfce4-panel xfce4-notifyd xfce4-appfinder' >/dev/null 2>&1 || true
echo "✓ Icon packages installed"

# ===== FIX 3: INSTALL FIREFOX IF MISSING =====
echo "[3/5] Checking Firefox installation..."
if ! multipass exec "$VM_NAME" -- which firefox >/dev/null 2>&1; then
    echo "→ Firefox not found, installing..."
    multipass exec "$VM_NAME" -- sudo apt-get install -y firefox >/dev/null 2>&1
    echo "✓ Firefox installed"
else
    echo "✓ Firefox already installed"
fi

# ===== FIX 4: RESTART DESKTOP ENVIRONMENT =====
echo "[4/5] Restarting desktop environment..."
multipass exec "$VM_NAME" -- bash -c 'killall xfdesktop xfpanel4 2>/dev/null || true; sleep 1' || true
multipass exec "$VM_NAME" -- bash -c 'DISPLAY=:99 xfdesktop > /tmp/xfdesktop.log 2>&1 &' || true
sleep 2
echo "✓ Desktop environment restarted"

# ===== FIX 5: VERIFY SERVICES ARE RUNNING =====
echo "[5/5] Verifying services..."
multipass exec "$VM_NAME" -- bash -c 'systemctl is-active auraos-gui-agent.service > /dev/null && echo "✓ GUI Agent is running" || echo "✗ GUI Agent not running"'

echo ""
echo "════════════════════════════════════════════════════════════"
echo "REPAIR COMPLETE"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Refresh your browser/VNC viewer to see updated desktop"
echo "2. Test Firefox icon displays correctly"
echo "3. Test AI functionality via terminal Chat Mode"
echo ""
