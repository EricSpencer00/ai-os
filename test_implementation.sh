#!/bin/bash
# Test script for AuraOS implementation

echo "🧪 AuraOS Implementation Test Suite"
echo "===================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if daemon is running
echo "1️⃣  Checking if daemon is running..."
if curl -s http://localhost:5050 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Daemon is running on port 5050"
else
    echo -e "${RED}✗${NC} Daemon is not running"
    echo "   Start it with: cd auraos_daemon && python3 main.py"
    exit 1
fi
echo ""

# Test shell plugin
echo "2️⃣  Testing Shell Plugin..."
RESPONSE=$(curl -s -X POST http://localhost:5050/generate_script \
    -H "Content-Type: application/json" \
    -d '{"intent": "list files in current directory"}')

if echo "$RESPONSE" | grep -q "script"; then
    echo -e "${GREEN}✓${NC} Shell plugin responding"
else
    echo -e "${RED}✗${NC} Shell plugin failed"
fi
echo ""

# Test decision engine routing
echo "3️⃣  Testing Decision Engine Routing..."

# Test VM routing
echo "   Testing VM routing..."
RESPONSE=$(curl -s -X POST http://localhost:5050/generate_script \
    -H "Content-Type: application/json" \
    -d '{"intent": "create vm test"}')

if echo "$RESPONSE" | grep -q "vm"; then
    echo -e "   ${GREEN}✓${NC} VM manager plugin detected"
else
    echo -e "   ${YELLOW}⚠${NC} VM manager plugin not detected (plugin may not be loaded)"
fi

# Test browser routing
echo "   Testing browser routing..."
RESPONSE=$(curl -s -X POST http://localhost:5050/generate_script \
    -H "Content-Type: application/json" \
    -d '{"intent": "open website https://google.com"}')

if echo "$RESPONSE" | grep -q "selenium\|navigate"; then
    echo -e "   ${GREEN}✓${NC} Selenium plugin detected"
else
    echo -e "   ${YELLOW}⚠${NC} Selenium plugin not detected"
fi

# Test window manager routing
echo "   Testing window manager routing..."
RESPONSE=$(curl -s -X POST http://localhost:5050/generate_script \
    -H "Content-Type: application/json" \
    -d '{"intent": "list apps"}')

if echo "$RESPONSE" | grep -q "window"; then
    echo -e "   ${GREEN}✓${NC} Window manager plugin detected"
else
    echo -e "   ${YELLOW}⚠${NC} Window manager plugin not detected"
fi
echo ""

# Check dependencies
echo "4️⃣  Checking System Dependencies..."

# Check QEMU
if command -v qemu-system-aarch64 &> /dev/null; then
    VERSION=$(qemu-system-aarch64 --version | head -n1)
    echo -e "   ${GREEN}✓${NC} QEMU installed: $VERSION"
else
    echo -e "   ${YELLOW}⚠${NC} QEMU not installed (brew install qemu)"
fi

# Check Ollama
if command -v ollama &> /dev/null; then
    echo -e "   ${GREEN}✓${NC} Ollama installed"
    
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓${NC} Ollama service is running"
        
        # Check for models
        MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | wc -l)
        if [ "$MODELS" -gt 0 ]; then
            echo -e "   ${GREEN}✓${NC} Ollama has $MODELS model(s) installed"
        else
            echo -e "   ${YELLOW}⚠${NC} No Ollama models installed (ollama pull gemma:2b)"
        fi
    else
        echo -e "   ${YELLOW}⚠${NC} Ollama not running (brew services start ollama)"
    fi
else
    echo -e "   ${YELLOW}⚠${NC} Ollama not installed (brew install ollama)"
fi

# Check Chrome/Chromium for Selenium
if [ -d "/Applications/Google Chrome.app" ]; then
    echo -e "   ${GREEN}✓${NC} Google Chrome installed"
elif [ -d "/Applications/Chromium.app" ]; then
    echo -e "   ${GREEN}✓${NC} Chromium installed"
else
    echo -e "   ${YELLOW}⚠${NC} Chrome not found (brew install --cask google-chrome)"
fi

echo ""

# Check Python packages
echo "5️⃣  Checking Python Packages..."
REQUIRED_PACKAGES=("flask" "requests" "selenium" "paramiko" "pyautogui")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "   ${GREEN}✓${NC} $package installed"
    else
        echo -e "   ${RED}✗${NC} $package not installed"
    fi
done

echo ""

# Check config
echo "6️⃣  Checking Configuration..."
if [ -f "auraos_daemon/config.json" ]; then
    echo -e "   ${GREEN}✓${NC} config.json exists"
    
    # Check for API key
    if grep -q "your-api-key-here" auraos_daemon/config.json 2>/dev/null; then
        echo -e "   ${YELLOW}⚠${NC} Groq API key not configured"
    else
        echo -e "   ${GREEN}✓${NC} Groq API key configured"
    fi
else
    echo -e "   ${RED}✗${NC} config.json not found (cp config.sample.json config.json)"
fi

echo ""
echo "===================================="
echo "✅ Implementation test complete!"
echo ""
echo "Next steps:"
echo "  1. Install missing dependencies if any"
echo "  2. Configure your Groq API key in config.json"
echo "  3. Start Ollama: brew services start ollama"
echo "  4. Download a model: ollama pull gemma:2b"
echo "  5. See QUICKSTART.md for usage examples"
echo ""
