#!/usr/bin/env python3
"""
AuraOS Terminal - Tri-Mode Application
Modes:
  1. AI Mode (Default): ChatGPT-like interface for automation tasks
     - Natural language requests (e.g., "open firefox", "make an excel sheet")
     - Auto-execution via ./auraos.sh automate
     - Full daemon integration
  
  2. Chat Mode: Direct conversation with Ollama
     - Chat with AI models running locally
     - No automation, just conversation
  
  3. Regular Mode: Standard terminal with AI file search
     - Shell command execution
     - AI-powered file search (prefix commands with "ai:" for smart search)
     - Command history navigation
"""
import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import shutil
import threading
import time
import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path

# Smart URL detection: use host gateway IP when running inside VM
def get_inference_url():
    """Get the correct inference server URL based on environment."""
    if os.path.exists("/opt/auraos"):
        # Running inside VM - use host gateway (192.168.2.1 for Multipass)
        return "http://192.168.2.1:8081"
    return "http://localhost:8081"

def get_agent_url():
    """Get the correct GUI agent URL based on environment."""
    # Agent always runs locally (inside VM or on host)
    return "http://localhost:8765"

INFERENCE_URL = get_inference_url()
AGENT_URL = get_agent_url()


class AuraOSTerminal:
    """Tri-mode terminal: AI mode (default), Chat mode, and Regular mode"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Terminal")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0a0e27')
        
        # State
        self.mode = "ai"  # "ai", "regular", or "chat"
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
        
        # Settings button (hamburger menu)
        settings_btn = tk.Button(
            top_frame, text="⚙️ Settings", command=self.show_settings,
            bg='#2d3547', fg='#ffffff', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=12, pady=10
        )
        settings_btn.pack(side='left', padx=5, pady=8)

        # Demo button for a polished, reproducible demo sequence
        demo_btn = tk.Button(
            top_frame, text="▶ Demo", command=self.start_demo,
            bg='#00bcd4', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=12, pady=10
        )
        demo_btn.pack(side='left', padx=5, pady=8)
        
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
        elif self.mode == "chat":
            self.append("💬 AuraOS Terminal - Chat Mode\n", "system")
            self.append("Direct Conversation with Ollama\n\n", "system")
            self.append("Chat with AI models running locally on your machine.\n", "info")
            self.append("Ensure Ollama is running with Farà-7B: OLLAMA_HOST=0.0.0.0 ollama serve\n\n", "warning")
            self.append("Examples:\n", "info")
            self.append("  • Hello, how are you?\n", "output")
            self.append("  • Explain quantum computing\n", "output")
            self.append("  • Write a Python function to sort a list\n\n", "output")
            self.append("Just type your message and press Enter!\n", "success")
        else:
            self.append("$ AuraOS Terminal - Regular Mode\n", "system")
            self.append("Standard Terminal with AI File Search\n\n", "system")
            self.append("Commands:\n", "info")
            self.append("  $ regular shell commands work normally\n", "output")
            self.append("  ai: find all files suffixed by .txt\n", "output")
            self.append("  ai: find all files with more than 500 words\n", "output")
            self.append("  ai: search for python files in src/\n\n", "output")
            self.append("(You can also type: 'ai <query>' without the colon)\n", "info")
            self.append("Type 'help' for more information.\n", "info")
    
    def switch_mode(self):
        """Cycle through AI, Chat, and Regular modes"""
        if self.mode == "ai":
            self.mode = "chat"
        elif self.mode == "chat":
            self.mode = "regular"
        else:
            self.mode = "ai"
        
        if self.mode == "ai":
            self.title_label.config(text="⚡ AuraOS Terminal (AI Mode)", fg='#00ff88')
            self.prompt_label.config(text="⚡ ", fg='#00ff88')
            self.mode_btn.config(text="🔄 Switch to Chat")
            self.log_event("MODE_SWITCH", "Switched to AI mode")
        elif self.mode == "chat":
            self.title_label.config(text="💬 AuraOS Terminal (Chat Mode)", fg='#dcdcaa')
            self.prompt_label.config(text="💬 ", fg='#dcdcaa')
            self.mode_btn.config(text="🔄 Switch to Regular")
            self.log_event("MODE_SWITCH", "Switched to Chat mode")
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
        elif self.mode == "chat":
            self.append(f"💬 {text}\n", "user")
            threading.Thread(target=self.execute_chat, args=(text,), daemon=True).start()
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
            elif text.lower().startswith("ai:") or text.lower().startswith("ai "):
                # AI file search — accept both 'ai: query' and 'ai query'
                if text.lower().startswith("ai:"):
                    search_query = text[3:].strip()
                else:
                    search_query = text[2:].strip()
                threading.Thread(target=self.execute_ai_search, args=(search_query,), daemon=True).start()
            else:
                # Regular shell command
                threading.Thread(target=self.execute_shell_command, args=(text,), daemon=True).start()
    
    def execute_ai_task(self, request_text):
        """Send request to the Vision Agent with smart fallback for common commands."""
        self.is_processing = True
        self.update_status("Processing...", "#00ff88")
        
        # Check for common commands that can be executed directly
        request_lower = request_text.lower().strip()
        
        # Direct execution for simple commands (when agent might be unavailable)
        direct_commands = {
            "open firefox": ["firefox"],
            "launch firefox": ["firefox"],
            "start firefox": ["firefox"],
            "open browser": ["firefox"],
            "open terminal": ["xfce4-terminal"],
            "open file manager": ["thunar"],
            "open files": ["thunar"],
        }
        
        # Check if this is a direct command we can handle
        for pattern, cmd in direct_commands.items():
            if pattern in request_lower:
                self.append(f"⟳ Executing: {' '.join(cmd)}...\n", "info")
                try:
                    env = os.environ.copy()
                    env["DISPLAY"] = env.get("DISPLAY", ":99")
                    subprocess.Popen(
                        cmd,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    self.append(f"✓ Launched {cmd[0]}\n", "success")
                    self.log_event("AI_DIRECT", f"Executed: {' '.join(cmd)}")
                    self.is_processing = False
                    self.update_status("Ready", "#6db783")
                    self.input_field.focus()
                    return
                except Exception as e:
                    self.append(f"⚠ Direct execution failed: {e}\n", "warning")
                    self.append("⟳ Trying via Vision Agent...\n", "info")
                break
        
        # Try Vision Agent for complex requests
        self.append("⟳ Sending request to Vision Agent...\n", "info")
        
        try:
            response = requests.post(
                "http://localhost:8765/ask",
                json={"query": request_text},
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                # Prefer structured fields: 'suggested' and 'executed'
                suggested = result.get("suggested", []) if isinstance(result, dict) else []
                executed = result.get("executed", []) if isinstance(result, dict) else []

                # Show suggested actions if present
                if suggested:
                    self.append(f"✓ Agent suggested {len(suggested)} actions.\n", "info")
                    for a in suggested:
                        self.append(f"  • {self.format_action(a)}\n", "output")

                # Show executed actions
                self.append(f"✓ Agent executed {len(executed)} actions.\n", "success")
                for action in executed:
                    self.append(f"  - {self.format_action(action)}\n", "output")

                # Persist structured action log for replay/demo
                try:
                    self.record_action_log(request_text, executed or suggested)
                except Exception:
                    pass

                self.log_event("AI_SUCCESS", request_text)
            else:
                self.append(f"✗ Agent Error: {response.text}\n", "error")
                self.log_event("AI_ERROR", response.text)
                
        except requests.exceptions.ConnectionError:
            self.append("✗ Cannot reach GUI Agent\n", "error")
            self.append("\n", "output")
            self.append("  The Vision Agent is not running.\n", "info")
            self.append("  \n", "output")
            self.append("  You can still use:\n", "warning")
            self.append("  • Switch to Regular mode for shell commands\n", "info")
            self.append("  • Switch to Chat mode for AI conversation\n", "info")
            self.append("  \n", "output")
            self.append("  To start the agent:\n", "info")
            self.append("  ./auraos.sh health\n\n", "info")
            self.log_event("AI_EXCEPTION", "Connection refused")
        except requests.exceptions.Timeout:
            self.append("✗ Request timed out (3 minutes)\n", "error")
            self.append("  Try a simpler request.\n\n", "info")
            self.log_event("AI_EXCEPTION", "Timeout")
        except Exception as e:
            self.append(f"✗ Unexpected error: {e}\n", "error")
            self.log_event("AI_EXCEPTION", str(e))
            
        self.is_processing = False
        self.update_status("Ready", "#6db783")
        self.input_field.focus()

    def format_action(self, action):
        """Return a human-friendly string for an action dict or simple value."""
        try:
            if isinstance(action, dict):
                # Common keys: action, type, text, amount, seconds, x, y
                # Accept either nested {'action': {...}} or direct dict
                act = action.get("action") if "action" in action and isinstance(action.get("action"), dict) else action
                if isinstance(act, dict):
                    atype = act.get("type") or act.get("action") or act.get("name")
                    parts = []
                    if atype:
                        parts.append(str(atype))
                    for k, v in act.items():
                        if k in ("type", "action", "name"): continue
                        parts.append(f"{k}={v}")
                    return "{" + ", ".join(parts) + "}"
                else:
                    return str(act)
            else:
                return str(action)
        except Exception:
            return str(action)

    def record_action_log(self, request_text, actions):
        """Append a JSON-line with timestamp, request, and actions for replay/export."""
        try:
            out = {
                "ts": datetime.now().isoformat(),
                "request": request_text,
                "actions": actions
            }
            path = "/tmp/auraos_terminal_actions.jsonl"
            with open(path, "a") as f:
                f.write(json.dumps(out, default=str) + "\n")
        except Exception:
            pass

    def start_demo(self):
        """Start an in-UI demo sequence in a background thread."""
        threading.Thread(target=self.run_demo_sequence, daemon=True).start()

    def run_demo_sequence(self):
        """Run a short demo sequence showing agent interactions."""
        seq = [
            "hi",
            "make an officelibre excel sheet with top 10 presidents' elections by popular vote",
            "create new excel sheet"
        ]
        try:
            self.update_status("Demo running...", "#00bcd4")
            for cmd in seq:
                # show user input
                self.input_field.delete(0, tk.END)
                self.input_field.insert(0, cmd)
                self.append(f"⚡ {cmd}\n", "ai")
                self.execute()
                # Pause to let agent process and for demo pacing
                time.sleep(3.5)
            self.append("\nDemo complete.\n", "success")
        except Exception as e:
            self.append(f"Demo error: {e}\n", "error")
        finally:
            self.update_status("Ready", "#6db783")

    def execute_chat(self, message):
        """Send message directly to inference server for chat."""
        self.is_processing = True
        self.update_status("Chatting with AI...", "#dcdcaa")
        self.append(f"⟳ Connecting to {INFERENCE_URL}...\n", "info")
        
        try:
            # Send to unified inference server /generate endpoint
            response = requests.post(
                f"{INFERENCE_URL}/generate",
                json={
                    "prompt": message
                },
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "").strip()
                if ai_response:
                    self.append(f"{ai_response}\n\n", "output")
                else:
                    self.append("(Empty response from model)\n\n", "warning")
                self.log_event("CHAT_SUCCESS", message)
            else:
                self.append(f"✗ Inference Server Error: {response.text}\n", "error")
                self.log_event("CHAT_ERROR", response.text)
                
        except requests.exceptions.ConnectionError:
            self.append(f"✗ Connection failed: Cannot reach inference server\n", "error")
            self.append(f"  URL: {INFERENCE_URL}\n", "info")
            self.append("  \n", "output")
            self.append("  Troubleshooting:\n", "warning")
            self.append("  1. On the HOST machine, start the inference server:\n", "info")
            self.append("     ./auraos.sh inference start\n", "info")
            self.append("  2. Make sure Ollama is running on the host\n", "info")
            self.append("  3. Check if server is listening: curl http://localhost:8081/health\n\n", "info")
            self.log_event("CHAT_EXCEPTION", "Connection refused")
        except requests.exceptions.Timeout:
            self.append(f"✗ Request timed out (3 minutes)\n", "error")
            self.append("  The AI model may be processing slowly.\n", "info")
            self.append("  Try a shorter message or check inference server status.\n\n", "info")
            self.log_event("CHAT_EXCEPTION", "Timeout")
        except Exception as e:
            self.append(f"✗ Unexpected error: {e}\n", "error")
            self.append("  Click '⚙️ Settings' for connection info.\n\n", "info")
            self.log_event("CHAT_EXCEPTION", str(e))
            
        self.is_processing = False
        self.update_status("Ready", "#6db783")
        self.input_field.focus()

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
    
    def show_settings(self):
        """Show settings dialog for configuring AI connections"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("AuraOS Terminal Settings")
        settings_window.geometry("600x500")
        settings_window.configure(bg='#1a1e37')
        
        # Title
        title = tk.Label(
            settings_window, text="⚙️ AuraOS Terminal Settings",
            font=('Arial', 16, 'bold'), fg='#00ff88', bg='#1a1e37'
        )
        title.pack(pady=20)
        
        # Info frame
        info_frame = tk.Frame(settings_window, bg='#0a0e27')
        info_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        info_text = scrolledtext.ScrolledText(
            info_frame, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
            font=('Menlo', 10), relief='flat', padx=15, pady=15
        )
        info_text.pack(fill='both', expand=True)
        
        # Configuration instructions
        config_text = """📡 AI Connection Configuration

The AuraOS Terminal has three modes:

1. AI Mode: Connects to GUI Agent for automation tasks
   • GUI Agent: http://localhost:8765/ask
   • Inference Server: http://localhost:8081 (auto-detects backends)

2. Chat Mode: Direct connection to Inference Server for conversation
   • Inference Server: http://localhost:8081/generate
   • Supports: llava:13b (via Ollama) or microsoft/Fara-7B (via Transformers)
   • Auto-detection: Tries Ollama first, falls back to Transformers

3. Regular Mode: Standard terminal with AI file search

Connection Status:
"""
        
        info_text.insert('1.0', config_text)
        
        # Check connection status
        try:
            response = requests.get("http://localhost:8765/health", timeout=2)
            if response.status_code == 200:
                info_text.insert(tk.END, "  ✓ GUI Agent: ONLINE\n", 'success')
            else:
                info_text.insert(tk.END, "  ✗ GUI Agent: ERROR\n", 'error')
        except:
            info_text.insert(tk.END, "  ✗ GUI Agent: OFFLINE\n", 'error')
        
        try:
            # Check inference server
            response = requests.get("http://localhost:8081/health", timeout=2)
            if response.status_code == 200:
                info_text.insert(tk.END, "  ✓ Inference Server: ONLINE\n", 'success')
            else:
                info_text.insert(tk.END, "  ✗ Inference Server: ERROR\n", 'error')
        except:
            info_text.insert(tk.END, "  ✗ Inference Server: OFFLINE\n\n", 'error')
            info_text.insert(tk.END, "Troubleshooting:\n", 'warning')
            info_text.insert(tk.END, "  1. Start inference server: python3 auraos_daemon/inference_server.py\n")
            info_text.insert(tk.END, "  2. Or use: ./auraos.sh inference start\n")
            info_text.insert(tk.END, "  3. Server auto-detects available models\n\n")
        
        info_text.insert(tk.END, "\nInference Server Configuration:\n", 'info')
        info_text.insert(tk.END, "  Chat Mode uses Inference Server on localhost:8081\n")
        info_text.insert(tk.END, "  AI Mode uses GUI Agent which connects to Inference Server\n")
        info_text.insert(tk.END, "  \n")
        info_text.insert(tk.END, "  Start the server with one of these:\n")
        info_text.insert(tk.END, "  1. Direct: python3 auraos_daemon/inference_server.py\n")
        info_text.insert(tk.END, "  2. Via script: ./auraos.sh inference start\n")
        info_text.insert(tk.END, "  \n")
        info_text.insert(tk.END, "  Backends (auto-detected):\n")
        info_text.insert(tk.END, "  • Ollama with llava:13b (if Ollama running and model available)\n")
        info_text.insert(tk.END, "  • Transformers with microsoft/Fara-7B (if torch/transformers installed)\n\n")
        
        info_text.insert(tk.END, "To configure models or API keys:\n", 'info')
        info_text.insert(tk.END, "  ./auraos.sh keys onboard\n")
        
        info_text.config(state='disabled')
        
        # Configure tags
        info_text.tag_config('success', foreground='#6db783', font=('Menlo', 10, 'bold'))
        info_text.tag_config('error', foreground='#f48771', font=('Menlo', 10, 'bold'))
        info_text.tag_config('warning', foreground='#dcdcaa', font=('Menlo', 10, 'bold'))
        info_text.tag_config('info', foreground='#9cdcfe', font=('Menlo', 10, 'bold'))
        
        # Close button
        close_btn = tk.Button(
            settings_window, text="Close", command=settings_window.destroy,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 11, 'bold'),
            relief='flat', cursor='hand2', padx=20, pady=10
        )
        close_btn.pack(pady=20)


if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSTerminal(root)
    root.mainloop()
