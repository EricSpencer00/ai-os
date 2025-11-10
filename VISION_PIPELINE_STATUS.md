# AuraOS Vision Pipeline - Status & Testing

## ✅ Completed

1. **GUI Setup & VNC**
   - ✅ x11vnc + noVNC working
   - ✅ VNC password authentication fixed (expect + x11vnc -storepasswd)
   - ✅ Browser access at http://localhost:6080/vnc.html
   - ✅ SSH tunnels established (5901→5900, 6080→6080)

2. **Ollama Vision Integration**
   - ✅ Fixed API endpoint: `/api/chat` instead of `/api/generate` (llava:13b requires chat API)
   - ✅ Base64 image encoding working
   - ✅ Two-stage analysis: description + coordinate extraction
   - ✅ JSON parsing with fallbacks
   - ✅ Coordinates being returned (x, y pairs)

3. **Script Consolidation**
   - ✅ All helpers merged into `auraos.sh`
   - ✅ Health check command: `./auraos.sh health`
   - ✅ GUI reset: `./auraos.sh gui-reset`
   - ✅ Screenshot: `./auraos.sh screenshot`
   - ✅ Automation: `./auraos.sh automate "<task>"`

## 🔍 Current Status - Vision Model Issues

The llava:13b model is returning coordinates but with questionable accuracy:

**Problem**: Model says it can't see images but still hallucinates responses

**Example Output**:
```
📋 Element descriptions: I'm sorry, but I can't analyze a screenshot...
🔍 Ollama response: {"action": "click", "x": 75, "y": 200, ...}
```

**Likely Causes**:
1. llava:13b may not be properly processing image data
2. Model weight file may be corrupted
3. Image encoding may have issues
4. Model version mismatch

## 🚀 Testing Better Models

**Currently Pulling**:
- `minicpm-v:latest` - Lightweight vision model (~4GB), optimized for UI tasks

**Other Good Options**:
```bash
# Option 1: Re-pull llava with specific size
ollama pull llava:7b  # Smaller, might work better

# Option 2: Try bakllava (better vision)
ollama pull bakllava  # Better visual understanding

# Option 3: Try minicpm-v (already pulling)
ollama pull minicpm-v:latest  # Best for UI/OCR tasks

# Option 4: Try llava-phi (if available)
ollama pull llava-phi
```

## 📝 How to Test

### Test 1: Check Model is Seeing Images

```bash
cd /Users/eric/GitHub/ai-os
./test_ollama_vision.sh
```

This sends a simple "describe the screenshot" prompt and checks the response.

### Test 2: Run Full Automation

```bash
./auraos.sh automate "click on home icon"
./auraos.sh automate "click on trash icon"
./auraos.sh automate "click terminal icon"
```

### Test 3: Check Returned Coordinates

Look for the JSON output - coordinates should vary based on task:
- Left sidebar icons: x ≈ 50-100
- Center of screen: x ≈ 640, y ≈ 360
- Top taskbar: y ≈ 0-30
- Bottom taskbar: y ≈ 700+

## 💡 Workaround: If Vision Still Fails

We can use a hybrid approach:

```python
# Fallback logic:
# 1. Try to use model vision
# 2. If coordinates are generic (640, 360) → fallback to heuristics
# 3. Parse task description and map to known icon locations
# 4. Use OCR or simpler pattern matching as backup
```

## 🎯 Next Steps

1. **Wait for minicpm-v** to finish downloading
2. **Test minicpm-v** with same prompts
3. **Compare results** - if better, switch to it
4. **If still issues**: Debug image encoding or try different model
5. **If that fails**: Build heuristic fallback system

## 📊 Performance Metrics

- **Screenshot capture**: ~1 second
- **Vision analysis (2-stage)**: ~10-15 seconds per task
- **Click execution**: <1 second
- **Total pipeline**: ~15-20 seconds

## 🔗 Files Modified

- `auraos_daemon/core/screen_automation.py` - Fixed Ollama API + improved analysis
- `auraos.sh` - Already has all commands (health, gui-reset, screenshot, automate)
- `test_ollama_vision.sh` - Testing script for direct Ollama API calls

## 📌 Quick Commands

```bash
# Check health
./auraos.sh health

# Reset GUI (if needed)
./auraos.sh gui-reset

# Test vision directly
./test_ollama_vision.sh

# Run automation
./auraos.sh automate "click file manager"

# Check logs
./auraos.sh logs

# View system status
./auraos.sh status
```

