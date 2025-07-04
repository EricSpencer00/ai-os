# daemon.py
# The final, autonomous AI daemon for AuraOS.
# This version implements a ReAct (Reason+Act) loop, allowing the AI
# to use tools, observe results, and reason step-by-step to solve complex tasks.

import os
import json
import requests
import subprocess
import logging
from flask import Flask, request, jsonify
import base64

# --- Basic Setup & Logging ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler("aura_os.log"), logging.StreamHandler()])

# --- Configuration Loading ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    OPENROUTER_API_KEY = config.get("OPENROUTER_API_KEY")
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not found in config.json.")
except Exception as e:
    logging.error(f"CRITICAL: Failed to load config. {e}. Exiting.")
    exit()

# --- LLM Provider Definitions ---
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AGENT_MODEL = "mistralai/mistral-7b-instruct:free"
MAX_AGENT_LOOPS = 7 # Max steps the agent can take

# --- Agent's Tools ---

def execute_shell(command: str) -> str:
    """Executes a shell command and returns its output or error."""
    logging.info(f"TOOL: Executing shell command: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        # Combine stdout and stderr to give the AI full context
        output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        return output.strip()
    except Exception as e:
        return f"Error executing shell command: {e}"

def write_file(path: str, content: str) -> str:
    """Writes content to a file. For self-modification, the path should be 'daemon.py'."""
    logging.info(f"TOOL: Writing to file: {path}")
    try:
        # For self-modification, we need the full path
        full_path = os.path.expanduser(f'~/aura-os/{path}')
        with open(full_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {path}."
    except Exception as e:
        return f"Error writing to file: {e}"

def read_file(path: str) -> str:
    """Reads the content of a file."""
    logging.info(f"TOOL: Reading file: {path}")
    try:
        full_path = os.path.expanduser(f'~/aura-os/{path}')
        with open(full_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

AVAILABLE_TOOLS = {
    "execute_shell": execute_shell,
    "write_file": write_file,
    "read_file": read_file,
}

# --- Core Agent Logic ---

@app.route('/agent_task', methods=['POST'])
def agent_task():
    """Receives a user's intent and starts the ReAct loop."""
    user_intent = request.json.get('intent')
    history = [] # The agent's scratchpad for this task

    for i in range(MAX_AGENT_LOOPS):
        logging.info(f"\n--- Agent Loop {i+1}/{MAX_AGENT_LOOPS} ---")
        
        # 1. REASON: Ask the AI for the next action
        system_prompt = f"""
You are AuraOS, a reasoning agent. Your goal is to achieve the user's objective by thinking step-by-step and using tools.

**Available Tools:**
- `execute_shell(command: str)`: Executes a shell command.
- `write_file(path: str, content: str)`: Writes to a file. To modify yourself, write to 'daemon.py'.
- `read_file(path: str)`: Reads a file.
- `finish(answer: str)`: Call this when the task is fully complete.

**Your Thought Process:**
1.  **Observation:** Review the history of previous actions and their results.
2.  **Thought:** Based on the observation and the original goal, decide the next logical step. If a previous step failed, analyze the error and form a new plan.
3.  **Action:** Choose ONE tool to execute. Your response MUST be a single, valid JSON object with "tool_name" and "tool_args" keys. Do not add any other text.

**History of this task so far:**
{json.dumps(history, indent=2)}

**User's Objective:** {user_intent}
"""
        
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": AGENT_MODEL, 
            "messages": [{"role": "system", "content": system_prompt}],
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            
            tool_call = json.loads(response.json()['choices'][0]['message']['content'])
            
            tool_name = tool_call.get("tool_name")
            tool_args = tool_call.get("tool_args", {})

        except Exception as e:
            logging.error(f"Failed to get or parse AI action: {e}")
            observation = f"Error: The last AI response was not a valid JSON object. Error: {e}. Please respond with only a valid JSON object."
            history.append({"action": "parse_ai_response", "observation": observation})
            continue

        # 2. ACT: Execute the chosen action
        if tool_name == "finish":
            logging.info("AI decided to finish the task.")
            return jsonify({"answer": tool_args.get("answer", "Task complete.")})

        if tool_name in AVAILABLE_TOOLS:
            tool_function = AVAILABLE_TOOLS[tool_name]
            observation = tool_function(**tool_args)
        else:
            observation = f"Error: Unknown tool '{tool_name}'. Please choose from the available tools."
        
        logging.info(f"Observation: {observation}")
        history.append({"action": tool_call, "observation": observation})

    return jsonify({"error": "Agent exceeded maximum loops."})

if __name__ == '__main__':
    logging.info("Starting AuraOS AI Daemon v9 (ReAct Agent)...")
    app.run(host='0.0.0.0', port=5000, debug=False)
