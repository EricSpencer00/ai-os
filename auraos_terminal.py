#!/usr/bin/env python3
"""
AuraOS Terminal - English to Bash Command Converter
Simple, focused tool that converts natural language to executable bash commands.

Usage:
  "show me all python files" → find . -name "*.py"
  "how much disk space do I have" → df -h
  "list large files" → find . -size +100M
  "create folder named test" → mkdir -p test
  exit to quit
"""
import os
import sys
import readline
import signal
import subprocess
import requests
from datetime import datetime

# Smart URL detection: use host gateway IP when running inside VM
def get_inference_url():
    """Get the correct inference server URL based on environment."""
    if os.path.exists("/opt/auraos"):
        # Running inside VM - use host gateway (192.168.2.1 for Multipass)
        return "http://192.168.2.1:8081"
    return "http://localhost:8081"

INFERENCE_URL = get_inference_url()

# Colored output helpers
def colored(text, color):
    colors = {
        'cyan': '\033[36m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'red': '\033[31m',
        'reset': '\033[0m',
        'blue': '\033[34m'
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

# Flag for graceful shutdown
terminate_request = False

def handle_termination(signum, frame):
    global terminate_request
    print(colored("\n\nGoodbye!", "cyan"))
    sys.exit(0)

signal.signal(signal.SIGINT, handle_termination)

def convert_english_to_bash(text):
    """
    Convert English text to bash command.
    Uses AI inference server for translation.
    """
    try:
        prompt = f"""You are a bash command generator. Convert this English request to a SINGLE bash command.
Request: {text}

Rules:
- Output ONLY the bash command, nothing else
- No explanations, no markdown, no code fences
- If you cannot convert it, reply: CANNOT_CONVERT
- Make the command safe (use -i flag for destructive operations)
- Use standard Unix utilities

Command:"""
        
        response = requests.post(
            f"{INFERENCE_URL}/generate",
            json={"prompt": prompt},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            command = result.get("response", "").strip()
            command = command.split('\n')[0].strip()  # First line only
            
            if command and "CANNOT_CONVERT" not in command and len(command) < 500:
                return command
    except:
        pass
    
    return None

def execute_command(command):
    """Execute a bash command and return output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.expanduser("~")
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out (30s limit)", 1
    except Exception as e:
        return "", str(e), 1

def main():
    """Main CLI loop"""
    print(colored("\n⚡ AuraOS Terminal - English to Bash", "green"))
    print(colored("━" * 50, "cyan"))
    print(colored("Convert English to bash commands", "yellow"))
    print(colored("Type 'exit', 'quit', or Ctrl+C to quit\n", "yellow"))
    
    while True:
        try:
            user_input = input(colored("You: ", "blue")).strip()
        except KeyboardInterrupt:
            print(colored("\n\nGoodbye!", "cyan"))
            sys.exit(0)
        
        if not user_input:
            continue
        
        # Exit conditions
        if user_input.lower() in ("exit", "quit"):
            print(colored("Goodbye!", "cyan"))
            sys.exit(0)
        
        print(colored("\n🤔 Converting to bash...", "yellow"), end=" ", flush=True)
        
        # Convert English to bash
        bash_command = convert_english_to_bash(user_input)
        
        if not bash_command:
            print(colored("✗ Could not convert", "red"))
            print(colored("  Try being more specific", "yellow"))
            print()
            continue
        
        print(colored("✓", "green"))
        print(colored(f"Command: ", "cyan") + colored(f"{bash_command}", "yellow"))
        print()
        
        # Ask for confirmation
        try:
            confirm = input(colored("Execute? (y/n): ", "blue")).strip().lower()
        except KeyboardInterrupt:
            print(colored("\n\nGoodbye!", "cyan"))
            sys.exit(0)
        
        if confirm not in ("y", "yes"):
            print(colored("Skipped\n", "yellow"))
            continue
        
        # Execute command
        print()
        stdout, stderr, code = execute_command(bash_command)
        
        if stdout:
            print(colored("Output:", "cyan"))
            print(stdout)
        
        if stderr and code != 0:
            print(colored("Error:", "red"))
            print(stderr)
        
        if code == 0 and not stdout:
            print(colored("✓ Command executed successfully", "green"))
        
        print()

if __name__ == "__main__":
    main()
