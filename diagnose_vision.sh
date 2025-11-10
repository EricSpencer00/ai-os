#!/bin/bash
# Diagnostic script to see what models actually see in the screenshot

set -e

SCREENSHOT="/tmp/auraos_screenshot.png"

if [ ! -f "$SCREENSHOT" ]; then
    echo "Capturing screenshot first..."
    curl -s http://localhost:8765/screenshot -o "$SCREENSHOT"
fi

echo "=== Screenshot Analysis ==="
echo "File: $SCREENSHOT"
ls -lh "$SCREENSHOT"
echo ""

# Convert image to base64
IMAGE_B64=$(base64 -i "$SCREENSHOT" | tr -d '\n')

# Test with qwen2.5-coder - ask it to describe what it sees
echo "Testing qwen2.5-coder:7b"
echo "Prompt: Describe every UI element you see in this desktop screenshot."
echo ""

RESPONSE=$(curl -s http://localhost:11434/api/generate \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"qwen2.5-coder:7b\",
        \"prompt\": \"Describe every UI element, icon, and text you see in this desktop screenshot. List them by position (top-left, left side, center, etc). Be very detailed.\",
        \"images\": [\"$IMAGE_B64\"],
        \"stream\": false,
        \"options\": {
            \"temperature\": 0.3,
            \"num_predict\": 500
        }
    }" 2>/dev/null)

# Extract and display response
echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
response = data.get('response', '')
print('Response:')
print(response[:1000])
if len(response) > 1000:
    print('...[truncated]')
" 2>/dev/null || echo "Error parsing response"

echo ""
echo ""
echo "This will help determine if the model is actually seeing the desktop or hallucinating."
