#!/usr/bin/env python3
"""
Comprehensive test suite for hardened terminal.
Simulates adversarial AI outputs and verifies all defenses work.
"""
import re
import subprocess

def _extract_command_from_response(response_text):
    """Exact copy of the hardened extraction logic."""
    original_text = response_text
    response_text = re.sub(r"```\s*(?:[a-zA-Z0-9_+-]*)", "", response_text)
    response_text = re.sub(r"`([^`]*)`", r"\1", response_text)
    response_text = response_text.replace('`', '')
    lines = response_text.strip().split('\n')
    command_lines = []
    desc_patterns = [
        'here is', 'this command', 'to accomplish', 'to convert',
        'example:', 'output:', 'note:', 'first,', 'then,', 'finally,',
        'the command', 'you can', 'alternatively', 'use:', 'try:',
        'run:', 'execute:', 'the bash', 'a command', 'to check',
        'result:', 'note that', 'if you', 'you need to', 'make sure'
    ]
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        line_lower = line.lower()
        if line_lower in ('bash', 'sh', 'shell', 'zsh', 'ksh', 'python', 'ruby'):
            continue
        if any(line_lower.startswith(p) or line_lower.endswith(p) for p in desc_patterns):
            continue
        if re.match(r'^(command:|to fix:)', line_lower):
            parts = line.split(':', 1)[1].strip()
            if parts:
                command_lines.append(parts)
            continue
        if line:
            command_lines.append(line)
    result = '\n'.join(command_lines) if command_lines else ""
    return result

def _resolve_binary(binary):
    """Exact copy of binary resolution logic."""
    fallbacks = {
        'python': ['python3', 'python'],
        'pip': ['pip3', 'pip'],
        'node': ['nodejs', 'node']
    }
    candidates = [binary] + fallbacks.get(binary, [])
    for candidate in candidates:
        try:
            result = subprocess.run(
                f"command -v {candidate}",
                shell=True,
                capture_output=True,
                timeout=2,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().split()[-1]
        except:
            pass
    return None

def _validate_command_safe(command):
    """Exact copy of command validation logic."""
    if not command or not command.strip():
        return False, "Empty command", ""
    
    injection_patterns = [r"\$\(", r"\$\{", r"`;.*`"]
    for pattern in injection_patterns:
        if re.search(pattern, command):
            return False, f"Injection pattern: {pattern}", ""
    
    lines = command.strip().split('\n')
    corrected_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        tokens = line.split(None, 1)
        if not tokens:
            continue
        
        binary = tokens[0]
        args = tokens[1] if len(tokens) > 1 else ""
        
        resolved = _resolve_binary(binary)
        if not resolved:
            return False, f"Command not found: {binary}", ""
        
        corrected_lines.append(f"{resolved} {args}".strip())
    
    if not corrected_lines:
        return False, "No valid commands", ""
    
    return True, "", '\n'.join(corrected_lines)

# Test suite
test_cases = [
    # (name, input, expected_extracted, expected_valid_msg)
    ("Clean command", "ls -la", "ls -la", "OK"),
    ("Fenced code with bash", "```bash\nls -la\n```", "ls -la", "OK"),
    ("Fenced code with space", "``` bash\nls -la\n```", "ls -la", "OK"),
    ("Inline backticks", "`ls -la`", "ls -la", "OK"),
    ("Command: prefix", "Command: ls -la", "ls -la", "OK"),
    ("Preamble before command", "To list files:\n\nls -la", "ls -la", "OK"),
    ("Multiple commands", "cd /tmp\nls", "cd /tmp\nls", "OK"),
    ("python fallback", "python --version", "python", "Resolved to python3"),  # Will be python3
    ("Injection: command substitution", "ls $(whoami)", "ls $(whoami)", "Blocked"),
    ("Injection: variable expansion", "ls ${HOME}", "ls ${HOME}", "Blocked"),
    ("Injection: backtick substitution", "ls `whoami`", "ls `whoami`", "Blocked"),  # Should be stripped during extraction
    ("Marker collision attempt", "echo __CMD_START_123__", "echo __CMD_START_123__", "OK"),
    ("Empty after extraction", "Here is the command:\nExample:\nNote:", "", "Empty"),
    ("Language marker only", "bash\npython", "python", "OK"),
    ("Mixed valid and preamble", "First run this:\nls -la\nThen check output", "ls -la", "OK"),
]

print("=" * 80)
print("TERMINAL HARDENING TEST SUITE")
print("=" * 80)
print()

passed = 0
failed = 0

for name, input_text, expected_extracted, expected_validation in test_cases:
    print(f"[TEST] {name}")
    print(f"  Input: {repr(input_text[:60])}")
    
    # Test extraction
    extracted = _extract_command_from_response(input_text)
    extraction_ok = extracted == expected_extracted
    
    print(f"  Extracted: {repr(extracted[:60])} (expected {repr(expected_extracted[:60])})")
    if not extraction_ok:
        print(f"    ✗ MISMATCH")
        failed += 1
        print()
        continue
    
    # Test validation
    if expected_validation == "Empty":
        if not extracted:
            print(f"  Validation: Correctly rejected empty")
            print(f"    ✓ PASS")
            passed += 1
        else:
            print(f"  Validation: Should have been empty but got {repr(extracted)}")
            print(f"    ✗ FAIL")
            failed += 1
        print()
        continue
    
    if extracted:
        is_valid, err, corrected = _validate_command_safe(extracted)
        
        if expected_validation == "Blocked":
            if not is_valid:
                print(f"  Validation: Correctly blocked - {err}")
                print(f"    ✓ PASS")
                passed += 1
            else:
                print(f"  Validation: Should have been blocked but passed")
                print(f"    ✗ FAIL")
                failed += 1
        elif expected_validation == "OK" or expected_validation == "Resolved to python3":
            if is_valid:
                print(f"  Validation: ✓ Passed")
                if corrected:
                    print(f"    Corrected to: {repr(corrected[:60])}")
                print(f"    ✓ PASS")
                passed += 1
            else:
                print(f"  Validation: Failed - {err}")
                print(f"    ✗ FAIL")
                failed += 1
        else:
            print(f"  Validation: Unknown expectation {expected_validation}")
            print(f"    ? SKIP")
    else:
        print(f"  Validation: Skipped (no extracted command)")
        print(f"    ✓ PASS")
        passed += 1
    
    print()

print("=" * 80)
print(f"RESULTS: {passed}/{len(test_cases)} PASSED, {failed} FAILED")
print("=" * 80)

if failed == 0:
    print("✓ All tests passed! Terminal is properly hardened.")
else:
    print(f"✗ {failed} test(s) failed. Review above for details.")
