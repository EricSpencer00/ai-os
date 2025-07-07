"""
Shell plugin for AuraOS Autonomous AI Daemon v8
Executes shell scripts and generates shell scripts from intent.
"""
import os
import json
import requests
import re
import subprocess
from flask import jsonify

# Load config for API keys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    GROQ_API_KEY = config.get("GROQ_API_KEY")
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL = "llama3-70b-8192"
except Exception:
    GROQ_API_KEY = None
    GROQ_API_URL = None
    GROQ_MODEL = None

class Plugin:
    name = "shell"
    def generate_script(self, intent, context):
        if not GROQ_API_KEY or not GROQ_API_URL:
            return jsonify({"error": "Groq API key or URL missing."}), 500
        system_prompt = (
            "You are a helpful assistant. Generate a bash shell script for the following user intent. "
            "Return only the script, no explanation."
        )
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": intent}
            ],
            "temperature": 0.1
        }
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            msg = response.json()["choices"][0]["message"]["content"]
            # Remove code block markers if present
            script = re.sub(r'```(bash|sh)?', '', msg, flags=re.IGNORECASE).replace('```', '').strip()
            return jsonify({"script_type": "shell", "script": script}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to generate script: {e}"}), 500

    def execute(self, script, context):
        try:
            result = subprocess.run(script, shell=True, capture_output=True, text=True)
            return jsonify({
                "status": "success" if result.returncode == 0 else "error",
                "return_code": result.returncode,
                "output": result.stdout,
                "error_output": result.stderr
            })
        except ImportError as e:
            # Report missing ability and trigger self-improvement
            ability = str(e).split('No module named ')[-1].replace("'", "").strip()
            try:
                # Use curl to avoid dependency on requests
                os.system(f"curl -s -X POST http://localhost:5050/report_missing_ability -H 'Content-Type: application/json' -d '{{\"ability\": \"{ability}\"}}'")
                os.system("curl -s -X POST http://localhost:5050/self_reflect")
            except Exception:
                pass
            return jsonify({"error": f"Missing ability: {ability}. Self-improvement triggered. Please retry shortly."}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
