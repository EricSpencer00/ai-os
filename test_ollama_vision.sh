#!/bin/bash
# Test Ollama vision API directly to debug image passing

echo "=== Testing Ollama Vision API ==="
echo ""

SCREENSHOT="/tmp/auraos_screenshot.png"
BASE64_IMAGE=$(base64 < "$SCREENSHOT" | tr -d '\n')

echo "Screenshot file: $SCREENSHOT"
echo "File size: $(ls -lh $SCREENSHOT | awk '{print $5}')"
echo "Base64 size: ${#BASE64_IMAGE} bytes"
echo ""

echo "Testing with llava:13b model..."
echo ""

# Test 1: Send image with a simple description request
echo "Sending image to Ollama /api/chat endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"llava:13b\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"Describe what you see in this screenshot. List all UI elements, icons, and labels you can identify.\",
        \"images\": [\"$BASE64_IMAGE\"]
      }
    ],
    \"stream\": false
  }")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null | head -50 || echo "$RESPONSE" | head -20

echo ""
echo "Testing with a simpler model (qwen2.5-coder)..."
echo ""

# Test 2: Try with qwen2.5-coder (text-only, should reject image)
RESPONSE=$(curl -s -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"qwen2.5-coder:7b\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"Describe what you see in this screenshot. List all UI elements.\"
      }
    ],
    \"stream\": false
  }")

echo "Response from qwen2.5-coder (no image):"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null | head -20 || echo "$RESPONSE" | head -20

echo ""
echo "Testing llava with /api/generate (old endpoint)..."
echo ""

# Test 3: Try with /api/generate
RESPONSE=$(curl -s -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"llava:13b\",
    \"prompt\": \"Describe this screenshot. List all visible UI elements and their locations.\",
    \"images\": [\"$BASE64_IMAGE\"],
    \"stream\": false
  }")

echo "Response from /api/generate endpoint:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null | head -50 || echo "$RESPONSE" | head -20
