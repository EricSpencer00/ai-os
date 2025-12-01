# Quick Reference: AI Integration & Repeatable Workflows

## One-Line Summaries

| Task | Command | Notes |
|------|---------|-------|
| **Onboard API key** | `./auraos.sh keys onboard` | Interactive; choose provider, paste key |
| **Test AI system** | `python3 scripts/test_ai_terminal.py` | Quick validation (no keys required) |
| **Use AI Terminal** | `python3 auraos_terminal.py` | Type requests in AI Mode |
| **Automate via CLI** | `./auraos.sh automate "open firefox"` | Command-line automation |
| **Start daemon** | `cd auraos_daemon && python3 main.py` | Daemon HTTP server on :5050 |
| **Call AI endpoint** | `curl -X POST http://localhost:5050/chat -d '{"message":"hi"}'` | HTTP JSON API |

---

## Full Workflows

### Workflow A: Set Up AI for the First Time
```bash
# 1. Onboard an API key (interactive)
./auraos.sh keys onboard
# → Choose: openrouter / openai / huggingface / other
# → Paste your API key (masked input)
# → Press 'y' to set as default provider

# 2. Test that everything works
python3 scripts/test_ai_terminal.py
# → Should show tests passed (using Ollama if no key, or your provider)

# 3. Launch the terminal and try it
python3 auraos_terminal.py
# → Type: "hi" or "open firefox"
# → You should see the provider used in the output
```

### Workflow B: Use AI from Command Line
```bash
# Ensure you've onboarded (or set PROVIDER env var)
./auraos.sh keys onboard

# Then automate via CLI
./auraos.sh automate "create a backup of Desktop to /tmp/backup"
./auraos.sh automate "list all Python files in ~/projects"

# Or call the daemon directly
curl -X POST http://localhost:5050/generate_script \
  -H 'Content-Type: application/json' \
  -d '{
    "intent": "find all PDF files larger than 50MB",
    "context": {"cwd": "/Users/eric/Documents"}
  }'
```

### Workflow C: Use AI from the Terminal GUI
```bash
# Start the terminal
python3 auraos_terminal.py

# In AI Mode (default):
#   Type: "open firefox"
#   Type: "create a file called notes.txt with today's date"
#   Type: "hi" (short chat, handled locally)

# Switch to Regular Mode:
#   Click "Switch to Regular"
#   Type shell commands normally
#   Prefix with "ai:" for AI file search: "ai: find python files"
```

### Workflow D: Integrate AI into Custom Scripts
```bash
# Python script
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/eric/GitHub/ai-os')

from core import ai_helper, key_store

# Get a key that was onboarded
provider = key_store.get_default_provider()
print(f"Using provider: {provider}")

# Call AI
result = ai_helper.get_ai_response(
    "Summarize the current directory structure",
    system_prompt="Be concise."
)

if result['success']:
    print(f"Response from {result['provider']}:")
    print(result['response'])
else:
    print(f"Error: {result['error']}")
```

### Workflow E: Inspect & Debug
```bash
# Check which provider is configured
cd /Users/eric/GitHub/ai-os
python3 -c "
import sys; sys.path.insert(0, '.')
from core import key_store
provider = key_store.get_default_provider()
keys = key_store.list_providers()
print(f'Default: {provider}')
print(f'Configured: {keys}')
"

# Check if Ollama is running
curl -s http://localhost:11434/api/tags | jq '.models[].name'

# View key store file (plaintext JSON)
cat ~/.auraos/api_keys.json

# View terminal logs
tail -f /tmp/auraos_terminal.log

# View daemon logs
tail -f auraos_daemon/aura_os.log
```

---

## Provider Precedence

When you call `ai_helper.get_ai_response(...)`, it tries providers in this order:

1. **Explicit `PROVIDER` env var** (if set)
   ```bash
   export PROVIDER=openrouter
   python3 auraos_terminal.py
   ```

2. **Default provider from key store** (set during onboarding)
   ```bash
   ./auraos.sh keys onboard  # Select and confirm default
   ```

3. **Legacy `OPENAI_API_KEY` env var** (fallback)
   ```bash
   export OPENAI_API_KEY=sk-...
   ```

