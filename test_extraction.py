#!/usr/bin/env python3
"""Test command extraction from AI responses"""
import re

def _extract_command_from_response(response_text):
    """Extract the actual command from potentially verbose AI response"""
    # First, strip all code-fence markers (with optional language identifier and spaces)
    # This handles ```bash, ``` bash, ```sh, ``` etc.
    response_text = re.sub(r"```\s*(?:[a-zA-Z0-9_+-]*)", "", response_text)
    
    # Remove inline backticks
    response_text = re.sub(r"`([^`]*)`", r"\1", response_text)

    lines = response_text.strip().split('\n')

    # Filter out empty lines, comments and formatting language markers
    command_lines = []
    desc_patterns = [
        'here is', 'this command', 'to accomplish', 'to convert',
        'example:', 'output:', 'note:', 'first,', 'then,', 'finally,',
        'the command', 'you can', 'alternatively', 'use:', 'try:',
        'run:', 'execute:', 'the bash', 'a command', 'to check'
    ]

    for line in lines:
        line = line.strip()

        # Skip empty or comment lines
        if not line or line.startswith('#'):
            continue

        line_lower = line.lower()

        # Skip lines that are just a language marker (e.g., 'bash', 'shell')
        if line_lower in ('bash', 'sh', 'shell'):
            continue

        # Skip obvious description patterns
        if any(line_lower.startswith(p) or line_lower.endswith(p) for p in desc_patterns):
            continue

        # Handle lines that prefix the command (e.g., "Command: ...")
        if re.match(r'^(command:|to fix:)', line_lower):
            parts = line.split(':', 1)[1].strip()
            if parts:
                command_lines.append(parts)
            continue

        # Looks like a real command line — append it
        if line:
            command_lines.append(line)

    # Return joined command lines if any
    if command_lines:
        return '\n'.join(command_lines)
    return ""

# Test cases from the screenshot and common AI patterns
test_cases = [
    ("```bash\npython --version\n```", "python --version"),
    ("Command: ```bash\npython --version", "python --version"),
    ("Command: ``` bash\npython --version", "python --version"),
    ("`python --version`", "python --version"),
    ("python --version", "python --version"),
    ("Here is the command:\n```bash\npython --version\n```", "python --version"),
    ("To check Python:\n\nCommand: ```bash\npython --version\n```", "python --version"),
    ("bash\npython --version", "python --version"),
    ("mkdir -p /tmp/test\ncd /tmp/test\nls", "mkdir -p /tmp/test\ncd /tmp/test\nls"),
]

print("Testing command extraction...\n")
passed = 0
failed = 0

for i, (input_text, expected) in enumerate(test_cases, 1):
    result = _extract_command_from_response(input_text)
    status = "✓" if result == expected else "✗"
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} Test {i}:")
    print(f"  Input:    {repr(input_text[:60])}")
    print(f"  Expected: {repr(expected)}")
    print(f"  Got:      {repr(result)}")
    if result != expected:
        print(f"  MISMATCH!")
    print()

print(f"\nResults: {passed}/{len(test_cases)} passed, {failed} failed")
