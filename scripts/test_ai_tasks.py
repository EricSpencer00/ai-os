#!/usr/bin/env python3
"""
Test AI responses for a list of terminal tasks.
- Uses the same extraction/validation logic as the terminal (no GUI import).
- Tries to call local inference server at INFERENCE_URL; if unavailable, uses a simulated response map.
- Does not execute arbitrary commands. It validates binaries via `command -v` and simulates retries.

Output: writes `ai_task_results.json` with per-task attempts and results.
"""

import os
import re
import json
import time
import random
import requests
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INFERENCE_URL = os.environ.get('INFERENCE_URL', 'http://localhost:8081')
MAX_RETRIES = 3

# Load tasks
TASKS_FILE = os.path.join(ROOT, 'terminal_tasks.md')
with open(TASKS_FILE, 'r') as f:
    lines = f.read().splitlines()

# Parse tasks numbered 1..30
TASKS = []
for ln in lines:
    m = re.match(r"^\s*(\d+)\.\s+(.*)$", ln)
    if m:
        TASKS.append(m.group(2).strip())

# Basic helper functions (replicating key terminal behavior)

def extract_command_from_response(response_text):
    # aggressive removal of fences/backticks
    t = re.sub(r"```\s*(?:[a-zA-Z0-9_+-]*)", "", response_text)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = t.replace('`', '')
    lines = [l.strip() for l in t.split('\n') if l.strip()]

    # skip preamble lines
    desc_patterns = [
        'here is', 'this command', 'to accomplish', 'to convert', 'example:', 'output:', 'note:',
        'first,', 'then,', 'finally,', 'the command', 'you can', 'alternatively', 'use:', 'try:',
        'run:', 'execute:', 'the bash', 'a command', 'to check', 'result:', 'note that'
    ]

    command_lines = []
    for line in lines:
        low = line.lower()
        if low in ('bash', 'sh', 'shell', 'zsh', 'python', 'node'):
            continue
        if any(low.startswith(p) or low.endswith(p) for p in desc_patterns):
            continue
        if re.match(r'^(command:|to fix:)', low):
            part = line.split(':', 1)[1].strip()
            if part:
                command_lines.append(part)
            continue
        command_lines.append(line)
    return '\n'.join(command_lines).strip()


def suggest_fallback(binary):
    fallbacks = {'python': 'python3', 'pip': 'pip3', 'node': 'nodejs'}
    return fallbacks.get(binary, None)


def get_platform_fallbacks(binary):
    """Return platform-specific fallback binaries for cross-platform compatibility."""
    import platform
    is_mac = platform.system() == 'Darwin'
    
    fallback_map = {
        'python': ['python3', 'python'],
        'pip': ['pip3', 'pip'],
        'node': ['nodejs', 'node'],
        'ip': ['ifconfig', 'networksetup'] if is_mac else ['ip'],
        'ss': ['netstat', 'lsof'] if is_mac else ['ss', 'netstat'],
    }
    return fallback_map.get(binary, [binary])


