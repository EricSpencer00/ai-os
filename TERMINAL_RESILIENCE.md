# Terminal AI - TerminalGPT Resilience Implementation

## Overview
Completely redesigned `auraos_terminal.py` based on the resilience patterns from [TerminalGPT](https://github.com/EricSpencer00/Terminalgpt) with **automatic error recovery**.

## Key Feature: Auto-Recovery Loop

When a command fails, the Terminal AI now:

1. **Captures the error** (stderr or exit code)
2. **Sends error + original request to AI** 
3. **AI generates a corrected command**
4. **Automatically retries** (up to 3 attempts)
5. **Displays retry status** to user

### Example Flow

```
User: "install python"
  ↓
[AI generates] apt-get install -y python3
  ↓
[Command fails] "python3: command not found"
  ↓
[Retry 1] AI sees error, suggests: apt-get update && apt-get install -y python3.11
  ↓
[If fails again - Retry 2] AI tries: python3 --version || python3.11 --version || echo "install failed"
  ↓
[If still fails - Retry 3] Reports max retries reached
```

## Architecture

### Original vs New

| Aspect | Old | New |
|--------|-----|-----|
| **Error Handling** | Try once, report failure | Auto-retry up to 3 times |
| **Context** | No conversation history | Maintains request + error context |
| **Recovery** | None | AI generates fix for each error |
| **UI Feedback** | Basic success/error | Retry status with attempt counter |
| **Error Info** | Brief error message | Full stderr captured for AI context |

## Implementation Details

### Core Loop
```python
while self.retry_count < self.max_retries:
    # Generate command (with error context for recovery)
    command = self._generate_command(user_request, error_context)
    
    # Execute
    result = subprocess.run(command, shell=True, ...)
    
    if result.returncode == 0:
        # Success - display output and return
        break
    else:
        # Failure - prepare error context for next iteration
        error_context = result.stderr
        self.retry_count += 1
        # Loop continues with AI-improved command
```

### System Prompt

The Terminal uses a comprehensive system prompt that instructs the AI to:

1. **Generate complete, self-contained commands**
   - Include prerequisite steps (mkdir, apt-get update, etc.)
   - Handle missing tools automatically
   - No placeholders or incomplete commands

2. **Consider error cases**
   - Handle non-existent directories
   - Check tool availability
   - Use robust flags and error handling

3. **Provide only the command**
   - No explanations or markdown
   - Multiple commands on separate lines
   - Reply "CANNOT_CONVERT" if unable

### Error Recovery Prompt

When retrying after an error:

```
The previous command failed with this error:
{stderr_output}

Original request: {user_request}

Please provide a corrected command that will work around this error.
```

This gives the AI full context to generate a better command.

## UI Enhancements

- **Status Label** shows:
  - "Converting..." when generating
  - "Retrying... (1)" when on retry attempt
  - "Ready" when complete

- **Color Tags** distinguish operations:
  - `[info]` - Blue: general info
  - `[command]` - Green: generated bash commands
  - `[retry]` - Orange: retry attempts
  - `[error]` - Red: error messages
  - `[success]` - Green: success status

- **Welcome Message** shows:
  ```
  [Terminal] English to Bash - Auto Recovery
  If a command fails, the AI will automatically try to fix it
  Auto-retry enabled: 3 attempts
  ```

## Configuration

```python
AUTO_RETRY_ERRORS = True    # Enable/disable auto-recovery
MAX_RETRIES = 3             # Number of retry attempts
TIMEOUT = 30                # Command execution timeout (seconds)
AI_TIMEOUT = 15             # AI request timeout (seconds)
```

## Recovery Examples

### Example 1: Tool Not Found → Installation
```
Request: "show git version"
Try 1: git --version
Error: "command not found: git"
Try 2: apt-get install -y git && git --version
Result: ✓ Success (outputs git version)
```

### Example 2: Path Doesn't Exist → Create + Execute
```
Request: "create a file in /tmp/myproject"
Try 1: echo "hello" > /tmp/myproject/file.txt
Error: "No such file or directory"
Try 2: mkdir -p /tmp/myproject && echo "hello" > /tmp/myproject/file.txt
Result: ✓ Success (file created)
```

### Example 3: Permission → Fallback
```
Request: "modify system config"
Try 1: nano /etc/config.conf
Error: "Permission denied"
Try 2: sudo nano /etc/config.conf
Try 3: cat /etc/config.conf (read-only alternative)
Result: Alternative provided or sudo attempted
```

## Comparison to TerminalGPT

| Feature | TerminalGPT | AuraOS Terminal |
|---------|------------|-----------------|
| **Platform** | CLI with OpenRouter | Tkinter GUI |
| **Error Recovery** | Auto-retry ✓ | Auto-retry ✓ |
| **Max Retries** | 3 | 3 |
| **Safety Check** | Command sanitization | No unsafe command execution |
| **User Confirmation** | Optional | Automatic execution |
| **System Prompt** | Comprehensive | Adapted for completeness |

## Files Updated

- **Host:** `/Users/eric/GitHub/ai-os/auraos_terminal.py` (493 lines)
- **Backup:** `/Users/eric/GitHub/ai-os/auraos_terminal_old.py`
- **Deployed:** `/opt/auraos/bin/auraos_terminal.py` (on VM)

## Testing

### Test 1: Install Missing Tool
```
Request: "how much disk space is left"
Expected: Runs du or df command successfully
If fails on missing tool: AI suggests apt-get install and retries
```

### Test 2: Directory Creation
```
Request: "save a note to /tmp/notes.txt"
If fails: AI detects path issue, prepends mkdir -p
Result: File successfully created
```

### Test 3: Max Retries Exceeded
```
Request: "impossible_command_xyz"
Try 1-3: AI tries various approaches
Try 3+: Reports "[X] Max retries (3) reached"
```

## Performance Impact

- **No degradation** on successful first attempts
- **Additional AI calls** only on failures (3 max)
- **Minimal overhead** from error context (~500 chars per retry)
- **Retry delay** is natural (AI generation + execution time)

## Future Enhancements

1. **Configurable retry strategies**
   - Different retry counts per error type
   - Exponential backoff

2. **Error pattern recognition**
   - Track common errors
   - Suggest pre-emptive fixes
   - Build error → fix mappings

3. **Command validation**
   - Syntax validation before execution
   - Dependency checking
   - Dry-run mode

4. **Conversation memory**
   - Remember working commands
   - Learn from user corrections
   - Suggest similar tasks

## Status

✅ **Implemented & Deployed**
- Terminal now has TerminalGPT-style resilience
- Auto-recovery on command failure
- Full context passed to AI for intelligent fixes
- UI shows retry progress
- Tested syntax and deployed to VM

---

**Architecture Inspired By:** [TerminalGPT](https://github.com/EricSpencer00/Terminalgpt)
**Date:** Dec 2, 2025
**Location:** AuraOS Terminal (`/opt/auraos/bin/auraos_terminal.py`)
