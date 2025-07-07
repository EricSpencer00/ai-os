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
        # Track error attempts in a file
        error_log_path = os.path.join(BASE_DIR, "last_error.log")
        try:
            result = subprocess.run(script, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                # On success, clear error log
                if os.path.exists(error_log_path):
                    os.remove(error_log_path)
                return jsonify({
                    "status": "success",
                    "return_code": result.returncode,
                    "output": result.stdout,
                    "error_output": result.stderr
                })
            else:
                # On error, log and handle retries
                error_output = result.stderr.strip()
                # Read previous error log
                error_count = 1
                last_error = ""
                if os.path.exists(error_log_path):
                    with open(error_log_path, "r") as f:
                        lines = f.readlines()
                        if len(lines) == 2:
                            last_error = lines[0].strip()
                            try:
                                error_count = int(lines[1].strip())
                            except Exception:
                                error_count = 1
                if error_output == last_error:
                    error_count += 1
                else:
                    error_count = 1
                # Save current error
                with open(error_log_path, "w") as f:
                    f.write(error_output + "\n" + str(error_count))
                # If error repeats 3+ times, rollback and try a different approach
                if error_count >= 3:
                    # Rollback to previous system (git reset)
                    os.system("git reset --hard HEAD~1")
                    os.system("git add daemon.py")
                    os.system("git commit -m '[ai] Rollback after repeated error' || true")
                    # Optionally, trigger self-improvement with a new approach
                    os.system(f"curl -s -X POST http://localhost:5050/report_missing_ability -H 'Content-Type: application/json' -d '{{\"ability\": \"alternative_solution\"}}'")
                    os.system("curl -s -X POST http://localhost:5050/self_reflect")
                    return jsonify({"error": f"Repeated error detected. Rolled back and will try a different approach. Error: {error_output}"}), 500
                else:
                    # Pass error back to system for reiteration
                    os.system(f"curl -s -X POST http://localhost:5050/report_missing_ability -H 'Content-Type: application/json' -d '{{\"ability\": \"{error_output[:100]}\"}}'")
                    os.system("curl -s -X POST http://localhost:5050/self_reflect")
                    return jsonify({"error": f"Error occurred. Self-improvement triggered. Please retry. Error: {error_output}"}), 500
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
