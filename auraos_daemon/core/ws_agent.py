"""
WebSocket-based agent control for low-latency, event-driven VM automation.

Instead of continuous polling/VNC, this module:
1. Runs a FastAPI WebSocket server inside the VM that accepts action commands
2. Receives JSON action payloads: {"action": "click", "x": 100, "y": 200}
3. Executes actions via xdotool / pyautogui in real-time
4. Returns status/confirmation immediately

This decouples the host planner from VNC overhead and enables reactive control.

Usage (host side):
  client = WebSocketAgent("ws://localhost:6789")
  client.connect()
  client.execute_action({"action": "click", "x": 100, "y": 200})
  client.execute_action({"action": "type", "text": "hello"})

Usage (guest side):
  # Run inside VM:
  python3 /opt/auraos/agent_ws_server.py

  # Or as systemd service (create /etc/systemd/system/auraos-agent-ws.service)
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    websockets = None
    WebSocketServerProtocol = None

try:
    import websocket
except ImportError:
    websocket = None

logger = logging.getLogger(__name__)


@dataclass
class ActionExecutor:
    """Executes action commands on the guest VM."""

    def __init__(self, display: str = ":1"):
        self.display = display

    def execute_click(self, x: int, y: int) -> Dict[str, Any]:
        """Execute a mouse click at (x, y)."""
        try:
            import subprocess

            subprocess.run(
                f"DISPLAY={self.display} xdotool mousemove {x} {y} click 1",
                shell=True,
                timeout=2,
            )
            return {"success": True, "action": "click", "x": x, "y": y}
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return {"success": False, "error": str(e)}

    def execute_type(self, text: str) -> Dict[str, Any]:
        """Type text."""
        try:
            import subprocess

            # Escape special characters
            safe_text = text.replace('"', '\\"')
            subprocess.run(
                f'DISPLAY={self.display} xdotool type "{safe_text}"',
                shell=True,
                timeout=5,
            )
            return {"success": True, "action": "type", "text": text}
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return {"success": False, "error": str(e)}

    def execute_key(self, key: str) -> Dict[str, Any]:
        """Press a key (enter, backspace, tab, escape, etc.)."""
        try:
            import subprocess

            # Validate key name
            valid_keys = {
                "enter",
                "return",
                "backspace",
                "delete",
                "tab",
                "escape",
                "esc",
                "space",
                "arrow_up",
                "arrow_down",
                "arrow_left",
                "arrow_right",
                "home",
                "end",
                "page_up",
                "page_down",
            }

            key_lower = key.lower()
            if key_lower not in valid_keys:
                return {"success": False, "error": f"Unknown key: {key}"}

            # Map friendly names to xdotool key names
            key_map = {
                "arrow_up": "Up",
                "arrow_down": "Down",
                "arrow_left": "Left",
                "arrow_right": "Right",
                "page_up": "Page_Up",
                "page_down": "Page_Down",
                "return": "Return",
                "esc": "Escape",
                "backspace": "BackSpace",
            }

            xdotool_key = key_map.get(key_lower, key_lower)

            subprocess.run(
                f"DISPLAY={self.display} xdotool key {xdotool_key}",
                shell=True,
                timeout=2,
            )
            return {"success": True, "action": "key", "key": key}
        except Exception as e:
            logger.error(f"Key press failed: {e}")
            return {"success": False, "error": str(e)}

    def execute_wait(self, duration: float = 1.0) -> Dict[str, Any]:
        """Wait for a specified duration."""
        try:
            import time

            time.sleep(min(duration, 10))  # Cap at 10 seconds
            return {"success": True, "action": "wait", "duration": duration}
        except Exception as e:
            logger.error(f"Wait failed: {e}")
            return {"success": False, "error": str(e)}

    def execute_screenshot(self) -> Dict[str, Any]:
        """Capture and return screenshot metadata."""
        try:
            import subprocess
            import os

            path = "/tmp/ws_screenshot.png"
            subprocess.run(
                f"DISPLAY={self.display} scrot -z {path}",
                shell=True,
                timeout=3,
            )
            if os.path.exists(path):
                return {"success": True, "action": "screenshot", "path": path}
            else:
                return {"success": False, "error": "Screenshot file not created"}
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"success": False, "error": str(e)}

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute any action."""
        action_type = action.get("action", "").lower()

        if action_type == "click":
            return self.execute_click(action.get("x", 640), action.get("y", 360))
        elif action_type == "type":
            return self.execute_type(action.get("text", ""))
        elif action_type == "key":
            return self.execute_key(action.get("key", "enter"))
        elif action_type == "wait":
            return self.execute_wait(action.get("duration", 1.0))
        elif action_type == "screenshot":
            return self.execute_screenshot()
        else:
            return {"success": False, "error": f"Unknown action: {action_type}"}


