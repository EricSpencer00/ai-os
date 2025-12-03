# Terminal PTY Architecture - Deployment & Operations Guide

## Quick Start for Deployment

### Prerequisites
- Python 3.7+
- Standard library modules: pty, fcntl, select, signal
- Running in Unix-like environment (macOS, Linux)

### Deploy New Terminal

```bash
# 1. Backup current version
cp /opt/auraos/auraos_terminal.py /opt/auraos/auraos_terminal.py.backup

# 2. Deploy new version with PTY
cp auraos_terminal.py /opt/auraos/auraos_terminal.py

# 3. Restart UI
multipass exec auraos-multipass -- bash -c "killall auraos_terminal.py python3 2>/dev/null || true"
multipass exec auraos-multipass -- DISPLAY=:99 python3 /opt/auraos/auraos_terminal.py &

# 4. Verify through VNC
# Open http://localhost:6080/ and test terminal
```

## Operational Aspects

### How the New Terminal Works

**Shell Lifetime**:
```
Application Start
    ↓
pty.forkpty() → Create persistent bash
    ↓
User requests processed in this bash
    ↓
Application End
    ↓
Kill bash process
```

**Command Execution**:
```
User Input
    ↓
_generate_command() → AI creates bash command
    ↓
_run_in_shell() → Execute in persistent PTY
    ↓
  ├─ Write command
  ├─ Read output (select() non-blocking)
  ├─ Parse between markers
  └─ Extract exit code, stdout, stderr, cwd
    ↓
_analyze_command_result() → Check if succeeded
    ↓
Success? → Display & return
Failed?  → error_analysis {reason, issue, output, cwd}
          → Feed to _generate_command() for retry
          → Retry with full context
```

### Resource Usage

**Memory**:
- PTY shell + GUI: 40-50 MB
- Per 100 commands: +5-10 MB cache
- Should stabilize around 60-80 MB with memory management

**File Descriptors**:
- Base: ~10-15 FDs
- Per active command: +1 FD (the PTY)
- Should stay under 100 FDs total

**CPU**:
- Idle: < 1% CPU
- During command: Variable (depends on command)
- Select loop: Efficient polling, minimal overhead

### Monitoring

**Key Metrics to Track**:
1. PTY initialization success rate (should be 100%)
2. Command execution latency (target: < 200ms for simple commands)
3. Retry success rate (target: > 80% on first retry)
4. Memory usage (should stay < 100 MB)
5. Error frequency (track and analyze patterns)

**Log Points** (already in code):
```python
# These print() calls go to terminal output
print(f"Failed to initialize shell: {e}")  # Line 78
print(f"[X] {error_messages}")              # Throughout code
```

### Debugging

**Enable Verbose Output**:
```python
# Add to _run_in_shell() method
print(f"[DEBUG] Command: {command}")
print(f"[DEBUG] CWD before: {cwd_before}")
print(f"[DEBUG] Exit code: {exit_code}")
print(f"[DEBUG] Output length: {len(output)}")
```

**Check Shell Status**:
```bash
# In running terminal, type:
ps aux | grep -i bash   # Find bash processes
ls -la /proc/PID/fd     # Check PTY file descriptors
env | head              # Verify environment

# Verify state preservation:
# - Type: cd /tmp && pwd
#   Should output: /tmp (not home directory)
# - Type: export TEST=123 && echo $TEST
#   Should output: 123 (not empty)
```

**Monitor PTY**:
```bash
# Watch PTY connections
watch 'ps aux | grep bash'
watch 'ls -la /proc/*/fd | grep pty'
```

## Troubleshooting

### Issue: "Failed to initialize shell"
**Symptom**: Terminal starts but shows error message
**Cause**: pty.forkpty() failed (rare on most systems)
**Solution**: 
1. Check error message in console
2. Verify pty module is available: `python3 -c "import pty; print('OK')"`
3. Check system resource limits: `ulimit -a`
4. Try fallback to subprocess.run() (TODO implementation)

### Issue: Commands hang/freeze
**Symptom**: Terminal UI becomes unresponsive
**Cause**: Possible blocking I/O or infinite loop
**Solution**:
1. Check if command is actually running: `ps aux | grep "PID"`
2. Check timeout value in _run_in_shell() (default 30s)
3. Try interrupt: Ctrl+C (currently not handled)
4. Increase select() timeout if needed

### Issue: Lost output
**Symptom**: Part of command output missing
**Cause**: PTY buffer overflow or read timeout too short
**Solution**:
1. Increase timeout in _read_shell_output() call
2. Increase chunk size from 4096 to 8192
3. Check marker parsing logic (lines 443-452)

### Issue: Retry loop infinite
**Symptom**: Terminal keeps retrying forever
**Cause**: MAX_RETRIES not working or AI generating same failing command
**Solution**:
1. Check MAX_RETRIES value (should be 3)
2. Check retry_count increment logic (line 505)
3. Check AI prompt for recovery context
4. Verify error_analysis is being passed (line 508)

