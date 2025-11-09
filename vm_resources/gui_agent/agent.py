#!/usr/bin/env python3
"""AuraOS GUI automation agent (minimal, API-key protected)

Endpoints:
 - GET  /health            -> 200 OK
 - GET  /screenshot        -> returns PNG screenshot (captures DISPLAY :1)
 - POST /ocr              -> {"path": "/tmp/foo.png"} -> {"text": "..."}
 - POST /click            -> {"x": 100, "y": 200}  -> simulates click via xdotool

Security: expects header 'X-API-Key' matching env var AURAOS_AGENT_KEY for state-changing endpoints.
"""
from flask import Flask, request, jsonify, send_file, abort
import os, subprocess, uuid, shlex

app = Flask(__name__)
API_KEY = os.environ.get('AURAOS_AGENT_KEY', 'auraos_dev_key')
DISPLAY = os.environ.get('DISPLAY', ':1')

def require_api_key():
    key = request.headers.get('X-API-Key')
    if key != API_KEY:
        abort(401, description='invalid api key')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'display': DISPLAY})

@app.route('/screenshot', methods=['GET'])
def screenshot():
    out = f'/tmp/screen_{uuid.uuid4().hex}.png'
    cmd = f'DISPLAY={shlex.quote(DISPLAY)} scrot {shlex.quote(out)}'
    subprocess.run(cmd, shell=True)
    if not os.path.exists(out):
        return jsonify({'error': 'screenshot failed'}), 500
    return send_file(out, mimetype='image/png')

@app.route('/ocr', methods=['POST'])
def ocr():
    require_api_key()
    data = request.json or {}
    path = data.get('path')
    if not path or not os.path.exists(path):
        return jsonify({'error':'missing path or file not found'}), 400
    proc = subprocess.run(['tesseract', path, 'stdout'], capture_output=True, text=True)
    return jsonify({'text': proc.stdout})

@app.route('/click', methods=['POST'])
def click():
    require_api_key()
    data = request.json or {}
    x = data.get('x')
    y = data.get('y')
    if x is None or y is None:
        return jsonify({'error':'x and y required'}), 400
    cmd = f'DISPLAY={shlex.quote(DISPLAY)} xdotool mousemove {int(x)} {int(y)} click 1'
    subprocess.run(cmd, shell=True)
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8765)
