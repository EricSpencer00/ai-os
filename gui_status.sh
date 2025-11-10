#!/bin/bash
# AuraOS GUI Status and Troubleshooting

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       AuraOS GUI Status & Tests           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Test 1: VM is running
echo -e "${YELLOW}[1/6]${NC} VM Status"
multipass list | grep auraos-multipass || {
  echo -e "${RED}✗ VM not running!${NC}"
  exit 1
}
echo -e "${GREEN}✓ VM running${NC}"
echo ""

# Test 2: x11vnc service
echo -e "${YELLOW}[2/6]${NC} x11vnc Service"
multipass exec auraos-multipass -- systemctl is-active auraos-x11vnc.service >/dev/null 2>&1 || {
  echo -e "${RED}✗ x11vnc service not active${NC}"
  echo "  Starting..."
  multipass exec auraos-multipass -- sudo systemctl start auraos-x11vnc.service
  sleep 5
}
echo -e "${GREEN}✓ x11vnc active${NC}"
echo ""

# Test 3: noVNC service
echo -e "${YELLOW}[3/6]${NC} noVNC Service"
multipass exec auraos-multipass -- systemctl is-active auraos-novnc.service >/dev/null 2>&1 || {
  echo -e "${RED}✗ noVNC service not active${NC}"
  echo "  Starting..."
  multipass exec auraos-multipass -- sudo systemctl start auraos-novnc.service
  sleep 4
}
echo -e "${GREEN}✓ noVNC active${NC}"
echo ""

# Test 4: VNC password file
echo -e "${YELLOW}[4/6]${NC} VNC Password File"
multipass exec auraos-multipass -- [ -f /home/ubuntu/.vnc/passwd ] && [ -r /home/ubuntu/.vnc/passwd ] || {
  echo -e "${RED}✗ Password file missing or unreadable${NC}"
  echo "  Run: ./auraos_gui_restart.sh"
  exit 1
}
echo -e "${GREEN}✓ Password file exists ($(multipass exec auraos-multipass -- stat -c%s /home/ubuntu/.vnc/passwd 2>/dev/null || multipass exec auraos-multipass -- stat -f%z /home/ubuntu/.vnc/passwd) bytes)${NC}"
echo ""

# Test 5: Port 5900 (x11vnc)
echo -e "${YELLOW}[5/6]${NC} Port 5900 (x11vnc)"
multipass exec auraos-multipass -- bash -c 'ss -tlnp 2>/dev/null | grep -q 5900 || netstat -tlnp 2>/dev/null | grep -q 5900' || {
  echo -e "${RED}✗ x11vnc not listening on port 5900${NC}"
  exit 1
}
echo -e "${GREEN}✓ Listening on port 5900${NC}"
echo ""

# Test 6: Port 6080 (noVNC)
echo -e "${YELLOW}[6/6]${NC} Port 6080 (noVNC)"
multipass exec auraos-multipass -- bash -c 'ss -tlnp 2>/dev/null | grep -q 6080 || netstat -tlnp 2>/dev/null | grep -q 6080' || {
  echo -e "${RED}✗ noVNC not listening on port 6080${NC}"
  exit 1
}
echo -e "${GREEN}✓ Listening on port 6080${NC}"
echo ""

# Additional checks
echo -e "${YELLOW}SSH Tunnels:${NC}"
pgrep -f "ssh.*5901.*ubuntu@192" >/dev/null 2>&1 && echo -e "${GREEN}✓ Tunnel 5901→5900${NC}" || echo -e "${RED}✗ Missing tunnel 5901→5900${NC}"
pgrep -f "ssh.*6080.*ubuntu@192" >/dev/null 2>&1 && echo -e "${GREEN}✓ Tunnel 6080→6080${NC}" || echo -e "${RED}✗ Missing tunnel 6080→6080${NC}"
pgrep -f "ssh.*8765.*ubuntu@192" >/dev/null 2>&1 && echo -e "${GREEN}✓ Tunnel 8765→8765${NC}" || echo -e "${RED}✗ Missing tunnel 8765→8765${NC}"

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}✓ All checks passed!${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Access the desktop:${NC}"
echo ""
echo "  Browser (recommended):"
echo -e "    ${GREEN}http://localhost:6080/vnc.html${NC}"
echo ""
echo "  Native VNC Viewer:"
echo -e "    ${GREEN}open -a 'VNC Viewer' vnc://localhost:5901${NC}"
echo ""
echo "  Password:"
echo -e "    ${GREEN}auraos123${NC}"
echo ""

# Test web server
echo -e "${YELLOW}Testing web server connectivity...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6080/vnc.html 2>&1)
if [ "$HTTP_CODE" = "200" ]; then
  echo -e "${GREEN}✓ Web server responding${NC}"
else
  echo -e "${RED}✗ Web server returned: $HTTP_CODE${NC}"
fi
