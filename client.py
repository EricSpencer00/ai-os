#!/usr/bin/env python3
# client.py
# A command-line client to interact with the AuraOS daemon.
# v5: Now autonomous. It auto-approves safe commands and asks the AI 
#     to retry commands that fail.

import requests
import sys
import os
import subprocess

DAEMON_URL = "http://127.0.0.1:5000"
MAX_RETRIES = 2

# A list of keywords that require user confirmation before execution.
DANGEROUS_KEYWORDS = [
    'rm ',      # Deleting files
    'sudo ',    # Superuser commands
    'mv ',      # Moving/renaming files can be destructive
    'mkfs',     # Formatting disks
    '> /dev/',  # Writing directly to devices
    'dd ',      # Low-level disk copy
    'chmod ',   # Changing permissions
    'chown ',   # Changing ownership
]

def get_open_windows():
    """Uses wmctrl to get a list of open window titles."""
    try:
        result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True, check=True)
        windows = [line.split(maxsplit=3)[3] for line in result.stdout.strip().split('\n') if len(line.split(maxsplit=3)) == 4]
        return windows
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

def is_script_safe(script):
    """Checks if the script contains any dangerous keywords."""
    return not any(keyword in script for keyword in DANGEROUS_KEYWORDS)

def autonomous_workflow(intent):
    """The main workflow, now with retries and auto-approval."""
    
    original_intent = intent
    retries = 0
    
    while retries <= MAX_RETRIES:
        print("\n" + "#"*60)
        if retries > 0:
            print(f"[*] This is retry attempt {retries}/{MAX_RETRIES}.")
        else:
            print(f"[*] Sending intent to daemon: '{intent}'")

        # 1. Generate the script
        current_directory = os.getcwd()
        open_windows = get_open_windows()
        
        payload = {
            "intent": intent,
            "context": {"cwd": current_directory, "windows": open_windows}
        }
        
        try:
            response = requests.post(f"{DAEMON_URL}/generate_script", json=payload)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"\n[!] Error connecting to daemon: {e}")
            return

        if "error" in data:
            print(f"\n[!] AI could not generate script: {data['error']}")
            return

        script = data.get("script")
        if not script:
            print("\n[!] Daemon returned an empty script.")
            return

        # 2. Confirm or Auto-Approve
        print("\n" + "="*50)
        print("AI has generated the following script to execute:")
        print(f"\n  {script}\n")
        print("="*50)
        
        if is_script_safe(script):
            print("[+] Script is considered safe. Auto-executing...")
        else:
            confirm = input("DANGEROUS KEYWORD DETECTED. Execute this script? (y/n): ").lower()
            if confirm != 'y':
                print("\n[*] Execution cancelled by user.")
                return

        # 3. Execute the script
        print("\n[*] Executing script...")
        try:
            display_var = os.environ.get('DISPLAY')
            exec_payload = {"script": script, "context": {"display": display_var}}
            exec_response = requests.post(f"{DAEMON_URL}/execute_script", json=exec_payload)
            exec_response.raise_for_status()
            exec_data = exec_response.json()
            
            print("\n--- Execution Result ---")
            print(f"Status: {exec_data.get('status')}")
            if exec_data.get('output'): print(f"Output:\n{exec_data.get('output')}")
            
            # 4. Handle results (Success or Retry)
            if exec_data.get('status') == 'success' and not exec_data.get('error_output'):
                print("\n[SUCCESS] Task completed successfully.")
                return # Exit the loop on success
            else:
                error_output = exec_data.get('error_output', 'Unknown error.')
                print(f"\n[FAILURE] Script failed to execute. Error:\n{error_output}")
                retries += 1
                if retries <= MAX_RETRIES:
                    # Prepare for the next loop iteration by refining the intent
                    intent = f"The original goal was '{original_intent}'. The last command '{script}' failed with the error: {error_output}. Please provide a new, corrected script to achieve the original goal."
                else:
                    print("[!] Max retries reached. Aborting.")

        except requests.exceptions.RequestException as e:
            print(f"\n[!] Error during execution: {e}")
            return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ai \"Your command for the AI\"")
        sys.exit(1)
    
    user_intent = " ".join(sys.argv[1:])
    autonomous_workflow(user_intent)
