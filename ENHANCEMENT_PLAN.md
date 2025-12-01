# AuraOS Enhancement Plan

## Completed ✅
1. Fixed browser "Unsupported request" error
2. Verified Ollama connection path
3. Created connection test script
4. Fixed all application bugs and soft errors

## In Progress 🔄

### Priority 1: Firefox Launch Fix (CRITICAL)
**Issue**: Browser says "Opened Firefox" but nothing happens
**Root Cause**: subprocess.Popen needs DISPLAY environment variable
**Fix**: Add `env={'DISPLAY': ':99'}` to Popen calls

### Priority 2: Terminal Simplification
**Current**: Uses Vision Agent HTTP calls → Complex, slow, requires screenshot processing
**Target**: Direct Ollama chat like TerminalGPT → Simple, fast, conversational

**Changes Needed**:
- Remove Vision Agent dependency from terminal
- Add direct Ollama API client
- Stream responses like ChatGPT
- Keep conversation history in memory

### Priority 3: Browser Redesign (MAJOR)
**Current**: Simple search interface
**Target**: Split-pane with Firefox embed + AI assistant

**Architecture**:
```
┌─────────────────────────────────────────────┐
│         AuraOS Browser                       │
├──────────────────┬──────────────────────────┤
│                  │                          │
│   Firefox        │   AI Assistant           │
│   (Selenium)     │   - Chat with vision     │
│                  │   - Auto screenshots     │
│   [resizable]    │   - Web automation       │
│                  │                          │
└──────────────────┴──────────────────────────┘
```

**Technical Requirements**:
1. Selenium WebDriver for Firefox control
2. Screenshot monitoring (every page change)
3. Vision model integration for context
4. Tkinter PanedWindow for split view
5. WebSocket or polling for browser events

### Priority 4: Automation Integration
**Components Needed**:
- selenium
- geckodriver (Firefox WebDriver)
- Screenshot diff detection
- Vision → Action pipeline

## Quick Wins (Do Now)

### 1. Fix Firefox Launch
File: `auraos_browser.py`
Change line ~235:
```python
# OLD
subprocess.Popen(["firefox", url])

# NEW  
subprocess.Popen(["firefox", url], env={**os.environ, 'DISPLAY': ':99'})
```

### 2. Add Health Check Integration
File: `auraos.sh` cmd_health()
Add after existing checks:
```bash
echo -e "${YELLOW}[8/8]${NC} Connection Test"
bash test_connections.sh --quiet || true
```

### 3. Simplify Terminal (Minimal Change)
Keep current terminal but add direct chat option:
- Add "Chat Mode" button
- Direct Ollama /api/chat calls
- No Vision Agent dependency for chat

## Next Steps

1. **Immediate** (30 min):
   - Fix Firefox DISPLAY environment variable
   - Add test_connections to health command
   - Verify both work

2. **Short Term** (2-3 hours):
   - Create simplified terminal chat mode
   - Direct Ollama integration
   - Test conversational AI

3. **Medium Term** (1-2 days):
   - Design new browser architecture
   - Add Selenium dependencies to VM
   - Build split-pane prototype

4. **Long Term**:
   - Full vision-powered browser automation
   - Screenshot monitoring
   - Auto-navigation capabilities

## Dependencies to Add

```bash
# In VM (auraos.sh vm-setup)
apt-get install -y firefox-geckodriver
pip3 install selenium pillow-simd numpy opencv-python
```

## Files to Modify

1. `auraos_browser.py` - Firefox launch fix (NOW)
2. `auraos.sh` - Health check integration (NOW)
3. `auraos_terminal.py` - Add chat mode (SOON)
4. `auraos_browser_v2.py` - New split-pane design (LATER)

## Testing Plan

- [ ] Test Firefox opens with search
- [ ] Test health command shows all green
- [ ] Test terminal chat without Vision Agent
- [ ] Test browser split view prototype
- [ ] Test Selenium automation

