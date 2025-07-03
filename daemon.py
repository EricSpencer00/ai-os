# daemon.py
# The core AI daemon for AuraOS.
# This program runs a simple web server that listens for prompts,
# forwards them to the local LLM running on the Mac Mini,
# and returns the AI's response.

import os
import requests
import json
from flask import Flask, request, jsonify

# --- Configuration ---
# Create the Flask web server application
app = Flask(__name__)

# The IP address of your Mac Mini running Ollama.
# IMPORTANT: You MUST replace "YOUR_MAC_MINI_IP" with the actual IP address.
# You can find this in your Mac's System Settings -> Network.
# It will look like "192.168.1.XX".
OLLAMA_HOST = "YOUR_MAC_MINI_IP" 
OLLAMA_PORT = 11434 # Default Ollama port

# The name of the local model you have downloaded on your Mac Mini.
# We'll use gemma:2b as planned.
OLLAMA_MODEL = "gemma:2b"

# --- The AI Endpoint ---
@app.route('/prompt', methods=['POST'])
def handle_prompt():
    """
    Handles incoming prompts from any part of the OS.
    """
    print("Received a request...")

    # 1. Get the prompt from the incoming request
    try:
        data = request.get_json()
        user_prompt = data['prompt']
        if not user_prompt:
            return jsonify({"error": "Prompt cannot be empty"}), 400
    except Exception as e:
        print(f"Error parsing request: {e}")
        return jsonify({"error": "Invalid JSON request"}), 400

    print(f"User prompt: '{user_prompt}'")

    # 2. Prepare the request for the Ollama server
    ollama_api_url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
    ollama_payload = {
        "model": OLLAMA_MODEL,
        "prompt": user_prompt,
        "stream": False # We want the full response at once
    }

    # 3. Send the request to Ollama and get the response
    try:
        print(f"Forwarding prompt to Ollama at {ollama_api_url}...")
        response = requests.post(ollama_api_url, json=ollama_payload)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        # The response from Ollama is a JSON object, we need to parse it
        response_data = response.json()
        ai_response = response_data.get('response', '').strip()

        print(f"AI Response: '{ai_response}'")
        
        # 4. Return the AI's response to the original caller
        return jsonify({"response": ai_response})

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        return jsonify({"error": f"Could not connect to the Ollama server at {OLLAMA_HOST}. Is it running?"}), 503
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal error occurred"}), 500


# --- Main execution ---
if __name__ == '__main__':
    # To run this server and make it accessible from your Mac's terminal (and other devices),
    # we run it on host '0.0.0.0'.
    print("Starting AuraOS AI Daemon...")
    print(f"Listening for requests on all network interfaces...")
    print("Press CTRL+C to stop the server.")
    app.run(host='0.0.0.0', port=5000, debug=True)