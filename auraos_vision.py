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
import sys
from pathlib import Path

# Set DISPLAY early before importing any X11-dependent modules
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":99"
if "XAUTHORITY" not in os.environ:
    # Try common locations for .Xauthority
    xauth_paths = [
        os.path.expanduser("~/.Xauthority"),
        "/home/ubuntu/.Xauthority",
        "/home/auraos/.Xauthority",
        "/root/.Xauthority"
    ]
    for path in xauth_paths:
        if os.path.exists(path) or os.path.isfile(path):
            os.environ["XAUTHORITY"] = path
            break
    else:
        # Fallback to home directory
        os.environ["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")

# Optional imports with detailed fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

try:
    from PIL import Image, ImageChops, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None
    ImageChops = None
    ImageDraw = None

try:
    import pyautogui
    HAS_PYAUTOGUI = True
    pyautogui.FAILSAFE = False
except ImportError:
    HAS_PYAUTOGUI = False
    pyautogui = None
except Exception as e:
    # Catch any exception during import (e.g., DISPLAY not found)
    HAS_PYAUTOGUI = False
    pyautogui = None

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

def check_dependencies():
    """Check if critical dependencies are available and log status."""
    issues = []
    
    if not HAS_PIL:
        issues.append("PIL/Pillow not installed")
    if not HAS_PYAUTOGUI:
        issues.append("pyautogui not installed")
    if not HAS_REQUESTS:
        issues.append("requests not installed")
    
    if issues:
        logger.warning("Missing dependencies: %s", ", ".join(issues))
        logger.warning("Install with: pip3 install pillow pyautogui requests")
    else:
        logger.info("All dependencies available")
    
    return len(issues) == 0

def get_inference_url():
    """Get the correct inference server URL based on environment."""
    if os.path.exists("/opt/auraos"):
        return "http://192.168.2.1:8081"
    return "http://localhost:8081"

INFERENCE_URL = get_inference_url()

