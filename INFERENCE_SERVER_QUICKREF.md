# Unified Inference Server - Quick Reference

## Quick Start

### 1. Start the Server

```bash
# Option A: Direct command
./auraos.sh inference start

# Option B: Manual
cd /Users/eric/GitHub/ai-os
source auraos_daemon/venv/bin/activate
python auraos_daemon/inference_server.py
```

### 2. Verify It's Running

```bash
# Check status
./auraos.sh inference status

# Or directly
curl http://localhost:8081/health

# Check available models
curl http://localhost:8081/models
```

### 3. Use It

**Terminal Chat Mode**: Open AuraOS Terminal → Chat Mode → Type message → Get response

**Daemon Vision**: Automation tasks automatically use the inference server

**CLI Commands**: Full management via `./auraos.sh inference`

## File Changes

### New Files
- `auraos_daemon/inference_server.py` - Main server (440+ lines)
- `INFERENCE_SERVER_IMPLEMENTATION.md` - Full documentation

### Modified Files
- `gui_agent.py` - Changed VisionClient to use localhost:8081
- `auraos_terminal.py` - Updated chat mode to use localhost:8081
- `auraos_daemon/core/screen_automation.py` - Updated to call inference server
- `auraos.sh` - Added `inference` command and Check 10 in health
- `auraos_daemon/requirements.txt` - Added comments about optional deps

## Architecture Overview

```
User Interface (Terminal, GUI Agent, Daemon)
              ↓
    Inference Server (localhost:8081)
     /generate  /ask  /health  /models
              ↓
    Backend Selector (auto-detection)
     ├─ Ollama Backend (if running)
     │   └─ llava:13b model
     └─ Transformers Backend (fallback)
         └─ microsoft/Fara-7B model
```

## Endpoints

| Endpoint | Method | Purpose | Input |
|----------|--------|---------|-------|
| `/health` | GET | Check server status | None |
| `/models` | GET | List available models | None |
| `/generate` | POST | Text generation | `{"prompt": "...", "max_tokens": 256}` |
| `/ask` | POST | Vision + question | `{"prompt": "...", "image": "base64..."}` |

## Environment Variables

```bash
# Ollama service location
export OLLAMA_URL="http://localhost:11434"

# HuggingFace model to use
export AURAOS_HF_MODEL="microsoft/Fara-7B"

# Force specific backend (auto|ollama|transformers)
export AURAOS_INFERENCE_BACKEND="auto"

# Device selection (auto|cuda|cpu)
export AURAOS_DEVICE="auto"
```

## Commands Reference

```bash
# Start the server
./auraos.sh inference start

# Stop the server
./auraos.sh inference stop

# Check if running
./auraos.sh inference status

# Stream logs
./auraos.sh inference logs

# Restart
./auraos.sh inference restart

# Full system health check (includes Check 10 for inference server)
./auraos.sh health
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Server won't start | Check `/tmp/auraos_inference_server.log` |
| Port 8081 in use | Kill process or use different port with `FLASK_PORT=8082` |
| Ollama not connecting | Verify with `curl http://localhost:11434/api/tags` |
| Transformers not loading | Run `pip install torch transformers accelerate` |
| Chat mode times out | Check logs, model may be slow on first inference |
| Vision analysis fails | Ensure image is properly base64 encoded |

## Backend Priority

1. **If Ollama is running** → Uses Ollama (llava:13b)
   - Fast for vision tasks
   - Already downloaded model
   - Requires Ollama service

2. **If Ollama unavailable** → Falls back to Transformers (microsoft/Fara-7B)
   - Works standalone
   - Loads on first run (~20-30s)
   - Better for text-only tasks

## Performance Expectations

| Task | Backend | Time | Memory |
|------|---------|------|--------|
| First startup | - | 10-30s | 100MB |
| Chat response | Ollama | 1-3s | 6-8GB |
| Chat response | Transformers | 3-8s | 10-12GB |
| Vision analysis | Either | 2-5s | +2GB |
| Subsequent requests | Either | 1-3s | Same |

## Testing Quick Commands

```bash
# 1. Start server
./auraos.sh inference start && sleep 2

# 2. Test health
curl -s http://localhost:8081/health | python3 -m json.tool

# 3. Test models
curl -s http://localhost:8081/models | python3 -m json.tool

# 4. Test text generation
curl -X POST http://localhost:8081/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?", "max_tokens": 100}'

# 5. Stop server
./auraos.sh inference stop
```

## Integration Checklist

- [x] Inference server created and tested
- [x] Terminal chat mode updated
- [x] GUI agent wired to server
- [x] Screen automation uses server
- [x] Health checks include server
- [x] CLI helpers for start/stop/status
- [x] Documentation complete
- [ ] End-to-end testing in live environment
- [ ] Performance benchmarking
- [ ] Systemd unit file (optional)

## Next Steps

1. **Test in Terminal**: Switch to Chat Mode and send a message
2. **Test Vision**: Run an automation task that requires screen analysis
3. **Monitor Logs**: Watch real-time logs during requests
4. **Verify Health**: Run full health check including Check 10
5. **Backend Switch**: Test fallback by stopping/starting Ollama

