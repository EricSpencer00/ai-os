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
        self.automation_running = False
        
        # Set DISPLAY for VM
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":99"
        
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
        
        # Screenshot button - text symbols for compatibility
        self.screenshot_btn = tk.Button(
            btn_frame, text="[+] Capture",
            command=self.take_screenshot,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=8, pady=5
        )
        self.screenshot_btn.pack(side='left', padx=(0, 5))
        
        # Analyze button
        self.analyze_btn = tk.Button(
            btn_frame, text="[*] Analyze",
            command=self.analyze,
            bg='#00ff88', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=8, pady=5
        )
        self.analyze_btn.pack(side='left', padx=(0, 5))
        
        # Clear button
        self.clear_btn = tk.Button(
            btn_frame, text="[x]",
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
        self.append_text("[Vision] Ready - Capture then Analyze\n", "info")
        
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
            
        self.is_processing = True
        self.status_label.config(text="Capturing...", fg='#ffaa00')
        self.append_text("[+] Capturing...\n", "info")
        
        threading.Thread(target=self._take_screenshot, daemon=True).start()
        
    def _take_screenshot(self):
        """Take screenshot in background"""
        try:
            screenshot = ImageGrab.grab()
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            self.screenshot_data = base64.b64encode(img_byte_arr.getvalue()).decode()
            
            self.append_text(f"[OK] Captured {screenshot.size[0]}x{screenshot.size[1]}\n", "success")
        except Exception as e:
            self.append_text(f"[Error] {e}\n", "error")
            
        self.is_processing = False
        self.status_label.config(text="Ready", fg='#6db783')
        
    def analyze(self):
        """Analyze screenshot with AI"""
        if self.is_processing:
            return
        
        # Auto-capture if needed
        if not self.screenshot_data:
            self.append_text("[*] Auto-capturing...\n", "info")
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
            self.append_text("[*] Sending to AI...\n", "info")
            
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
            else:
                self.append_text(f"[Error] Server: {response.status_code}\n", "error")
                
        except requests.exceptions.ConnectionError:
            self.append_text(f"[Error] Cannot reach {INFERENCE_URL}\n", "error")
        except Exception as e:
            self.append_text(f"[Error] {str(e)}\n", "error")
            
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
        """Automation loop"""
        step = 0
        max_steps = 15
        
        while self.automation_running and step < max_steps:
            step += 1
            self.append_text(f"\n[Step {step}]\n", "action")
            
            try:
                # Capture screen
                if HAS_PIL:
                    screenshot = ImageGrab.grab()
                    buffer = io.BytesIO()
                    screenshot.save(buffer, format='PNG')
                    img_data = base64.b64encode(buffer.getvalue()).decode()
                else:
                    self.append_text("[Error] PIL required\n", "error")
                    break
                
                # Ask AI what to do
                payload = {
                    "model": "llava:13b",
                    "prompt": f'''Task: "{task}"
Look at this screen and determine ONE action to take.
Reply ONLY with JSON like:
{{"action":"click","x":500,"y":300,"why":"clicking button"}}
{{"action":"type","text":"hello","why":"typing text"}}
{{"action":"done","why":"task complete"}}
{{"action":"wait","why":"loading"}}''',
                    "images": [img_data],
                    "stream": False
                }
                
                # Use the vision /ask endpoint which accepts images and a query
                response = requests.post(f"{INFERENCE_URL}/ask", json={
                    "query": payload.get("prompt"),
                    "images": payload.get("images", []),
                    "parse_json": False
                }, timeout=60)
                
                if response.status_code == 200:
                    ai_text = response.json().get('response', '{}')
                    
                    # Parse JSON from response
                    try:
                        json_match = re.search(r'\{[^}]+\}', ai_text)
                        action_data = json.loads(json_match.group()) if json_match else {"action": "wait"}
                    except:
                        action_data = {"action": "wait", "why": "parse error"}
                    
                    action = action_data.get('action', 'wait')
                    why = action_data.get('why', '')
                    
                    self.append_text(f"[AI] {why}\n", "ai")
                    
                    if action == 'done':
                        self.append_text("[Auto] Complete!\n", "success")
                        break
                    elif action == 'click':
                        x, y = action_data.get('x', 0), action_data.get('y', 0)
                        self.append_text(f"[Click] ({x},{y})\n", "action")
                        self._do_click(x, y)
                    elif action == 'type':
                        text = action_data.get('text', '')
                        self.append_text(f"[Type] {text[:20]}...\n", "action")
                        self._do_type(text)
                    
                    time.sleep(2)
                else:
                    self.append_text(f"[Error] {response.status_code}\n", "error")
                    time.sleep(3)
                    
            except Exception as e:
                self.append_text(f"[Error] {str(e)[:40]}\n", "error")
                time.sleep(3)
        
        self.automation_running = False
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
    
    def _do_click(self, x, y):
        """Execute click"""
        try:
            subprocess.run(
                ['xdotool', 'mousemove', str(x), str(y), 'click', '1'],
                check=True, env={**os.environ, 'DISPLAY': ':99'}
            )
        except Exception as e:
            self.append_text(f"[Error] Click: {e}\n", "error")
    
    def _do_type(self, text):
        """Execute typing"""
        try:
            subprocess.run(
                ['xdotool', 'type', '--clearmodifiers', text],
                check=True, env={**os.environ, 'DISPLAY': ':99'}
            )
        except Exception as e:
            self.append_text(f"[Error] Type: {e}\n", "error")

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSVision(root)
    root.mainloop()
