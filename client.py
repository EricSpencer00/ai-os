# client.py
# A command-line client to interact with the AuraOS daemon.
# Demonstrates the Generate -> Confirm -> Execute workflow.

import requests
import sys

DAEMON_URL = "http://127.0.0.1:5000"

def generate_and_execute(intent):
    """The main workflow for handling a user's intent."""
    print(f"[*] Sending intent to daemon: '{intent}'")
    
    # 1. Generate the script
    try:
        response = requests.post(f"{DAEMON_URL}/generate_script", json={"intent": intent})
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
        print("Usage: python3 client.py \"Your command for the AI\"")
        sys.exit(1)
    
    user_intent = " ".join(sys.argv[1:])
    generate_and_execute(user_intent)

