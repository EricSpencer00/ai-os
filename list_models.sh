#!/bin/bash
# List and test available Ollama vision models

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  Ollama Vision Models - Status Check${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Get current config
echo -e "${YELLOW}Current Configuration:${NC}"
cd "$(dirname "$0")/auraos_daemon"
python3 << 'PYTHON'
from core.key_manager import KeyManager
km = KeyManager()
config = km.get_ollama_config()
if config:
    print(f"  Model: {config.get('model', 'unknown')}")
    print(f"  Vision Model: {config.get('vision_model', 'unknown')}")
    print(f"  Base URL: {config.get('base_url', 'http://localhost:11434')}")
else:
    print("  No Ollama config found")
PYTHON

echo ""
echo -e "${YELLOW}Available Models:${NC}"
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 << 'PYTHON'
import sys, json
try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    if models:
        for i, m in enumerate(models, 1):
            name = m.get('name', 'unknown')
            size_gb = m.get('size', 0) / (1024**3)
            print(f"  {i}. {name:<30} ({size_gb:>5.1f} GB)")
    else:
        print("  No models available")
except:
    print("  Error fetching models")
PYTHON

echo ""
echo -e "${YELLOW}Vision Model Testing:${NC}"
echo ""
echo "To switch vision models, use:"
echo -e "  ${GREEN}./auraos.sh keys ollama <model> <vision_model>${NC}"
echo ""
echo "Examples:"
echo -e "  ${GREEN}./auraos.sh keys ollama llava:13b llava:13b${NC}"
echo -e "  ${GREEN}./auraos.sh keys ollama llava:13b minicpm-v${NC}"
echo -e "  ${GREEN}./auraos.sh keys ollama qwen2.5-coder:7b minicpm-v${NC}"
echo ""
echo "To test current vision model:"
echo -e "  ${GREEN}./test_ollama_vision.sh${NC}"
echo ""
