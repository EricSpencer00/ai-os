# daemon.py
# AuraOS Autonomous AI Daemon v7.1
import os, json, requests, subprocess, logging, base64, re, threading, time
from flask import Flask, request, jsonify

app = Flask(__name__)

# Use absolute paths for config and log files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "aura_os.log")
DAEMON_PATH = os.path.join(BASE_DIR, "daemon.py")
UPDATER_PATH = os.path.join(BASE_DIR, "updater.py")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)

# --- Load config ---
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    GROQ_API_KEY = config.get("GROQ_API_KEY")
    OPENROUTER_API_KEY = config.get("OPENROUTER_API_KEY")
except FileNotFoundError:
    logging.error("Missing config.json.")
    exit(1)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEEPSEEK_MODEL = "deepseek/deepseek-r1-0528:free"

COMPLEX_TASK_KEYWORDS = [
    "modify", "improve", "learn", "add a feature", "update", "change your code",
    "scrape", "list of", "find data", "get information on", "what are", "who are"
]

# --- Local LLM via Ollama ---
def query_ollama_llama3(messages, temperature=0.1):
    """Query the local llama3 model via Ollama REST API."""
    try:
        response = requests.post(
            "http://localhost:11434/v1/chat/completions",
            json={
                "model": "llama3",
                "messages": messages,
                "temperature": temperature
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        msg = data["choices"][0]["message"]["content"]
        match = re.search(r'\{.*\}', msg, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON found in LLM response.")
        return json.loads(match.group(0))
    except Exception as e:
        logging.error(f"[Ollama Llama3] Error: {e}")
        raise

@app.route("/generate_script", methods=["POST"])
def generate_script():
    data = request.get_json(force=True)
    user_intent = data.get("intent", "").strip()
    context = data.get("context", {})
    cwd = context.get("cwd", ".")
    windows = context.get("windows", [])

    # --- Intent Routing Table ---
    intent_routes = [
        (lambda intent: any(k in intent.lower() for k in COMPLEX_TASK_KEYWORDS), "script"),
        (lambda intent: intent.lower() in ["hi", "hello", "hey"], "greeting"),
        # Add more (predicate, handler_name) pairs as the system learns
    ]

    # --- Handler Functions ---
    def handle_script():
        window_list_str = "\n- " + "\n- ".join(windows) if windows else "No open windows detected."
        logging.info(f"[Script Gen] Intent: '{user_intent}'")
        system_prompt = f"""
        You are AuraOS's autonomous daemon. Generate either a Python or shell script based on the intent.
        Self-modify if the request includes 'learn', 'add a feature', 'improve', or 'modify yourself'.
        Return JSON: {{"script_type": "shell" or "python", "script": "..."}}
        CONTEXT:
        - CWD: {cwd}
        - Open Windows: {window_list_str}
        """
        is_complex = any(k in user_intent.lower() for k in COMPLEX_TASK_KEYWORDS)
        try:
            if is_complex:
                # Use local llama3 via Ollama for complex tasks
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_intent}
                ]
                result = query_ollama_llama3(messages)
                return jsonify(result), 200
            else:
                model, api_key, api_url = GROQ_MODEL, GROQ_API_KEY, GROQ_API_URL
                if not api_key:
                    return jsonify({"error": "Groq API key missing"}), 500
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_intent}
                    ],
                    "temperature": 0.1
                }
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.post(api_url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                response_json = response.json()
                if "error" in response_json:
                    raise ValueError(f"API Error: {response_json['error']}")
                msg = response_json["choices"][0]["message"]["content"]
                match = re.search(r'\{.*\}', msg, re.DOTALL)
                if not match:
                    raise ValueError("No valid JSON found in LLM response.")
                content = match.group(0)
                return jsonify(json.loads(content)), 200
        except Exception as e:
            logging.error(f"[Script Gen] Error: {e}")
            return jsonify({"error": "Failed to generate script.", "details": str(e)}), 500

    def handle_greeting():
        return jsonify({"message": "hello!"}), 200

    def handle_unknown():
        # Log unknown intent for self-improvement
        logging.warning(f"[Intent Router] Unknown intent: '{user_intent}'")
        with open(os.path.join(BASE_DIR, "unknown_intents.log"), "a") as f:
            f.write(json.dumps({"intent": user_intent, "context": context, "time": time.time()}) + "\n")
        return jsonify({"message": "I'm not sure how to handle that yet, but I'm learning!"}), 200

    # --- Routing Logic ---
    for predicate, handler_name in intent_routes:
        if predicate(user_intent):
            if handler_name == "script":
                return handle_script()
            elif handler_name == "greeting":
                return handle_greeting()
    # Fallback for unknown intents: use local LLM for a basic response
    try:
        messages = [
            {"role": "system", "content": "You are AuraOS's helpful assistant. Respond conversationally to the user's message."},
            {"role": "user", "content": user_intent}
        ]
        result = query_ollama_llama3(messages)
        return jsonify({"message": result.get("response", result)}), 200
    except Exception as e:
        logging.error(f"[Fallback LLM] Error: {e}")
        return jsonify({"message": "I'm not sure how to handle that yet, but I'm learning!"}), 200

def is_malicious_script(script):
    dangerous_patterns = [
        r"rm\s+-rf\s+/", r"rm\s+-rf\s+~", r"rm\s+-rf", r"shutdown", r"reboot", r"halt",
        r"mkfs", r"dd\s+if=", r":(){:|:&};:", r"kill\s+-9\s+1", r"killall", r"poweroff",
        r"init\s+0", r"sudo\s+", r"chown\s+-R\s+root", r"chmod\s+000", r">\s+/dev/sda",
        r">\s+/dev/nvme", r"/dev/null\s*\|\s*dd", r"wget\s+http", r"curl\s+http",
        r"scp\s+", r"ftp\s+", r"nc\s+", r"ncat\s+", r"netcat\s+",
        r"python\s+-c.*import\s+os;.*os.system", r"os\.system", r"subprocess\.Popen",
        r"subprocess\.call", r"eval", r"exec", r"open\s*\(", r"import\s+socket",
        r"import\s+ftplib", r"import\s+paramiko"
    ]
    return any(re.search(pattern, script, re.IGNORECASE) for pattern in dangerous_patterns)

@app.route("/execute_script", methods=["POST"])
def execute_script():
    data = request.get_json(force=True)
    script = data.get("script")
    context = data.get("context", {})
    display = context.get("display")
    if not script:
        return jsonify({"error": "No script provided."}), 400
    if is_malicious_script(script):
        logging.error(f"[Execution] Blocked potentially malicious script: {script}")
        return jsonify({"error": "Script flagged as potentially malicious and was not executed."}), 400
    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display
    logging.warning(f"[Execution] Running script: {script}")
    result = subprocess.run(script, shell=True, capture_output=True, text=True, env=env)
    return jsonify({
        "status": "success" if result.returncode == 0 else "error",
        "return_code": result.returncode,
        "output": result.stdout,
        "error_output": result.stderr
    })

@app.route("/self_reflect", methods=["POST"])
def self_reflect():
    if not OPENROUTER_API_KEY:
        return jsonify({"error": "OpenRouter API key missing"}), 500

    try:
        # Only include the last 5 unknown intents for self-reflection
        unknown_intents_path = os.path.join(BASE_DIR, "unknown_intents.log")
        last_unknowns = []
        if os.path.exists(unknown_intents_path):
            with open(unknown_intents_path, "r") as f:
                lines = f.readlines()
                last_unknowns = [json.loads(line) for line in lines[-5:] if line.strip()]

        with open(LOG_PATH, "r") as log:
            logs = log.read()[-5000:]
        with open(DAEMON_PATH, "r") as code:
            src = code.read()

        system_prompt = (
            "You are a self-improving daemon. Given logs, source code, and recent unknown user intents, output improved daemon.py. "
            "Return only a JSON object: {\"code\": \"...new daemon.py code...\", \"packages\": [\"...optional deps...\"]} "
            "Recent unknown intents: " + json.dumps(last_unknowns)
        )
        task = f"LOGS: {logs}\nSOURCE: {src}"

        logging.warning("[Self-Reflect] Sending self-improvement task to OpenRouter...")
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",
            "X-Title": "AuraOS Autonomous Daemon"
        }
        payload = {
            "model": OPENROUTER_DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task}
            ],
            "temperature": 0.1
        }

        r = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=15)
        if r.status_code != 200:
            logging.error(f"[Self-Reflect] OpenRouter response: {r.text}")
        r.raise_for_status()
        response_json = r.json()
        logging.warning(f"[Self-Reflect] LLM Raw Response: {json.dumps(response_json, indent=2)[:1000]}...")

        if "error" in response_json:
            raise ValueError(f"API Error: {response_json['error']}")
        if "choices" not in response_json:
            raise ValueError("Response missing 'choices' key")

        msg = response_json["choices"][0]["message"]["content"]
        # Multi-stage JSON parsing
        try:
            # Remove markdown code block if present
            if msg.strip().startswith('```json'):
                msg = re.sub(r'^```json|```$', '', msg.strip(), flags=re.MULTILINE).strip()
            content = json.loads(msg)
        except Exception:
            match = re.search(r'\{.*\}', msg, re.DOTALL)
            if not match:
                raise ValueError("No valid JSON found in model output")
            content = json.loads(match.group(0))

        # Ensure content is a dict and has 'code' key
        if not isinstance(content, dict) or not isinstance(content.get("code", ""), str) or not content["code"]:
            raise ValueError("Invalid code in update payload")

        b64 = base64.b64encode(json.dumps(content).encode()).decode()
        subprocess.run(["python3", UPDATER_PATH, b64], check=False)
        return jsonify({"status": "update triggered"}), 200

    except Exception as e:
        logging.error(f"[Self-Reflect] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def periodic_self_reflect():
    time.sleep(60)  # Initial delay for server startup
    while True:
        try:
            logging.info("[Periodic Self-Reflect] Initiating self-reflection...")
            response = requests.post(
                "http://localhost:5050/self_reflect",
                timeout=15,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                logging.error(f"[Periodic] Unexpected status: {response.status_code}")
        except Exception as e:
            logging.error(f"[Periodic Self-Reflect] Error: {e}")
        time.sleep(3600)

threading.Thread(target=periodic_self_reflect, daemon=True).start()

if __name__ == "__main__":
    logging.info("Starting AuraOS AI Daemon v7.1...")
    app.run(host="0.0.0.0", port=5050)
