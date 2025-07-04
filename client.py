#!/usr/bin/env python3
# client.py
# The final, simplified client for the AuraOS ReAct Agent.
# Its only job is to send the user's intent and print the final result.

import requests
import sys

DAEMON_URL = "http://127.0.0.1:5000"

def run_agent_task(intent):
    """Sends the user's intent to the agent and prints the final result."""
    print(f"[*] Sending task to AuraOS Agent: '{intent}'")
    
    try:
        # The new endpoint handles the entire reasoning loop
        response = requests.post(f"{DAEMON_URL}/agent_task", json={"intent": intent})
        response.raise_for_status()
        data = response.json()
        
        print("\n" + "="*25 + " Task Complete " + "="*25)
        if "answer" in data:
            print(f"Final Answer:\n{data['answer']}")
        elif "error" in data:
            print(f"Agent failed to complete the task. Final error: {data['error']}")
        else:
            print("Agent finished without a final answer.")
        print("="*67)

    except requests.exceptions.RequestException as e:
        print(f"\n[!] CRITICAL ERROR: Could not connect to daemon. Is it running? Details: {e}")
        return
    except Exception as e:
        print(f"\n[!] An unexpected client-side error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ai \"Your command for the AI\"")
        sys.exit(1)
    
    user_intent = " ".join(sys.argv[1:])
    run_agent_task(user_intent)
