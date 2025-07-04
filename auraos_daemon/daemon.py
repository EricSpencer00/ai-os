# daemon.py
# AuraOS Autonomous AI Daemon v7
import os, json, requests, subprocess, logging, base64, re, threading, time
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("aura_os.log"),
        logging.StreamHandler()
    ]
)

# --- Load config ---
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    GROQ_API_KEY = config.get("GROQ_API_KEY")
    OPENROUTER_API_KEY = config.get("OPENROUTER_API_KEY")
except FileNotFoundError:
    logging.error("Missing config.json.")
    exit(1)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEEPSEEK_MODEL = "deepseek/deepseek-coder"

COMPLEX_TASK_KEYWORDS = ["modify", "improve", "learn", "add a feature", "update", "change your code", "scrape", "list of", "find data", "get information on", "what are", "who are"]

@app.route("/generate_script", methods=["POST"])
def generate_script():
    data = request.get_json()
    user_intent = data.get("intent")
    context = data.get("context", {})
    cwd = context.get("cwd", ".")
    windows = context.get("windows", [])
    window_list_str = "
- " + "
- ".join(windows) if windows else "No open windows detected."
    logging.info(f"[Script Gen] Intent: '{user_intent}'")

    system_prompt = f"""
    You are AuraOS's autonomous daemon. Generate either a Python or shell script based on the intent.
    Self-modify if the request includes 'learn', 'add a feature', 'improve', or 'modify yourself'.

    Return JSON: {{"script_type": "shell" or "python", "script": "..."}}
    """

    is_complex = any(k in user_intent.lower() for k in COMPLEX_TASK_KEYWORDS)
    if is_complex:
        model, api_key, api_url = OPENROUTER_DEEPSEEK_MODEL, OPENROUTER_API_KEY, OPENROUTER_API_URL
        if not api_key: return jsonify({"error": "OpenRouter key missing"}), 500
    else:
        model, api_key, api_url = GROQ_MODEL, GROQ_API_KEY, GROQ_API_URL
        if not api_key: return jsonify({"error": "Groq key missing"}), 500

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_intent}],
        "temperature": 0.1
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        msg = response.json()["choices"][0]["message"]["content"]
        content = re.search(r'{.*}', msg, re.DOTALL).group(0)
        return jsonify(json.loads(content)), 200
    except Exception as e:
        logging.error(f"[Script Gen] Error: {e}")
        return jsonify({"error": "Failed to generate script."}), 500

@app.route("/execute_script", methods=["POST"])
def execute_script():
    data = request.get_json()
    script = data.get("script")
    context = data.get("context", {})
    display = context.get("display")
    if not script: return jsonify({"error": "No script provided."}), 400
    env = os.environ.copy()
    if display: env["DISPLAY"] = display
    logging.warning(f"[Execution] Running script:
{script}")
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
        with open("aura_os.log", "r") as log: logs = log.read()[-5000:]
        with open("daemon.py", "r") as code: src = code.read()
        system_prompt = "You are a self-improving daemon. Given logs and source code, output improved daemon.py."
        task = f"LOGS:
{logs}

SOURCE:
{src}"
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": OPENROUTER_DEEPSEEK_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": task}],
            "temperature": 0.1
        }
        r = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)
        msg = r.json()["choices"][0]["message"]["content"]
        content = re.search(r'{.*}', msg, re.DOTALL).group(0)
        update = json.loads(content)
        b64 = base64.b64encode(json.dumps(update).encode()).decode()
        subprocess.run(["python3", "updater.py", b64], check=False)
        return jsonify({"status": "update triggered"}), 200
    except Exception as e:
        logging.error(f"[Self-Reflect] Failed: {e}")
        return jsonify({"error": str(e)}), 500

def periodic_self_reflect():
    while True:
        time.sleep(3600)
        try:
            requests.post("http://localhost:5000/self_reflect")
        except:
            pass

threading.Thread(target=periodic_self_reflect, daemon=True).start()

if __name__ == "__main__":
    logging.info("Starting AuraOS AI Daemon v7...")
    app.run(host="0.0.0.0", port=5000)
