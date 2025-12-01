# AuraOS Terminal v3.0 — Test Plan & Verification Guide

## Test Overview

Complete testing strategy for v3.0 covering unit tests, integration tests, and manual verification.

## Phase 1: Pre-Deployment Tests

### 1.1 Environment Setup Test

**Prerequisites Check**:
```bash
#!/bin/bash
# Check all prerequisites

echo "=== Checking Prerequisites ==="
python3 --version || echo "❌ Python3 not found"
pip3 --version || echo "❌ pip3 not found"

# Check Python packages
pip3 show flask || echo "❌ Flask not installed"
pip3 show requests || echo "❌ Requests not installed"
pip3 show pillow || echo "❌ Pillow not installed"

# Check system tools
which screencapture || which scrot || echo "⚠️  Screenshot tool not available"
which git || echo "❌ Git not found"

# Check directories
[ -d ~/ai-os ] && echo "✓ Repo directory found" || echo "❌ Repo directory not found"
[ -d ~/ai-os/auraos_daemon ] && echo "✓ Daemon directory found" || echo "❌ Daemon directory not found"

echo "=== Prerequisites Check Complete ==="
```

**Expected Output**: All checks should pass with ✓ marks

**Pass Criteria**: 
- [ ] Python 3.8+
- [ ] pip3 available
- [ ] flask installed
- [ ] requests installed  
- [ ] Screenshot tool available
- [ ] Repo structure correct

### 1.2 Syntax Validation

**Test Files**:
```bash
#!/bin/bash

echo "=== Syntax Validation ==="

# Check Python syntax
python3 -m py_compile auraos_terminal_v3.py && echo "✓ Terminal syntax OK" || echo "❌ Terminal syntax error"
python3 -m py_compile auraos_daemon/core/ai_handler.py && echo "✓ AI Handler syntax OK" || echo "❌ AI Handler syntax error"
python3 -m py_compile auraos_daemon/core/screen_context.py && echo "✓ Screen Context syntax OK" || echo "❌ Screen Context syntax error"

# Check imports
python3 -c "from auraos_daemon.core.ai_handler import EnhancedAIHandler" && echo "✓ AI Handler import OK" || echo "❌ AI Handler import failed"
python3 -c "from auraos_daemon.core.screen_context import ScreenContextDB, ScreenCaptureManager" && echo "✓ Screen Context import OK" || echo "❌ Screen Context import failed"

echo "=== Syntax Check Complete ==="
```

**Pass Criteria**:
- [ ] Terminal syntax valid
- [ ] AI Handler syntax valid
- [ ] Screen Context syntax valid
- [ ] All imports successful

## Phase 2: Unit Tests

### 2.1 Screen Context System Tests

**Test: Database Initialization**
```python
def test_screen_context_db_init():
    """Test SQLite database initialization"""
    db = ScreenContextDB(":memory:")  # Use in-memory DB for testing
    
    # Should create tables
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    
    assert 'screenshots' in tables, "screenshots table not created"
    assert 'state_changes' in tables, "state_changes table not created"
    print("✓ Database initialization test passed")
```

**Test: Hash Deduplication**
```python
def test_screenshot_deduplication():
    """Test that identical screenshots aren't stored twice"""
    db = ScreenContextDB(":memory:")
    
    # Add same file twice
    result1 = db.add_screenshot("test_screenshot.png", "Test 1")
    result2 = db.add_screenshot("test_screenshot.png", "Test 2")
    
    assert result1 == True, "First insert should succeed"
    assert result2 == False, "Duplicate should be rejected"
    print("✓ Deduplication test passed")
```

**Test: Context Query**
```python
def test_get_recent_context():
    """Test querying recent context"""
    db = ScreenContextDB(":memory:")
    
    # Add some test data
    db.add_screenshot("test1.png", "First")
    db.add_screenshot("test2.png", "Second")
    db.add_state_change("TEST_EVENT", "Test change")
    
    context = db.get_recent_context(minutes=5)
    
    assert len(context['screenshots']) == 2, "Should have 2 screenshots"
    assert len(context['state_changes']) >= 1, "Should have state changes"
    print("✓ Context query test passed")
```