4. **Local Ollama** (final fallback; no key needed)
   - Requires Ollama running on `localhost:11434`
   - Uses model from `OLLAMA_MODEL` env var or default `gemma:2b`

---

## Key Storage Details

**Location**: `~/.auraos/api_keys.json`  
**Format**: Plaintext JSON (mode 0o600 — readable only by you)

**Example**:
```json
{
  "keys": {
    "openrouter": "sk-or-v1-...",
    "openai": "sk-..."
  },
  "default_provider": "openrouter"
}
```

**To view**:
```bash
cat ~/.auraos/api_keys.json
```

**To manually edit**:
```bash
# Edit directly
nano ~/.auraos/api_keys.json

# Or use Python
python3 -c "
import sys; sys.path.insert(0, '/Users/eric/GitHub/ai-os')
from core import key_store
key_store.set_key('openai', 'sk-...')
key_store.set_default_provider('openai')
"

# Or use the CLI
./auraos.sh keys onboard
```

---

## Environment Variables (Optional Overrides)

| Env Var | Default | Use Case |
|---------|---------|----------|
| `PROVIDER` | (from key_store) | Force a specific provider |
| `OPENAI_API_KEY` | (none) | Legacy: set if no key_store |
| `OPENROUTER_API_KEY` | (none) | Legacy: OpenRouter key (use key_store instead) |
| `OLLAMA_URL` | `http://localhost:11434/api/chat` | Custom Ollama endpoint |
| `OLLAMA_MODEL` | `gemma:2b` | Which Ollama model to use |

**Example**:
```bash
export PROVIDER=ollama OLLAMA_MODEL=mistral
python3 auraos_terminal.py
# Will use local Ollama mistral model instead of cloud provider
```

---

## Troubleshooting

### "Error: Unsupported request: hello"
- **Cause**: Short chat input was forwarded to `auraos.sh`, which doesn't handle chat.
- **Fix**: Restart the terminal after pulling latest code:
  ```bash
  git pull origin dev
  python3 auraos_terminal.py  # Restart
  ```

### "No module named 'requests'"
- **Cause**: `requests` library isn't installed, but `ai_helper` gracefully falls back to `urllib`.
- **Fix**: Not a real error — the code works fine without it. Optional: install for better performance:
  ```bash
  pip install requests
  ```

### "Ollama not available"
- **Cause**: Ollama isn't running or isn't accessible at the default URL.
- **Fix**:
  ```bash
  # Check if Ollama is running
  curl http://localhost:11434/api/tags
  
  # If not, start it
  ollama serve
  
  # Or customize the URL
  export OLLAMA_URL=http://192.168.1.100:11434/api/chat
  ```

### "API key rejected"
- **Cause**: Key is invalid, expired, or has insufficient permissions.
- **Fix**:
  ```bash
  # Re-onboard with a new/valid key
  ./auraos.sh keys onboard
  
  # Or remove the old key and add a new one
  python3 -c "
  import sys; sys.path.insert(0, '.')
  from core import key_store
  key_store.remove_key('openrouter')
  key_store.set_key('openrouter', 'NEW_KEY')
  "
  ```

---

## For Developers

**Code locations**:
- Core logic: `core/ai_helper.py`, `core/key_store.py`, `core/api_key_cli.py`
- Terminal: `auraos_terminal.py`
- Daemon: `auraos_daemon/daemon.py`
- Tests: `scripts/test_ai_terminal.py`
- Audit: `AUDIT_AI_INTEGRATION.md`

**Adding new AI features**:
1. Use `ai_helper.get_ai_response(prompt, system_prompt)` for unified provider/Ollama logic.
2. If you need to log the provider used, check the returned dict: `result['provider']`.
3. Add a command to `auraos.sh` if you want it repeatable from the shell.

**Example**:
```python
from core import ai_helper

result = ai_helper.get_ai_response("What files are on the Desktop?")
if result['success']:
    print(f"[{result['provider']}] {result['response']}")
else:
    print(f"Failed: {result['error']}")
```

---

**Last Updated**: 2025-11-10  
**Status**: ✅ All workflows repeatable via `auraos.sh`
