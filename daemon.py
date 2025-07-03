# daemon.py
# The advanced AI daemon for AuraOS.
# This version supports multiple LLM providers, generates executable scripts
# from user intent, executes them securely, and logs all actions.

import os
import json
import requests
import subprocess
import logging
from flask import Flask, request, jsonify

# --- Basic Setup & Logging ---
app = Flask(__name__)

# Set up logging to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("aura_os.log"), # Log to a file
        logging.StreamHandler()             # Also print to console
    ]
)

# --- Configuration Loading ---
# We will store secrets and configs in a separate file.
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
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_MODEL = "gemma:2b" # Our local "reflex" model

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192" # A powerful model for script generation

# --- Core Endpoints ---

@app.route('/prompt', methods=['POST'])
def handle_prompt():
    """
    Handles simple, direct prompts using the fast, local LLM.
    Use this for simple Q&A or direct command translation.
    """
    data = request.get_json()
    user_prompt = data.get('prompt')
    logging.info(f"[Local Prompt] Received: '{user_prompt}'")
    
    ollama_api_url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
    payload = {"model": OLLAMA_MODEL, "prompt": user_prompt, "stream": False}
    
    try:
        response = requests.post(ollama_api_url, json=payload)
        response.raise_for_status()
        ai_response = response.json().get('response', '').strip()
        logging.info(f"[Local Prompt] Response: '{ai_response}'")
        return jsonify({"response": ai_response})
    except requests.exceptions.RequestException as e:
        logging.error(f"Error connecting to Ollama: {e}")
        return jsonify({"error": "Could not connect to local Ollama server."}), 503

@app.route('/generate_script', methods=['POST'])
def generate_script():
    """
    Translates a user's natural language INTENT into an executable shell script.
    This uses the powerful external LLM.
    """
    data = request.get_json()
    user_intent = data.get('intent')
    logging.info(f"[Script Gen] Received Intent: '{user_intent}'")

    if not GROQ_API_KEY:
        return jsonify({"error": "Groq API key is not configured on the server."}), 500

    # This is the "magic" - a carefully crafted prompt to guide the AI.
    system_prompt = """
    You are an expert Linux shell script generator. Your task is to convert a user's intent into a single, executable shell script.
    - Only respond with a JSON object containing a single key: "script".
    - The script should be a single string.
    - Do not add any explanation or conversational text.
    - If the user's intent is unclear or dangerous (e.g., 'delete my whole system'), respond with a JSON object containing an "error" key.
    - The script must be safe and efficient.
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
        "temperature": 0.2, # Low temperature for predictability
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        generated_json = response.json()['choices'][0]['message']['content']
        script_data = json.loads(generated_json) # Parse the JSON string from the LLM
        
        logging.info(f"[Script Gen] Generated Script: {script_data.get('script')}")
        return jsonify(script_data), 200
    except Exception as e:
        logging.error(f"Error during script generation: {e}")
        return jsonify({"error": "Failed to generate script."}), 500

@app.route('/execute_script', methods=['POST'])
def execute_script():
    """
    Executes a shell script provided in the request.
    This is a powerful and DANGEROUS endpoint.
    """
    data = request.get_json()
    script_to_run = data.get('script')
    
    if not script_to_run:
        return jsonify({"error": "No script provided."}), 400

    logging.warning(f"[Execution] Preparing to run script: {script_to_run}")
    
    try:
        # Execute the script using subprocess.
        # `shell=True` is powerful but requires caution. We trust the script
        # because the user will confirm it on the client side.
        result = subprocess.run(
            script_to_run, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=False # Do not raise exception on non-zero exit codes
        )
        
        output = result.stdout
        error_output = result.stderr
        
        logging.info(f"[Execution] STDOUT: {output}")
        if error_output:
            logging.error(f"[Execution] STDERR: {error_output}")
            
        return jsonify({
            "status": "success" if result.returncode == 0 else "error",
            "return_code": result.returncode,
            "output": output,
            "error_output": error_output
        })

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

# --- Main execution ---
if __name__ == '__main__':
    logging.info("Starting AuraOS AI Daemon v2...")
    app.run(host='0.0.0.0', port=5000, debug=False) # Debug mode is off for stability
