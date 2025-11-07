#!/bin/bash
# AuraOS Quick Installation Script for M1 Macs

set -e  # Exit on error

echo "╔════════════════════════════════════════╗"
echo "║   AuraOS Installation Script v1.0      ║"
echo "║   For Apple Silicon (M1/M2/M3) Macs    ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script is for macOS only${NC}"
    exit 1
fi

# Check if running on Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    echo -e "${YELLOW}Warning: This script is optimized for Apple Silicon (M1/M2/M3)${NC}"
    echo -e "${YELLOW}You appear to be on Intel. Continue? (y/n)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}Step 1/7: Checking Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo -e "${GREEN}✓${NC} Homebrew already installed"
fi
echo ""

echo -e "${BLUE}Step 2/7: Installing QEMU...${NC}"
if ! command -v qemu-system-aarch64 &> /dev/null; then
    echo "Installing QEMU (this may take a few minutes)..."
    brew install qemu
    echo -e "${GREEN}✓${NC} QEMU installed"
else
    echo -e "${GREEN}✓${NC} QEMU already installed"
    qemu-system-aarch64 --version | head -n1
fi
echo ""

echo -e "${BLUE}Step 3/7: Installing Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    brew install ollama
    echo -e "${GREEN}✓${NC} Ollama installed"
else
    echo -e "${GREEN}✓${NC} Ollama already installed"
fi
echo ""

echo -e "${BLUE}Step 4/7: Starting Ollama service...${NC}"
brew services start ollama 2>/dev/null || true
sleep 2

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
for i in {1..10}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Ollama service is running"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${YELLOW}⚠${NC} Ollama may not have started. Continue anyway."
    fi
    sleep 1
done
echo ""

echo -e "${BLUE}Step 5/7: Downloading LLM model...${NC}"
if ollama list 2>/dev/null | grep -q "gemma:2b"; then
    echo -e "${GREEN}✓${NC} gemma:2b model already installed"
else
    echo "Downloading gemma:2b model (this may take a few minutes)..."
    ollama pull gemma:2b
    echo -e "${GREEN}✓${NC} Model downloaded"
fi
echo ""

echo -e "${BLUE}Step 6/7: Installing Python dependencies...${NC}"
cd "$(dirname "$0")/auraos_daemon"
if [ -f "requirements.txt" ]; then
    echo "Installing Python packages..."
    pip3 install -r requirements.txt --quiet
    echo -e "${GREEN}✓${NC} Python dependencies installed"
else
    echo -e "${RED}Error: requirements.txt not found${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 7/7: Setting up configuration...${NC}"
if [ ! -f "config.json" ]; then
    if [ -f "config.sample.json" ]; then
        cp config.sample.json config.json
        echo -e "${GREEN}✓${NC} Created config.json from sample"
        echo ""
        echo -e "${YELLOW}⚠ IMPORTANT: You need to add your Groq API key!${NC}"
        echo ""
        echo "1. Get a free API key from: https://console.groq.com/keys"
        echo "2. Edit config.json and replace 'your-api-key-here' with your key"
        echo ""
        echo "Press Enter to open config.json in default editor..."
        read -r
        open config.json
    else
        echo -e "${RED}Error: config.sample.json not found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} config.json already exists"
fi
echo ""

echo "╔════════════════════════════════════════╗"
echo "║       Installation Complete! 🎉         ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo ""
echo "1. Make sure you've added your Groq API key to config.json"
echo ""
echo "2. Start the AuraOS daemon:"
echo -e "   ${BLUE}cd auraos_daemon && python3 main.py${NC}"
echo ""
echo "3. In another terminal, try it out:"
echo -e "   ${BLUE}curl -X POST http://localhost:5050/generate_script \\${NC}"
echo -e "   ${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "   ${BLUE}  -d '{\"intent\": \"list all python files\"}' | jq${NC}"
echo ""
echo "4. Read the documentation:"
echo "   - QUICKSTART.md - Get started in 10 minutes"
echo "   - VM_SETUP.md - Complete VM setup guide"
echo "   - README.md - Full documentation"
echo ""
echo -e "${GREEN}Happy automating! 🚀${NC}"
echo ""

# Optional: Install jq for pretty JSON output
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Tip: Install jq for pretty JSON output:${NC}"
    echo "     brew install jq"
    echo ""
fi