### 2.2 AI Handler Tests

**Test: Script Validation - Safe Script**
```python
def test_safe_script_validation():
    """Test that safe scripts pass validation"""
    handler = EnhancedAIHandler({})
    
    safe_scripts = [
        "ls -la",
        "pip install -r requirements.txt",
        "tar -czf backup.tgz ~/project",
        "mkdir -p ~/backups",
    ]
    
    for script in safe_scripts:
        result = handler._validate_script(script, "test intent")
        assert result['is_safe'] == True, f"Script should be safe: {script}"
    
    print("✓ Safe script validation passed")
```

**Test: Script Validation - Dangerous Script**
```python
def test_dangerous_script_blocking():
    """Test that dangerous scripts are blocked"""
    handler = EnhancedAIHandler({})
    
    dangerous_scripts = [
        "rm -rf /",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs /dev/sda1",
        "chmod 000 /etc",
        ":(){:|:&};:",  # Fork bomb
    ]
    
    for script in dangerous_scripts:
        result = handler._validate_script(script, "test intent")
        assert result['is_safe'] == False, f"Script should be blocked: {script}"
        assert len(result['notes']) > 0, f"Should explain why: {script}"
    
    print("✓ Dangerous script blocking passed")
```

**Test: Fallback Plan**
```python
def test_fallback_plan():
    """Test fallback heuristics when daemon unavailable"""
    handler = EnhancedAIHandler({})
    
    test_cases = [
        ("install python packages", "pip install"),
        ("backup files", "tar"),
        ("restart service", "systemctl restart"),
    ]
    
    for intent, expected_keyword in test_cases:
        result = handler._fallback_plan(intent)
        assert expected_keyword in result['script'], f"Should contain {expected_keyword}"
        assert len(result['reasoning']) > 0, "Should have reasoning"
    
    print("✓ Fallback plan test passed")
```

## Phase 3: Integration Tests

### 3.1 Terminal + AI Handler Integration

**Test: AI Task Processing Flow**
```bash
#!/bin/bash
# Integration test

echo "=== Integration Test: AI Task Flow ==="

# Start daemon if not running
curl http://localhost:5000/health >/dev/null 2>&1 || {
    echo "Starting daemon..."
    cd auraos_daemon && python main.py &
    DAEMON_PID=$!
    sleep 2
}

# Test AI task
python3 << 'PYTEST'
import sys
sys.path.insert(0, 'auraos_daemon')

from core.ai_handler import EnhancedAIHandler

handler = EnhancedAIHandler({})

# Test safe task
result = handler.process_ai_request("list files in current directory", auto_execute=False)

assert result['status'] in ['completed', 'pending_approval', 'blocked_safety'], f"Unexpected status: {result['status']}"
assert len(result['steps']) > 0, "Should have execution steps"

print("✓ AI task processing test passed")
PYTEST

echo "=== Integration Test Complete ==="
```

### 3.2 Daemon Integration Test

**Test: Daemon Health Check**
```bash
#!/bin/bash

echo "=== Testing Daemon Integration ==="

# Check daemon is running
HEALTH=$(curl -s http://localhost:5000/health)
if [ -z "$HEALTH" ]; then
    echo "❌ Daemon not running or not responding"
    exit 1
fi

echo "✓ Daemon is responding"
echo "Response: $HEALTH"

# Check key endpoints exist
for endpoint in /generate_script /execute_script /validate_output /health; do
    echo "  Testing $endpoint..."
    # Just check it's in the code
    grep -q "$endpoint" auraos_daemon/core/daemon.py && echo "    ✓ Endpoint defined" || echo "    ❌ Not found"
done

echo "=== Daemon Integration Test Complete ==="
```

## Phase 4: Manual Testing

### 4.1 Terminal Launch & UI

