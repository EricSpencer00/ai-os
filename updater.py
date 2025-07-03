# updater.py
# A trusted supervisor script that applies updates to the AuraOS daemon.
# It handles code replacement, package installation, and service restarts.

import sys
import os
import subprocess

def log(message):
    """Simple logger for the updater."""
    print(f"[Updater] {message}")

def install_packages(packages):
    """Installs a list of pip packages using the venv's pip."""
    if not packages:
        return True
    
    log(f"Installing packages: {', '.join(packages)}")
    try:
        # IMPORTANT: Use the full path to the venv's pip and run with sudo
        pip_path = os.path.expanduser('~/aura-os/venv/bin/pip')
        command = ['sudo', pip_path, 'install'] + packages
        subprocess.run(command, check=True)
        log("Package installation successful.")
        return True
    except subprocess.CalledProcessError as e:
        log(f"ERROR: Failed to install packages: {e}")
        return False

def update_daemon_code(new_code):
    """Replaces the content of daemon.py with the new code."""
    log("Updating daemon.py source code...")
    try:
        daemon_path = os.path.expanduser('~/aura-os/daemon.py')
        with open(daemon_path, 'w') as f:
            f.write(new_code)
        log("Daemon code updated successfully.")
        return True
    except IOError as e:
        log(f"ERROR: Failed to write new daemon code: {e}")
        return False

def restart_service():
    """Restarts the aura-daemon systemd service."""
    log("Restarting aura-daemon.service...")
    try:
        command = ['sudo', 'systemctl', 'restart', 'aura-daemon.service']
        subprocess.run(command, check=True)
        log("Service restarted successfully.")
        # A small delay to let the service initialize
        subprocess.run(['sleep', '3'], check=True)
        
        # Check status
        status_command = ['sudo', 'systemctl', 'is-active', 'aura-daemon.service']
        result = subprocess.run(status_command, capture_output=True, text=True)
        if result.stdout.strip() == 'active':
            log("HEALTH CHECK: Service is active.")
            return True
        else:
            log("HEALTH CHECK FAILED: Service is not active after restart.")
            return False

    except subprocess.CalledProcessError as e:
        log(f"ERROR: Failed to restart service: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 updater.py \"<base64_encoded_json_payload>\"")
        sys.exit(1)

    import base64
    import json

    try:
        payload_b64 = sys.argv[1]
        payload_json = base64.b64decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        
        new_code = payload.get('code')
        packages = payload.get('packages', [])

        if not new_code:
            raise ValueError("Payload must contain 'code' for the new daemon.")

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        log(f"FATAL: Invalid payload. {e}")
        sys.exit(1)

    log("--- Starting AuraOS Self-Update ---")
    
    if packages and not install_packages(packages):
        sys.exit(1)
        
    if not update_daemon_code(new_code):
        sys.exit(1)
        
    if not restart_service():
        sys.exit(1)
        
    log("--- Update Complete ---")

