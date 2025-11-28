# Farà-7B Model Setup Guide

AuraOS now uses **Farà-7B** instead of llama2/llava:13b for all local AI interactions (chat, automation, vision tasks).

## What is Farà-7B?

Farà-7B is a high-quality 7B parameter language model from Hugging Face, optimized for:
- Natural language understanding and generation
- Task automation and planning
- Screen understanding and UI element identification
- Fast inference on consumer hardware

## Installation

### 1. **Install Ollama** (if not already installed)

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

### 2. **Pull Farà-7B Model**

```bash
ollama pull fara-7b
```

This downloads ~4GB and stores the model locally.

### 3. **Start Ollama Server**

```bash
# Start with network access (required for VM and daemon communication)
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

Or, add to a systemd service or startup script:

```bash
export OLLAMA_HOST=0.0.0.0:11434
ollama serve &
```

### 4. **Verify Installation**

```bash
curl http://localhost:11434/api/tags | jq '.models[] | select(.name | contains("fara"))'
```

Should output something like:
```json
{
  "name": "fara-7b:latest",
  "modified_at": "2025-11-28T...",
  "size": 4500000000,
  "digest": "..."
}
```

## Configuration in AuraOS

All AuraOS applications automatically use Farà-7B when configured:

### **Terminal (Chat Mode)**
- Type a message in Chat Mode → sends to `http://localhost:11434/api/generate` with model `fara-7b`
- Settings dialog shows current model and connection status

### **GUI Agent** (`gui_agent.py`)
- Captures screenshots and sends vision tasks to Ollama with Farà-7B
- Parses responses into UI automation commands (click, type, scroll)
- Runs at `http://localhost:8765/ask`

### **Daemon** (`auraos_daemon/daemon.py`)
- `screen_automation.py` uses Farà-7B for vision-based screen analysis
- `key_manager.py` defaults to Farà-7B for local Ollama backend
- Falls back to cloud providers (Groq, OpenRouter) if configured

## Troubleshooting

### Model Not Found
```bash
# List installed models
ollama list

# If fara-7b is missing, pull it again
ollama pull fara-7b
```

### Connection Refused
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

### Slow Responses
- Fara-7B needs ~2-8GB of VRAM depending on hardware
- If system is slow, ensure you're not running other GPU tasks
- CPU-only mode is supported but slower; use GPU if available

### Terminal Chat Mode Not Working
1. Ensure Ollama is running: `ps aux | grep ollama`
2. Click Settings in terminal and check connection status
3. Verify model is pulled: `ollama list | grep fara`

## Performance

- **Inference speed**: ~50 tokens/sec on GPU, ~5 tokens/sec on CPU (macOS/Linux)
- **Memory**: ~4GB model size + ~2-4GB VRAM for inference
- **Latency**: ~1-3 seconds for typical requests

## Alternatives

If you want a different model, you can:

1. **Use a larger model** (slower but better quality):
   ```bash
   ollama pull llama2       # 7B alternative
   ollama pull mistral      # 7B, faster
   ollama pull llama2:13b   # 13B, better quality
   ```

2. **Use a cloud provider**:
   - Set `GROQ_API_KEY` for Groq (llama3-70b is free tier)
   - Set `OPENROUTER_API_KEY` for OpenRouter (various models)
   - Daemon automatically falls back to cloud if configured

3. **Edit model defaults** in code:
   - Terminal: `auraos_terminal.py` line 414 → `"model": "your-model"`
   - GUI Agent: `gui_agent.py` line 110 → `"model": "your-model"`
   - Daemon: `auraos_daemon/core/key_manager.py` line 195 → `model="your-model"`

## Complete Setup Example

```bash
# 1. Install Ollama
brew install ollama

# 2. Pull Farà-7B
ollama pull fara-7b

# 3. Start server in background
OLLAMA_HOST=0.0.0.0:11434 ollama serve &

# 4. Test
curl http://localhost:11434/api/generate -d '{
  "model": "fara-7b",
  "prompt": "Hello, how are you?",
  "stream": false
}' | jq .response

# 5. Start AuraOS terminal
python3 auraos_terminal.py

# 6. Switch to Chat Mode and test
# (Click "Switch to Regular" twice to get to Chat Mode)
# Type: "Hello!"
```

## Next Steps

- Run the terminal demo: `python3 tools/terminal_demo.py --sample`
- Use daemon for automation: `./auraos.sh automate "your task"`
- Configure API keys for cloud fallback: `./auraos.sh keys onboard`

---

**Questions?** Check `ARCHITECTURE_V2.md` for AI pipeline details or `README.md` for full setup.