class AuraOSVision:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Vision")
        self.root.geometry("340x550")
        self.root.configure(bg='#0a0e27')
        self.root.resizable(True, True)
        
        self.is_processing = False
        self.screenshot_data = None
        self.screenshot_size = None
        self.automation_running = False
        self.last_action_type = None
        
        # Set DISPLAY for VM - prefer :0 over :99
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":0"
        
        # Check dependencies early
        check_dependencies()
        
        logger.info("AuraOS Vision initialized - Inference URL: %s", INFERENCE_URL)
        logger.info("Dependencies - PIL: %s, pyautogui: %s, requests: %s", HAS_PIL, HAS_PYAUTOGUI, HAS_REQUESTS)
        
        self.setup_ui()
        
        # Vision is a sidebar utility window - let it be a normal window
        # Don't try to make it desktop type or it gets hidden behind everything
        try:
            self.root.attributes('-type', 'utility')
        except Exception:
            pass  # Window manager may not support this, that's ok
        
    def setup_ui(self):
        # Title bar (compact)
        title_frame = tk.Frame(self.root, bg='#0a0e27')
        title_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        title = tk.Label(
            title_frame, text="AuraOS Vision",
            font=('Arial', 14, 'bold'), fg='#00ff88', bg='#0a0e27'
        )
        title.pack(side='left')
        
        self.status_label = tk.Label(
            title_frame, text="Ready",
            font=('Arial', 10), fg='#6db783', bg='#0a0e27'
        )
        self.status_label.pack(side='right')
        
        # Quick action buttons (compact row)
        btn_frame = tk.Frame(self.root, bg='#0a0e27')
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        # Screenshot button
        self.screenshot_btn = tk.Button(
            btn_frame, text="📷 Capture",
            command=self.take_screenshot,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=8, pady=5
        )
        self.screenshot_btn.pack(side='left', padx=(0, 5))
        
        # Analyze button
        self.analyze_btn = tk.Button(
            btn_frame, text="🤖 Analyze",
            command=self.analyze,
            bg='#00ff88', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=8, pady=5
        )
        self.analyze_btn.pack(side='left', padx=(0, 5))
        
        # Clear button
        self.clear_btn = tk.Button(
            btn_frame, text="✖️",
            command=self.clear_output,
            bg='#2d3547', fg='#ffffff', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=8, pady=5
        )
        self.clear_btn.pack(side='left')
        
        # Output area
        output_frame = tk.Frame(self.root, bg='#0a0e27')
        output_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.output_area = scrolledtext.ScrolledText(
            output_frame, wrap=tk.WORD, bg='#1a1f3c', fg='#d4d4d4',
            font=('Consolas', 10), relief='flat', height=12
        )
        self.output_area.pack(fill='both', expand=True)
        self.output_area.config(state='disabled')
        
        # Tags
        self.output_area.tag_config('info', foreground='#9cdcfe')
        self.output_area.tag_config('success', foreground='#6db783')
        self.output_area.tag_config('error', foreground='#f48771')
        self.output_area.tag_config('ai', foreground='#00d4ff')
        self.output_area.tag_config('action', foreground='#ffaa00')
        
        # Welcome
        self.append_text("👁️ Ready - Capture then Analyze\n", "info")
        
        # Separator
        sep = tk.Frame(self.root, bg='#2d3547', height=2)
        sep.pack(fill='x', padx=10, pady=5)
        
        # Cluely Automation Section
        auto_label = tk.Label(
            self.root, text="Cluely Automation",
            font=('Arial', 12, 'bold'), fg='#ff7f50', bg='#0a0e27'
        )
        auto_label.pack(anchor='w', padx=10)
        
        # Task input
        task_frame = tk.Frame(self.root, bg='#0a0e27')
        task_frame.pack(fill='x', padx=10, pady=5)
        
        self.task_entry = tk.Entry(
            task_frame, font=('Arial', 10), bg='#1a1f3c', fg='#ffffff',
            insertbackground='#00ff88', relief='flat'
        )
        self.task_entry.pack(fill='x', ipady=5)
        self.task_entry.insert(0, "Describe task for AI...")
        self.task_entry.bind('<FocusIn>', self._clear_placeholder)
        
        # Automation buttons
        auto_btn_frame = tk.Frame(self.root, bg='#0a0e27')
        auto_btn_frame.pack(fill='x', padx=10, pady=5)
        
        self.start_auto_btn = tk.Button(
            auto_btn_frame, text="▶ Start",
            command=self.start_automation,
            bg='#ff7f50', fg='#ffffff', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=8, pady=5
        )
        self.start_auto_btn.pack(side='left', padx=(0, 5))
        
        self.stop_auto_btn = tk.Button(
            auto_btn_frame, text="⏸ Stop",
            command=self.stop_automation,
            bg='#ff4444', fg='#ffffff', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=8, pady=5, state='disabled'
        )
        self.stop_auto_btn.pack(side='left')
        
        # Status bar
        self.auto_status = tk.Label(
            self.root, text="Automation: Idle",
            font=('Arial', 9), fg='#888888', bg='#0a0e27'
        )
        self.auto_status.pack(side='bottom', pady=5)
    
    def _clear_placeholder(self, event):
        if self.task_entry.get() == "Describe task for AI...":
            self.task_entry.delete(0, 'end')
        
    def append_text(self, text, tag='info'):
        """Append text to output area"""
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, text, tag)
        self.output_area.see(tk.END)
        self.output_area.config(state='disabled')
        self.root.update_idletasks()
        
    def clear_output(self):
        """Clear output area"""
        self.output_area.config(state='normal')
        self.output_area.delete(1.0, tk.END)
        self.output_area.config(state='disabled')
        self.append_text("[Cleared]\n", "info")
        
    def take_screenshot(self):
        """Take a screenshot"""
        if self.is_processing:
            return
        
        if not HAS_PIL:
            self.append_text("[Error] PIL not installed\n", "error")
            return
        
        if not HAS_PYAUTOGUI:
            self.append_text("[Error] pyautogui not installed\n", "error")
            return
            
        self.is_processing = True
        self.status_label.config(text="Capturing...", fg='#ffaa00')
        self.append_text("[+] Capturing...\n", "info")
        
        threading.Thread(target=self._take_screenshot, daemon=True).start()
        
    def _take_screenshot(self):
        """Take screenshot in background using scrot (most reliable method)"""
        try:
            # Use scrot directly - it's the most reliable method
            temp_path = f"/tmp/auraos_vision_screenshot_{int(time.time())}.png"
            
            result = subprocess.run(
                ["scrot", temp_path],
                capture_output=True,
                timeout=5,
                env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":99")}
            )
            
            if result.returncode != 0:
                # If scrot fails, try pyautogui as fallback
                try:
                    screenshot = pyautogui.screenshot()
                    self.append_text("[+] Using pyautogui fallback\n", "info")
                except Exception as e:
                    raise Exception(f"Both scrot and pyautogui failed: {e}")
            else:
                # Load the screenshot from scrot
                if not os.path.exists(temp_path):
                    raise Exception(f"scrot created no file at {temp_path}")
                
                screenshot = Image.open(temp_path)
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
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
            logger.error(err_msg, exc_info=True)
            
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
        
        if not HAS_PIL or not HAS_PYAUTOGUI or not HAS_REQUESTS:
            self.append_text("[Error] Missing dependencies for automation\n", "error")
            return
        
        self.automation_running = True
        self.start_auto_btn.config(state='disabled')
        self.stop_auto_btn.config(state='normal')
        self.auto_status.config(text="Automation: Running", fg='#00ff88')
        self.append_text(f"\n[Auto] Task: {task}\n", "action")
        
        threading.Thread(target=self._automation_loop, args=(task,), daemon=True).start()
    
    def _automation_loop(self, task):
        """Automation loop with resilience features"""
        step = 0
        max_steps = 15
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        logger.info("Starting automation loop for task: %s", task)
        
        while self.automation_running and step < max_steps:
            step += 1
            self.append_text(f"\n[Step {step}/{max_steps}]\n", "action")
            
            try:
                # Capture full screen
                screenshot = pyautogui.screenshot()
                self.screenshot_size = screenshot.size
                
                logger.debug("Full desktop captured: %dx%d", screenshot.size[0], screenshot.size[1])
                self.append_text(f"[Screen] Captured: {screenshot.size[0]}x{screenshot.size[1]}\n", "info")
                
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                img_data = base64.b64encode(buffer.getvalue()).decode()
                
                # Improved automation prompt
                prompt = f'''You are an AI assistant controlling a desktop computer. Your task:

TASK: "{task}"

RULES:
1. You see the ENTIRE desktop - interact with applications OTHER than "AuraOS Vision"
2. Return ONLY ONE JSON action per response
3. Valid actions:
   {{"action":"click","x":500,"y":300,"why":"reason for clicking here"}}
   {{"action":"type","text":"hello","why":"reason for typing this"}}
   {{"action":"done","why":"task completed successfully"}}
   {{"action":"wait","why":"waiting for something to load"}}

Current step {step}/{max_steps}. Respond with ONLY JSON, nothing else.'''
                
                response = requests.post(
                    f"{INFERENCE_URL}/ask",
                    json={
                        "query": prompt,
                        "images": [img_data],
                        "parse_json": False
                    },
                    timeout=60
                )
                
                if response.status_code != 200:
                    err_msg = f"[Error] Server returned {response.status_code}"
                    self.append_text(f"{err_msg}\n", "error")
                    logger.error(err_msg)
                    consecutive_errors += 1
                    time.sleep(3)
                    continue
                
                ai_text = response.json().get('response', '{}')
                logger.debug("AI response: %s", ai_text[:150])
                
                # Parse JSON from response
                action_data = self._parse_json_response(ai_text)
                
                action = action_data.get('action', 'wait')
                why = action_data.get('why', '')
                
                self.append_text(f"[AI] {why}\n", "ai")
                logger.info("Action: %s - %s", action, why)
                
                consecutive_errors = 0
                
                if action == 'done':
                    self.append_text("[Auto] Task Complete!\n", "success")
                    logger.info("Automation completed at step %d", step)
                    break
                    
                elif action == 'click':
                    x, y = action_data.get('x', 0), action_data.get('y', 0)
                    if self._validate_coordinates(x, y):
                        self.append_text(f"[Click] ({x},{y})\n", "action")
                        logger.info("Executing click at (%d, %d)", x, y)
                        self._do_click(x, y)
                        self.last_action_type = 'click'
                    else:
                        self.append_text(f"[Skip] Invalid coords: ({x},{y})\n", "error")
                        logger.warning("Invalid coordinates: (%d, %d)", x, y)
                        
                elif action == 'type':
                    text = action_data.get('text', '')
                    if text:
                        self.append_text(f"[Type] {text[:30]}...\n", "action")
                        logger.info("Executing type: %s", text[:30])
                        self._do_type(text)
                        self.last_action_type = 'type'
                    else:
                        self.append_text("[Skip] Empty text\n", "error")
                    
                else:  # wait or unknown
                    self.append_text("[Wait] Pausing...\n", "info")
                    self.last_action_type = 'wait'
                
                # Adaptive cooldown
                cooldown = self._get_adaptive_cooldown(action)
                time.sleep(cooldown)
                
            except requests.exceptions.Timeout:
                err_msg = "[Error] AI timeout (60s)"
                self.append_text(f"{err_msg}\n", "error")
                logger.error(err_msg)
                consecutive_errors += 1
                time.sleep(3)
                
            except requests.exceptions.ConnectionError as e:
                err_msg = f"[Error] Connection failed"
                self.append_text(f"{err_msg}\n", "error")
                logger.error("Connection error: %s", e)
                consecutive_errors += 1
                time.sleep(3)
                
            except Exception as e:
                err_msg = f"[Error] {str(e)[:50]}"
                self.append_text(f"{err_msg}\n", "error")
                logger.exception("Automation exception")
                consecutive_errors += 1
                time.sleep(2)
            
            if consecutive_errors >= max_consecutive_errors:
                self.append_text(f"[Error] Too many errors - stopping\n", "error")
                logger.error("Stopping: %d consecutive errors", consecutive_errors)
                break
        
        if step >= max_steps and self.automation_running:
            self.append_text(f"[Auto] Max steps reached\n", "action")
            logger.info("Stopped: max steps")
        
        self.automation_running = False
        logger.info("Automation loop ended at step %d", step)
        self.root.after(0, self._reset_auto_ui)
    
    def _parse_json_response(self, text):
        """Parse JSON from AI response with fallback"""
        try:
            # Try to find JSON object in response
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.warning("No JSON found in: %s", text[:80])
                return {"action": "wait", "why": "no JSON"}
        except json.JSONDecodeError as e:
            logger.warning("JSON parse error: %s", e)
            return {"action": "wait", "why": "parse error"}
    
    def stop_automation(self):
        """Stop automation"""
        self.automation_running = False
        self.append_text("\n[Auto] Stopped\n", "action")
        logger.info("Automation stopped by user")
        self._reset_auto_ui()
    
    def _reset_auto_ui(self):
        """Reset automation UI state"""
        self.start_auto_btn.config(state='normal')
        self.stop_auto_btn.config(state='disabled')
        self.auto_status.config(text="Automation: Idle", fg='#888888')
    
    def _validate_coordinates(self, x, y):
        """Validate click coordinates"""
        if not self.screenshot_size:
            logger.warning("No screenshot size available")
            return False
        
        width, height = self.screenshot_size
        valid = 0 <= x <= width and 0 <= y <= height
        
        if not valid:
            logger.warning("Coords out of bounds: (%d,%d) vs %dx%d", x, y, width, height)
        
        return valid
    
    def _get_adaptive_cooldown(self, action_type):
        """Get cooldown based on action type"""
        cooldowns = {
            'click': 1.5,
            'type': 2.5,
            'wait': 1.0,
            'done': 0.5,
            'default': 2.0
        }
        return cooldowns.get(action_type, cooldowns['default'])
    
    def _check_xdotool(self):
        """Check if xdotool is available"""
        import shutil
        return shutil.which('xdotool') is not None
    
    def _do_click(self, x, y):
        """Execute click with fallback"""
        # Try pyautogui first
        if HAS_PYAUTOGUI:
            try:
                pyautogui.moveTo(x, y, duration=0.1)
                pyautogui.click(x, y)
                logger.debug("Click via pyautogui at (%d, %d)", x, y)
                return True
            except Exception as e:
                logger.warning("pyautogui click failed: %s", e)
        
        # Fallback to xdotool
        if not self._check_xdotool():
            self.append_text("[Error] No click method available\n", "error")
            logger.error("Neither pyautogui nor xdotool available")
            return False

        try:
            env = os.environ.copy()
            env['DISPLAY'] = env.get('DISPLAY', ':0')
            
            cmd = ['xdotool', 'mousemove', str(x), str(y), 'click', '1']
            result = subprocess.run(cmd, env=env, timeout=5, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.debug("Click via xdotool at (%d, %d)", x, y)
                return True
            else:
                logger.error("xdotool failed: %s", result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("xdotool timeout")
            return False
        except Exception as e:
            logger.error("xdotool error: %s", e)
            return False
    
    def _do_type(self, text):
        """Execute typing with fallback"""
        if not text:
            return
            
        # Try pyautogui first
        if HAS_PYAUTOGUI:
            try:
                pyautogui.write(text, interval=0.05)
                logger.debug("Typed %d chars via pyautogui", len(text))
                return True
            except Exception as e:
                logger.warning("pyautogui type failed: %s", e)
        
        # Fallback to xdotool
        if not self._check_xdotool():
            self.append_text("[Error] No typing method available\n", "error")
            logger.error("Neither pyautogui nor xdotool available")
            return False
            
        try:
            env = os.environ.copy()
            env['DISPLAY'] = env.get('DISPLAY', ':0')
            
            subprocess.run(
                ['xdotool', 'type', '--clearmodifiers', text],
                env=env,
                timeout=10,
                capture_output=True,
                check=True
            )
            logger.debug("Typed %d chars via xdotool", len(text))
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("xdotool type timeout")
            return False
        except Exception as e:
            logger.error("xdotool type error: %s", e)
            return False

    def _verify_click_coordinates(self, x, y, save_prefix='/tmp/vision_click'):
        """Debug helper: verify click coordinates with before/after screenshots"""
        try:
            if not HAS_PYAUTOGUI or not HAS_PIL:
                return {"ok": False, "reason": "missing_dependencies"}

            before = pyautogui.screenshot()
            before.save(f"{save_prefix}_before.png")

            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.click(x, y)
            time.sleep(0.5)

            after = pyautogui.screenshot()
            after.save(f"{save_prefix}_after.png")

            # Compute difference
            diff = ImageChops.difference(before, after).convert('L')
            bbox = diff.getbbox()

            debug_img = after.copy()
            draw = ImageDraw.Draw(debug_img)

            # Draw crosshair at requested position
            draw.line((x-10, y, x+10, y), fill=(0, 255, 0), width=2)
            draw.line((x, y-10, x, y+10), fill=(0, 255, 0), width=2)

            details = {"ok": True, "requested": (x, y), "bbox": bbox}

            if bbox:
                cx = (bbox[0] + bbox[2]) // 2
                cy = (bbox[1] + bbox[3]) // 2
                dx = cx - x
                dy = cy - y
                details.update({"center": (cx, cy), "offset": (dx, dy)})
                draw.rectangle(bbox, outline=(255, 0, 0), width=2)
            else:
                details.update({"center": None, "offset": None})

            debug_img.save(f"{save_prefix}_debug.png")
            logger.info("Click verification: %s", details)
            return details

        except Exception as e:
            logger.exception("Click verification failed")
            return {"ok": False, "reason": str(e)}


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AuraOS Vision')
    parser.add_argument('--verify-click', nargs=2, metavar=('X', 'Y'), 
                       help='Verify click coordinates', type=int)
    args = parser.parse_args()

    try:
        if args.verify_click:
            # Verification mode
            x, y = args.verify_click
            root = tk.Tk()
            root.withdraw()
            app = AuraOSVision(root)
            result = app._verify_click_coordinates(x, y)
            print(json.dumps(result, indent=2))
            return 0

        # Normal GUI mode
        root = tk.Tk()
        app = AuraOSVision(root)
        
        logger.info("AuraOS Vision started successfully")
        print("AuraOS Vision ready - logs at ~/.auraos/logs/vision.log")
        
        root.mainloop()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        print(f"ERROR: {e}")
        print("Check ~/.auraos/logs/vision.log for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())