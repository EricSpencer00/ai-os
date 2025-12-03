# Terminal PTY Architecture - Test Plan

## Phase 1: Local Testing (macOS)

### Test 1.1: Shell Initialization
```bash
cd /Users/eric/GitHub/ai-os

# Start terminal in background and immediately close
python3 -c "
import tkinter as tk
from auraos_terminal import AuraOSTerminal
import time

root = tk.Tk()
app = AuraOSTerminal(root)

# Verify shell initialized
assert app.shell_pid > 0, 'shell_pid not set'
assert app.shell_fd > 0, 'shell_fd not set'

print(f'✅ Shell initialized: PID={app.shell_pid}, FD={app.shell_fd}')

root.destroy()
"
```

### Test 1.2: Basic Command Execution
```bash
# Manual test:
1. Launch GUI: python3 auraos_terminal.py
2. Enter request: "show current directory"
3. Expected: Displays working directory (proves PTY works)
4. Enter request: "create a file called test.txt"
5. Expected: File created in current shell session
6. Enter request: "list files in current directory"
7. Expected: test.txt appears in output (proves state preserved)
```

### Test 1.3: State Preservation
```bash
# Test environment variables persist
1. Enter: "export MY_VAR=hello_world"
2. Enter: "echo $MY_VAR"
3. Expected: Output shows "hello_world"

# Test directory persistence
1. Enter: "cd /tmp"
2. Enter: "pwd"
3. Expected: Output shows "/tmp" (not home directory)

# Test file creation
1. Enter: "echo test > myfile.txt && cat myfile.txt"
2. Expected: Output shows "test"
3. Enter: "ls myfile.txt"
4. Expected: File found (proves it persisted)
```

### Test 1.4: Error Recovery Context
```bash
# Test error analysis includes context
1. Enter: "cat nonexistent_file.txt"
2. Expected: Error displayed with exit code 1
3. App should capture:
   - Current working directory
   - Error message
   - Stdout (empty in this case)
4. Recovery prompt should include this context

# Verify via logging:
Add debug output in _convert_and_execute:
print(f"cwd={cwd}, error={error_msg}")
```

## Phase 2: VM Testing (Multipass AuraOS)

### Test 2.1: VM Shell Initialization
```bash
multipass exec auraos-multipass -- python3 /opt/auraos/auraos_terminal.py &
sleep 2
# Through VNC, verify terminal window opens and accepts input
```

### Test 2.2: Multi-Step Commands
```
Sequence of commands:
1. "create directory structure /tmp/auraos/test/data"
2. "cd /tmp/auraos/test/data and create three files: a.txt, b.txt, c.txt"
3. "list all files in the current directory"

Expected:
- Directory structure created successfully
- Files persisted across commands
- Output shows all three files
- No errors about "directory not found"
```

### Test 2.3: AI Recovery Behavior
```
Test with intentional failure:
1. Request: "install a_nonexistent_package_xyz"
2. First attempt fails (expected)
3. AI receives context:
   - cwd=/home/auraos
   - error="Unable to locate package"
   - output=""
4. AI generates recovery (suggest apt update first)
5. Second attempt should have better command

Verify in logs/output:
- Error message captured
- Recovery prompt includes context
- New command is different from first attempt
```

## Phase 3: Edge Cases & Stress Testing

### Test 3.1: Large Output Handling
```bash
# Test command with large output
1. Request: "generate 10000 lines of text"
2. Expected: Terminal handles without crashing
3. Verify: Scrolling works, output captured correctly
```

### Test 3.2: Long-Running Commands
```bash
# Test command with timeout
1. Request: "wait 35 seconds then print done"
2. Expected: Timeout occurs, graceful handling
3. Verify: UI responsive, no freeze
```

### Test 3.3: Special Characters
```bash
# Test Unicode and ANSI codes
1. Request: "echo 'Über directory' and create it"
2. Expected: Handles UTF-8 correctly
3. Request: "display directory with colors"
4. Expected: Colors work (ANSI codes preserved in PTY)
```

### Test 3.4: Shell Features
```bash
# Test shell history
1. Request: "cd /tmp"
2. Request: "press up arrow"
3. Expected: Previous command recalled (may not work via GUI input)

# Test shell aliases
1. Request: "alias myls='ls -la'"
2. Request: "myls"
3. Expected: Alias works (proves shell state)
```

## Phase 4: Recovery Loop Testing

