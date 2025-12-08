#!/usr/bin/env python3
"""
AuraOS Vision - Compact Sidebar AI Assistant
Features:
1. Small sidebar buttons for quick access
2. Auto-analyze screen on button click
3. Cluely Automation - AI operates screen autonomously
"""
import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import os
import base64
import json
import time
import io
import re
import logging
from pathlib import Path

# Optional imports
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from PIL import ImageGrab, Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Setup logging
LOG_DIR = Path.home() / ".auraos" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "vision.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_inference_url():
    """Get the correct inference server URL based on environment."""
    if os.path.exists("/opt/auraos"):
        return "http://192.168.2.1:8081"
    return "http://localhost:8081"

INFERENCE_URL = get_inference_url()
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LLAVA_MODEL = os.environ.get("AURAOS_LLAVA_MODEL", "llava:13b")

class AuraOSVision:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Vision")
        self.root.geometry("340x550")  # Compact sidebar size
        self.root.configure(bg='#0a0e27')
        self.root.resizable(True, True)
        
        self.is_processing = False
        self.screenshot_data = None
        self.screenshot_size = None
        self.automation_running = False
        self.last_action_type = None  # Track action type for adaptive cooldown
        self.recent_actions = []  # keep short context window for llava planning
        
        # Set DISPLAY for VM
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":99"
        
        logger.info("AuraOS Vision initialized - Inference URL: %s", INFERENCE_URL)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Title bar (compact)
        title_frame = tk.Frame(self.root, bg='#0a0e27')
        title_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        title = tk.Label(
            title_frame, text="AuraOS Vision",
            font=('Arial', 14, 'bold'), fg='#00ff88', bg='#0a0e27'
                """Continuous automation loop using LLaVA 13B via Ollama."""
                step = 0
                consecutive_errors = 0
                max_consecutive_errors = 5

                logger.info("Starting automation loop for task: %s", task)

                while self.automation_running:
                    step += 1
                    self.auto_status.config(text=f"Automation: Running (step {step})", fg='#00ff88')
                    self.append_text(f"\n[Step {step}]\n", "action")

                    try:
                        if not HAS_PIL:
                            raise RuntimeError("PIL required for screenshots")

                        screenshot = ImageGrab.grab()
                        self.screenshot_size = screenshot.size
                        buffer = io.BytesIO()
                        screenshot.save(buffer, format='PNG')
                        img_data = base64.b64encode(buffer.getvalue()).decode()
                        logger.debug("Screenshot captured: %dx%d", screenshot.size[0], screenshot.size[1])

                        plan = self._plan_action_with_llava(task, img_data)
                        if not plan:
                            self.append_text("[Wait] No action returned, retrying...\n", "warning")
                            consecutive_errors += 1
                            time.sleep(2)
                            continue

                        action = plan.get('action', 'wait')
                        why = plan.get('why', '')
                        self._record_action_context(action, why)
                        self.append_text(f"[AI] {why}\n", "ai")
                        logger.info("Action determined: %s - %s", action, why)
                        consecutive_errors = 0

                        if action == 'done':
                            self.append_text("[Auto] Task Complete!\n", "success")
                            logger.info("Automation completed successfully at step %d", step)
                            break
                        if action == 'fail':
                            self.append_text("[Auto] Marked as failed - stopping.\n", "error")
                            logger.error("Automation failed: %s", why)
                            break

                        if action == 'click':
                            x, y = int(plan.get('x', 0)), int(plan.get('y', 0))
                            if self._validate_coordinates(x, y):
                                self.append_text(f"[Click] ({x},{y})\n", "action")
                                self._do_click(x, y)
                                self.last_action_type = 'click'
                            else:
                                self.append_text(f"[Skip] Click out of bounds: ({x},{y})\n", "error")
                                logger.warning("Click coordinates invalid: (%d,%d)", x, y)
                        elif action == 'type':
                            text = plan.get('text', '')
                            self.append_text(f"[Type] {text[:40]}\n", "action")
                            self._do_type(text)
                            self.last_action_type = 'type'
                        elif action == 'key':
                            key = plan.get('key', '')
                            self.append_text(f"[Key] {key}\n", "action")
                            self._do_key(key)
                            self.last_action_type = 'key'
                        elif action == 'scroll':
                            amount = int(plan.get('amount', 0))
                            self.append_text(f"[Scroll] {amount}\n", "action")
                            self._do_scroll(amount)
                            self.last_action_type = 'scroll'
                        else:
                            self.append_text("[Wait] Cooling down...\n", "info")
                            self.last_action_type = 'wait'

                        cooldown = self._get_adaptive_cooldown(action)
                        time.sleep(cooldown)

                    except requests.exceptions.Timeout:
                        err_msg = "[Error] LLaVA request timeout"
                        self.append_text(f"{err_msg}\n", "error")
                        logger.error(err_msg)
                        consecutive_errors += 1
                        time.sleep(3)
                    except requests.exceptions.ConnectionError as e:
                        err_msg = f"[Error] Cannot reach Ollama: {e}"
                        self.append_text(f"{err_msg}\n", "error")
                        logger.error(err_msg)
                        consecutive_errors += 1
                        time.sleep(3)
                    except Exception as e:
                        err_msg = f"[Error] {str(e)[:80]}"
                        self.append_text(f"{err_msg}\n", "error")
                        logger.exception("Automation loop exception")
                        consecutive_errors += 1
                        time.sleep(2)

                    if consecutive_errors >= max_consecutive_errors:
                        self.append_text(f"[Error] Too many errors ({consecutive_errors}) - stopping\n", "error")
                        logger.error("Stopping automation due to %d consecutive errors", consecutive_errors)
                        break

                self.automation_running = False
                logger.info("Automation loop completed at step %d", step)
                self.root.after(0, self._reset_auto_ui)
        self.append_text("[+] Capturing...\n", "info")
        
        threading.Thread(target=self._take_screenshot, daemon=True).start()
        
    def _take_screenshot(self):
        """Take screenshot in background"""
        try:
            screenshot = ImageGrab.grab()
            self.screenshot_size = screenshot.size
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            self.screenshot_data = base64.b64encode(img_byte_arr.getvalue()).decode()
            
            msg = f"[OK] Captured {screenshot.size[0]}x{screenshot.size[1]}"
            self.append_text(f"{msg}\n", "success")
            logger.info(msg)
        except Exception as e:
            err_msg = f"[Error] Screenshot: {e}"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
            
        self.is_processing = False
        self.status_label.config(text="Ready", fg='#6db783')
        
    def analyze(self):
        """Analyze screenshot with AI"""
        if self.is_processing:
            return
        
        # Auto-capture if needed
        if not self.screenshot_data:
            self.append_text("📷 Auto-capturing...\n", "info")
            self.take_screenshot()
            self.root.after(1500, self.analyze)
            return
        
        if not HAS_REQUESTS:
            self.append_text("[Error] requests not installed\n", "error")
            return
            
        self.is_processing = True
        self.status_label.config(text="Analyzing...", fg='#00d4ff')
        self.analyze_btn.config(state='disabled')
        
        threading.Thread(target=self._analyze, daemon=True).start()
        
    def _analyze(self):
        """Analyze screenshot with AI"""
        try:
            self.append_text("🤖 Sending to AI...\n", "info")
            logger.debug("Starting analysis request to %s", INFERENCE_URL)
            
            # Vision endpoint is /ask on the unified inference server
            response = requests.post(
                f"{INFERENCE_URL}/ask",
                json={
                    "query": "Describe what you see on this screen. Be concise. What is visible and what actions could be taken?",
                    "images": [self.screenshot_data],
                    "parse_json": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get("response", "").strip()
                self.append_text(f"\n[AI] {analysis}\n\n", "ai")
                logger.info("Analysis completed successfully")
            else:
                err_msg = f"[Error] Server: {response.status_code}"
                self.append_text(f"{err_msg}\n", "error")
                logger.error(err_msg)
                
        except requests.exceptions.ConnectionError as e:
            err_msg = f"[Error] Cannot reach {INFERENCE_URL}: {e}"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
        except requests.exceptions.Timeout:
            err_msg = "[Error] Analysis timeout (60s)"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
        except Exception as e:
            err_msg = f"[Error] Analysis failed: {str(e)}"
            self.append_text(f"{err_msg}\n", "error")
            logger.exception("Analysis exception")
            
        self.is_processing = False
        self.status_label.config(text="Ready", fg='#6db783')
        self.analyze_btn.config(state='normal')
    
    def start_automation(self):
        """Start Cluely automation"""
        task = self.task_entry.get().strip()
        if not task or task == "Describe task for AI...":
            self.append_text("[Error] Enter a task first\n", "error")
            return
        
        self.automation_running = True
        self.start_auto_btn.config(state='disabled')
        self.stop_auto_btn.config(state='normal')
        self.auto_status.config(text="Automation: Running", fg='#00ff88')
        self.append_text(f"\n[Auto] Task: {task}\n", "action")
        
        threading.Thread(target=self._automation_loop, args=(task,), daemon=True).start()
    
    def _automation_loop(self, task):
        """Continuous automation loop using LLaVA 13B via Ollama."""
        step = 0
        consecutive_errors = 0
        max_consecutive_errors = 5

        logger.info("Starting automation loop for task: %s", task)

        while self.automation_running:
            step += 1
            self.auto_status.config(text=f"Automation: Running (step {step})", fg='#00ff88')
            self.append_text(f"\n[Step {step}]\n", "action")

            try:
                if not HAS_PIL:
                    raise RuntimeError("PIL required for screenshots")

                screenshot = ImageGrab.grab()
                self.screenshot_size = screenshot.size
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                img_data = base64.b64encode(buffer.getvalue()).decode()
                logger.debug("Screenshot captured: %dx%d", screenshot.size[0], screenshot.size[1])

                plan = self._plan_action_with_llava(task, img_data)
                if not plan:
                    self.append_text("[Wait] No action returned, retrying...\n", "warning")
                    consecutive_errors += 1
                    time.sleep(2)
                    continue

                action = plan.get('action', 'wait')
                why = plan.get('why', '')
                self._record_action_context(action, why)
                self.append_text(f"[AI] {why}\n", "ai")
                logger.info("Action determined: %s - %s", action, why)
                consecutive_errors = 0

                if action == 'done':
                    self.append_text("[Auto] Task Complete!\n", "success")
                    logger.info("Automation completed successfully at step %d", step)
                    break
                if action == 'fail':
                    self.append_text("[Auto] Marked as failed - stopping.\n", "error")
                    logger.error("Automation failed: %s", why)
                    break

                if action == 'click':
                    x, y = int(plan.get('x', 0)), int(plan.get('y', 0))
                    if self._validate_coordinates(x, y):
                        self.append_text(f"[Click] ({x},{y})\n", "action")
                        self._do_click(x, y)
                        self.last_action_type = 'click'
                    else:
                        self.append_text(f"[Skip] Click out of bounds: ({x},{y})\n", "error")
                        logger.warning("Click coordinates invalid: (%d,%d)", x, y)
                elif action == 'type':
                    text = plan.get('text', '')
                    self.append_text(f"[Type] {text[:40]}\n", "action")
                    self._do_type(text)
                    self.last_action_type = 'type'
                elif action == 'key':
                    key = plan.get('key', '')
                    self.append_text(f"[Key] {key}\n", "action")
                    self._do_key(key)
                    self.last_action_type = 'key'
                elif action == 'scroll':
                    amount = int(plan.get('amount', 0))
                    self.append_text(f"[Scroll] {amount}\n", "action")
                    self._do_scroll(amount)
                    self.last_action_type = 'scroll'
                else:
                    self.append_text("[Wait] Cooling down...\n", "info")
                    self.last_action_type = 'wait'

                cooldown = self._get_adaptive_cooldown(action)
                time.sleep(cooldown)

            except requests.exceptions.Timeout:
                err_msg = "[Error] LLaVA request timeout"
                self.append_text(f"{err_msg}\n", "error")
                logger.error(err_msg)
                consecutive_errors += 1
                time.sleep(3)
            except requests.exceptions.ConnectionError as e:
                err_msg = f"[Error] Cannot reach Ollama: {e}"
                self.append_text(f"{err_msg}\n", "error")
                logger.error(err_msg)
                consecutive_errors += 1
                time.sleep(3)
            except Exception as e:
                err_msg = f"[Error] {str(e)[:80]}"
                self.append_text(f"{err_msg}\n", "error")
                logger.exception("Automation loop exception")
                consecutive_errors += 1
                time.sleep(2)

            if consecutive_errors >= max_consecutive_errors:
                self.append_text(f"[Error] Too many errors ({consecutive_errors}) - stopping\n", "error")
                logger.error("Stopping automation due to %d consecutive errors", consecutive_errors)
                break

        self.automation_running = False
        logger.info("Automation loop completed at step %d", step)
        self.root.after(0, self._reset_auto_ui)
    
    def stop_automation(self):
        """Stop automation"""
        self.automation_running = False
        self.append_text("\n[Auto] Stopped\n", "action")
        self._reset_auto_ui()
    
    def _reset_auto_ui(self):
        self.start_auto_btn.config(state='normal')
        self.stop_auto_btn.config(state='disabled')
        self.auto_status.config(text="Automation: Idle", fg='#888888')

    def _plan_action_with_llava(self, task, img_data):
        """Call LLaVA 13B via Ollama with recent context to choose next action."""
        context_lines = [
            f"- {entry['action']}: {entry['why']}" for entry in self.recent_actions[-6:]
        ]
        context_block = "\n".join(context_lines) if context_lines else "(no prior actions)"
        width, height = self.screenshot_size or (0, 0)

        prompt = f"""
You are AuraOS Vision, an autonomous desktop agent. Goal: "{task}".
Screen size: {width}x{height}.
Recent actions:\n{context_block}
Choose the single best next action to move toward the goal.
Return ONLY one JSON object with keys: action, why, and the needed fields for that action.
Allowed actions:
- click: include integer x and y within screen bounds.
- type: include text.
- key: include key (e.g., enter, tab, esc, ctrl+l).
- scroll: include amount (positive scrolls down).
- wait: when loading.
- done: when goal achieved.
- fail: if blocked and human help needed.
"""

        raw = self._call_llava(prompt, [img_data])
        return self._extract_action_json(raw)

    def _call_llava(self, prompt, images_b64):
        if not HAS_REQUESTS:
            raise RuntimeError("requests is required for llava automation")

        payload = {
            "model": LLAVA_MODEL,
            "prompt": prompt,
            "images": images_b64,
            "stream": False,
        }
        url = f"{DEFAULT_OLLAMA_URL}/api/generate"
        logger.debug("Sending LLaVA request to %s", url)
        resp = requests.post(url, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")

    def _extract_action_json(self, raw_text):
        if not raw_text:
            return None
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    def _record_action_context(self, action, why):
        self.recent_actions.append({"action": action, "why": why, "ts": time.time()})
        self.recent_actions = self.recent_actions[-6:]
    
    def _validate_coordinates(self, x, y):
        """Validate click coordinates are within screen bounds"""
        if not self.screenshot_size:
            logger.warning("No screenshot size - cannot validate coordinates")
            return False
        
        width, height = self.screenshot_size
        if x < 0 or x > width or y < 0 or y > height:
            logger.warning("Coordinates out of bounds: (%d,%d) vs screen %dx%d", x, y, width, height)
            return False
        
        return True
    
    def _get_adaptive_cooldown(self, action_type):
        """Adaptive cooldown based on action type"""
        cooldowns = {
            'click': 1.5,     # Clicks are quick
            'type': 2.5,      # Typing needs time to register
            'key': 1.2,
            'scroll': 1.0,
            'wait': 1.0,      # Waiting is fastest
            'default': 2.0
        }
        return cooldowns.get(action_type, cooldowns['default'])
    
    def _do_click(self, x, y):
        """Execute click with error handling"""
        try:
            subprocess.run(
                ['xdotool', 'mousemove', str(x), str(y), 'click', '1'],
                check=True, env={**os.environ, 'DISPLAY': ':99'},
                timeout=5,
                capture_output=True
            )
            logger.debug("Click executed at (%d, %d)", x, y)
        except subprocess.TimeoutExpired:
            err_msg = "[Error] Click timeout"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
        except Exception as e:
            err_msg = f"[Error] Click failed: {e}"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)

    def _do_key(self, key):
        """Press a single key via xdotool."""
        try:
            subprocess.run(
                ['xdotool', 'key', '--clearmodifiers', key],
                check=True, env={**os.environ, 'DISPLAY': ':99'},
                timeout=5,
                capture_output=True
            )
            logger.debug("Key pressed: %s", key)
        except Exception as e:
            err_msg = f"[Error] Key press failed: {e}"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)

    def _do_scroll(self, amount):
        """Scroll using xdotool (positive = down)."""
        try:
            # xdotool button 4 = scroll up, 5 = scroll down
            button = '5' if amount >= 0 else '4'
            repeats = min(max(abs(amount) // 100, 1), 10)
            for _ in range(repeats):
                subprocess.run(
                    ['xdotool', 'click', button],
                    check=True, env={**os.environ, 'DISPLAY': ':99'},
                    timeout=3,
                    capture_output=True
                )
            logger.debug("Scrolled %s (%d steps)", button, repeats)
        except Exception as e:
            err_msg = f"[Error] Scroll failed: {e}"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
    
    def _do_type(self, text):
        """Execute typing with error handling"""
        try:
            subprocess.run(
                ['xdotool', 'type', '--clearmodifiers', text],
                check=True, env={**os.environ, 'DISPLAY': ':99'},
                timeout=10,
                capture_output=True
            )
            logger.debug("Typed %d characters", len(text))
        except subprocess.TimeoutExpired:
            err_msg = "[Error] Type timeout"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
        except Exception as e:
            err_msg = f"[Error] Type failed: {e}"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSVision(root)
    root.mainloop()