**Test Steps**:
1. [ ] Launch: `python auraos_terminal_v3.py`
2. [ ] Verify window opens (1200x800)
3. [ ] Verify title shows "AuraOS Terminal v3.0"
4. [ ] Verify buttons visible: ☰ Menu, ⚡ AI
5. [ ] Verify welcome message displayed
6. [ ] Verify input field ready (cursor visible)
7. [ ] Verify status shows "Ready"
8. [ ] Verify color scheme applied (dark theme)

**Expected Result**: Terminal fully functional with all UI elements visible

### 4.2 AI Button Test

**Test Steps**:
1. [ ] Click ⚡ AI button
2. [ ] Verify input field shows "ai- " prefix
3. [ ] Verify prompt indicator changes to ⚡
4. [ ] Verify cursor at end of text
5. [ ] Type test request: "list files"
6. [ ] Hit Enter
7. [ ] Verify AI task initiated

**Expected Result**: Input pre-filled, ready for natural language input

### 4.3 Safe Task Execution Test

**Test Steps**:
1. [ ] Click ⚡ AI button
2. [ ] Type: "ai- show system time"
3. [ ] Hit Enter
4. [ ] Observe execution steps:
   - [ ] ✓ [1] Screen Capture
   - [ ] ✓ [2] Script Generation
   - [ ] ✓ [3] Safety Validation
   - [ ] ⟳ [4] Executing
   - [ ] ✓ [5] Post-Validation
5. [ ] Verify result shown with timestamp
6. [ ] Verify back to ready state

**Expected Result**: Task auto-executes without confirmation, results displayed

### 4.4 Blocked Task Test

**Test Steps**:
1. [ ] Click ⚡ AI button
2. [ ] Type: "ai- delete system files"
3. [ ] Hit Enter
4. [ ] Verify safety validation blocks:
   - [ ] Shows ⚠ Safety Validation: Blocked
   - [ ] Shows reason for blocking
   - [ ] Shows suggestion (e.g., "Did you mean...")
5. [ ] Verify NO execution happens
6. [ ] Verify back to ready state

**Expected Result**: Dangerous operation blocked with explanation

### 4.5 Regular Shell Command Test

**Test Steps**:
1. [ ] Type regular command (without ai- prefix): "date"
2. [ ] Hit Enter
3. [ ] Verify executes as regular shell command
4. [ ] Verify output displayed
5. [ ] Verify no AI processing

**Expected Result**: Regular shell commands still work normally

### 4.6 Command History Test

**Test Steps**:
1. [ ] Type several commands (mixed ai- and regular)
2. [ ] Hit Up arrow to navigate history
3. [ ] Verify previous commands appear
4. [ ] Hit Up again to go further back
5. [ ] Hit Down arrow to go forward
6. [ ] Verify all history navigates correctly

**Expected Result**: History navigation works smoothly

### 4.7 Screen Capture Test

**Test Steps**:
1. [ ] Run a few AI tasks
2. [ ] Check directory: `ls -la /tmp/auraos_screenshots/`
3. [ ] Verify PNG files created
4. [ ] Check count: should have multiple screenshots
5. [ ] Verify no exact duplicates (hash-based dedup)
6. [ ] Verify file sizes reasonable (~100-500 KB)

**Expected Result**: Screenshots captured on screen changes

### 4.8 Database Test

**Test Steps**:
1. [ ] Run several AI tasks
2. [ ] Check database: `ls -la /tmp/auraos_screen_context.db`
3. [ ] Query database:
   ```bash
   sqlite3 /tmp/auraos_screen_context.db "SELECT COUNT(*) FROM screenshots;"
   ```
4. [ ] Verify count matches screenshots
5. [ ] Query state changes:
   ```bash
   sqlite3 /tmp/auraos_screen_context.db "SELECT event_type, COUNT(*) FROM state_changes GROUP BY event_type;"
   ```
6. [ ] Verify events logged

**Expected Result**: Database populated with screenshots and events

### 4.9 Log Test

**Test Steps**:
1. [ ] Run several tasks (AI and regular)
2. [ ] Check logs: `tail -20 /tmp/auraos_terminal_v3.log`
3. [ ] Verify entries for each task
4. [ ] Check timestamps are reasonable
5. [ ] Verify log format consistent
6. [ ] Verify no errors logged (for successful tasks)

