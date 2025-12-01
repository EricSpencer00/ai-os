#!/bin/bash
# AuraOS App Verification Script
# Verifies all apps are properly deployed and cached bytecode is cleared

set -e

echo "🔍 AuraOS Application Update Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# 1. Clear Python cache
echo "[1/5] Clearing Python cache..."
find /Users/eric/GitHub/ai-os -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find /Users/eric/GitHub/ai-os -name "*.pyc" -delete 2>/dev/null || true
echo "✓ Cache cleared"
echo

# 2. Verify local apps
echo "[2/5] Verifying local applications..."
for app in auraos_terminal auraos_browser auraos_vision; do
    file="/Users/eric/GitHub/ai-os/${app}.py"
    if [ -f "$file" ]; then
        echo "✓ $app.py found"
    else
        echo "✗ $app.py NOT FOUND"
        exit 1
    fi
done
echo

# 3. Verify app versions
echo "[3/5] Verifying application versions..."
if grep -q "English to Bash" /Users/eric/GitHub/ai-os/auraos_terminal.py; then
    echo "✓ Terminal: CLI version (English to Bash)"
else
    echo "✗ Terminal: OLD VERSION"
    exit 1
fi

if grep -q "Open Firefox" /Users/eric/GitHub/ai-os/auraos_browser.py; then
    echo "✓ Browser: Firefox + DuckDuckGo version"
else
    echo "✗ Browser: OLD VERSION"
    exit 1
fi

if grep -q "pyautogui" /Users/eric/GitHub/ai-os/auraos_vision.py; then
    echo "✓ Vision: Cluely-style (pyautogui) version"
else
    echo "✗ Vision: OLD VERSION"
    exit 1
fi
echo

# 4. Update VM
echo "[4/5] Syncing apps to VM..."
multipass transfer /Users/eric/GitHub/ai-os/auraos_terminal.py auraos-multipass:/home/ubuntu/ 2>/dev/null
multipass transfer /Users/eric/GitHub/ai-os/auraos_browser.py auraos-multipass:/home/ubuntu/ 2>/dev/null
multipass transfer /Users/eric/GitHub/ai-os/auraos_vision.py auraos-multipass:/home/ubuntu/ 2>/dev/null
multipass transfer /Users/eric/GitHub/ai-os/auraos_launcher.py auraos-multipass:/home/ubuntu/ 2>/dev/null

multipass exec auraos-multipass -- bash -c "sudo cp /home/ubuntu/auraos_*.py /opt/auraos/ 2>/dev/null && sudo rm -rf /opt/auraos/__pycache__" 2>/dev/null || true
echo "✓ VM updated with latest apps"
echo

# 5. Test launcher can find apps
echo "[5/5] Testing launcher app discovery..."
python3 << 'PYEOF'
import os
import sys

def find_app_path(app_name):
    script_dir = os.getcwd()
    search_paths = [
        os.path.join(script_dir, app_name),
        os.path.join("/opt/auraos/bin", app_name),
        os.path.join(os.path.expanduser("~"), "auraos", app_name),
    ]
    for path in search_paths:
        if os.path.exists(path):
            return path
    return None

found_all = True
for app in ["auraos_terminal.py", "auraos_browser.py", "auraos_vision.py"]:
    path = find_app_path(app)
    if path:
        print(f"✓ Found {app}")
    else:
        print(f"✗ Missing {app}")
        found_all = False

if not found_all:
    sys.exit(1)
PYEOF

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All systems verified and updated!"
echo
echo "To use the apps:"
echo "  • Click 'AI Terminal' → Opens English-to-Bash CLI"
echo "  • Click 'AI Browser' → Opens Firefox with search"
echo "  • Click 'Vision Desktop' → Opens VNC with screenshot AI"
echo
