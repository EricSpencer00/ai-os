#!/usr/bin/env python3
# client.py
# A command-line client to interact with the AuraOS daemon.
# v3: Now window-aware. It sends the current directory AND a list of open windows.

import requests
import sys
import os
import subprocess

DAEMON_URL = "http://127.0.0.1:5000"

def get_open_windows():
    """Uses wmctrl to get a list of open window titles."""
    try:
        # wmctrl -l lists windows in the format: ID  Desktop  Machine  Title
        result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True, check=True)
        windows = []
        for line in result.stdout.strip().split('\n'):
            parts = line.split(maxsplit=3)
            if len(parts) == 4:
                # We only care about the title
                windows.append(parts[3])
        return windows
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        # wmctrl might not be installed or might fail
        print(f"[!] Warning: Could not get window list. Is 'wmctrl' installed? Error: {e}")
        return []

def generate_and_execute(intent):
    """The main workflow for handling a user's intent."""
    print(f"[*] Sending intent to daemon: '{intent}'")
    
    # --- NEW: Get all context ---
    current_directory = os.getcwd()
    open_windows = get_open_windows()
    
    print(f"[*] Context (CWD): {current_directory}")
    print(f"[*] Context (Windows): {open_windows}")

    # 1. Generate the script
    try:
        payload = {
            "intent": intent,
            "context": {
                "cwd": current_directory,
                "windows": open_windows # Send the list of windows
            }
        }
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

    # 2. Confirm with the user
    print("\n" + "="*50)
    print("AI has generated the following script to execute:")
    print(f"\n  {script}\n")
    print("="*50)
    
    confirm = input("Do you want to execute this script? (y/n): ").lower()

    if confirm != 'y':
        print("\n[*] Execution cancelled by user.")
        return

    # 3. Execute the script
    print("\n[*] Executing script...")
    try:
        exec_response = requests.post(f"{DAEMON_URL}/execute_script", json={"script": script})
        exec_response.raise_for_status()
        exec_data = exec_response.json()
        
        print("\n--- Execution Result ---")
        print(f"Status: {exec_data.get('status')}")
        if exec_data.get('output'):
            print(f"Output:\n{exec_data.get('output')}")
        if exec_data.get('error_output'):
            print(f"Errors:\n{exec_data.get('error_output')}")
        print("------------------------")

    except requests.exceptions.RequestException as e:
        print(f"\n[!] Error during execution: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ai \"Your command for the AI\"")
        sys.exit(1)
    
    user_intent = " ".join(sys.argv[1:])
    generate_and_execute(user_intent)
