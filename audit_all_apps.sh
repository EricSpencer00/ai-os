#!/bin/bash
# Comprehensive AuraOS Audit Script
# Tests all components for functionality

set +e  # Don't exit on errors, we want to report all issues

echo "═══════════════════════════════════════════════════════════"
echo "AuraOS COMPREHENSIVE FUNCTIONALITY AUDIT"
echo "═══════════════════════════════════════════════════════════"
echo ""

ISSUES=()
FIXES_NEEDED=()

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; ISSUES+=("$1"); }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_fix_needed() { FIXES_NEEDED+=("$1"); }

# ===== CHECK 1: VM & BASIC SERVICES =====
echo ""
echo "CHECK 1: VM & BASIC SERVICES"
echo "────────────────────────────"

if multipass list | grep -q "auraos-multipass.*Running"; then
    log_success "VM is running"
else
    log_error "VM is not running"
    exit 1
fi

# Check core services
if multipass exec auraos-multipass -- systemctl is-active auraos-x11vnc.service > /dev/null 2>&1; then
    log_success "x11vnc service is running"
else
    log_error "x11vnc service is not running"
    log_fix_needed "Restart x11vnc: multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service"
fi

if multipass exec auraos-multipass -- systemctl is-active auraos-novnc.service > /dev/null 2>&1; then
    log_success "noVNC service is running"
else
    log_error "noVNC service is not running"
    log_fix_needed "Restart noVNC: multipass exec auraos-multipass -- sudo systemctl restart auraos-novnc.service"
fi

if multipass exec auraos-multipass -- systemctl is-active auraos-gui-agent.service > /dev/null 2>&1; then
    log_success "GUI Agent service is running"
else
    log_error "GUI Agent service is not running"
    log_fix_needed "Restart GUI Agent: multipass exec auraos-multipass -- sudo systemctl restart auraos-gui-agent.service"
fi

# ===== CHECK 2: DESKTOP ENVIRONMENT & ICONS =====
echo ""
echo "CHECK 2: DESKTOP ENVIRONMENT & ICONS"
echo "─────────────────────────────────────"

if multipass exec auraos-multipass -- bash -c 'ps aux | grep -q "[x]fdesktop"'; then
    log_success "Desktop environment (xfdesktop) is running"
else
    log_error "Desktop environment is not running - icons will not display"
    log_fix_needed "Restart desktop: multipass exec auraos-multipass -- killall xfdesktop; sleep 1; DISPLAY=:99 xfdesktop &"
fi

# Check if icon theme is configured
ICON_CHECK=$(multipass exec auraos-multipass -- bash -c 'xfconf-query -c xsettings -p /Net/IconThemeName 2>/dev/null' || echo "MISSING")
if [ "$ICON_CHECK" != "MISSING" ]; then
    log_success "Icon theme is configured: $ICON_CHECK"
else
    log_warning "Icon theme might not be properly configured"
    log_fix_needed "Set icon theme in xfconf"
fi

# ===== CHECK 3: INFERENCE SERVER =====
echo ""
echo "CHECK 3: INFERENCE SERVER (Port 8081)"
echo "──────────────────────────────────────"

if curl -s http://localhost:8081/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8081/health)
    log_success "Inference server is running"
    echo "   Status: $HEALTH"
else
    log_error "Inference server is NOT running (localhost:8081 unreachable)"
    log_fix_needed "Start inference server: ./auraos.sh inference start"
fi

# ===== CHECK 4: GUI AGENT API =====
echo ""
echo "CHECK 4: GUI AGENT API (Port 8765)"
echo "───────────────────────────────────"

if curl -s http://localhost:8765/health > /dev/null 2>&1; then
    log_success "GUI Agent API is responding"
else
    log_error "GUI Agent API is NOT responding (localhost:8765 unreachable)"
    log_fix_needed "Restart GUI Agent: multipass exec auraos-multipass -- sudo systemctl restart auraos-gui-agent.service"
fi

# ===== CHECK 5: VISION FUNCTIONALITY =====
echo ""
echo "CHECK 5: VISION FUNCTIONALITY"
echo "─────────────────────────────"

# Test if screenshots are being captured
SCREENSHOT_COUNT=$(multipass exec auraos-multipass -- bash -c 'ls /tmp/auraos_screenshots/ 2>/dev/null | wc -l')
if [ "$SCREENSHOT_COUNT" -gt 0 ]; then
    log_success "Screenshots are being captured ($SCREENSHOT_COUNT total)"
else
    log_error "No screenshots are being captured - vision will not work"
    log_fix_needed "Check /tmp/auraos_screenshots directory permissions"
fi

# Test inference server vision endpoint (requires setting up payload)
log_warning "Vision endpoint testing requires live model - manual verification recommended"

# ===== CHECK 6: TERMINAL & CHAT MODE =====
echo ""
echo "CHECK 6: TERMINAL & CHAT MODE"
echo "──────────────────────────────"

if python3 -m py_compile /Users/eric/GitHub/ai-os/auraos_terminal.py > /dev/null 2>&1; then
    log_success "auraos_terminal.py compiles"
else
    log_error "auraos_terminal.py has syntax errors"
    log_fix_needed "Fix syntax errors in auraos_terminal.py"
fi

# Check if terminal can connect to inference server
# This would be done in the actual terminal runtime

# ===== CHECK 7: BROWSER APP =====
echo ""
echo "CHECK 7: BROWSER APP"
echo "────────────────────"

if python3 -m py_compile /Users/eric/GitHub/ai-os/auraos_browser.py > /dev/null 2>&1; then
    log_success "auraos_browser.py compiles"
else
    log_error "auraos_browser.py has syntax errors"
    log_fix_needed "Fix syntax errors in auraos_browser.py"
fi

# ===== CHECK 8: LAUNCHER =====
echo ""
echo "CHECK 8: APPLICATION LAUNCHER"
echo "──────────────────────────────"

if python3 -m py_compile /Users/eric/GitHub/ai-os/auraos_launcher.py > /dev/null 2>&1; then
    log_success "auraos_launcher.py compiles"
else
    log_error "auraos_launcher.py has syntax errors"
    log_fix_needed "Fix syntax errors in auraos_launcher.py"
fi

# ===== CHECK 9: FIREFOX INSTALLATION =====
echo ""
echo "CHECK 9: FIREFOX INSTALLATION"
echo "──────────────────────────────"

if multipass exec auraos-multipass -- which firefox > /dev/null 2>&1; then
    log_success "Firefox is installed in VM"
else
    log_error "Firefox is NOT installed in VM"
    log_fix_needed "Install Firefox: multipass exec auraos-multipass -- sudo apt-get install -y firefox"
fi

# ===== SUMMARY =====
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "AUDIT SUMMARY"
echo "═══════════════════════════════════════════════════════════"

if [ ${#ISSUES[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ No critical issues found!${NC}"
else
    echo -e "${RED}✗ Found ${#ISSUES[@]} issues:${NC}"
    for issue in "${ISSUES[@]}"; do
        echo "  - $issue"
    done
fi

echo ""
if [ ${#FIXES_NEEDED[@]} -gt 0 ]; then
    echo "RECOMMENDED FIXES:"
    echo "─────────────────"
    for i in "${!FIXES_NEEDED[@]}"; do
        echo "$((i+1)). ${FIXES_NEEDED[$i]}"
    done
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
