#!/bin/bash
# Test different Ollama models for vision tasks

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== Ollama Vision Model Test ===${NC}"
echo ""

# First, capture a screenshot
echo "Capturing screenshot..."
SCREENSHOT="/tmp/auraos_screenshot_test.png"
curl -s http://localhost:8765/screenshot -o "$SCREENSHOT" 2>/dev/null || {
    echo -e "${RED}Failed to capture screenshot${NC}"
    exit 1
}
echo -e "${GREEN}✓ Screenshot captured${NC}"
echo ""

# Read image as base64
IMAGE_B64=$(base64 -i "$SCREENSHOT" | tr -d '\n')

# Test models
MODELS=("llava:13b" "qwen2.5-coder:7b" "deepseek-r1:8b" "gpt-oss:20b")
TASK="click on file manager"

for MODEL in "${MODELS[@]}"; do
    echo -e "${YELLOW}Testing: $MODEL${NC}"
    
    # Check if model is available
    if ! curl -s http://localhost:11434/api/tags | grep -q "\"name\": \"$MODEL\""; then
        echo -e "${RED}  ✗ Not available${NC}"
        continue
    fi
    
    # Simple prompt
    PROMPT="Look at this desktop screenshot. Find the file manager icon. Return the X,Y pixel coordinates as JSON: {\"x\": 100, \"y\": 100}"
    
    # Call Ollama
    RESPONSE=$(curl -s http://localhost:11434/api/generate \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$MODEL\",
            \"prompt\": \"$PROMPT\",
            \"images\": [\"$IMAGE_B64\"],
            \"stream\": false,
            \"options\": {
                \"temperature\": 0.1,
                \"num_predict\": 100
            }
        }" 2>/dev/null)
    
    # Extract response
    RESULT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('response', ''))" 2>/dev/null || echo "")
    
    if [ -z "$RESULT" ]; then
        echo -e "${RED}  ✗ No response${NC}"
    else
        # Check if response contains coordinates
        if echo "$RESULT" | grep -q '"x"'; then
            echo -e "${GREEN}  ✓ Response includes coordinates${NC}"
            echo "    Preview: ${RESULT:0:100}..."
        else
            echo -e "${RED}  ✗ No coordinates in response${NC}"
            echo "    Got: ${RESULT:0:80}..."
        fi
    fi
    echo ""
done

echo -e "${YELLOW}=== Summary ===${NC}"
echo ""
echo "Recommended models for vision tasks (in order):"
echo "1. llava:34b    - Best accuracy (if available)"
echo "2. qwen2.5-coder:7b - Good balance"
echo "3. llava:13b    - Lightweight, reasonable"
echo ""
echo "To pull a larger model:"
echo "  ollama pull llava:34b"
echo ""
