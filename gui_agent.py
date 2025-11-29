#!/usr/bin/env python3
"""
AuraOS GUI Agent
Runs inside the VM to provide HTTP access to the desktop (screenshots, clicks, typing).
"""
import os
import sys
import time
import threading
import logging
import requests
import base64
import json
import math
import operator
from functools import reduce
from flask import Flask, request, jsonify, send_file
import pyautogui
from PIL import Image, ImageChops
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gui_agent.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Configuration
SCREENSHOT_DIR = "/tmp/auraos_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
# Default: if running in VM, use host gateway; if running on host, use localhost
DEFAULT_INFERENCE_URL = "http://192.168.2.1:8081" if os.path.exists("/opt/auraos") else "http://localhost:8081"
INFERENCE_SERVER_URL = os.environ.get("AURAOS_INFERENCE_URL", DEFAULT_INFERENCE_URL)

# PyAutoGUI safety settings
pyautogui.FAILSAFE = False

class ScreenMonitor(threading.Thread):
    """Monitors screen for changes and caches screenshots."""
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.last_image = None
        self.history = [] # List of (timestamp, filepath)
        self.lock = threading.Lock()
        self.running = True

    def run(self):
        logging.info("ScreenMonitor started.")
        while self.running:
            try:
                img = pyautogui.screenshot()
                timestamp = int(time.time())
                
                if self.last_image:
                    diff = ImageChops.difference(img, self.last_image)
                    histogram = diff.histogram()
                    # Calculate RMS difference
                    rms = math.sqrt(reduce(operator.add,
                        map(lambda h, i: h*(i**2), histogram, range(256))
                    ) / (float(img.size[0]) * img.size[1]))
                    
                    if rms > 5: # Threshold for "meaningful change"
                        self._save_screenshot(img, timestamp)
                else:
                    self._save_screenshot(img, timestamp)
                
                self.last_image = img
                time.sleep(2) # Check every 2 seconds
            except Exception as e:
                logging.error(f"ScreenMonitor error: {e}")
                time.sleep(5)

    def _save_screenshot(self, img, timestamp):
        filename = f"screen_{timestamp}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        img.save(filepath)
        
        with self.lock:
            self.history.append((timestamp, filepath))
            # Keep last 10 screenshots
            if len(self.history) > 10:
                old_ts, old_path = self.history.pop(0)
                try:
                    os.remove(old_path)
                except:
                    pass
        logging.info(f"Captured meaningful screenshot: {filename}")

    def get_recent_screenshots(self, limit=3):
        with self.lock:
            return self.history[-limit:]