**Expected Result**: Complete audit trail in logs

### 4.10 Menu Test

**Test Steps**:
1. [ ] Click ☰ Menu button
2. [ ] Verify menu panel opens on left side
3. [ ] Verify commands and help text displayed
4. [ ] Verify scrollable
5. [ ] Click ☰ Menu again
6. [ ] Verify menu closes

**Expected Result**: Menu toggles smoothly with helpful content

### 4.11 Help Command Test

**Test Steps**:
1. [ ] Type: "help"
2. [ ] Hit Enter
3. [ ] Verify help text displayed in output area
4. [ ] Verify includes AI mode explanation
5. [ ] Verify includes examples
6. [ ] Verify information is accurate

**Expected Result**: Helpful information displayed

### 4.12 Exit Test

**Test Steps**:
1. [ ] Type: "exit"
2. [ ] Hit Enter
3. [ ] Verify terminal closes
4. [ ] Verify graceful shutdown (no errors)
5. [ ] Verify logs finalized

**Expected Result**: Clean exit

## Phase 5: Performance Tests

### 5.1 Memory Usage Test

**Test**:
```bash
#!/bin/bash
# Monitor memory during operation

echo "=== Memory Usage Test ==="

# Get initial memory
BEFORE=$(ps aux | grep auraos_terminal | grep -v grep | awk '{print $6}')
echo "Initial memory: ${BEFORE}K"

# Run terminal with sample tasks for 5 minutes
# Monitor memory periodically
# Get final memory
AFTER=$(ps aux | grep auraos_terminal | grep -v grep | awk '{print $6}')
echo "Final memory: ${AFTER}K"

GROWTH=$((AFTER - BEFORE))
echo "Memory growth: ${GROWTH}K"

# Should be < 100MB
if [ $GROWTH -lt 102400 ]; then
    echo "✓ Memory growth acceptable"
else
    echo "⚠️  Excessive memory growth"
fi
```

**Pass Criteria**: Memory growth < 100 MB over 5 minutes

### 5.2 Execution Speed Test

**Test**:
```bash
#!/bin/bash

echo "=== Execution Speed Test ==="

# Time various operations
echo "Testing task execution time..."

time_task() {
    START=$(date +%s%N)
    python3 << PYTEST
import sys
sys.path.insert(0, 'auraos_daemon')
from core.ai_handler import EnhancedAIHandler
handler = EnhancedAIHandler({})
result = handler.process_ai_request("list files", auto_execute=False)
PYTEST
    END=$(date +%s%N)
    ELAPSED=$(( (END - START) / 1000000 ))
    echo "Task took ${ELAPSED}ms"
}

time_task

# Should be < 5 seconds
```

**Pass Criteria**: Task completion < 5 seconds average

### 5.3 Storage Test

**Test**:
```bash
#!/bin/bash

echo "=== Storage Test ==="

# Monitor disk usage
echo "Screenshot directory size:"
du -sh /tmp/auraos_screenshots

echo "Database size:"
ls -lh /tmp/auraos_screen_context.db

echo "Total logs:"
du -sh /tmp/auraos*.log

# Should be < 1GB total
TOTAL=$(du -s /tmp/auraos_* | awk '{s+=$1} END {print s}')
TOTAL_MB=$((TOTAL / 1024))
echo "Total usage: ${TOTAL_MB}MB"

if [ $TOTAL_MB -lt 1024 ]; then
    echo "✓ Storage usage acceptable"
else
    echo "⚠️  High disk usage"
fi
```

**Pass Criteria**: Total usage < 1 GB

## Phase 6: Stress Tests

### 6.1 High-Volume Task Test

**Test**: Run 50 tasks rapidly
```bash
#!/bin/bash

echo "=== Stress Test: 50 Tasks ==="

for i in {1..50}; do
    echo "Task $i..."
    python3 -c "
import sys
sys.path.insert(0, 'auraos_daemon')
from core.ai_handler import EnhancedAIHandler
handler = EnhancedAIHandler({})
result = handler.process_ai_request('task $i', auto_execute=False)
print(f'Task $i: {result[\"status\"]}')" || echo "Failed at task $i"
done

echo "✓ Stress test completed"
```