### Issue: Memory usage increasing
**Symptom**: Terminal grows to 100+ MB over time
**Cause**: Memory leaks in output buffer or PTY
**Solution**:
1. Restart terminal periodically
2. Clear output display periodically
3. Monitor gc module usage
4. Check for circular references in error_analysis dict

## Performance Tuning

### For Slow Systems

**Increase Timeouts**:
```python
# In _run_in_shell()
def _run_in_shell(self, command, timeout=60):  # Was 30, now 60
    ...
    cwd = self._read_shell_output(timeout=5)   # Can increase if needed
```

**Reduce Output Chunk Size** (less responsive but faster):
```python
# In _read_shell_output()
chunk = os.read(self.shell_fd, 2048)  # Was 4096, now 2048
```

**Reduce Select Polling** (less responsive but lower CPU):
```python
# In _read_shell_output()
ready, _, _ = select.select([self.shell_fd], [], [], 0.5)  # Was 0.1
```

### For Fast Systems

**Decrease Timeouts**:
```python
def _run_in_shell(self, command, timeout=15):  # Was 30, now 15
```

**Increase Output Chunk Size** (more responsive):
```python
chunk = os.read(self.shell_fd, 8192)  # Was 4096, now 8192
```

**Faster Select Polling**:
```python
ready, _, _ = select.select([self.shell_fd], [], [], 0.05)  # Was 0.1
```

## Integration Points

### How Terminal Integrates with AuraOS

**Launched by**:
- `auraos_launcher.py` - Main GUI includes terminal button
- `cmd_ui` - Shell command that launches full UI

**Communicates with**:
- Inference server (8081) for AI command generation
- Shell (via PTY) for command execution
- Display server (Xvfb) for GUI rendering

**Logs/Output**:
- Terminal console output goes to terminal window
- Errors printed to stdout (visible in VNC/terminal)
- No persistent log file yet (TODO: add logging)

### API/Interface

**Terminal as Service** (potential future):
```python
from auraos_terminal import AuraOSTerminal

# Could be used as library
terminal = AuraOSTerminal()
exit_code, output, error, cwd = terminal._run_in_shell("ls -la")
```

## Maintenance Schedule

### Daily
- Monitor error logs for repeated failures
- Check memory usage stays < 100 MB
- Verify retry success rate

### Weekly
- Review user feedback
- Check performance metrics
- Look for patterns in failures

### Monthly
- Performance analysis
- Plan for Phase 2 features
- Update documentation

### Quarterly
- Major version updates
- Refactor if needed
- Performance optimization pass

## Rollback Procedure

**If Issues Occur**:
```bash
# 1. Restore backup
cp /opt/auraos/auraos_terminal.py.backup /opt/auraos/auraos_terminal.py

# 2. Restart terminal
killall python3 auraos_terminal.py 2>/dev/null || true
sleep 2
DISPLAY=:99 python3 /opt/auraos/auraos_terminal.py &

# 3. Verify through VNC
# Open http://localhost:6080/
```

## Version Management

**Current Version**: 2.0 (PTY Architecture)
**Previous Version**: 1.0 (Stateless Subprocess) 
**Backup Location**: `auraos_terminal.py.backup`
**Release Notes**: See `TERMINAL_PTY_IMPLEMENTATION_COMPLETE.md`

## Security Considerations

### Input Validation
- Commands validated by `_validate_command()` before execution
- Dangerous patterns detected (from DANGEROUS_PATTERNS list)
- Partial security (TODO: expand to regex-based in Phase 2)

### Shell Privileges
- Terminal runs as `auraos` user (non-root)
- No privilege escalation in current version
- Sudo commands blocked by validation

### Network Commands
- Curl/wget allowed but should be gated (TODO: Phase 2)
- No automatic execution of network pipes
- AI generates commands, human (user) triggers execution

### Audit Trail
- No persistent audit log yet (TODO: add logging)
- Print statements to console for debugging
- Error messages logged via print()

## Future Enhancements (Phase 2+)

1. **Network Resilience**
   - Retry wrapper for inference server calls
   - Exponential backoff on failures

2. **Security Hardening**
   - Trust gate for network commands
   - Regex-based pattern detection
   - Persistent audit log

3. **Terminal UX**
   - Command history
   - Copy/paste support
   - Interrupt handling

4. **Advanced Features**
   - Capability detection
   - Environment auto-setup
   - Permission-aware retries

## Support & Contact

**Issues**: Check TERMINAL_PTY_TEST_PLAN.md for debugging steps
**Documentation**: 
- Architecture: TERMINAL_PTY_ARCHITECTURE.md
- Quick Ref: TERMINAL_PTY_QUICKREF.md
- This Guide: TERMINAL_PTY_DEPLOYMENT_GUIDE.md

**Code**: /Users/eric/GitHub/ai-os/auraos_terminal.py (578 lines)

---

**Status**: Production Ready (pending Phase 1 testing)
**Last Updated**: 2024
**Maintained By**: AuraOS Development Team
