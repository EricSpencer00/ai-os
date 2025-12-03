# 🚀 AuraOS Terminal - Auto-Recovery Quick Reference

## What Changed?

Your Terminal AI now **automatically fixes failed commands** using the same resilience patterns from [TerminalGPT](https://github.com/EricSpencer00/Terminalgpt).

## How It Works

```
User Request
    ↓
[AI] Generate Command
    ↓
Execute
    ↓
Success? → Done ✓
    ↓
Failure
    ↓
[Retry 1-3] AI fixes command with error context
    ↓
Success? → Done ✓
    ↓
Max Retries? → Report failure
```

## Example Scenarios

### Scenario 1: Missing Tool
```
You: "install nodejs"
AI:  apt-get install -y nodejs
Fail: "nodejs: command not found"
Retry: apt-get update && apt-get install -y nodejs
OK:  Successfully installed ✓
```

### Scenario 2: Directory Doesn't Exist
```
You: "create file in /tmp/project/data.txt"
AI:  echo "hello" > /tmp/project/data.txt
Fail: "No such file or directory"
Retry: mkdir -p /tmp/project && echo "hello" > /tmp/project/data.txt
OK:  File created ✓
```

### Scenario 3: Permission Issues
```
You: "read system config"
AI:  cat /etc/config.conf
Fail: "Permission denied"
Retry: sudo cat /etc/config.conf
OK:  Config displayed ✓
```

## Key Features

| Feature | Details |
|---------|---------|
| **Auto Retry** | Up to 3 attempts to fix failures |
| **Smart Context** | AI gets full error message for each retry |
| **UI Feedback** | Shows "Retrying... (1/3)" during attempts |
| **No Loss** | Output from successful attempts shown |
| **Timeout Safe** | 30s command timeout, 15s AI timeout |
| **Toggle Option** | `AUTO_RETRY_ERRORS = True/False` in code |

## UI Indicators

| Status | Meaning |
|--------|---------|
| `[?] Generating command...` | AI is creating the command |
| `[*] Executing...` | Running the command |
| `[OK] Command executed successfully` | Success ✓ |
| `[!] Command failed. Auto-retrying (1/3)...` | Attempting fix |
| `[X] Command failed: ...` | Final failure after max retries |

## Configuration

Edit these values in `/opt/auraos/bin/auraos_terminal.py`:

```python
AUTO_RETRY_ERRORS = True   # Enable auto-recovery
MAX_RETRIES = 3            # How many attempts
```

## What It's Based On

This implementation is modeled after **[TerminalGPT](https://github.com/EricSpencer00/Terminalgpt)** which features:

- ✓ Automatic error recovery with context
- ✓ Multi-attempt retry loop
- ✓ Full error messages passed to AI
- ✓ Comprehensive system prompts for command generation
- ✓ Safety considerations

## Testing Commands

Try these to see auto-recovery in action:

```bash
# Test 1: Missing package
show me disk usage

# Test 2: Directory creation
create file in /tmp/test/nested/file.txt

# Test 3: Tool installation
check nodejs version

# Test 4: File permissions
read sudoers file

# Test 5: Complex operation
find all python files and count them
```

## Architecture

```
┌─────────────────────────────────┐
│  User Request (Natural Language)│
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  System Prompt (Comprehensive)  │
│  + Error Context (if retry)     │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  AI Command Generation          │
│  (Inference Server/llava:13b)   │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Command Execution              │
│  (subprocess.run, 30s timeout)  │
└────────────┬────────────────────┘
             ↓
        ┌────┴────┐
        ↓         ↓
    Success    Failure
      ✓        (if retries < max)
      │         │
      │         ↓
      │    [Capture stderr]
      │         ↓
      │    [AI generates fix]
      │         ↓
      │    [Execute retry]
      │         ↓
      └─────────┘
```

## Performance

- **First attempt success:** No overhead
- **Failed attempt:** ~1-3s extra per retry (AI generation)
- **Max retries:** 3, so worst case = 2 additional AI calls + 2 executions
- **Timeout protection:** All operations bounded (30s command, 15s AI)

## Advanced Usage

### View Retry Logic
```bash
ssh auraos-multipass
grep -A 30 "_convert_and_execute" /opt/auraos/bin/auraos_terminal.py
```

### Disable Auto-Recovery
Edit the file and set:
```python
AUTO_RETRY_ERRORS = False
```

### Increase Max Retries
```python
MAX_RETRIES = 5  # or whatever number
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Retrying too much" | Set `AUTO_RETRY_ERRORS = False` |
| "Commands too slow" | Commands may be complex; this is normal |
| "Retry not helping" | Some tasks genuinely can't be fixed automatically |
| "Inference server error" | Check host inference server is running: `curl localhost:8081/health` |

## Status

✅ **Live on VM**
- Location: `/opt/auraos/bin/auraos_terminal.py`
- Syntax: Verified ✓
- Deployment: Complete ✓
- Features: All active ✓

Ready to use! Launch from AuraOS Launcher → Terminal

---

**Inspired By:** [EricSpencer00/Terminalgpt](https://github.com/EricSpencer00/Terminalgpt)
**Implementation Date:** Dec 2, 2025
**Type:** Tkinter GUI with Resilient AI Command Execution
