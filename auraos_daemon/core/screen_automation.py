#!/usr/bin/env python3
"""AI Screen Automation - Vision-based screen interaction for AuraOS

Uses GPT-4V or Claude-3 to analyze screenshots and determine click coordinates.
Integrates with the VM GUI agent to perform automated actions.
"""
import os
import json
import base64
import requests
from typing import Dict, Optional, Tuple, List
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.key_manager import KeyManager


class ScreenAutomation:
    """AI-powered screen automation using vision models (via local inference server)"""
    
    def __init__(self, agent_url: str = "http://localhost:8765", 
                 api_key: Optional[str] = None,
                 inference_url: str = "http://localhost:8081"):
        """Initialize screen automation
        
        Args:
            agent_url: URL of the GUI agent running in the VM
            api_key: API key for the agent (default: from KeyManager)
            inference_url: URL of the local inference server
        """
        self.agent_url = agent_url.rstrip('/')
        self.inference_url = inference_url.rstrip('/')
        self.km = KeyManager()
        self.api_key = api_key or self.km.get_key("agent") or "auraos_dev_key"
        
        # Vision model configuration
        self.vision_provider = None
        self.vision_api_key = None
        self._configure_vision()
    
    def _configure_vision(self):
        """Configure vision model (GPT-4V, Claude-3, or local inference server with llava:13b or Fara-7B)"""
        # Try OpenAI GPT-4V first
        openai_key = self.km.get_key("openai")
        if openai_key:
            self.vision_provider = "openai"
            self.vision_api_key = openai_key
            return
        
        # Try Anthropic Claude-3
        anthropic_key = self.km.get_key("anthropic")
        if anthropic_key:
            self.vision_provider = "anthropic"
            self.vision_api_key = anthropic_key
            return
        
        # Fallback to local inference server (supports both llava:13b and Fara-7B)
        self.vision_provider = "local_inference"
        self.vision_api_key = None  # Local, no key needed
        return
    
    def _extract_element_hints(self, task: str) -> str:
        """Extract search hints from task description"""
        # Common UI elements and keywords
        hints = {
            "file manager": "folder icon, file browser, Thunar",
            "terminal": "terminal icon, command line, console",
            "firefox": "Firefox icon, web browser",
            "chrome": "Chrome icon, Chromium",
            "trash": "trash can icon, recycle bin",
            "home": "home icon, home folder",
            "applications": "applications menu, app launcher",
            "settings": "settings icon, configuration",
            "network": "network icon, wifi",
            "sound": "speaker icon, volume",
            "time": "clock, time display",
            "date": "calendar, date display",
        }
        
        # Find matching hints from task
        task_lower = task.lower()
        matched_hints = []
        for keyword, hint_text in hints.items():
            if keyword in task_lower:
                matched_hints.append(hint_text)
        
        if matched_hints:
            return ", ".join(matched_hints)
        
        # If no match, extract probable element name
        if "click on" in task_lower:
            element = task_lower.split("click on")[-1].strip()
        elif "click" in task_lower:
            element = task_lower.split("click")[-1].strip()
        else:
            element = task.strip()
        
        return element[:100]  # Limit to 100 chars
    
    def capture_screen(self) -> Optional[str]:
        """Capture a screenshot from the VM
        
        Returns:
            Path to saved screenshot or None if failed
        """
        try:
            response = requests.get(
                f"{self.agent_url}/screenshot",
                timeout=10
            )
            
            if response.status_code == 200:
                # Save screenshot
                screenshot_path = Path("/tmp/auraos_screenshot.png")
                with open(screenshot_path, 'wb') as f:
                    f.write(response.content)
                return str(screenshot_path)
            else:
                print(f"Screenshot failed: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None
    
    def analyze_screen(self, screenshot_path: str, task: str) -> Optional[Dict]:
        """Analyze screenshot with vision AI and get action coordinates
        
        Args:
            screenshot_path: Path to screenshot image
            task: Natural language task (e.g., "click the Firefox icon")
            
        Returns:
            Dict with action info: {"action": "click", "x": 100, "y": 200, "confidence": 0.9}
        """
        if not self.vision_provider:
            print("No vision model available")
            return None
        
        # Read and encode image
        with open(screenshot_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        if self.vision_provider == "openai":
            return self._analyze_with_openai(image_data, task)
        elif self.vision_provider == "anthropic":
            return self._analyze_with_anthropic(image_data, task)
        elif self.vision_provider in ("ollama", "local_inference"):
            return self._analyze_with_ollama(screenshot_path, task)
        
        return None
    
    def _analyze_with_openai(self, image_data: str, task: str) -> Optional[Dict]:
        """Analyze with GPT-4V"""
        prompt = f"""You are analyzing a desktop screenshot to help automate a task.

Task: {task}

Analyze the screenshot and provide:
1. The X,Y coordinates to click (origin is top-left, Y increases downward)
2. Your confidence level (0.0-1.0)
3. A brief explanation

Respond ONLY with valid JSON in this format:
{{"action": "click", "x": 100, "y": 200, "confidence": 0.9, "explanation": "Firefox icon located at..."}}

If the task cannot be completed, respond with:
{{"action": "none", "confidence": 0.0, "explanation": "Cannot find..."}}"""
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.vision_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4-vision-preview",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 300
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                # Parse JSON from response
                return json.loads(content)
            else:
                print(f"OpenAI API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            return None
    
    def _analyze_with_anthropic(self, image_data: str, task: str) -> Optional[Dict]:
        """Analyze with Claude-3"""
        prompt = f"""You are analyzing a desktop screenshot to help automate a task.

Task: {task}

Analyze the screenshot and provide the X,Y coordinates to click. Respond ONLY with valid JSON:
{{"action": "click", "x": 100, "y": 200, "confidence": 0.9, "explanation": "..."}}"""
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.vision_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-opus-20240229",
                    "max_tokens": 300,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_data
                                    }
                                },
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["content"][0]["text"]
                return json.loads(content)
            else:
                print(f"Anthropic API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error calling Anthropic: {e}")
            return None
    
    def _analyze_with_ollama(self, screenshot_path: str, task: str) -> Optional[Dict]:
        """Analyze with local inference server (supports both Ollama and Transformers backends)"""
        # Read and base64 encode the image
        with open(screenshot_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Extract element hints for better context
        element_hints = self._extract_element_hints(task)
        
        # Prepare the vision task prompt
        vision_prompt = f"""You are analyzing a desktop screenshot to help automate a task.

Task: {task}
Looking for: {element_hints}

Analyze the screenshot and identify the exact X,Y coordinates to click to complete this task.
The screen is typically 1280x720 pixels:
- Top-left corner is (0, 0)
- Center is around (640, 360)
- Left sidebar icons are typically at x: 50-100
- Taskbar items are at the bottom

Respond with ONLY valid JSON in this exact format:
{{"action": "click", "x": <number>, "y": <number>, "confidence": <0.0-1.0>, "explanation": "<brief description>"}}

If the task cannot be completed, respond with:
{{"action": "none", "confidence": 0.0, "explanation": "Cannot find the required element"}}"""

        try:
            # Call the unified inference server /ask endpoint
            response = requests.post(
                f"{self.inference_url}/ask",
                json={
                    "prompt": vision_prompt,
                    "image": image_b64
                },
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # The /ask endpoint returns parsed JSON directly
                if "action" in result:
                    print(f"🔍 Inference response: action={result.get('action')}, "
                          f"x={result.get('x')}, y={result.get('y')}, "
                          f"confidence={result.get('confidence', 0.0)}")
                    return result
                else:
                    print(f"⚠ Unexpected response format: {result}")
                    return None
            else:
                print(f"❌ Inference server error: {response.status_code}")
                if response.text:
                    print(f"   {response.text[:200]}")
                return None
        except Exception as e:
            print(f"❌ Error calling inference server at {self.inference_url}: {e}")
            return None
    
    def _parse_response_json(self, content: str) -> Optional[Dict]:
        """Extract and parse JSON from model response
        
        Handles cases where model adds text before/after JSON
        """
        if not content:
            return None
        
        try:
            # Try direct JSON parse first
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in response
        import re
        
        # Look for {..."action"... pattern
        json_pattern = r'\{[^{}]*"action"[^{}]*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        if matches:
            # Use the first complete match
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if "action" in parsed and "x" in parsed and "y" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue
        
        # Try broader JSON extraction
        if "{" in content and "}" in content:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            try:
                return json.loads(content[json_start:json_end])
            except json.JSONDecodeError:
                pass
        
        return None
    
    def click(self, x: int, y: int) -> bool:
        """Execute a click at coordinates via the VM agent
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful
        """
        try:
            response = requests.post(
                f"{self.agent_url}/click",
                headers={"X-API-Key": self.api_key},
                json={"x": x, "y": y},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✓ Clicked at ({x}, {y})")
                return True
            else:
                print(f"Click failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"Error executing click: {e}")
            return False
    
    def automate_task(self, task: str) -> bool:
        """Fully automated task execution: capture screen, analyze, and act
        
        Args:
            task: Natural language task description
            
        Returns:
            True if task completed successfully
        """
        print(f"🤖 Automating task: {task}")
        
        # Step 1: Capture screen
        print("📸 Capturing screen...")
        screenshot = self.capture_screen()
        if not screenshot:
            print("❌ Failed to capture screenshot")
            return False
        
        print(f"✓ Screenshot saved: {screenshot}")
        
        # Step 2: Analyze with vision AI
        print("🔍 Analyzing screen with AI...")
        analysis = self.analyze_screen(screenshot, task)
        if not analysis:
            print("❌ Failed to analyze screenshot")
            return False
        
        print(f"✓ Analysis: {json.dumps(analysis, indent=2)}")
        
        # Step 3: Execute action
        if analysis.get("action") == "click" and analysis.get("confidence", 0) > 0.5:
            x = analysis["x"]
            y = analysis["y"]
            print(f"👆 Executing click at ({x}, {y})...")
            return self.click(x, y)
        else:
            print(f"❌ Cannot complete task: {analysis.get('explanation', 'Low confidence')}")
            return False


def main():
    """CLI interface for screen automation"""
    import sys
    
    if len(sys.argv) < 2:
        print("AuraOS Screen Automation")
        print("\nUsage:")
        print("  python screen_automation.py capture")
        print("  python screen_automation.py click <x> <y>")
        print("  python screen_automation.py task <description>")
        print("\nExamples:")
        print("  python screen_automation.py task 'click the Firefox icon'")
        print("  python screen_automation.py task 'open the terminal'")
        return
    
    sa = ScreenAutomation()
    command = sys.argv[1]
    
    if command == "capture":
        screenshot = sa.capture_screen()
        if screenshot:
            print(f"Screenshot saved: {screenshot}")
        else:
            print("Failed to capture screenshot")
    
    elif command == "click":
        if len(sys.argv) < 4:
            print("Usage: click <x> <y>")
            return
        x = int(sys.argv[2])
        y = int(sys.argv[3])
        sa.click(x, y)
    
    elif command == "task":
        if len(sys.argv) < 3:
            print("Usage: task <description>")
            return
        task = " ".join(sys.argv[2:])
        success = sa.automate_task(task)
        sys.exit(0 if success else 1)
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