**Pass Criteria**: All 50 tasks complete without crashes

### 6.2 Long-Running Task Test

**Test**: 5-minute continuous operation
```bash
#!/bin/bash

echo "=== Stress Test: Long-Running ==="

timeout 300 python3 << 'PYTEST'
import sys, time
sys.path.insert(0, 'auraos_daemon')
from core.ai_handler import EnhancedAIHandler

handler = EnhancedAIHandler({})
start = time.time()

while time.time() - start < 300:  # 5 minutes
    result = handler.process_ai_request("test task", auto_execute=False)
    time.sleep(1)

print("✓ 5-minute test completed")
PYTEST
```

**Pass Criteria**: No memory leaks, stable operation

## Test Execution Checklist

### Before Deployment
- [ ] Phase 1: Environment setup - ALL PASS
- [ ] Phase 2: Unit tests - ALL PASS
- [ ] Phase 3: Integration tests - ALL PASS
- [ ] Phase 4: Manual tests - ALL PASS (12 tests)
- [ ] Phase 5: Performance tests - ALL PASS
- [ ] Phase 6: Stress tests - ALL PASS

### Before Production
- [ ] All above plus:
- [ ] Security review of code
- [ ] Performance benchmarking
- [ ] Backup/recovery testing
- [ ] Monitoring setup
- [ ] Documentation review
- [ ] User training

## Test Results Template

```
═══════════════════════════════════════════════════════
AuraOS Terminal v3.0 - Test Results
═══════════════════════════════════════════════════════

Date: _______________
Tester: _______________
Environment: Linux / macOS / Other

PHASE 1: Environment Setup     ☐ PASS  ☐ FAIL
PHASE 2: Unit Tests            ☐ PASS  ☐ FAIL
PHASE 3: Integration Tests     ☐ PASS  ☐ FAIL
PHASE 4: Manual Tests
  4.1 Terminal Launch          ☐ PASS  ☐ FAIL
  4.2 AI Button                ☐ PASS  ☐ FAIL
  4.3 Safe Task Execution      ☐ PASS  ☐ FAIL
  4.4 Blocked Task             ☐ PASS  ☐ FAIL
  4.5 Regular Commands         ☐ PASS  ☐ FAIL
  4.6 History Navigation       ☐ PASS  ☐ FAIL
  4.7 Screen Capture           ☐ PASS  ☐ FAIL
  4.8 Database                 ☐ PASS  ☐ FAIL
  4.9 Logging                  ☐ PASS  ☐ FAIL
  4.10 Menu                    ☐ PASS  ☐ FAIL
  4.11 Help Command            ☐ PASS  ☐ FAIL
  4.12 Exit                    ☐ PASS  ☐ FAIL

PHASE 5: Performance Tests     ☐ PASS  ☐ FAIL
PHASE 6: Stress Tests          ☐ PASS  ☐ FAIL

OVERALL RESULT:                ☐ PASS  ☐ FAIL

Notes:
_______________________________________________________
_______________________________________________________

Known Issues:
_______________________________________________________

Recommendations:
_______________________________________________________
```

## Continuous Testing

For ongoing monitoring:

```bash
#!/bin/bash
# Continuous test script (runs daily)

LOG="/tmp/auraos_test_$(date +%Y%m%d).log"

echo "=== Daily Test Run ===" >> $LOG
date >> $LOG

# Run key tests
python3 -m pytest tests/ >> $LOG 2>&1
echo "Unit tests: $?" >> $LOG

# Health check
curl http://localhost:5000/health >> $LOG 2>&1
echo "Health check: $?" >> $LOG

# Storage check
du -sh /tmp/auraos_* >> $LOG 2>&1

echo "Test complete" >> $LOG
```

---

**Testing is complete when ALL boxes are checked ✓**
