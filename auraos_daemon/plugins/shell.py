"""
Shell plugin for AuraOS Autonomous AI Daemon v8
Executes shell scripts and generates shell scripts from intent.
"""
import os
import json
import requests
import re
import subprocess
import shutil
import time
from flask import jsonify
from core.security import sanitize_command, is_safe_url
from core.memory import Memory

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

DOWNLOADS_DIR = os.path.expanduser('~/Downloads')

class Plugin:
    name = "shell"
    
    def __init__(self):
        self.memory = Memory()
        
    def classify_intent(self, intent):
        """
        Classify the user intent as one of: [file_operation, web, system, script, chat, greeting, unknown]
        """
        lower_intent = intent.lower()
        if any(word in lower_intent for word in ["hello", "hi", "hey", "greetings"]):
            return "greeting"
        if any(word in lower_intent for word in ["how are you", "who are you", "what is your name"]):
            return "chat"
        if any(word in lower_intent for word in ["list", "search", "find", "copy", "move", "delete", "file", "folder", "directory"]):
            return "file_operation"
        if any(word in lower_intent for word in ["open website", "fetch", "download", "web", "browser", "navigate"]):
            return "web"
        if any(word in lower_intent for word in ["system info", "cpu", "memory", "disk", "os version"]):
            return "system"
        if any(word in lower_intent for word in ["script", "run", "execute", "bash", "python", "shell"]):
            return "script"
        return "unknown"

    def generate_script(self, intent, context):
        category = self.classify_intent(intent)
        if category == "greeting":
            return jsonify({"script_type": "chat", "script": "Hello! How can I help you today?"}), 200
        if category == "chat":
            return jsonify({"script_type": "chat", "script": "I'm AuraOS, your AI assistant!"}), 200
            
        # Get memory context for similar commands
        memory_context = self.memory.get_context_for_intent(intent)
        
        # Build the system prompt with memory context
        base_prompt = ""
        if category == "file_operation":
            base_prompt = (
                "You are a file assistant. Generate a bash shell script for the following file operation. "
                "All new files must be created in the user's Downloads folder ($HOME/Downloads). "
                "If you need to use or modify an existing file, make a copy in the Downloads folder first. "
                "You may look at (read) any file on the system, but never modify or delete originals. "
                "Return only the script, no explanation."
            )
        elif category == "web":
            base_prompt = (
                "You are a web automation assistant. Generate a bash shell script for the following web task. "
                "All downloads must go to the user's Downloads folder. "
                "Return only the script, no explanation."
            )
        elif category == "system":
            base_prompt = (
                "You are a system info assistant. Generate a bash shell script for the following system info task. "
                "Return only the script, no explanation."
            )
        elif category == "script":
            base_prompt = (
                "You are a script assistant. Generate a bash shell script for the following user intent. "
                "All new files must be created in the user's Downloads folder ($HOME/Downloads). "
                "Return only the script, no explanation."
            )
        else:
            # fallback to generic
            base_prompt = (
                "You are a helpful assistant. Generate a bash shell script for the following user intent. "
                "All new files must be created in the user's Downloads folder ($HOME/Downloads). "
                "If you need to use or modify an existing file, make a copy in the Downloads folder first. "
                "You may look at (read) any file on the system, but never modify or delete originals. "
                "Return only the script, no explanation."
            )
            
        # Enhance with memory context if available
        system_prompt = base_prompt
        if memory_context:
            system_prompt = (
                f"{base_prompt}\n\n"
                f"Here are some similar commands I've run before that might help you:\n{memory_context}\n"
                f"Generate a script for the current request using this history as context."
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
            # Add retry mechanism for API calls
            max_retries = 3
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
                    response.raise_for_status()
                    msg = response.json()["choices"][0]["message"]["content"]
                    # Remove code block markers if present
                    script = re.sub(r'```(bash|sh)?', '', msg, flags=re.IGNORECASE).replace('```', '').strip()
                    return jsonify({"script_type": "shell", "script": script}), 200
                except requests.exceptions.RequestException as req_e:
                    retry_count += 1
                    last_error = req_e
                    if retry_count < max_retries:
                        # Exponential backoff: wait 1, 2, 4 seconds between retries
                        time.sleep(2 ** (retry_count - 1))
                    else:
                        break
            
            # If we're here, all retries failed
            if last_error:
                return jsonify({"error": f"Failed to generate script after {max_retries} attempts: {last_error}"}), 500
        except Exception as e:
            return jsonify({"error": f"Failed to generate script: {e}"}), 500

    def execute(self, script, context):
        # Track error attempts in a file
        error_log_path = os.path.join(BASE_DIR, "last_error.log")
        debug_log_path = os.path.join(BASE_DIR, "ai_debug.log")
        try:
            # Sanitize the script for security
            sanitized_script = sanitize_command(script)
            if sanitized_script is None:
                with open(debug_log_path, "a") as dbg:
                    dbg.write(f"[SECURITY] Blocked potentially dangerous command: {script}\n")
                return jsonify({"error": "This command contains potentially harmful operations and has been blocked for security reasons."}), 403
                
            result = subprocess.run(sanitized_script, shell=True, capture_output=True, text=True)
            # Log all execution details
            with open(debug_log_path, "a") as dbg:
                dbg.write(f"\n---\n[EXECUTE] Script: {script}\nReturn code: {result.returncode}\nStdout: {result.stdout}\nStderr: {result.stderr}\n")
            if result.returncode == 0:
                # On success, clear error log
                if os.path.exists(error_log_path):
                    os.remove(error_log_path)
                
                # Record successful command in memory
                if context and 'intent' in context:
                    self.memory.add_command(
                        intent=context['intent'],
                        script=sanitized_script,
                        result=result.stdout
                    )
                    
                return jsonify({
                    "status": "success",
                    "return_code": result.returncode,
                    "output": result.stdout,
                    "error_output": result.stderr
                })
            else:
                # On error, log and handle retries
                error_output = result.stderr.strip()
                # If error_output is null/empty, do not return anything
                if not error_output:
                    return ("", 204)
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
                    os.system("git reset --hard HEAD~1")
                    os.system("git add daemon.py")
                    os.system("git commit -m '[ai] Rollback after repeated error' || true")
                    try:
                        requests.post("http://localhost:5050/report_missing_ability", 
                                     headers={"Content-Type": "application/json"}, 
                                     json={"ability": "alternative_solution"}, 
                                     timeout=5)
                        requests.post("http://localhost:5050/self_reflect", timeout=5)
                    except Exception as req_err:
                        with open(debug_log_path, "a") as dbg:
                            dbg.write(f"[REQUEST ERROR] Failed to trigger self-improvement: {req_err}\n")
                    with open(debug_log_path, "a") as dbg:
                        dbg.write(f"[ROLLBACK] Repeated error. Rolled back and triggered self-reflect. Error: {error_output}\n")
                    
                    # Record failed command in memory
                    if context and 'intent' in context:
                        self.memory.add_command(
                            intent=context['intent'],
                            script=sanitized_script,
                            error=f"Repeated error: {error_output}"
                        )
                    
                    return jsonify({"error": f"Repeated error detected. Rolled back and will try a different approach. Error: {error_output}"}), 500
                else:
                    try:
                        requests.post("http://localhost:5050/report_missing_ability", 
                                     headers={"Content-Type": "application/json"}, 
                                     json={"ability": error_output[:100]}, 
                                     timeout=5)
                        requests.post("http://localhost:5050/self_reflect", timeout=5)
                    except Exception as req_err:
                        with open(debug_log_path, "a") as dbg:
                            dbg.write(f"[REQUEST ERROR] Failed to trigger self-improvement: {req_err}\n")
                    with open(debug_log_path, "a") as dbg:
                        dbg.write(f"[SELF-IMPROVE] Error occurred. Triggered self-reflect. Error: {error_output}\n")
                    
                    # Record error in memory
                    if context and 'intent' in context:
                        self.memory.add_command(
                            intent=context['intent'],
                            script=sanitized_script,
                            error=error_output
                        )
                    
                    return jsonify({"error": f"Error occurred. Self-improvement triggered. Please retry. Error: {error_output}"}), 500
        except ImportError as e:
            ability = str(e).split('No module named ')[-1].replace("'", "").strip()
            try:
                requests.post("http://localhost:5050/report_missing_ability", 
                             headers={"Content-Type": "application/json"}, 
                             json={"ability": ability}, 
                             timeout=5)
                requests.post("http://localhost:5050/self_reflect", timeout=5)
                with open(debug_log_path, "a") as dbg:
                    dbg.write(f"[IMPORT ERROR] Missing ability: {ability}. Triggered self-reflect.\n")
            except Exception as req_err:
                with open(debug_log_path, "a") as dbg:
                    dbg.write(f"[REQUEST ERROR] Failed to trigger self-improvement: {req_err}\n")
            return jsonify({"error": f"Missing ability: {ability}. Self-improvement triggered. Please retry shortly."}), 500
        except Exception as e:
            with open(debug_log_path, "a") as dbg:
                dbg.write(f"[EXCEPTION] {str(e)}\n")
            return jsonify({"error": str(e)}), 500