class VisionClient:
    """Client for interacting with Vision LLM (local inference server)."""
    def __init__(self, base_url):
        self.base_url = base_url  # Expected: http://localhost:8081

    def ask(self, query, image_paths):
        url = f"{self.base_url}/ask"
        
        images_b64 = []
        for _, path in image_paths:
            try:
                with open(path, "rb") as f:
                    images_b64.append(base64.b64encode(f.read()).decode('utf-8'))
            except Exception as e:
                logging.error(f"Failed to read image {path}: {e}")

        # Craft a prompt for the vision model
        prompt = f"""You are an AI OS Assistant controlling a computer.
User Request: "{query}"
Based on the attached screenshots of the user's screen, output a JSON list of actions to perform.
Supported actions:
- {{"action": "click", "x": 100, "y": 200}}
- {{"action": "type", "text": "hello"}}
- {{"action": "key", "key": "enter"}}
- {{"action": "scroll", "amount": 10}}
- {{"action": "wait", "seconds": 1}}

Output ONLY the JSON list. Example: [{{"action": "click", "x": 10, "y": 10}}]
"""
        
        payload = {
            "query": prompt,
            "images": images_b64 if images_b64 else [],
            "parse_json": True
        }

        try:
            logging.info(f"Sending request to local inference server at {url}...")
            # Increased timeout to 180s for slower models/hardware
            response = requests.post(url, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logging.error(f"VisionClient error: {e}")
            return None

# Initialize components
monitor = ScreenMonitor()
monitor.start()
vision_client = VisionClient(INFERENCE_SERVER_URL)

@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.json
        query = data.get('query')
        if not query:
            return jsonify({"error": "Missing query"}), 400
            
        logging.info(f"Received AI query: {query}")
        
        # Check if this is an app installation request
        if any(keyword in query.lower() for keyword in ["install ", "install application", "install app"]):
            return handle_app_installation(query)
        
        # Get context
        recent_screens = monitor.get_recent_screenshots()
        
        # Ask LLM
        llm_response = vision_client.ask(query, recent_screens)
        
        if not llm_response:
            return jsonify({"error": "Failed to get response from AI"}), 500
            
        logging.info(f"AI Response: {llm_response}")
        
        # Parse and execute actions
        try:
            actions = json.loads(llm_response)
            
            # Handle single object response
            if isinstance(actions, dict):
                actions = [actions]
                
            if not isinstance(actions, list):
                return jsonify({"error": "AI response is not a list or dict", "raw": llm_response}), 500
                
            results = []
            for action in actions:
                if not isinstance(action, dict):
                    continue
                    
                act_type = action.get("action")
                if act_type == "click":
                    pyautogui.click(x=action.get("x"), y=action.get("y"))
                elif act_type == "type":
                    pyautogui.write(action.get("text"), interval=0.05)
                elif act_type == "key":
                    pyautogui.press(action.get("key"))
                elif act_type == "scroll":
                    pyautogui.scroll(action.get("amount"))
                elif act_type == "wait":
                    time.sleep(action.get("seconds", 1))
                results.append({"status": "success", "action": action})
                time.sleep(0.5)
                
            return jsonify({"status": "success", "executed": results})
            
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON from AI", "raw": llm_response}), 500
            
    except Exception as e:
        logging.error(f"Ask failed: {e}")
        return jsonify({"error": str(e)}), 500

def handle_app_installation(query):
    """
    Smart app installer for AuraOS.
    Handles requests like "install firefox", "install chromium", etc.
    Uses apt-get inside the VM.
    """
    try:
        # Extract app name from query
        app_name = None
        keywords = ["install", "application", "app"]
        words = query.lower().split()
        
        for i, word in enumerate(words):
            if word == "install" and i + 1 < len(words):
                # Get the next word(s) as app name
                potential_app = words[i + 1]
                if potential_app not in keywords:
                    app_name = potential_app
                    break
        
        if not app_name:
            return jsonify({"error": "Could not determine which app to install"}), 400
        
        logging.info(f"Installing app: {app_name}")
        
        # Map common app names to package names
        package_map = {
            "firefox": "firefox",
            "chromium": "chromium-browser",
            "chrome": "chromium-browser",
            "git": "git",
            "python": "python3",
            "node": "nodejs",
            "npm": "npm",
            "docker": "docker.io",
            "curl": "curl",
            "wget": "wget",
            "vlc": "vlc",
            "gimp": "gimp",
            "blender": "blender",
        }
        
        package_name = package_map.get(app_name.lower(), app_name.lower())
        
        # Install via multipass
        install_cmd = [
            "multipass", "exec", "auraos-multipass", "--",
            "sudo", "bash", "-c",
            f"apt-get update -qq && apt-get install -y {package_name}"
        ]
        
        logging.info(f"Running install command: {' '.join(install_cmd)}")
        
        result = subprocess.run(
            install_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            logging.info(f"Successfully installed {app_name}")
            return jsonify({
                "status": "success",
                "message": f"{app_name} installed successfully",
                "executed": [{"action": "install", "app": app_name, "status": "success"}]
            }), 200
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logging.error(f"Failed to install {app_name}: {error_msg}")
            return jsonify({
                "status": "error",
                "message": f"Failed to install {app_name}",
                "error": error_msg[:200],
                "executed": []
            }), 500
            
    except subprocess.TimeoutExpired:
        logging.error(f"Installation timeout for {app_name}")
        return jsonify({
            "status": "error",
            "message": f"Installation timeout for {app_name}",
            "executed": []
        }), 500
    except Exception as e:
        logging.error(f"App installation error: {e}")
        return jsonify({
            "status": "error",
            "message": f"Installation error: {str(e)}",
            "executed": []
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "platform": sys.platform})

@app.route('/screenshot', methods=['GET'])
def screenshot():
    try:
        # Capture screenshot
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        
        # Take screenshot
        img = pyautogui.screenshot()
        img.save(filepath)
        
        # Return image
        return send_file(filepath, mimetype='image/png')
    except Exception as e:
        logging.error(f"Screenshot failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/click', methods=['POST'])
def click():
    try:
        data = request.json
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            return jsonify({"error": "Missing x or y coordinates"}), 400
            
        logging.info(f"Clicking at ({x}, {y})")
        pyautogui.click(x=x, y=y)
        
        return jsonify({"status": "success", "action": "click", "x": x, "y": y})
    except Exception as e:
        logging.error(f"Click failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/type', methods=['POST'])
def type_text():
    try:
        data = request.json
        text = data.get('text')
        
        if not text:
            return jsonify({"error": "Missing text"}), 400
            
        logging.info(f"Typing: {text}")
        pyautogui.write(text, interval=0.05)
        
        return jsonify({"status": "success", "action": "type"})
    except Exception as e:
        logging.error(f"Typing failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/key', methods=['POST'])
def press_key():
    try:
        data = request.json
        key = data.get('key')
        
        if not key:
            return jsonify({"error": "Missing key"}), 400
            
        logging.info(f"Pressing key: {key}")
        pyautogui.press(key)
        
        return jsonify({"status": "success", "action": "press", "key": key})
    except Exception as e:
        logging.error(f"Key press failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/scroll', methods=['POST'])
def scroll():
    try:
        data = request.json
        amount = data.get('amount', 0)
        
        logging.info(f"Scrolling: {amount}")
        pyautogui.scroll(amount)
        
        return jsonify({"status": "success", "action": "scroll", "amount": amount})
    except Exception as e:
        logging.error(f"Scroll failed: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure DISPLAY is set
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':99'
        
    logging.info("Starting AuraOS GUI Agent on port 8765...")
    app.run(host='0.0.0.0', port=8765)
