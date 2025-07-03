# daemon.py
# The advanced AI daemon for AuraOS.
# v4: Now window-aware. It can generate commands to switch between open windows.

import os
import json
import requests
import subprocess
import logging
from flask import Flask, request, jsonify

# --- Basic Setup & Logging ---
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("aura_os.log"),
        logging.StreamHandler()
    ]
)

# --- Configuration Loading ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    GROQ_API_KEY = config.get("GROQ_API_KEY")
    if not GROQ_API_KEY:
        logging.warning("Groq API key not found in config.json. Script generation will fail.")
except FileNotFoundError:
    logging.error("CRITICAL: config.json not found. Please create it. Exiting.")
    exit()

# --- LLM Provider Definitions ---
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192"

# --- Core Endpoints ---

@app.route('/generate_script', methods=['POST'])
def generate_script():
    """
    Translates a user's natural language INTENT into an executable shell script.
    This is now aware of open windows.
    """
    data = request.get_json()
    user_intent = data.get('intent')
    context = data.get('context', {})
    cwd = context.get('cwd', '.')
    
    windows = context.get('windows', [])
    window_list_str = "\n- ".join(windows) if windows else "No open windows detected."
    
    logging.info(f"[Script Gen] Intent: '{user_intent}' | CWD: '{cwd}' | Windows: {windows}")

    if not GROQ_API_KEY:
        return jsonify({"error": "Groq API key is not configured on the server."}), 500

    system_prompt = f"""
    You are an expert Linux shell script generator. Your task is to convert a user's intent into a single, executable shell script.
    
    CONTEXT:
    - The user's current directory is: {cwd}
    - The user has the following windows open:
    - {window_list_str}

    INSTRUCTIONS:
    - For file operations, assume the current directory unless a full path is specified.
    - To switch to an open window, use the command `wmctrl -a "substring_of_window_title"`. For example, to switch to a Firefox window, you can use `wmctrl -a "Firefox"`. Be specific enough to avoid ambiguity.
    - Only respond with a JSON object containing a single key: "script".
    - The script must be a single string. Do not add any explanation.
    - If the intent is unclear or dangerous, respond with a JSON object containing an "error" key.
    """

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_intent}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        generated_json = response.json()['choices'][0]['message']['content']
        script_data = json.loads(generated_json)
        logging.info(f"[Script Gen] Generated Script: {script_data.get('script')}")
        return jsonify(script_data), 200
    except Exception as e:
        logging.error(f"Error during script generation: {e}")
        return jsonify({"error": "Failed to generate script."}), 500

@app.route('/execute_script', methods=['POST'])
def execute_script():
    """Executes a shell script provided in the request."""
    data = request.get_json()
    script_to_run = data.get('script')
    if not script_to_run:
        return jsonify({"error": "No script provided."}), 400
    
    logging.warning(f"[Execution] Preparing to run script: {script_to_run}")

    # --- NEW: Get graphical context for running GUI apps ---
    context = data.get('context', {})
    display_var = context.get('display')
    
    script_env = os.environ.copy()
    if display_var:
        script_env['DISPLAY'] = display_var
        logging.info(f"[Execution] Using DISPLAY={display_var} for GUI context.")

    try:
        result = subprocess.run(
            script_to_run, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=False,
            env=script_env # Use the modified environment
        )
        output = result.stdout
        error_output = result.stderr
        logging.info(f"[Execution] STDOUT: {output}")
        if error_output: logging.error(f"[Execution] STDERR: {error_output}")
        return jsonify({"status": "success" if result.returncode == 0 else "error", "return_code": result.returncode, "output": output, "error_output": error_output})
    except Exception as e:
        logging.critical(f"[Execution] Failed to execute script: {e}")
        return jsonify({"error": f"An unexpected error occurred during execution: {e}"}), 500

@app.route('/get_logs', methods=['GET'])
def get_logs():
    """A simple endpoint to view the action history."""
    try:
        with open('aura_os.log', 'r') as f:
            return f.read(), 200, {'Content-Type': 'text/plain'}
    except FileNotFoundError:
        return "Log file not found.", 404

if __name__ == '__main__':
    logging.info("Starting AuraOS AI Daemon v4 (Window-Aware)...")
    app.run(host='0.0.0.0', port=5000, debug=False)
