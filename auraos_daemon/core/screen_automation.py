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
    """AI-powered screen automation using vision models"""
    
    def __init__(self, agent_url: str = "http://localhost:8765", 
                 api_key: Optional[str] = None):
        """Initialize screen automation
        
        Args:
            agent_url: URL of the GUI agent running in the VM
            api_key: API key for the agent (default: from KeyManager)
        """
        self.agent_url = agent_url.rstrip('/')
        self.km = KeyManager()
        self.api_key = api_key or self.km.get_key("agent") or "auraos_dev_key"
        
        # Vision model configuration
        self.vision_provider = None
        self.vision_api_key = None
        self._configure_vision()
    
    def _configure_vision(self):
        """Configure vision model (GPT-4V, Claude-3, or Ollama LLaVA)"""
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
        
        # Fallback to local Ollama with LLaVA
        ollama_config = self.km.get_ollama_config()
        if ollama_config:
            self.vision_provider = "ollama"
            self.vision_api_key = None  # Local, no key needed
            return
        
        print("Warning: No vision model configured. Add OpenAI, Anthropic, or enable Ollama.")
    
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
        elif self.vision_provider == "ollama":
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
        """Analyze with local Ollama LLaVA"""
        ollama_config = self.km.get_ollama_config()
        base_url = ollama_config.get("base_url", "http://localhost:11434")
        model = ollama_config.get("vision_model", "llava:13b")
        
        # Read and base64 encode the image for Ollama
        with open(screenshot_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = f"""You are a desktop automation assistant analyzing a screenshot.

Task: {task}

Look at the screenshot carefully. Identify the UI element mentioned in the task and provide its pixel coordinates.
The coordinate system has origin (0,0) at the top-left corner. X increases to the right, Y increases downward.

Respond with ONLY a valid JSON object in this exact format:
{{"action": "click", "x": 100, "y": 200, "confidence": 0.9, "explanation": "Found Firefox icon in top-left area"}}

If you cannot find the element or complete the task, respond:
{{"action": "none", "confidence": 0.0, "explanation": "Element not visible in screenshot"}}

Remember: Provide ONLY the JSON object, no other text."""
        
        try:
            # Ollama vision API (v1.0+ format)
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Lower temperature for more deterministic coordinates
                        "num_predict": 200
                    }
                },
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "").strip()
                print(f"Ollama response: {content[:200]}...")
                
                # Try to extract JSON from response
                if "{" in content and "}" in content:
                    json_start = content.index("{")
                    json_end = content.rindex("}") + 1
                    parsed = json.loads(content[json_start:json_end])
                    return parsed
                else:
                    print("No JSON found in Ollama response")
                    return None
            else:
                print(f"Ollama API error: {response.status_code} - {response.text}")
                return None
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Content was: {content}")
            return None
        except Exception as e:
            print(f"Error calling Ollama: {e}")
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
