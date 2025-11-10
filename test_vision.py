#!/usr/bin/env python3
"""Test Ollama vision with actual screenshot analysis"""

import sys
import json
import base64
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "auraos_daemon"))
from core.screen_automation import ScreenAutomation


def test_vision_simple():
    """Test Ollama vision with simple description task"""
    
    print("=== Testing Ollama Vision ===\n")
    
    # Capture screenshot
    automation = ScreenAutomation()
    print("📸 Capturing screenshot...")
    screenshot = automation.capture_screen()
    
    if not screenshot:
        print("❌ Failed to capture screenshot")
        return
    
    print(f"✓ Screenshot: {screenshot}\n")
    
    # Test 1: Simple description
    print("Test 1: Describe what you see")
    print("-" * 50)
    
    with open(screenshot, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llava:13b",
            "prompt": "Describe what you see in this desktop screenshot. What applications or icons are visible?",
            "images": [img_b64],
            "stream": False
        },
        timeout=90
    )
    
    if response.status_code == 200:
        result = response.json()
        description = result.get("response", "")
        print(f"AI Response:\n{description}\n")
    else:
        print(f"❌ Error: {response.status_code}\n")
        return
    
    # Test 2: Find specific element
    print("\nTest 2: Locate file manager icon")
    print("-" * 50)
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llava:13b",
            "prompt": """Look at this XFCE desktop screenshot carefully. 

I need you to find the FILE MANAGER icon (usually looks like a folder) in the taskbar at the bottom.

The screen is 1280x720 pixels. Origin (0,0) is top-left corner.
X increases to the right (max 1280).
Y increases downward (max 720).

Respond with ONLY valid JSON:
{"x": <number>, "y": <number>, "confidence": <0.0-1.0>, "description": "brief description of what you found"}

Example: {"x": 450, "y": 690, "confidence": 0.85, "description": "folder icon in taskbar"}""",
            "images": [img_b64],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 150
            }
        },
        timeout=90
    )
    
    if response.status_code == 200:
        result = response.json()
        content = result.get("response", "").strip()
        print(f"Raw AI Response:\n{content}\n")
        
        # Try to parse JSON
        if "{" in content and "}" in content:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            try:
                parsed = json.loads(content[json_start:json_end])
                print(f"Parsed coordinates:")
                print(f"  X: {parsed.get('x')}")
                print(f"  Y: {parsed.get('y')}")
                print(f"  Confidence: {parsed.get('confidence')}")
                print(f"  Description: {parsed.get('description')}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
    else:
        print(f"❌ Error: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("✓ Vision test complete")
    print(f"\nScreenshot saved at: {screenshot}")
    print("Open it to verify what the AI should be seeing.")


if __name__ == "__main__":
    test_vision_simple()
