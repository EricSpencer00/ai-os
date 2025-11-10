#!/usr/bin/env python3
"""AI OS Demo - Vision-based desktop automation with Ollama

Demonstrates the full pipeline:
1. Capture screenshot from VM
2. Send to Ollama vision model with task
3. Get coordinates from AI
4. Execute click action
5. Capture new screenshot to verify
"""

import sys
import time
from pathlib import Path

# Add auraos_daemon to path
sys.path.insert(0, str(Path(__file__).parent / "auraos_daemon"))

from core.screen_automation import ScreenAutomation
from core.key_manager import KeyManager


def demo_ai_click(task: str = "click on the terminal icon in the taskbar"):
    """Run a single AI-driven click task"""
    
    print("=" * 60)
    print("AuraOS AI Vision Demo")
    print("=" * 60)
    print()
    
    # Ensure Ollama is configured
    km = KeyManager()
    if not km.get_ollama_config():
        print("Enabling Ollama with default settings...")
        km.enable_ollama(base_url="http://localhost:11434", vision_model="llava:13b")
    
    # Initialize screen automation
    print("Initializing screen automation...")
    automation = ScreenAutomation(agent_url="http://localhost:8765")
    
    if not automation.vision_provider:
        print("❌ No vision provider configured!")
        print("Ollama should be running with llava:13b model")
        print("Run: ollama pull llava:13b")
        return False
    
    print(f"✓ Using vision provider: {automation.vision_provider}")
    print()
    
    # Step 1: Capture initial screenshot
    print("📸 Step 1: Capturing screenshot...")
    screenshot_path = automation.capture_screen()
    
    if not screenshot_path:
        print("❌ Screenshot failed!")
        return False
    
    print(f"✓ Screenshot saved: {screenshot_path}")
    print()
    
    # Step 2: Analyze with AI vision
    print(f"🤖 Step 2: Analyzing screenshot with task: '{task}'")
    print("(This may take 10-30 seconds for Ollama to process the image...)")
    
    start_time = time.time()
    result = automation.analyze_screen(screenshot_path, task)
    duration = time.time() - start_time
    
    if not result:
        print("❌ AI analysis failed!")
        return False
    
    print(f"✓ Analysis complete in {duration:.1f}s")
    print(f"  Action: {result.get('action')}")
    print(f"  Coordinates: ({result.get('x')}, {result.get('y')})")
    print(f"  Confidence: {result.get('confidence', 0):.2f}")
    print(f"  Explanation: {result.get('explanation', 'N/A')}")
    print()
    
    # Check if action is valid
    if result.get('action') != 'click':
        print(f"⚠️  AI returned action '{result.get('action')}' instead of 'click'")
        if result.get('action') == 'none':
            print(f"   Reason: {result.get('explanation')}")
        return False
    
    if result.get('confidence', 0) < 0.5:
        print(f"⚠️  Low confidence ({result.get('confidence')}), proceeding anyway...")
    
    # Step 3: Execute click
    print(f"🖱️  Step 3: Executing click at ({result['x']}, {result['y']})...")
    
    success = automation.click(result['x'], result['y'])
    
    if not success:
        print("❌ Click failed!")
        return False
    
    print("✓ Click executed")
    print()
    
    # Step 4: Wait and capture new screenshot to verify
    print("⏱️  Step 4: Waiting 2s for UI to update...")
    time.sleep(2)
    
    print("📸 Capturing verification screenshot...")
    new_screenshot = automation.capture_screen()
    
    if new_screenshot:
        print(f"✓ Verification screenshot saved: {new_screenshot}")
        print()
        print("=" * 60)
        print("✅ Demo complete!")
        print()
        print(f"Compare screenshots:")
        print(f"  Before: {screenshot_path}")
        print(f"  After:  {new_screenshot}")
        print()
        return True
    else:
        print("⚠️  Verification screenshot failed")
        return False


def demo_multi_step():
    """Run multiple AI-driven tasks in sequence"""
    
    tasks = [
        "click on the Firefox icon",
        "click on the terminal icon in the taskbar",
        "click on the file manager icon"
    ]
    
    print("=" * 60)
    print("Multi-Step AI Automation Demo")
    print("=" * 60)
    print()
    
    for i, task in enumerate(tasks, 1):
        print(f"\n--- Task {i}/{len(tasks)}: {task} ---\n")
        
        success = demo_ai_click(task)
        
        if not success:
            print(f"❌ Task {i} failed, stopping demo")
            return False
        
        if i < len(tasks):
            print(f"\nWaiting 3s before next task...\n")
            time.sleep(3)
    
    print("\n" + "=" * 60)
    print("✅ All tasks completed successfully!")
    print("=" * 60)
    return True


def main():
    """Main entry point"""
    
    if len(sys.argv) > 1:
        # Custom task from command line
        task = " ".join(sys.argv[1:])
        demo_ai_click(task)
    else:
        # Default demo
        print("Usage: python3 demo_ai_os.py [custom task]")
        print()
        print("Examples:")
        print("  python3 demo_ai_os.py click on the Firefox icon")
        print("  python3 demo_ai_os.py click the close button")
        print()
        print("Running default demo...")
        print()
        
        demo_ai_click("click on the file manager icon in the taskbar")


if __name__ == "__main__":
    main()
