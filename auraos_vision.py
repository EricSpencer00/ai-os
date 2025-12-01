#!/usr/bin/env python3
"""
AuraOS Vision - Cluely-style AI Screen Assistant
A transparent overlay that can:
1. See your screen
2. Understand what's happening
3. Execute actions on your behalf
4. Answer questions about what's visible
"""
import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import os
import sys
import json
import base64
import io
import time
import requests
from datetime import datetime

# Try to import PIL for screenshots
try:
    from PIL import Image, ImageTk, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("PIL not available - install with: pip install pillow")

# Try to import pyautogui for actions
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False
    print("PyAutoGUI not available - install with: pip install pyautogui")


def get_inference_url():
    """Get inference server URL based on environment."""
    if os.path.exists("/opt/auraos"):
        return "http://192.168.2.1:8081"
    return "http://localhost:8081"


INFERENCE_URL = get_inference_url()


class AuraOSVision:
    """Cluely-style AI Vision Assistant"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Vision")
        self.root.geometry("500x600")
        self.root.configure(bg='#1a1a2e')
        
        # Make window stay on top
        self.root.attributes('-topmost', True)
        
        # State
        self.is_watching = False
        self.last_screenshot = None
        self.action_history = []
        
        self.setup_ui()
        self.log("AuraOS Vision ready. Click 'Start Watching' to begin.")
        
    def setup_ui(self):
        """Create the UI"""
        # Title
        title_frame = tk.Frame(self.root, bg='#1a1a2e')
        title_frame.pack(fill='x', padx=20, pady=15)
        
        title = tk.Label(
            title_frame,
            text="👁️ AuraOS Vision",
            font=('Arial', 20, 'bold'),
            fg='#00ff88',
            bg='#1a1a2e'
        )
        title.pack(side='left')
        
        # Status indicator
        self.status_dot = tk.Label(
            title_frame,
            text="●",
            font=('Arial', 16),
            fg='#666666',
            bg='#1a1a2e'
        )
        self.status_dot.pack(side='right')
        
        # Control buttons
        btn_frame = tk.Frame(self.root, bg='#1a1a2e')
        btn_frame.pack(fill='x', padx=20, pady=10)
        
        self.watch_btn = tk.Button(
            btn_frame,
            text="▶ Start Watching",
            command=self.toggle_watching,
            bg='#00ff88',
            fg='#1a1a2e',
            font=('Arial', 12, 'bold'),
            relief='flat',
            padx=20,
            pady=10,
            cursor='hand2'
        )
        self.watch_btn.pack(side='left', padx=5)
        
        screenshot_btn = tk.Button(
            btn_frame,
            text="📸 Screenshot",
            command=self.take_screenshot,
            bg='#3a3a5e',
            fg='#ffffff',
            font=('Arial', 11),
            relief='flat',
            padx=15,
            pady=10,
            cursor='hand2'
        )
        screenshot_btn.pack(side='left', padx=5)
        
        # Input area
        input_frame = tk.Frame(self.root, bg='#1a1a2e')
        input_frame.pack(fill='x', padx=20, pady=10)
        
        input_label = tk.Label(
            input_frame,
            text="What would you like me to do?",
            font=('Arial', 11),
            fg='#888888',
            bg='#1a1a2e'
        )
        input_label.pack(anchor='w')
        
        self.input_entry = tk.Entry(
            input_frame,
            font=('Arial', 13),
            bg='#2a2a4e',
            fg='#ffffff',
            insertbackground='#00ff88',
            relief='flat',
            bd=0
        )
        self.input_entry.pack(fill='x', pady=(5, 0), ipady=12)
        self.input_entry.bind('<Return>', lambda e: self.execute_request())
        
        # Quick actions
        quick_frame = tk.Frame(self.root, bg='#1a1a2e')
        quick_frame.pack(fill='x', padx=20, pady=10)
        
        quick_label = tk.Label(
            quick_frame,
            text="Quick Actions:",
            font=('Arial', 10),
            fg='#666666',
            bg='#1a1a2e'
        )
        quick_label.pack(anchor='w')
        
        quick_btns_frame = tk.Frame(quick_frame, bg='#1a1a2e')
        quick_btns_frame.pack(fill='x', pady=5)
        
        quick_actions = [
            ("What's on screen?", "describe what you see on screen"),
            ("Click here", "click at the center of the screen"),
            ("Open Firefox", "open firefox browser"),
            ("Type hello", "type 'Hello World'"),
        ]
        
        for label, action in quick_actions:
            btn = tk.Button(
                quick_btns_frame,
                text=label,
                command=lambda a=action: self.quick_action(a),
                bg='#2a2a4e',
                fg='#aaaaaa',
                font=('Arial', 9),
                relief='flat',
                padx=10,
                pady=5,
                cursor='hand2'
            )
            btn.pack(side='left', padx=2)
        
        # Output/Log area
        log_frame = tk.Frame(self.root, bg='#1a1a2e')
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        log_label = tk.Label(
            log_frame,
            text="Activity Log:",
            font=('Arial', 10),
            fg='#666666',
            bg='#1a1a2e'
        )
        log_label.pack(anchor='w')
        
        self.log_text = tk.Text(
            log_frame,
            font=('Menlo', 10),
            bg='#0a0a1e',
            fg='#cccccc',
            relief='flat',
            wrap='word',
            padx=10,
            pady=10
        )
        self.log_text.pack(fill='both', expand=True, pady=5)
        self.log_text.config(state='disabled')
        
        # Configure tags
        self.log_text.tag_config('success', foreground='#00ff88')
        self.log_text.tag_config('error', foreground='#ff6b6b')
        self.log_text.tag_config('info', foreground='#4ecdc4')
        self.log_text.tag_config('action', foreground='#ffe66d')
        
        # Execute button
        self.exec_btn = tk.Button(
            self.root,
            text="🚀 Execute Request",
            command=self.execute_request,
            bg='#00ff88',
            fg='#1a1a2e',
            font=('Arial', 12, 'bold'),
            relief='flat',
            padx=20,
            pady=12,
            cursor='hand2'
        )
        self.exec_btn.pack(fill='x', padx=20, pady=(0, 20))
        
        # Focus input
        self.input_entry.focus()
    
    def log(self, message, tag='info'):
        """Add message to log"""
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert('end', f"[{timestamp}] ", 'info')
        self.log_text.insert('end', f"{message}\n", tag)
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        self.root.update_idletasks()
    
    def toggle_watching(self):
        """Toggle screen watching"""
        self.is_watching = not self.is_watching
        if self.is_watching:
            self.watch_btn.config(text="⏹ Stop Watching", bg='#ff6b6b')
            self.status_dot.config(fg='#00ff88')
            self.log("Started watching screen...", 'success')
            self.watch_loop()
        else:
            self.watch_btn.config(text="▶ Start Watching", bg='#00ff88')
            self.status_dot.config(fg='#666666')
            self.log("Stopped watching.", 'info')
    
    def watch_loop(self):
        """Periodic screenshot capture while watching"""
        if self.is_watching:
            self.take_screenshot(silent=True)
            self.root.after(5000, self.watch_loop)  # Every 5 seconds
    
    def take_screenshot(self, silent=False):
        """Capture screenshot"""
        if not HAS_PIL:
            self.log("PIL not installed - cannot take screenshots", 'error')
            return None
        
        try:
            # Try different screenshot methods
            screenshot = None
            
            # Method 1: Use scrot on Linux
            if sys.platform == 'linux':
                try:
                    subprocess.run(['scrot', '/tmp/auraos_screen.png', '-o'], 
                                   capture_output=True, timeout=5)
                    screenshot = Image.open('/tmp/auraos_screen.png')
                except:
                    pass
            
            # Method 2: Use ImageGrab (works on macOS and Windows)
            if screenshot is None:
                try:
                    screenshot = ImageGrab.grab()
                except:
                    pass
            
            # Method 3: Use pyautogui
            if screenshot is None and HAS_PYAUTOGUI:
                try:
                    screenshot = pyautogui.screenshot()
                except:
                    pass
            
            if screenshot:
                self.last_screenshot = screenshot
                if not silent:
                    self.log(f"Screenshot captured ({screenshot.size[0]}x{screenshot.size[1]})", 'success')
                return screenshot
            else:
                if not silent:
                    self.log("Could not capture screenshot", 'error')
                return None
                
        except Exception as e:
            if not silent:
                self.log(f"Screenshot error: {e}", 'error')
            return None
    
    def quick_action(self, action):
        """Execute a quick action"""
        self.input_entry.delete(0, 'end')
        self.input_entry.insert(0, action)
        self.execute_request()
    
    def execute_request(self):
        """Execute the user's request"""
        request = self.input_entry.get().strip()
        if not request:
            return
        
        self.log(f"Request: {request}", 'action')
        self.input_entry.delete(0, 'end')
        
        # Run in background thread
        threading.Thread(target=self._process_request, args=(request,), daemon=True).start()
    
    def _process_request(self, request):
        """Process request with AI"""
        request_lower = request.lower()
        
        # Handle simple direct commands first
        if 'click' in request_lower:
            self._do_click(request_lower)
            return
        
        if 'type' in request_lower or 'write' in request_lower:
            self._do_type(request)
            return
        
        if 'open firefox' in request_lower or 'open browser' in request_lower:
            self._do_open_app('firefox')
            return
        
        if 'open terminal' in request_lower:
            self._do_open_app('xfce4-terminal')
            return
        
        if 'describe' in request_lower or "what's on" in request_lower or 'what is on' in request_lower:
            self._describe_screen()
            return
        
        # For complex requests, use AI
        self._ai_request(request)
    
    def _do_click(self, request):
        """Perform click action"""
        if not HAS_PYAUTOGUI:
            self.log("PyAutoGUI not available for clicking", 'error')
            return
        
        try:
            # Parse coordinates if provided
            import re
            coords = re.findall(r'(\d+)\s*,?\s*(\d+)', request)
            if coords:
                x, y = int(coords[0][0]), int(coords[0][1])
            else:
                # Click center of screen
                screen_size = pyautogui.size()
                x, y = screen_size[0] // 2, screen_size[1] // 2
            
            pyautogui.click(x, y)
            self.log(f"Clicked at ({x}, {y})", 'success')
        except Exception as e:
            self.log(f"Click failed: {e}", 'error')
    
    def _do_type(self, request):
        """Type text"""
        if not HAS_PYAUTOGUI:
            self.log("PyAutoGUI not available for typing", 'error')
            return
        
        try:
            # Extract text to type (between quotes or after 'type')
            import re
            match = re.search(r"['\"](.+?)['\"]", request)
            if match:
                text = match.group(1)
            else:
                # Get text after 'type' or 'write'
                text = re.sub(r'^.*(type|write)\s*', '', request, flags=re.IGNORECASE).strip()
            
            if text:
                pyautogui.write(text, interval=0.05)
                self.log(f"Typed: '{text}'", 'success')
            else:
                self.log("No text to type", 'error')
        except Exception as e:
            self.log(f"Type failed: {e}", 'error')
    
    def _do_open_app(self, app):
        """Open an application"""
        try:
            env = os.environ.copy()
            env['DISPLAY'] = env.get('DISPLAY', ':99')
            subprocess.Popen([app], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log(f"Opened {app}", 'success')
        except Exception as e:
            self.log(f"Failed to open {app}: {e}", 'error')
    
    def _describe_screen(self):
        """Describe what's on screen using AI"""
        self.log("Analyzing screen...", 'info')
        
        screenshot = self.take_screenshot(silent=True)
        if not screenshot:
            self.log("Cannot analyze - no screenshot available", 'error')
            return
        
        # Convert to base64
        try:
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Send to inference server
            response = requests.post(
                f"{INFERENCE_URL}/ask",
                json={
                    "query": "Describe what you see on this computer screen. Be specific about any windows, applications, or content visible.",
                    "images": [img_b64]
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                description = result.get('response', 'No description available')
                self.log(f"Screen: {description}", 'success')
            else:
                self.log(f"AI error: {response.status_code}", 'error')
                
        except requests.exceptions.ConnectionError:
            self.log(f"Cannot reach AI server at {INFERENCE_URL}", 'error')
            self.log("Start it with: ./auraos.sh inference start", 'info')
        except Exception as e:
            self.log(f"Analysis error: {e}", 'error')
    
    def _ai_request(self, request):
        """Send complex request to AI for planning"""
        self.log("Consulting AI...", 'info')
        
        # Take fresh screenshot
        screenshot = self.take_screenshot(silent=True)
        
        try:
            images = []
            if screenshot:
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                images.append(base64.b64encode(buffer.getvalue()).decode('utf-8'))
            
            prompt = f"""You are an AI assistant controlling a computer. The user wants: "{request}"

Based on the screen (if visible), output a JSON list of actions to perform.
Supported actions:
- {{"action": "click", "x": 100, "y": 200}}
- {{"action": "type", "text": "hello"}}
- {{"action": "key", "key": "enter"}}
- {{"action": "scroll", "amount": -3}}
- {{"action": "wait", "seconds": 1}}

Output ONLY the JSON list, nothing else. Example: [{{"action": "click", "x": 100, "y": 100}}]"""
            
            response = requests.post(
                f"{INFERENCE_URL}/ask",
                json={
                    "query": prompt,
                    "images": images,
                    "parse_json": True
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                actions = result.get('actions', [])
                
                if not actions:
                    # Try to parse from response text
                    resp_text = result.get('response', '')
                    try:
                        actions = json.loads(resp_text)
                    except:
                        self.log(f"AI response: {resp_text[:200]}", 'info')
                        return
                
                # Execute actions
                self._execute_actions(actions)
            else:
                self.log(f"AI error: {response.status_code}", 'error')
                
        except requests.exceptions.ConnectionError:
            self.log(f"Cannot reach AI at {INFERENCE_URL}", 'error')
        except Exception as e:
            self.log(f"AI request error: {e}", 'error')
    
    def _execute_actions(self, actions):
        """Execute a list of AI-generated actions"""
        if not HAS_PYAUTOGUI:
            self.log("PyAutoGUI not available - cannot execute actions", 'error')
            return
        
        if not isinstance(actions, list):
            actions = [actions]
        
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            
            act_type = action.get('action', action.get('type', ''))
            
            try:
                if act_type == 'click':
                    x, y = action.get('x', 0), action.get('y', 0)
                    pyautogui.click(x, y)
                    self.log(f"  [{i+1}] Clicked ({x}, {y})", 'action')
                    
                elif act_type == 'type':
                    text = action.get('text', '')
                    pyautogui.write(text, interval=0.03)
                    self.log(f"  [{i+1}] Typed: '{text}'", 'action')
                    
                elif act_type == 'key':
                    key = action.get('key', '')
                    pyautogui.press(key)
                    self.log(f"  [{i+1}] Pressed: {key}", 'action')
                    
                elif act_type == 'scroll':
                    amount = action.get('amount', 0)
                    pyautogui.scroll(amount)
                    self.log(f"  [{i+1}] Scrolled: {amount}", 'action')
                    
                elif act_type == 'wait':
                    seconds = action.get('seconds', 1)
                    time.sleep(seconds)
                    self.log(f"  [{i+1}] Waited: {seconds}s", 'action')
                
                time.sleep(0.3)  # Brief pause between actions
                
            except Exception as e:
                self.log(f"  [{i+1}] Action failed: {e}", 'error')
        
        self.log("Actions completed.", 'success')


def main():
    # Set DISPLAY for VM environment
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':99'
    
    root = tk.Tk()
    app = AuraOSVision(root)
    root.mainloop()


if __name__ == "__main__":
    main()
