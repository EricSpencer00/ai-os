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
from PIL import ImageChops, ImageDraw

# Optional imports with detailed fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

try:
    import pyautogui
    HAS_PYAUTOGUI = True
    # Set display early for screenshot
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":99"
    pyautogui.FAIL_SAFE = False
except ImportError:
    HAS_PYAUTOGUI = False
    pyautogui = None
except Exception as e:
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
        self.root.geometry("340x550")  # Compact sidebar size
        self.root.configure(bg='#0a0e27')
        self.root.resizable(True, True)
        
        self.is_processing = False
        self.screenshot_data = None
        self.screenshot_size = None
        self.automation_running = False
        self.last_action_type = None  # Track action type for adaptive cooldown
        
        # Set DISPLAY for VM
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":99"
        
        # Check dependencies early
        check_dependencies()
        
        logger.info("AuraOS Vision initialized - Inference URL: %s", INFERENCE_URL)
        logger.info("Dependencies - PIL: %s, pyautogui: %s, requests: %s", HAS_PIL, HAS_PYAUTOGUI, HAS_REQUESTS)
        
        self.setup_ui()
        
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
        
        # Screenshot button - with emoji icon
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
            auto_btn_frame, text="[>] Start",
            command=self.start_automation,
            bg='#ff7f50', fg='#ffffff', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=8, pady=5
        )
        self.start_auto_btn.pack(side='left', padx=(0, 5))
        
        self.stop_auto_btn = tk.Button(
            auto_btn_frame, text="[||] Stop",
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
        """Take screenshot in background using pyautogui (works on Linux with X11)"""
        try:
            # Use pyautogui.screenshot() which works on Linux with DISPLAY set
            screenshot = pyautogui.screenshot()
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
                # Capture FULL screen (entire desktop, not just this window)
                if not HAS_PIL or not HAS_PYAUTOGUI:
                    self.append_text("[Error] PIL and pyautogui required\n", "error")
                    logger.error("PIL or pyautogui not available")
                    break
                
                screenshot = pyautogui.screenshot()
                self.screenshot_size = screenshot.size
                
                # Log captured size for debugging
                logger.debug("Full desktop captured: %dx%d", screenshot.size[0], screenshot.size[1])
                self.append_text(f"[Screen] Captured full desktop: {screenshot.size[0]}x{screenshot.size[1]}\n", "info")
                
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                img_data = base64.b64encode(buffer.getvalue()).decode()
                
                # Improved automation prompt with full desktop context
                prompt = f'''You are an AI assistant controlling a desktop computer screen. Your task is to help the user accomplish:

TASK: "{task}"

IMPORTANT INSTRUCTIONS:
1. You are looking at the ENTIRE desktop screen with multiple windows/applications
2. Do NOT interact with the "AuraOS Vision" application window itself (that's just the control panel)
3. Focus on completing the task in OTHER applications on the desktop (Terminal, Browser, Files, etc.)
4. When you see text input fields or UI elements in other apps, that's where you should click and type
5. Return exactly ONE of these JSON actions:
   {{"action":"click","x":500,"y":300,"why":"clicking the Firefox icon to open browser"}}
   {{"action":"type","text":"hello","why":"typing text into the currently focused field"}}
   {{"action":"done","why":"task has been completed successfully"}}
   {{"action":"wait","why":"page is loading, need to wait for content"}}

RESPOND ONLY WITH JSON, nothing else. Example valid responses:
{{"action":"click","x":640,"y":360,"why":"opening Firefox to search"}}
{{"action":"type","text":"search query","why":"entering search text"}}
{{"action":"done","why":"search results are now displayed"}}
'''
                
                # Send to inference server with full screen context and improved prompt
                response = requests.post(
                    f"{INFERENCE_URL}/ask",
                    json={
                        "query": prompt,
                        "images": [img_data],  # Pass the full desktop screenshot
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
                
                # Parse JSON from response with fallback
                action_data = {"action": "wait"}
                try:
                    json_match = re.search(r'\{[^}]+\}', ai_text)
                    if json_match:
                        action_data = json.loads(json_match.group())
                    else:
                        logger.warning("No JSON found in response: %s", ai_text[:80])
                except json.JSONDecodeError as e:
                    logger.warning("JSON parse failed: %s", e)
                    action_data = {"action": "wait", "why": "parse error"}
                
                action = action_data.get('action', 'wait')
                why = action_data.get('why', '')
                
                self.append_text(f"[AI] {why}\n", "ai")
                logger.info("Action determined: %s - %s", action, why)
                
                consecutive_errors = 0  # Reset error counter on success
                
                if action == 'done':
                    self.append_text("[Auto] Task Complete!\n", "success")
                    logger.info("Automation completed successfully at step %d", step)
                    break
                    
                elif action == 'click':
                    x, y = action_data.get('x', 0), action_data.get('y', 0)
                    if self._validate_coordinates(x, y):
                        self.append_text(f"[Click] ({x},{y})\n", "action")
                        logger.info("Executing click at (%d, %d)", x, y)
                        self._do_click(x, y)
                        self.last_action_type = 'click'
                    else:
                        self.append_text(f"[Skip] Click out of bounds: ({x},{y})\n", "error")
                        logger.warning("Click coordinates invalid: (%d, %d)", x, y)
                        
                elif action == 'type':
                    text = action_data.get('text', '')
                    self.append_text(f"[Type] {text[:20]}...\n", "action")
                    logger.info("Executing type: %s", text[:30])
                    self._do_type(text)
                    self.last_action_type = 'type'
                    
                else:  # wait or unknown
                    self.append_text(f"[Wait] Pausing...\n", "info")
                    self.last_action_type = 'wait'
                
                # Adaptive cooldown
                cooldown = self._get_adaptive_cooldown(action)
                time.sleep(cooldown)
                
            except requests.exceptions.Timeout:
                err_msg = "[Error] AI request timeout (60s)"
                self.append_text(f"{err_msg}\n", "error")
                logger.error(err_msg)
                consecutive_errors += 1
                time.sleep(3)
                
            except requests.exceptions.ConnectionError as e:
                err_msg = f"[Error] Cannot reach inference server: {e}"
                self.append_text(f"{err_msg}\n", "error")
                logger.error(err_msg)
                consecutive_errors += 1
                time.sleep(3)
                
            except Exception as e:
                err_msg = f"[Error] {str(e)[:50]}"
                self.append_text(f"{err_msg}\n", "error")
                logger.exception("Automation loop exception")
                consecutive_errors += 1
                time.sleep(2)
            
            # Exit if too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                self.append_text(f"[Error] Too many errors ({consecutive_errors}) - stopping\n", "error")
                logger.error("Stopping automation due to %d consecutive errors", consecutive_errors)
                break
        
        # Final status
        if step >= max_steps and self.automation_running:
            self.append_text(f"[Auto] Reached max steps ({max_steps})\n", "action")
            logger.info("Automation stopped: max steps reached")
        
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
            'wait': 1.0,      # Waiting is fastest
            'default': 2.0
        }
        return cooldowns.get(action_type, cooldowns['default'])
    
    def _check_xdotool(self):
        """Check if xdotool is available"""
        import shutil
        return shutil.which('xdotool') is not None
    
    def _do_click(self, x, y):
        """Execute click with error handling - uses pyautogui as fallback"""
        # Try pyautogui first (more reliable)
        if HAS_PYAUTOGUI:
            try:
                # Move to coordinate then click - do a small retry loop
                attempts = 3
                for i in range(attempts):
                    try:
                        pyautogui.moveTo(x, y, duration=0.05)
                        pyautogui.click(x, y)
                        logger.debug("Click executed at (%d, %d) via pyautogui (attempt %d)", x, y, i+1)
                        return True
                    except Exception as inner_e:
                        logger.warning("pyautogui click attempt %d failed: %s", i+1, inner_e)
                        time.sleep(0.15)
                logger.warning("pyautogui click failed after %d attempts", attempts)
            except Exception as e:
                logger.warning("pyautogui click failed: %s, trying xdotool", e)
        
        # Fallback to xdotool: use absolute move + click and include X env vars
        if not self._check_xdotool():
            err_msg = "[Error] xdotool not found and pyautogui failed"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
            return False

        try:
            env = os.environ.copy()
            # Respect existing DISPLAY/XAUTHORITY if present, else default to :99
            env['DISPLAY'] = env.get('DISPLAY', ':99')
            if 'XAUTHORITY' not in env:
                env['XAUTHORITY'] = '/home/auraos/.Xauthority'

            # Try a couple of xdotool clicks to be robust
            for attempt in range(2):
                cmd = ['xdotool', 'mousemove', str(x), str(y), 'click', '1']
                res = subprocess.run(cmd, check=False, env=env, timeout=6, capture_output=True, text=True)
                if res.returncode == 0:
                    logger.debug("Click executed at (%d, %d) via xdotool (attempt %d)", x, y, attempt+1)
                    return True
                else:
                    logger.warning("xdotool attempt %d failed: rc=%s out=%s err=%s", attempt+1, res.returncode, res.stdout, res.stderr)
                    time.sleep(0.15)

            err_msg = "[Error] xdotool click attempts failed"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
            return False
        except subprocess.TimeoutExpired:
            err_msg = "[Error] Click timeout"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
            return False
        except Exception as e:
            err_msg = f"[Error] Click failed: {e}"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
            return False
    
    def _do_type(self, text):
        """Execute typing with error handling - uses pyautogui as fallback"""
        # Try pyautogui first (more reliable)
        if HAS_PYAUTOGUI:
            try:
                pyautogui.typewrite(text, interval=0.02)
                logger.debug("Typed %d characters via pyautogui", len(text))
                return
            except Exception as e:
                logger.warning("pyautogui type failed: %s, trying xdotool", e)
        
        # Fallback to xdotool
        if not self._check_xdotool():
            err_msg = "[Error] xdotool not found and pyautogui failed"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
            return
            
        try:
            subprocess.run(
                ['xdotool', 'type', '--clearmodifiers', text],
                check=True, env={**os.environ, 'DISPLAY': ':99'},
                timeout=10,
                capture_output=True
            )
            logger.debug("Typed %d characters via xdotool", len(text))
        except subprocess.TimeoutExpired:
            err_msg = "[Error] Type timeout"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)
        except Exception as e:
            err_msg = f"[Error] Type failed: {e}"
            self.append_text(f"{err_msg}\n", "error")
            logger.error(err_msg)

    def _verify_click_coordinates(self, x, y, save_prefix='/tmp/vision_click'):
        """Debug helper: capture before/after screenshots around a click and compute diff.

        Saves: {save_prefix}_before.png, {save_prefix}_after.png, {save_prefix}_debug.png
        Returns a dict with bbox and offset information.
        """
        try:
            if not HAS_PYAUTOGUI or not HAS_PIL:
                return {"ok": False, "reason": "missing_dependencies"}

            # Ensure we have a recent screenshot size
            before = pyautogui.screenshot()
            before.save(f"{save_prefix}_before.png")

            # Perform a single click using our normal routine but without retries to exercise exact behaviour
            try:
                pyautogui.moveTo(x, y, duration=0.05)
                pyautogui.click(x, y)
            except Exception as e:
                logger.warning("_verify_click_coordinates: pyautogui click error: %s", e)

            time.sleep(0.35)

            after = pyautogui.screenshot()
            after.save(f"{save_prefix}_after.png")

            # Compute difference bbox
            diff = ImageChops.difference(before, after).convert('L')
            bbox = diff.getbbox()  # (left, upper, right, lower)

            debug_img = after.copy()
            draw = ImageDraw.Draw(debug_img)

            # Draw expected coordinate crosshair
            cross_color = (0, 255, 0)
            draw.line((x-10, y, x+10, y), fill=cross_color)
            draw.line((x, y-10, x, y+10), fill=cross_color)

            details = {"ok": True, "requested": (x, y), "bbox": bbox}

            if bbox:
                cx = (bbox[0] + bbox[2]) // 2
                cy = (bbox[1] + bbox[3]) // 2
                dx = cx - x
                dy = cy - y
                details.update({"center": (cx, cy), "offset": (dx, dy)})
                # Draw bbox in red
                draw.rectangle(bbox, outline=(255, 0, 0), width=2)
                draw.ellipse((cx-5, cy-5, cx+5, cy+5), outline=(255,0,0), width=2)
            else:
                details.update({"center": None, "offset": None})

            debug_img.save(f"{save_prefix}_debug.png")

            logger.info("Click verify details: %s", details)
            return details

        except Exception as e:
            logger.exception("_verify_click_coordinates failed: %s", e)
            return {"ok": False, "reason": str(e)}

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = AuraOSVision(root)
        
        # Show startup status
        logger.info("AuraOS Vision started successfully")
        print("AuraOS Vision ready - check ~/.auraos/logs/vision.log for details")
        
        root.mainloop()
    except Exception as e:
        logger.critical("Failed to start AuraOS Vision: %s", e, exc_info=True)
        print(f"ERROR: Failed to start Vision app: {e}")
        print("Check ~/.auraos/logs/vision.log for details")
        raise
