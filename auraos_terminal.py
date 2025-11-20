#!/usr/bin/env python3
"""
AuraOS Terminal - Dual-Mode Application
Modes:
  1. AI Mode (Default): ChatGPT-like interface for automation tasks
     - Natural language requests (e.g., "open firefox", "make an excel sheet")
     - Auto-execution via ./auraos.sh automate
     - Full daemon integration
  
  2. Regular Mode: Standard terminal with AI file search
     - Shell command execution
     - AI-powered file search (prefix commands with "ai:" for smart search)
     - Command history navigation
"""
import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import shutil
import threading
import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path


class AuraOSTerminal:
    """Dual-mode terminal: AI mode (default) and Regular mode"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Terminal")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0a0e27')
        
        # State
        self.mode = "ai"  # "ai" or "regular"
        self.command_history = []
        self.history_index = -1
        self.is_processing = False
        
        self.setup_ui()
        self.log_event("STARTUP", "AuraOS Terminal initialized (AI mode)")
    
    def setup_ui(self):
        """Setup user interface"""
        # Top bar
        top_frame = tk.Frame(self.root, bg='#1a1e37', height=60)
        top_frame.pack(fill='x')
        
        # Mode toggle button
        self.mode_btn = tk.Button(
            top_frame, text="🔄 Switch to Regular", command=self.switch_mode,
            bg='#9cdcfe', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=12, pady=10
        )
        self.mode_btn.pack(side='left', padx=10, pady=8)
        
        # Title
        self.title_label = tk.Label(
            top_frame, text="⚡ AuraOS Terminal (AI Mode)", 
            font=('Arial', 14, 'bold'), fg='#00ff88', bg='#1a1e37'
        )
        self.title_label.pack(side='left', padx=20, pady=8)
        
        # Status
        self.status_label = tk.Label(
            top_frame, text="Ready", font=('Arial', 10),
            fg='#6db783', bg='#1a1e37'
        )
        self.status_label.pack(side='right', padx=20, pady=8)
        
        # Main content
        main_frame = tk.Frame(self.root, bg='#0a0e27')
        main_frame.pack(fill='both', expand=True)
        
        # Output display
        self.output_area = scrolledtext.ScrolledText(
            main_frame, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
            font=('Menlo', 11), insertbackground='#00d4ff',
            relief='flat', padx=15, pady=15
        )
        self.output_area.pack(fill='both', expand=True)
        self.output_area.config(state='disabled')
        
        # Configure text tags
        self._setup_text_tags()
        
        # Welcome message
        self.show_welcome()
        
        # Input frame
        input_frame = tk.Frame(self.root, bg='#1a1e37', height=80)
        input_frame.pack(fill='x')
        
        # Prompt
        self.prompt_label = tk.Label(
            input_frame, text="⚡ ", font=('Menlo', 12, 'bold'),
            fg='#00ff88', bg='#1a1e37'
        )
        self.prompt_label.pack(side='left', padx=(15, 0), pady=10)
        
        # Input field
        self.input_field = tk.Entry(
            input_frame, bg='#2d3547', fg='#ffffff',
            font=('Menlo', 12), insertbackground='#00d4ff',
            relief='flat', bd=0
        )
        self.input_field.pack(side='left', fill='both', expand=True, 
                              ipady=10, padx=(5, 10), pady=10)
        self.input_field.bind('<Return>', lambda e: self.execute())
        self.input_field.bind('<Up>', self.history_up)
        self.input_field.bind('<Down>', self.history_down)
        self.input_field.bind('<Escape>', lambda e: self.input_field.delete(0, tk.END))
        
        # Send button
        send_btn = tk.Button(
            input_frame, text="Send", command=self.execute,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=12, pady=6
        )
        send_btn.pack(side='right', padx=10, pady=10)
        
        # Focus input
        self.input_field.focus()
    
    def _setup_text_tags(self):
        """Setup text formatting tags"""
        tags = {
            "system": {"foreground": "#00d4ff", "font": ('Menlo', 11, 'bold')},
            "user": {"foreground": "#4ec9b0", "font": ('Menlo', 11, 'bold')},
            "ai": {"foreground": "#00ff88", "font": ('Menlo', 11, 'bold')},
            "output": {"foreground": "#d4d4d4", "font": ('Menlo', 10)},
            "error": {"foreground": "#f48771", "font": ('Menlo', 10, 'bold')},
            "success": {"foreground": "#6db783", "font": ('Menlo', 10, 'bold')},
            "info": {"foreground": "#9cdcfe", "font": ('Menlo', 10)},
            "warning": {"foreground": "#dcdcaa", "font": ('Menlo', 10, 'bold')},
        }
        for tag_name, config in tags.items():
            self.output_area.tag_config(tag_name, **config)
    
    def show_welcome(self):
        """Show welcome message based on mode"""
        self.output_area.config(state='normal')
        self.output_area.delete(1.0, tk.END)
        self.output_area.config(state='disabled')
        
        if self.mode == "ai":
            self.append("⚡ AuraOS Terminal - AI Mode\n", "system")
            self.append("ChatGPT-like Interface for Automation\n\n", "system")
            self.append("Examples of what you can ask:\n", "info")
            self.append("  • open firefox\n", "output")
            self.append("  • make an excel sheet with top 5 presidents by salary\n", "output")
            self.append("  • create a backup of important files\n", "output")
            self.append("  • find all files larger than 100MB\n", "output")
            self.append("  • install python dependencies\n", "output")
            self.append("  • download and extract the latest release\n\n", "output")
            self.append("Just describe what you want to do in plain English!\n", "success")
            self.append("Type 'help' for more information.\n", "info")
        else:
            self.append("$ AuraOS Terminal - Regular Mode\n", "system")
            self.append("Standard Terminal with AI File Search\n\n", "system")
            self.append("Commands:\n", "info")
            self.append("  $ regular shell commands work normally\n", "output")
            self.append("  ai: find all files suffixed by .txt\n", "output")
            self.append("  ai: find all files with more than 500 words\n", "output")
            self.append("  ai: search for python files in src/\n\n", "output")
            self.append("Type 'help' for more information.\n", "info")
    
    def switch_mode(self):
        """Switch between AI and Regular mode"""
        self.mode = "regular" if self.mode == "ai" else "ai"
        
        if self.mode == "ai":
            self.title_label.config(text="⚡ AuraOS Terminal (AI Mode)", fg='#00ff88')
            self.prompt_label.config(text="⚡ ", fg='#00ff88')
            self.mode_btn.config(text="🔄 Switch to Regular")
            self.log_event("MODE_SWITCH", "Switched to AI mode")
        else:
            self.title_label.config(text="$ AuraOS Terminal (Regular Mode)", fg='#4ec9b0')
            self.prompt_label.config(text="$ ", fg='#4ec9b0')
            self.mode_btn.config(text="🔄 Switch to AI")
            self.log_event("MODE_SWITCH", "Switched to Regular mode")
        
        self.show_welcome()
        self.input_field.focus()
    
    def execute(self):
        """Execute command or AI request"""
        if self.is_processing:
            return
        
        text = self.input_field.get().strip()
        if not text:
            return
        
        self.command_history.append(text)
        self.history_index = len(self.command_history)
        self.input_field.delete(0, tk.END)
        
        if self.mode == "ai":
            self.append(f"⚡ {text}\n", "ai")
            threading.Thread(target=self.execute_ai_task, args=(text,), daemon=True).start()
        else:
            self.append(f"$ {text}\n", "user")
            
            # Handle special commands
            if text.lower() == "help":
                self.show_regular_help()
            elif text.lower() == "exit":
                self.log_event("EXIT", "User closed terminal")
                self.root.quit()
            elif text.lower() == "clear":
                self.output_area.config(state='normal')
                self.output_area.delete(1.0, tk.END)
                self.output_area.config(state='disabled')
            elif text.lower().startswith("ai:"):
                # AI file search
                search_query = text[3:].strip()
                threading.Thread(target=self.execute_ai_search, args=(search_query,), daemon=True).start()
            else:
                # Regular shell command
                threading.Thread(target=self.execute_shell_command, args=(text,), daemon=True).start()
    
    def execute_ai_task(self, request_text):
        """Send request to the Vision Agent."""
        self.is_processing = True
        self.update_status("Processing with Vision Agent...", "#00ff88")
        self.append("⟳ Sending request to Vision Agent...\n", "info")
        
        try:
            # Try Vision Agent first
            response = requests.post(
                "http://localhost:8765/ask",
                json={"query": request_text},
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                executed = result.get("executed", [])
                self.append(f"✓ Agent executed {len(executed)} actions.\n", "success")
                for action in executed:
                    act = action.get("action", {})
                    self.append(f"  - {act}\n", "output")
                self.log_event("AI_SUCCESS", request_text)
            else:
                self.append(f"✗ Agent Error: {response.text}\n", "error")
                self.log_event("AI_ERROR", response.text)
                
        except Exception as e:
            self.append(f"✗ Connection failed: {e}\n", "error")
            self.append("  Is the GUI Agent running?\n", "warning")
            self.log_event("AI_EXCEPTION", str(e))
            
        self.is_processing = False
        self.update_status("Ready", "#6db783")
        self.input_field.focus()
                        self.append(f"✗ Error executing command: {e}\n\n", "error")
                        self.log_event("AI_ERROR", str(e))

                elif action == "advice":
                    # Show advice text
                    self.append(explanation + "\n\n", "info")
                    self.log_event("AI_ADVICE", request_text[:200])
                else:
                    # Ask user to clarify
                    self.append("✗ Could not map request to an automated action. Please rephrase.\n\n", "error")
                    self.log_event("AI_CLARIFY", request_text[:200])

            else:
                # Fallback to previous behavior: call auraos.sh or local handlers
                # But first, detect short chat/greetings and handle locally so we don't call auraos.sh
                rt = request_text.strip().lower()
                greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "how are you", "yo"]
                # If it's a short greeting or clearly not an automation request, reply locally
                if len(rt.split()) <= 4 and any(g in rt for g in greetings):
                    try:
                        resp = local_conversational_ai(request_text)
                        self.append(resp + "\n", "output")
                    except Exception:
                        self.append("I'm here — but couldn't form a reply right now.\n", "error")
                    self.update_status("Ready", "#6db783")
                    self.is_processing = False
                    return

                auraos_path = None
                local_path = os.path.join(os.getcwd(), "auraos.sh")
                if os.path.isfile(local_path) and os.access(local_path, os.X_OK):
                    auraos_path = local_path
                else:
                    auraos_path = shutil.which("auraos.sh")

                if auraos_path:
                    cmd = [auraos_path, "automate", request_text]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=120,
                        cwd=os.path.expanduser("~")
                    )
                else:
                    rt = request_text.lower()
                    if "open firefox" in rt or rt.strip() == "open firefox":
                        try:
                            subprocess.Popen(["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            self.append("✓ Launched Firefox\n", "success")
                            result = subprocess.CompletedProcess(args=["firefox"], returncode=0, stdout="Launched Firefox")
                        except Exception as e:
                            result = subprocess.CompletedProcess(args=["firefox"], returncode=1, stdout="", stderr=str(e))
                    else:
                        raise FileNotFoundError("auraos.sh not found and AI unavailable; cannot automate this request.")

                if result.stdout:
                    self.append(result.stdout, "output")

                if result.returncode == 0:
                    self.append("\n✓ Task completed successfully\n\n", "success")
                    self.log_event("AI_SUCCESS", request_text[:60])
                else:
                    if result.stderr:
                        self.append(f"\nError: {result.stderr}\n\n", "error")
                    self.append(f"✗ Exit code: {result.returncode}\n\n", "error")
                    self.log_event("AI_ERROR", f"{request_text[:60]} (exit: {result.returncode})")

            self.update_status("Ready", "#6db783")

        except Exception as e:
            self.append(f"✗ Error: {str(e)}\n\n", "error")
            self.update_status("Error", "#f48771")
            self.log_event("AI_ERROR", str(e))
        finally:
            self.is_processing = False
    
    def execute_ai_search(self, search_query):
        """Execute AI-powered file search"""
        try:
            self.is_processing = True
            self.update_status("Searching with AI...", "#9cdcfe")
            self.append(f"🔍 Searching for: {search_query}\n", "info")
            # Prefer auraos.sh if available otherwise run a local find as fallback
            auraos_path = shutil.which("auraos.sh") or os.path.join(os.getcwd(), "auraos.sh") if os.path.isfile(os.path.join(os.getcwd(), "auraos.sh")) else None
            if auraos_path:
                cmd = [auraos_path, "automate", f"find files: {search_query}"]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=60,
                    cwd=os.path.expanduser("~")
                )
            else:
                # Run a local find limited to user's home directory and return the first 200 matches
                try:
                    find_cmd = [
                        "bash", "-lc",
                        "find ~ -type f -iname '*%s*' 2>/dev/null | head -n 200" % search_query.replace("'","'\\''")
                    ]
                    result = subprocess.run(find_cmd, capture_output=True, text=True, timeout=60)
                except Exception as e:
                    result = subprocess.CompletedProcess(args=find_cmd, returncode=1, stdout="", stderr=str(e))
            
            if result.stdout:
                self.append(result.stdout, "output")
            
            if result.returncode == 0:
                self.append("\n✓ Search completed\n\n", "success")
                self.log_event("AI_SEARCH", search_query[:60])
            else:
                if result.stderr:
                    self.append(f"\nError: {result.stderr}\n\n", "error")
            
            self.update_status("Ready", "#6db783")
        
        except subprocess.TimeoutExpired:
            self.append("✗ Search timed out (60s limit)\n\n", "error")
            self.update_status("Error", "#f48771")
        except Exception as e:
            self.append(f"✗ Error: {str(e)}\n\n", "error")
            self.update_status("Error", "#f48771")
        finally:
            self.is_processing = False
    
    def execute_shell_command(self, command):
        """Execute regular shell command"""
        try:
            self.is_processing = True
            self.update_status("Running...", "#9cdcfe")
            
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, cwd=os.path.expanduser("~")
            )
            
            if result.stdout:
                self.append(result.stdout, "output")
            
            if result.returncode == 0:
                if not result.stdout:
                    self.append("✓ Success\n", "success")
                self.log_event("COMMAND", f"{command} (success)")
            else:
                if result.stderr:
                    self.append(result.stderr, "error")
                self.append(f"✗ Exit code: {result.returncode}\n", "error")
                self.log_event("COMMAND", f"{command} (exit: {result.returncode})")
            
            self.append("\n", "output")
            self.update_status("Ready", "#6db783")
        
        except subprocess.TimeoutExpired:
            self.append("✗ Command timed out (30s limit)\n\n", "error")
            self.update_status("Timeout", "#f48771")
        except Exception as e:
            self.append(f"✗ Error: {str(e)}\n\n", "error")
            self.update_status("Error", "#f48771")
        finally:
            self.is_processing = False
    
    def show_regular_help(self):
        """Show help for regular mode"""
        help_text = """
