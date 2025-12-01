#!/bin/bash
# Test AuraOS Connections & Dependencies

echo "🔍 AuraOS System Connection Test"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

all_passed=0

# Test 1: Host Ollama
echo "1. HOST OLLAMA"
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    test_result 0 "Ollama running on host (localhost:11434)"
else
    test_result 1 "Ollama NOT running on host"
    echo "   Start with: OLLAMA_HOST=0.0.0.0 ollama serve"
    all_passed=1
fi
echo ""

# Test 2: VM Running
echo "2. VM STATUS"
if multipass list 2>/dev/null | grep -q "auraos-multipass.*Running"; then
    test_result 0 "VM is running"
else
    test_result 1 "VM is not running"
    echo "   Start with: multipass start auraos-multipass"
    all_passed=1
fi
echo ""

# Test 3: VM can reach host Ollama
echo "3. VM → HOST OLLAMA CONNECTION"
if multipass exec auraos-multipass -- curl -s http://192.168.2.1:11434/api/tags >/dev/null 2>&1; then
    test_result 0 "VM can reach Ollama on host (192.168.2.1:11434)"
else
    test_result 1 "VM CANNOT reach Ollama on host"
    echo "   Note: 192.168.2.1 is the gateway IP for Multipass"
    echo "   Verify host IP: ifconfig | grep inet | grep -v 127"
    all_passed=1
fi
echo ""

# Test 4: GUI Agent running
echo "4. GUI AGENT (inside VM)"
if multipass exec auraos-multipass -- sudo systemctl is-active auraos-gui-agent.service >/dev/null 2>&1; then
    test_result 0 "GUI Agent service is running"
else
    test_result 1 "GUI Agent service NOT running"
    echo "   Start with: ./auraos.sh restart"
    all_passed=1
fi
echo ""

# Test 5: VNC accessible
echo "5. VNC ACCESS"
if curl -s http://localhost:6080/vnc.html >/dev/null 2>&1; then
    test_result 0 "noVNC is accessible (http://localhost:6080/vnc.html)"
else
    test_result 1 "noVNC is NOT accessible"
    echo "   Verify: ./auraos.sh status"
    all_passed=1
fi
echo ""

# Test 6: Connection path
echo "6. CONNECTION PATH"
echo "   Browser (VM) → GUI Agent (VM:8765) → Ollama (Host:11434)"
if multipass exec auraos-multipass -- curl -s http://localhost:8765/health >/dev/null 2>&1; then
    test_result 0 "Browser can reach GUI Agent locally"
else
    test_result 1 "Browser CANNOT reach GUI Agent"
    all_passed=1
fi
echo ""

# Summary
echo "=================================="
if [ $all_passed -eq 0 ]; then
    echo -e "${GREEN}✓ All connections working!${NC}"
    echo ""
    echo "Connection flow:"
    echo "  1. AuraOS Home → Launch Browser/Terminal/Settings"
    echo "  2. Browser/Terminal → GUI Agent (http://localhost:8765)"
    echo "  3. GUI Agent → Ollama (http://192.168.2.1:11434)"
    echo ""
else
    echo -e "${YELLOW}⚠ Some connections failed${NC}"
    echo ""
    echo "Fix steps:"
    echo "  1. Start Ollama on host:"
    echo "     OLLAMA_HOST=0.0.0.0 ollama serve"
    echo "  2. Verify VM is running:"
    echo "     ./auraos.sh health"
    echo "  3. Restart services:"
    echo "     ./auraos.sh restart"
fi
echo ""