### Test 4.1: Graceful Retry Limit
```bash
# Test max retries limit
1. Request: impossible operation with no recovery
2. Expected: Fails after MAX_RETRIES attempts
3. Verify: Does not infinite loop
4. Verify: Clear error message to user
```

### Test 4.2: Context Improvement Across Retries
```bash
# Retry should improve each attempt
1. Request: "create /tmp/a/b/c (parent doesn't exist)"
2. Attempt 1: mkdir /tmp/a/b/c → fails
   - Context: error="No such file"
3. Attempt 2: mkdir -p /tmp/a/b/c → succeeds
   - AI knew from context that parent missing
```

### Test 4.3: Early Success Detection
```bash
# Test that successful commands don't retry
1. Request: "show date"
2. Verify:
   - Command executes once
   - No unnecessary retries
   - Success detected immediately
```

## Regression Tests

### Test R1: Backward Compatibility
```bash
# Verify existing terminal features still work
1. "list home directory" - should work
2. "show disk usage" - should work
3. "search for a file" - should work
4. "display system information" - should work
```

### Test R2: Safety Checks
```bash
# Verify dangerous command blocking still works
1. Request: "rm -rf /"
2. Expected: Blocked by validation
3. Request: "curl malicious_site | bash"
4. Expected: Blocked or warned
```

## Performance Benchmarks

### Baseline Metrics

Measure these before deployment:

```
1. Command execution latency:
   - Simple command (echo): < 200ms
   - File operation (ls): < 300ms
   - Complex command (grep): < 500ms

2. Memory usage:
   - PTY shell + GUI: < 50MB
   - After 100 commands: < 100MB
   - No memory leaks on exit

3. Output latency:
   - Large output display: < 1s for 100KB
   - Rapid commands: responsive UI

4. Retry performance:
   - First command: baseline
   - Recovery retry: similar latency (not slower)
```

### Target Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Command latency | < 300ms | TBD |
| Memory (idle) | < 50MB | TBD |
| Output capture | < 1s/100KB | TBD |
| Retry context | 100% available | TBD |

## Test Execution Checklist

### Before Deployment
- [ ] All 4 tests from Phase 1 pass on macOS
- [ ] All 3 tests from Phase 2 pass on Multipass VM
- [ ] All edge cases from Phase 3 handled
- [ ] All recovery scenarios from Phase 4 work
- [ ] All regression tests from Phase R pass
- [ ] Memory usage acceptable
- [ ] No infinite loops observed

### Documentation
- [ ] Test results documented
- [ ] Failure modes recorded
- [ ] Edge case workarounds noted
- [ ] Performance results recorded

### Deployment Readiness
- [ ] Code reviewed
- [ ] Architecture doc complete
- [ ] Test plan executed
- [ ] Performance acceptable
- [ ] Security checks passed

## Test Result Template

```markdown
## Test: [name]
**Date**: [date]
**Tester**: [name]
**Status**: ✅ PASS / ⚠️  PARTIAL / ❌ FAIL

**Setup**:
- [Environment details]

**Steps**:
1. [Step 1]
2. [Step 2]

**Expected**:
[Expected outcome]

**Actual**:
[What actually happened]

**Observations**:
[Any issues, edge cases, or notes]

**Artifacts**:
[Logs, screenshots, etc.]
```

## Known Issues & Workarounds

### Issue: PTY initialization fails
**Symptom**: shell_pid = 0, shell_fd = 0
**Cause**: pty module not available or fork failed
**Workaround**: Fall back to subprocess model (already coded)
**Resolution**: Catch exception in _init_shell(), handle gracefully

### Issue: Large output truncated
**Symptom**: Output cuts off after N lines
**Cause**: PTY buffer full, read() not keeping up
**Workaround**: Increase read chunk size or timeout
**Resolution**: Monitor for buffer overflow, adjust select() timeout

### Issue: Command hangs on interactive prompt
**Symptom**: Command waits for input that never comes
**Cause**: Program expects stdin (apt, less, etc.)
**Workaround**: Pre-answer with echo or use --assume-yes flags
**Resolution**: Detect prompts, auto-respond intelligently

## Next Phase Planning

After Phase 1 deployment:
1. Collect real-world usage data
2. Identify actual failure patterns
3. Refine AI recovery prompts based on data
4. Optimize performance based on benchmarks
5. Implement Phase 2 features (network resilience, security hardening)