Regular Mode Help
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Commands:
  $ ls -la                    List files with details
  $ pwd                       Print working directory
  $ cd ~/projects             Change directory
  $ python script.py          Run Python script
  $ git status                Check git status
  $ help                      Show this help
  $ exit                      Close terminal

AI File Search (prefix with 'ai:'):
  ai: find all files suffixed by .txt
  ai: find all files with more than 500 words
  ai: find python files in src/
  ai: search for config files

Keyboard Shortcuts:
  ↑/↓ arrows                  Navigate history
  Escape                      Clear input
  Enter                       Execute command

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        self.append(help_text, "info")
    
    def append(self, text, tag="output"):
        """Append text to output area"""
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, text, tag)
        self.output_area.see(tk.END)
        self.output_area.config(state='disabled')
        self.root.update_idletasks()
    
    def update_status(self, text, color='#6db783'):
        """Update status label"""
        self.status_label.config(text=text, fg=color)
        self.root.update_idletasks()
    
    def history_up(self, event):
        """Navigate history up"""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.input_field.delete(0, tk.END)
            self.input_field.insert(0, self.command_history[self.history_index])
    
    def history_down(self, event):
        """Navigate history down"""
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input_field.delete(0, tk.END)
            self.input_field.insert(0, self.command_history[self.history_index])
        elif self.history_index == len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            self.input_field.delete(0, tk.END)
    
    def log_event(self, action, message):
        """Log event to file"""
        try:
            log_path = "/tmp/auraos_terminal.log"
            with open(log_path, "a") as f:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                f.write(f"[{ts}] {action}: {message}\n")
        except:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSTerminal(root)
    root.mainloop()
