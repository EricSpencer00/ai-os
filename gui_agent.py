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
from flask import Flask, request, jsonify, send_file
import pyautogui
from PIL import Image
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

# PyAutoGUI safety settings
pyautogui.FAILSAFE = False

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
