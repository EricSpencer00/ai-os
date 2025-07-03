# daemon.py
# The advanced AI daemon for AuraOS.
# v6: Now multi-lingual and multi-provider. It uses OpenRouter for specialized tasks.

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
    OPENROUTER_API_KEY = config.get("OPENROUTER_API_KEY") # Using OpenRouter key now
except FileNotFoundError:
    logging.error("CRITICAL: config.json not found. Please create it. Exiting.")
    exit()

# --- LLM Provider Definitions ---
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192"

# --- OpenRouter Configuration ---
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEEPSEEK_MODEL = "deepseek/deepseek-coder" # The free Deepseek Coder model

# --- Core Endpoints ---

@app.route('/generate_script', methods=['POST'])
def generate_script():
    """
    Translates a user's intent into an executable script, deciding
    between shell and Python and switching AI models based on the task.
    """
    data = request.get_json()
    user_intent = data.get('intent')
    context = data.get('context', {})
    cwd = context.get('cwd', '.')
    windows = context.get('windows', [])
    window_list_str = "\n- ".join(windows) if windows else "No open windows detected."
    
    logging.info(f"[Script Gen] Intent: '{user_intent}'")

    system_prompt = f"""
    You are the core AI of AuraOS, an AI-native operating system. Your primary function is to assist the user by generating scripts. You have two special capabilities: Standard Scripting and Self-Modification.

    **1. STANDARD SCRIPTING PROTOCOL**
    - For simple file/system tasks, generate a 'shell' script.
    - For complex logic, web scraping, or data processing, generate a 'python' script.
    - Your response MUST be a JSON object with "script_type" and "script" keys.

    **2. SELF-MODIFICATION PROTOCOL (TOP PRIORITY)**
    - If the user asks you to "learn", "improve", "add a feature", or "modify yourself", you MUST follow this protocol. You are generating the new version of your own source code (`daemon.py`).
    - **Step 1:** Recall your own structure. You are a Flask app in a file named `daemon.py`. You have endpoints like `/generate_script` and `/execute_script`.
    - **Step 2:** Generate the **complete, new, and correct source code for `daemon.py`** from scratch that implements the user's requested change, while preserving all existing functionality.
    - **Step 3:** If the new code requires new python packages, identify them in a "packages" list.
    - **Step 4:** Generate a 'shell' script that calls the supervisor `updater.py`. The script MUST be in the format: `python3 updater.py <base64_encoded_json_payload>`.
    - **Step 5:** The payload is a base64-encoded JSON object: `{{ "code": "...", "packages": ["...", "..."] }}`. You must generate this payload correctly.

    **CONTEXT FOR STANDARD SCRIPTING:**
    - CWD: {cwd}
    - Open Windows: {window_list_str}
    """
    
    # --- Model Switching Logic ---
    is_modification_task = any(keyword in user_intent.lower() for keyword in ["modify", "improve", "learn", "add a feature"])

    if is_modification_task:
        logging.info("Task identified as self-modification. Switching to OpenRouter DeepSeek model.")
        api_url = OPENROUTER_API_URL
        api_key = OPENROUTER_API_KEY
        model = OPENROUTER_DEEPSEEK_MODEL
        if not api_key:
            return jsonify({"error": "OpenRouter API key not configured for self-modification."}), 500
    else:
        api_url = GROQ_API_URL
        api_key = GROQ_API_KEY
        model = GROQ_MODEL
        if not api_key:
            return jsonify({"error": "Groq API key not configured for standard tasks."}), 500

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # OpenRouter recommends these headers for identification
        "HTTP-Referer": "https://github.com/your-repo/AuraOS", 
        "X-Title": "AuraOS"
    }
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_intent}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        generated_json_string = response.json()['choices'][0]['message']['content']
        script_data = json.loads(generated_json_string) # The model itself returns a JSON string

        logging.info(f"[Script Gen] Generated '{script_data.get('script_type')}' script using {model}.")
        return jsonify(script_data), 200
    except Exception as e:
        logging.error(f"Error during script generation with {model}: {e}")
        return jsonify({"error": f"Failed to generate script using {model}."}), 500

@app.route('/execute_script', methods=['POST'])
def execute_script():
    """Executes a shell script provided in the request."""
    data = request.get_json()
    script_to_run = data.get('script')
    context = data.get('context', {})
    display_var = context.get('display')
    
    if not script_to_run: return jsonify({"error": "No script provided."}), 400
    logging.warning(f"[Execution] Preparing to run SHELL script: {script_to_run}")
    
    script_env = os.environ.copy()
    if display_var: script_env['DISPLA