# ===== Guest-side WebSocket server (runs inside VM) =====


async def handle_client(
    websocket: WebSocketServerProtocol,
    executor: ActionExecutor,
    on_action: Optional[Callable] = None,
):
    """Handle incoming WebSocket connections."""
    logger.info(f"Client connected: {websocket.remote_address}")

    try:
        async for message in websocket:
            try:
                action = json.loads(message)
                logger.debug(f"Received action: {action}")

                # Execute the action
                result = executor.execute(action)

                # Notify callback if provided
                if on_action:
                    on_action(action, result)

                # Send result back to client
                await websocket.send(json.dumps(result))
            except json.JSONDecodeError:
                error_msg = {"success": False, "error": "Invalid JSON"}
                await websocket.send(json.dumps(error_msg))
            except Exception as e:
                logger.error(f"Action execution error: {e}")
                error_msg = {"success": False, "error": str(e)}
                await websocket.send(json.dumps(error_msg))
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"Client disconnected: {websocket.remote_address}")


async def start_ws_server(
    host: str = "0.0.0.0",
    port: int = 6789,
    display: str = ":1",
    on_action: Optional[Callable] = None,
):
    """Start the WebSocket server (runs in guest VM)."""
    if not websockets:
        logger.error("websockets library not installed. Install: pip install websockets")
        return

    executor = ActionExecutor(display=display)

    async with websockets.serve(
        lambda ws: handle_client(ws, executor, on_action),
        host,
        port,
    ):
        logger.info(f"WebSocket server listening on ws://{host}:{port}")
        await asyncio.Future()  # run forever


# ===== Host-side WebSocket client =====


class WebSocketAgent:
    """Client for connecting to guest WebSocket agent."""

    def __init__(self, uri: str = "ws://localhost:6789", timeout: int = 10):
        """
        Args:
            uri: WebSocket URI (e.g., "ws://localhost:6789")
            timeout: connection timeout in seconds
        """
        self.uri = uri
        self.timeout = timeout
        self.ws = None

    def connect(self) -> bool:
        """Connect to the WebSocket server."""
        if not websocket:
            logger.error("websocket-client library not installed. Install: pip install websocket-client")
            return False

        try:
            self.ws = websocket.create_connection(
                self.uri,
                timeout=self.timeout,
            )
            logger.info(f"Connected to {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False

    def disconnect(self):
        """Disconnect from the server."""
        if self.ws:
            try:
                self.ws.close()
                logger.info("Disconnected from WebSocket server")
            except Exception as e:
                logger.error(f"Disconnect error: {e}")

    def execute_action(self, action: Dict[str, Any], timeout: int = 5) -> Dict[str, Any]:
        """
        Execute an action on the guest and wait for result.

        Args:
            action: action dict (e.g., {"action": "click", "x": 100, "y": 200})
            timeout: response timeout in seconds

        Returns:
            result dict from guest
        """
        if not self.ws:
            return {"success": False, "error": "Not connected"}

        try:
            # Send action
            self.ws.send(json.dumps(action))

            # Receive result with timeout
            self.ws.settimeout(timeout)
            response = self.ws.recv()
            result = json.loads(response)

            logger.debug(f"Action result: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            return {"success": False, "error": str(e)}

    def click(self, x: int, y: int) -> bool:
        """Convenience method: click at (x, y)."""
        result = self.execute_action({"action": "click", "x": x, "y": y})
        return result.get("success", False)

    def type(self, text: str) -> bool:
        """Convenience method: type text."""
        result = self.execute_action({"action": "type", "text": text})
        return result.get("success", False)

    def key(self, key: str) -> bool:
        """Convenience method: press key."""
        result = self.execute_action({"action": "key", "key": key})
        return result.get("success", False)

    def wait(self, duration: float = 1.0) -> bool:
        """Convenience method: wait."""
        result = self.execute_action({"action": "wait", "duration": duration})
        return result.get("success", False)
