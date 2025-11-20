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
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.lima.internal:11434") # Default for macOS Multipass

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
    """Client for interacting with Vision LLM (Ollama)."""
    def __init__(self, base_url):
        self.base_url = base_url

    def ask(self, query, image_paths):
        url = f"{self.base_url}/api/generate"
        
        images_b64 = []
        for _, path in image_paths:
            try:
                with open(path, "rb") as f:
                    images_b64.append(base64.b64encode(f.read()).decode('utf-8'))
            except Exception as e:
                logging.error(f"Failed to read image {path}: {e}")

        # If no images, just send text
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
            "model": "llava:13b",
            "prompt": prompt,
            "stream": False,
            "images": images_b64 if images_b64 else None,
            "format": "json" 
        }

        try:
            logging.info(f"Sending request to Ollama at {url}...")
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logging.error(f"VisionClient error: {e}")
            return None

# Initialize components
monitor = ScreenMonitor()
monitor.start()
vision_client = VisionClient(OLLAMA_URL)

@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.json
        query = data.get('query')
        if not query:
            return jsonify({"error": "Missing query"}), 400
            
        logging.info(f"Received AI query: {query}")
        
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
