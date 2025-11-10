#!/usr/bin/env bash
# Install WebSocket agent inside the VM
# This script is meant to run inside the guest VM as part of bootstrap

set -euo pipefail

echo "[ws-agent-bootstrap] Installing WebSocket agent..."

# Install Python dependencies
apt-get update -qq
apt-get install -y -qq python3-pip xdotool scrot || true

# Create agent directory
AGENT_DIR="/opt/auraos/ws_agent"
mkdir -p "$AGENT_DIR"

# Install websockets library for Python
python3 -m pip install --upgrade pip websockets 2>/dev/null || true
python3 -m pip install websocket-client 2>/dev/null || true

# Create the WebSocket agent server script
cat > "$AGENT_DIR/ws_server.py" << 'WSCODE'
#!/usr/bin/env python3
"""
WebSocket-based agent server for AuraOS VM.
Listens for action commands and executes them via xdotool.
"""
import asyncio
import json
import logging
import subprocess
import sys
import os
from pathlib import Path

try:
    import websockets
    from websockets.server import serve
except ImportError:
    print("websockets not installed — try: pip3 install websockets")
    sys.exit(1)

# Setup logging
LOG_DIR = "/var/log/auraos"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/ws_agent.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

DISPLAY = os.environ.get("DISPLAY", ":1")


class ActionExecutor:
    """Executes action commands."""

    @staticmethod
    def click(x: int, y: int) -> dict:
        try:
            subprocess.run(
                f"DISPLAY={DISPLAY} xdotool mousemove {int(x)} {int(y)} click 1",
                shell=True,
                timeout=2,
            )
            return {"success": True, "action": "click"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def type_text(text: str) -> dict:
        try:
            safe_text = text.replace('"', '\\"')
            subprocess.run(
                f'DISPLAY={DISPLAY} xdotool type "{safe_text}"',
                shell=True,
                timeout=5,
            )
            return {"success": True, "action": "type"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def key_press(key: str) -> dict:
        try:
            key_map = {
                "arrow_up": "Up",
                "arrow_down": "Down",
                "arrow_left": "Left",
                "arrow_right": "Right",
                "page_up": "Page_Up",
                "page_down": "Page_Down",
                "return": "Return",
                "enter": "Return",
                "esc": "Escape",
                "escape": "Escape",
                "backspace": "BackSpace",
                "delete": "Delete",
                "tab": "Tab",
                "space": "space",
                "home": "Home",
                "end": "End",
            }
            xdotool_key = key_map.get(key.lower(), key.lower())
            subprocess.run(
                f"DISPLAY={DISPLAY} xdotool key {xdotool_key}",
                shell=True,
                timeout=2,
            )
            return {"success": True, "action": "key"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def wait(duration: float) -> dict:
        try:
            import time
            time.sleep(min(float(duration), 10))
            return {"success": True, "action": "wait"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def screenshot() -> dict:
        try:
            path = "/tmp/ws_agent_screenshot.png"
            subprocess.run(
                f"DISPLAY={DISPLAY} scrot -z {path}",
                shell=True,
                timeout=3,
            )
            if os.path.exists(path):
                return {"success": True, "action": "screenshot", "path": path}
            return {"success": False, "error": "Screenshot failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def execute(cls, action: dict) -> dict:
        action_type = action.get("action", "").lower()
        try:
            if action_type == "click":
                return cls.click(action.get("x", 640), action.get("y", 360))
            elif action_type == "type":
                return cls.type_text(action.get("text", ""))
            elif action_type == "key":
                return cls.key_press(action.get("key", "enter"))
            elif action_type == "wait":
                return cls.wait(action.get("duration", 1.0))
            elif action_type == "screenshot":
                return cls.screenshot()
            else:
                return {"success": False, "error": f"Unknown action: {action_type}"}
        except Exception as e:
            logger.exception(f"Error executing {action_type}")
            return {"success": False, "error": str(e)}


async def handle_client(websocket, path):
    """Handle incoming WebSocket connections."""
    client_addr = websocket.remote_address
    logger.info(f"Client connected: {client_addr}")

    try:
        async for message in websocket:
            try:
                action = json.loads(message)
                logger.debug(f"Executing action: {action}")
                result = ActionExecutor.execute(action)
                await websocket.send(json.dumps(result))
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"success": False, "error": "Invalid JSON"}))
            except Exception as e:
                logger.error(f"Error: {e}")
                await websocket.send(json.dumps({"success": False, "error": str(e)}))
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"Client disconnected: {client_addr}")


async def main():
    host = "0.0.0.0"
    port = 6789
    logger.info(f"Starting WebSocket server on ws://{host}:{port}")
    async with serve(handle_client, host, port):
        logger.info("Server ready")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
WSCODE

chmod +x "$AGENT_DIR/ws_server.py"

echo "[ws-agent-bootstrap] Creating systemd service for WebSocket agent..."

cat > /etc/systemd/system/auraos-ws-agent.service <<'WSSVC'
[Unit]
Description=AuraOS WebSocket Agent (event-driven control)
After=network.target

[Service]
Type=simple
User=root
Environment=DISPLAY=:1
ExecStart=/usr/bin/python3 /opt/auraos/ws_agent/ws_server.py
Restart=on-failure
RestartSec=5

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
WSSVC

systemctl daemon-reload
systemctl enable --now auraos-ws-agent.service || true

# Mark bootstrap as done (if we got here, things are working)
mkdir -p /var/log/auraos
touch /var/log/auraos/bootstrap_done

echo "[ws-agent-bootstrap] WebSocket agent installed and started"
echo "  Server listening on ws://localhost:6789"
echo "  Service: systemctl status auraos-ws-agent"
echo "  Logs: journalctl -u auraos-ws-agent -f"
