# daemon.py
# The advanced AI daemon for AuraOS.
# v6: Now multi-lingual. It decides whether to generate a shell script or a 
#     more powerful Python script based on the user's request.

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
    Translates a user's intent into an executable script, deciding
    between shell and Python based on the task's complexity.
    """
    data = request.get_json()
    user_intent = data.get('intent')
    context = data.get('context', {})
    cwd = context.get('cwd', '.')
    windows = context.get('windows', [])
    window_list_str = "\n- ".join(windows) if windows else "No open windows detected."
    
    logging.info(f"[Script Gen] Intent: '{user_intent}'")

    # --- The system prompt that teaches the AI its new skill ---
    system_prompt = f"""
    You are an expert script generator. Your task is to convert a user's request into an executable script. You can generate either shell or Python scripts.

    DECISION CRITERIA:
    - If the task involves simple file operations (ls, cd, mkdir, cp), system commands, or window management (wmctrl), generate a 'shell' script.
    - If the task requires complex logic, web scraping, accessing APIs, or processing large amounts of data (e.g., "list all MLB players and their salaries"), you MUST generate a 'python' script.
    - Python scripts should be self-contained and use standard libraries (like requests, json, os) if possible. Do not assume non-standard packages are installed.

    RESPONSE FORMAT:
    - You MUST respond with a JSON object containing two keys: "script_type" (a string, either "shell" or "python") and "script" (the code as a single string).
    - Do not add any explanation or conversational text.
    - If the task is impossible or dangerous, respond with a JSON object containing an "error" key.

    CONTEXT:
    - The user's current directory is: {cwd}
    - The user has the following windows open:
    - {window_list_str}
    """

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_intent}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        generated_json = response.json()['choices'][0]['message']['content']
        script_data = json.loads(generated_json)
        logging.info(f"[Script Gen] Generated '{script_data.get('script_type')}' script.")
        return jsonify(script_data), 200
    except Exception as e:
        logging.error(f"Error during script generation: {e}")
        return jsonify({"error": "Failed to generate script."}), 500

@app.route('/execute_script', methods=['POST'])
def execute_script():
    """
    Executes a shell script provided in the request. 
    Note: The client is responsible for executing Python scripts.
    """
    data = request.get_json()
    script_to_run = data.get('script')
    context = data.get('context', {})
    display_var = context.get('display')
    
    if not script_to_run: return jsonify({"error": "No script provided."}), 400
    logging.warning(f"[Execution] Preparing to run SHELL script: {script_to_run}")
    
    script_env = os.environ.copy()
    if display_var: script_env['DISPLAY'] = display_var

    try:
        result = subprocess.run(script_to_run, shell=True, capture_output=True, text=True, check=False, env=script_env)
        output = result.stdout
        error_output = result.stderr
        logging.info(f"[Execution] STDOUT: {output}")
        if error_output: logging.error(f"[Execution] STDERR: {error_output}")
        return jsonify({"status": "success" if result.returncode == 0 else "error", "return_code": result.returncode, "output": output, "error_output": error_output})
    except Exception as e:
        logging.critical(f"[Execution] Failed to execute script: {e}")
        return jsonify({"error": f"An unexpected error occurred during execution: {e}"}), 500

if __name__ == '__main__':
    logging.info("Starting AuraOS AI Daemon v6 (Multi-lingual)...")
    app.run(host='0.0.0.0', port=5000, debug=False)
