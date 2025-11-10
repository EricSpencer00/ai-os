# daemon.py
# AuraOS Autonomous AI Daemon v8.4
import os, json, requests, subprocess, logging, base64, re, threading, time
from flask import Flask, request, jsonify
from core.llm_router import get_router

app = Flask(__name__)
VERSION = "8.4"

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

# Initialize a shared LLM router (may be None if unavailable)
try:
    ROUTER = get_router()
    logging.info(f"LLM Router available: {ROUTER is not None}")
except Exception as e:
    logging.warning(f"Failed to initialize LLM Router: {e}")
    ROUTER = None

@app.route("/generate_script", methods=["POST"])
def generate_script():
    data = request.get_json(force=True)
    user_intent = data.get("intent", "")
    context = data.get("context", {})
    cwd = context.get("cwd", ".")
    windows = context.get("windows", [])

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

    # Use the centralized LLM router (local Ollama preferred, fallback to cloud)
    if not ROUTER:
        logging.error("No LLM router available for script generation")
        return jsonify({"error": "No LLM available"}), 500

    try:
        res = ROUTER.route(user_intent, context={"system_prompt": system_prompt})
        if not res.get('success'):
            logging.error(f"[Script Gen] LLM routing failed: {res.get('error')}")
            return jsonify({"error": "LLM call failed", "details": res.get('error')}), 500

        msg = res.get('response', '')
        # Extract and parse JSON from model response
        content = re.sub(r'```json|```', '', msg, flags=re.IGNORECASE)
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON found in LLM response.")
        content = match.group(0)
        return jsonify(json.loads(content)), 200
    except Exception as e:
        logging.error(f"[Script Gen] Error: {e}")
        return jsonify({"error": "Failed to generate script.", "details": str(e)}), 500

def is_malicious_script(script):
    dangerous_patterns = [
        r"rm\s+-rf\s+/?",
        r"rm\s+-rf\b",
        r"shutdown", r"reboot", r"halt", r"mkfs", r"dd\s+if=",
        r":(){:|:&};:", r"kill\s+-9\s+1", r"killall", r"poweroff",
        r"init\s+0", r"sudo\s+", r"chown\s+-R\s+root", r"chmod\s+000",
        r">\s+/dev/sda", r">\s+/dev/nvme", r"/dev/null\s*\|\s*dd",
        r"wget\s+http", r"curl\s+http", r"scp\s+", r"ftp\s+",
        r"nc\s+", r"ncat\s+", r"netcat\s+",
        r"python\s+-c.*import\s+os;.*os.system",
        r"os\.system", r"subprocess\.Popen", r"subprocess\.call",
        r"eval", r"exec", r"open\s*\(", r"import\s+socket",
        r"import\s+ftplib", r"import\s+paramiko",
        r"shutil\.rmtree\s*\(.*\)",
        r"os\.remove\s*\(.*\)",
        r"os\.unlink\s*\(.*\)"
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, script, re.IGNORECASE):
            return True
    return False

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
    try:
        with open(LOG_PATH, "r") as log:
            logs = log.read()[-5000:]
        with open(DAEMON_PATH, "r") as code:
            src = code.read()

        system_prompt = (
            "You are a self-improving daemon. Given logs and source code, output improved daemon.py. "
            "Return only a JSON object: {\"code\": \"...new daemon.py code...\", \"packages\": [\"...optional deps...\"]}"
        )
        task = f"LOGS: {logs}\nSOURCE: {src}"

        logging.warning("[Self-Reflect] Sending self-improvement task to configured LLM via router...")
        if not ROUTER:
            logging.error("No LLM router available for self-reflect")
            return jsonify({"error": "No LLM available"}), 500

        try:
            res = ROUTER.route(task, context={"system_prompt": system_prompt})
            if not res.get('success'):
                logging.error(f"[Self-Reflect] LLM routing failed: {res.get('error')}")
                return jsonify({"error": "LLM call failed", "details": res.get('error')}), 500

            msg = res.get('response', '')
            content = re.sub(r'```json|```', '', msg, flags=re.IGNORECASE).strip()
            try:
                decoder = json.JSONDecoder()
                update, idx = decoder.raw_decode(content)
            except json.JSONDecodeError as e:
                logging.error(f"[Self-Reflect] JSON parse error: {e}\nContent: {content}")
                raise ValueError("Invalid JSON format in model response") from e

            b64 = base64.b64encode(json.dumps(update).encode()).decode()
            subprocess.run(["python3", UPDATER_PATH, b64], check=False)
            return jsonify({"status": "update triggered"}), 200

        except Exception as parse_err:
            logging.error(f"[Self-Reflect] Response parse error: {parse_err}")
            return jsonify({"error": "Parse failed", "details": str(parse_err)}), 500

    except Exception as e:
        logging.error(f"[Self-Reflect] Failed: {e}")
        return jsonify({"error": str(e)}), 500

def periodic_self_reflect():
    while True:
        time.sleep(3600)
        try:
            requests.post("http://localhost:5050/self_reflect", timeout=10)
        except Exception as e:
            logging.error(f"[Periodic Self-Reflect] Error: {e}")

threading.Thread(target=periodic_self_reflect, daemon=True).start()

# Conversational AI: Use a local model for simple Q&A/chat
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_message = data.get("message", "")
    # Use centralized router for conversational responses (local preferred)
    if ROUTER:
        res = ROUTER.route(user_message, context={})
        if res.get('success'):
            return jsonify({"response": res.get('response')}), 200
        else:
            logging.warning(f"Local router failed for chat: {res.get('error')}")

    # Fallback to simple local stub
    response = local_conversational_ai(user_message)
    return jsonify({"response": response}), 200

# Intent classification: decide if input is chat or task

def classify_intent(user_input):
    # Simple heuristic: if question is short and not requesting a list, dataset, or script, treat as chat
    if len(user_input.split()) < 12 and not any(word in user_input.lower() for word in ["list", "top", "dataset", "script", "find", "scrape", "download", "search", "generate", "feature", "improve", "add", "update"]):
        return "chat"
    return "task"

def local_conversational_ai(message):
    # Stub: Replace with call to local LLM (llama.cpp, ollama, etc.)
    # For now, just echo or use a simple lookup
    factoids = {
        "who is the 44th president?": "Barack Obama was the 44th President of the United States.",
        "what is the capital of france?": "Paris is the capital of France."
    }
    return factoids.get(message.strip().lower(), "I'm a local AI and can answer simple questions. Please ask!")

# Unified AI endpoint: routes to chat or script generation
@app.route("/ai", methods=["POST"])
def ai():
    data = request.get_json(force=True)
    user_input = data.get("input", "")
    intent_type = classify_intent(user_input)
    if intent_type == "chat":
        response = local_conversational_ai(user_input)
        return jsonify({"type": "chat", "response": response})
    else:
        # Forward to script generation logic
        # Reuse generate_script logic
        return generate_script()

if __name__ == "__main__":
    logging.info("Starting AuraOS AI Daemon v8.4...")
    app.run(host="0.0.0.0", port=5050)