def resolve_binary(binary):
    # Try common fallbacks, including platform-specific
    fallbacks = get_platform_fallbacks(binary)
    for c in fallbacks:
        try:
            r = subprocess.run(['command', '-v', c], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip().splitlines()[0]
        except Exception:
            pass
    return None


def validate_command_safe(command):
    if not command or not command.strip():
        return False, 'Empty command', ''
    # injection detection
    if re.search(r"\$\(|\$\{", command):
        return False, 'Injection pattern detected', ''
    lines = command.strip().split('\n')
    corrected = []
    for line in lines:
        tokens = line.split(None, 1)
        if not tokens:
            continue
        binary = tokens[0].strip('`')
        args = tokens[1] if len(tokens) > 1 else ''
        resolved = resolve_binary(binary)
        if not resolved:
            fb = suggest_fallback(binary)
            return False, f'Command not found: {binary} (try: {fb})', ''
        corrected.append(f"{resolved} {args}".strip())
    return True, '', '\n'.join(corrected)


# Simple simulated responses in case inference server is unavailable
SIMULATED_MAP = {
    'Show current working directory': 'pwd',
    'List files in the current directory (long listing)': 'ls -la',
    'Show hidden files': 'ls -la --hidden',
    'List Python files recursively': "find . -name '*.py'",
    "Count number of lines in a file `README.md'": "wc -l README.md",
    'Count number of lines in a file `README.md`': 'wc -l README.md',
    'Show first 10 lines of `README.md`': 'head -n 10 README.md',
    'Show disk usage of current directory': 'du -sh .',
    'Show free disk space': 'df -h',
    'Show `python` version': 'python --version',
    'Show `python3` version': 'python3 --version',
    'Install `requests` into user site (pip)': 'pip install --user requests',
    'Show active network interfaces': 'ifconfig || networksetup -listallnetworkservices',
    'Ping `8.8.8.8` once': 'ping -c 1 8.8.8.8',
    'Show top 5 memory-consuming processes': "ps aux --sort=-%mem | head -n 6",
    'Show last 200 lines of `debug_logs.md` (if present)': 'tail -n 200 debug_logs.md',
    'Search for "TODO" in repository': 'grep -R "TODO" . || true',
    'Count files in repository': 'find . -type f | wc -l',
    'Find large files (>10M)': 'find . -type f -size +10M -exec ls -lh {} \\; || true',
    'Show available package updates (apt-get) [non-destructive]': 'sudo apt-get -s upgrade | head -n 20 || echo "apt-get not available"',
    'Print environment variables related to PATH': 'env | grep PATH',
    'Show git branch and latest commit': 'git rev-parse --abbrev-ref HEAD && git log -1 --oneline',
    'Create a directory `tmp_test_dir` (non-destructive)': 'mkdir -p tmp_test_dir',
    'Remove the created `tmp_test_dir` (only if exists and empty)': 'rmdir tmp_test_dir || true',
    'Show installed pip packages (user)': 'pip list --user',
    'Show Node.js version': 'node --version',
    'List listening TCP ports': 'netstat -tuln || lsof -i -P -n',
    'Show last reboot time': 'who -b || last reboot | head -1',
    'Display kernel uname info': 'uname -a',
    'Show contents of `/etc/passwd` (read-only)': 'cat /etc/passwd',
    'Run shell command to check if port 8081 is open locally': 'netstat -tuln | grep 8081 || lsof -i :8081 || echo "Port 8081 not open"'
}

RESULTS = []

# Check inference server availability
use_real_ai = False
try:
    r = requests.get(INFERENCE_URL, timeout=1)
    use_real_ai = r.ok
except Exception:
    use_real_ai = False

print('Using real AI:', use_real_ai, 'INFERENCE_URL=', INFERENCE_URL)

for i, task in enumerate(TASKS[:30], start=1):
    record = {'task_id': i, 'task': task, 'attempts': []}
    print('\n---')
    print(f'Task {i}: {task}')

    error_analysis = None
    attempt = 0
    success = False

    while attempt < MAX_RETRIES and not success:
        attempt += 1
        print(f' Attempt {attempt}/{MAX_RETRIES}')

        # Build prompt like terminal uses
        if error_analysis:
            cwd_ctx = f"Current directory: {error_analysis.get('cwd','~')}\n"
            hint = error_analysis.get('hint','')
            hint_text = f"HINT: {hint}\n" if hint else ''
            prompt = f"Fix this command that failed:\nOriginal request: {task}\n{cwd_ctx}{hint_text}Error: {error_analysis.get('issue','Unknown')}\nPrevious output: {error_analysis.get('output','')}\n\nOutput ONLY a new bash command to fix this. NOTHING ELSE."
        else:
            prompt = task

        # Query AI or use simulation
        response_text = ''
        if use_real_ai:
            try:
                r = requests.post(f"{INFERENCE_URL}/generate", json={'prompt': prompt}, timeout=8)
                if r.status_code == 200:
                    response_text = r.json().get('response','')
                else:
                    response_text = ''
            except Exception as e:
                response_text = ''
        if not response_text:
            # fallback simulated
            response_text = SIMULATED_MAP.get(task, '')

        extracted = extract_command_from_response(response_text)
        is_valid, err, corrected = validate_command_safe(extracted)

        attempt_record = {
            'attempt': attempt,
            'ai_raw_response': response_text,
            'extracted_command': extracted,
            'validation_ok': is_valid,
            'validation_err': err,
            'corrected': corrected
        }

        # If validation fails (e.g., command not found), prepare error_analysis and retry
        if not is_valid:
            # derive hint from err
            hint = ''
            if 'Command not found' in err:
                hint = 'Command not found; suggest fallback (python3/pip3/nodejs)'
            elif 'Injection pattern' in err:
                hint = 'Input contains command substitution; simplified to non-substituted form.'
            attempt_record['should_retry'] = True
            record['attempts'].append(attempt_record)

            error_analysis = {
                'reason': 'validation_failed',
                'issue': err,
                'output': '',
                'hint': hint,
                'cwd': '~'
            }
            print('  Validation failed:', err)
            time.sleep(0.3 + random.random()*0.5)
            continue
        else:
            # success for our test (we don't execute commands)
            attempt_record['should_retry'] = False
            record['attempts'].append(attempt_record)
            record['final_command'] = corrected if corrected else extracted
            record['status'] = 'validated'
            success = True
            print('  Validated command:', record['final_command'])
            break

    if not success:
        record['status'] = 'failed_validation'
        print('  Task failed validation after attempts')

    RESULTS.append(record)

# Save results
out_file = os.path.join(ROOT, 'ai_task_results.json')
with open(out_file, 'w') as f:
    json.dump(RESULTS, f, indent=2)

print('\nDone. Results written to', out_file)
