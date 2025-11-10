# AuraOS Vision Automation - Setup & Troubleshooting

## Current Status

✅ **GUI Access Working**: VNC/noVNC fully functional  
✅ **Ollama Integration**: Vision models available  
⚠️ **Vision Accuracy**: Currently generic (hallucinating coordinates)

## The Problem

Ollama's vision models (llava:13b, qwen2.5-coder:7b) are returning center-screen coordinates (640, 360) regardless of what's being asked. This suggests:

1. **Model Hallucination**: Small models may not properly see/understand images
2. **Image Format Issue**: Images may not be encoded correctly for the model
3. **Model Limitation**: These models may need better prompting or different architecture

## Solutions

### Option 1: Use Cloud-Based Vision (Recommended for Accuracy)

Switch to GPT-4V (OpenAI) which is significantly more accurate:

```bash
# Get API key from https://platform.openai.com/api-keys
./auraos.sh keys add openai sk-proj-YOUR_KEY_HERE

# Test automate will now use GPT-4V
./auraos.sh automate "click on file manager"
```

**Pros**:
- 95%+ accuracy on UI element detection
- Handles complex interfaces
- Worth the API cost for reliability

**Cons**:
- Requires OpenAI API credits (~$0.05 per screenshot)
- Internet connection required

### Option 2: Use Anthropic Claude-3 (Also Recommended)

```bash
# Get API key from https://console.anthropic.com
./auraos.sh keys add anthropic sk-ant-YOUR_KEY_HERE

# Test automate will now use Claude-3
./auraos.sh automate "click on file manager"
```

**Pros**:
- Excellent visual understanding
- Good for UI automation
- Similar cost to OpenAI

### Option 3: Improve Local Model (Advanced)

If you want to keep using Ollama locally:

#### a) Upgrade to larger vision model

```bash
# Pull llava:34b (8GB, much better accuracy)
ollama pull llava:34b

# Configure to use it
./auraos.sh keys ollama llava:34b llava:34b
```

Then test:
```bash
./auraos.sh automate "click on file manager"
```

#### b) Use LLaVA-NeXT (better than llava:13b)

```bash
# If available in Ollama
ollama pull llava-next:13b
./auraos.sh keys ollama llava-next:13b llava-next:13b
```

#### c) Fine-tune prompting (hacky but may help)

The prompting strategy could be improved:

1. **Two-stage approach**: 
   - First: Ask model to describe ALL visible elements with positions
   - Second: Parse response to find coordinates

2. **Reference grid**:
   - Ask model to return coordinates relative to a grid overlay

3. **OCR-based fallback**:
   - Use OCR to find text, then click near it

### Option 4: Hybrid Approach (Smart)

- Use local models for simple tasks (returns should fail with low confidence)
- Fall back to cloud API for complex tasks
- Cache results to minimize API calls

```python
# Example: In screen_automation.py
if confidence < 0.5:  # Low confidence from local model
    # Fall back to GPT-4V
    return self._analyze_with_openai(image_data, task)
```

## Recommended Action Right Now

### For Immediate Reliable Automation:
```bash
# 1. Get an API key (free tier available)
./auraos.sh keys add openai YOUR_KEY

# 2. Test
./auraos.sh automate "click on the File System icon"

# 3. Monitor your usage at https://platform.openai.com/account/usage
```

### For Local-Only (Development):
```bash
# Keep using llava:13b but accept limitations
./auraos.sh keys ollama llava:13b llava:13b

# Test manually first
./auraos.sh screenshot
# Check /tmp/auraos_screenshot.png to verify what's visible

# Then try:
./auraos.sh automate "click near the left side of the screen"
```

## Testing Model Performance

```bash
# Capture a screenshot
./auraos.sh screenshot

# Diagnose what model sees
./diagnose_vision.sh

# Try task
./auraos.sh automate "click on Home"

# Check results
# Compare returned coordinates to actual icon position in VNC viewer
```

## Next Steps

1. **Choose a provider** (OpenAI/Anthropic recommended for now)
2. **Configure it**: `./auraos.sh keys add provider KEY`
3. **Test**: `./auraos.sh automate "click on file manager"`
4. **Monitor**: Check if clicks are accurate
5. **Iterate**: Refine prompts if needed

## Files Modified

- `auraos.sh` - Consolidated scripts, added health/gui-reset commands
- `auraos_daemon/core/screen_automation.py` - Improved prompting, better parsing
- `auraos_daemon/core/key_manager.py` - Support for vision_model config
- `diagnose_vision.sh` - New diagnostic tool

## Summary

The VNC/noVNC setup is perfect. The AI vision accuracy issue with local Ollama models is a known limitation of small models. Options:

1. **Best**: Use GPT-4V or Claude-3 (cloud API)
2. **Good**: Use larger local model (llava:34b)
3. **Fair**: Accept limitations, use generic instructions

Recommend starting with Option 1 for reliable results.
