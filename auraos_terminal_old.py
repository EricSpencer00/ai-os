#!/usr/bin/env python3
"""
AuraOS Terminal - English to Bash GUI with Resilient Error Recovery
Tkinter GUI for converting English to bash commands with intelligent fallbacks
"""
import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import sys
import os
import requests
import re

# Smart URL detection: use host gateway IP when running inside VM
def get_inference_url():
    """Get the correct inference server URL based on environment."""
    if os.path.exists("/opt/auraos"):
        return "http://192.168.2.1:8081"
    return "http://localhost:8081"

INFERENCE_URL = get_inference_url()

# Common error recovery patterns
ERROR_RECOVERY_PATTERNS = {
    "not found": {
        "keywords": ["not found", "command not found", "no such file"],
        "recovery": "suggest_install"
    },
    "permission denied": {
        "keywords": ["permission denied", "access denied"],
        "recovery": "suggest_sudo"
    },
    "file exists": {
        "keywords": ["file exists", "already exists", "exists"],
        "recovery": "suggest_force"
    },
    "no such directory": {
        "keywords": ["no such directory", "cannot access"],
        "recovery": "suggest_create_dir"
    }
}

# Tool availability cache
TOOL_CACHE = {}

class AuraOSTerminal:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Terminal")
        self.root.geometry("900x700")
        self.root.configure(bg='#0a0e27')
        
        self.is_processing = False
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        self.original_request = None
        self.setup_ui()
        
    def setup_ui(self):
        # Title Bar
        title_frame = tk.Frame(self.root, bg='#1a1e37', height=60)
        title_frame.pack(fill='x')
        
        title = tk.Label(
            title_frame, text="⚡ English to Bash Terminal",
            font=('Arial', 16, 'bold'), fg='#00ff88', bg='#1a1e37'
        )
        title.pack(side='left', padx=20, pady=15)
        
        self.status_label = tk.Label(
            title_frame, text="Ready", font=('Arial', 10),
            fg='#6db783', bg='#1a1e37'
        )
        self.status_label.pack(side='right', padx=20, pady=15)
        
        # Output Area
        output_frame = tk.Frame(self.root, bg='#0a0e27')
        output_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        output_label = tk.Label(
            output_frame, text="Output:", font=('Arial', 10),
            fg='#9cdcfe', bg='#0a0e27'
        )
        output_label.pack(anchor='w')
        
        self.output_area = scrolledtext.ScrolledText(
            output_frame, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
            font=('Menlo', 10), relief='flat', padx=10, pady=10
        )
        self.output_area.pack(fill='both', expand=True, pady=(5, 15))
        self.output_area.config(state='disabled')
        
        # Configure tags
        self.output_area.tag_config('info', foreground='#9cdcfe')
        self.output_area.tag_config('success', foreground='#6db783')
        self.output_area.tag_config('error', foreground='#f48771')
        self.output_area.tag_config('command', foreground='#00ff88')
        
        # Input Area
        input_frame = tk.Frame(self.root, bg='#1a1e37')
        input_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        prompt = tk.Label(
            input_frame, text="You:", font=('Menlo', 12, 'bold'),
            fg='#00ff88', bg='#1a1e37'
        )
        prompt.pack(side='left', padx=(0, 10))
        
        self.input_field = tk.Entry(
            input_frame, bg='#2d3547', fg='#ffffff',
            font=('Menlo', 12), insertbackground='#00d4ff',
            relief='flat', bd=0
        )
        self.input_field.pack(side='left', fill='both', expand=True, ipady=10)
        self.input_field.bind('<Return>', lambda e: self.process())
        
        # Buttons
        btn_frame = tk.Frame(input_frame, bg='#1a1e37')
        btn_frame.pack(side='right', padx=(10, 0))
        
        send_btn = tk.Button(
            btn_frame, text="Send", command=self.process,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=20, pady=8
        )
        send_btn.pack(side='left', padx=5)
        
        clear_btn = tk.Button(
            btn_frame, text="Clear", command=self.clear_output,
            bg='#2d3547', fg='#ffffff', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=20, pady=8
        )
        clear_btn.pack(side='left', padx=5)
        
        # Welcome
        self.append_text("⚡ AuraOS Terminal - English to Bash\n", "info")
        self.append_text("Convert natural language to bash commands\n\n", "info")
        self.append_text("Examples:\n", "info")
        self.append_text("  • show me all files\n", "command")
        self.append_text("  • find python files\n", "command")
        self.append_text("  • how much disk space\n", "command")
        self.append_text("  • list large files\n\n", "command")
        
        self.input_field.focus()
        
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
        
    def process(self):
        """Process user input"""
        if self.is_processing:
            return
            
        text = self.input_field.get().strip()
        if not text:
            return
            
        self.input_field.delete(0, tk.END)
        self.append_text(f"\nYou: {text}\n", "command")
        self.is_processing = True
        self.status_label.config(text="Converting...", fg='#dcdcaa')
        
        threading.Thread(target=self._convert_and_execute, args=(text,), daemon=True).start()
        
    def _convert_and_execute(self, text):
        """Convert English to bash and execute with error recovery"""
        self.original_request = text
        self.recovery_attempts = 0
        self._execute_with_recovery(text)
            # Convert to bash
            prompt = f"""You are a bash command generator. Convert this English request to a SINGLE bash command.
Request: {text}

Rules:
- Output ONLY the bash command, nothing else
- No explanations, no markdown, no code fences
- If you cannot convert it, reply: CANNOT_CONVERT
- Make the command safe
- Use standard Unix utilities

Command:"""
            
            self.append_text("[?] Converting to bash...\n", "info")
            
            response = requests.post(
                f"{INFERENCE_URL}/generate",
                json={"prompt": prompt},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                command = result.get("response", "").strip()
                command = command.split('\n')[0].strip()
                
                if command and "CANNOT_CONVERT" not in command and len(command) < 500:
                    self.append_text(f"📝 Command: {command}\n", "command")
                    
                    # Execute
                    self.append_text("\n[Settings] Executing...\n", "info")
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=os.path.expanduser("~")
                    )
                    
                    if result.stdout:
                        self.append_text(f"\n{result.stdout}", "info")
                    
                    if result.returncode == 0:
                        self.append_text("[OK] Command executed successfully\n", "success")
                    else:
                        if result.stderr:
                            self.append_text(f"Error: {result.stderr}\n", "error")
                        self.append_text(f"Exit code: {result.returncode}\n", "error")
                else:
                    self.append_text("[X] Could not convert request\n", "error")
            else:
                self.append_text(f"[X] Server error: {response.text[:100]}\n", "error")
                
        except subprocess.TimeoutExpired:
            self.append_text("[X] Command timed out\n", "error")
        except requests.exceptions.ConnectionError:
            self.append_text("[X] Cannot reach inference server\n", "error")
            self.append_text(f"  URL: {INFERENCE_URL}\n", "info")
        except Exception as e:
            self.append_text(f"[X] Error: {str(e)}\n", "error")
            
        self.is_processing = False
        self.status_label.config(text="Ready", fg='#6db783')

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSTerminal(root)
    root.mainloop()
