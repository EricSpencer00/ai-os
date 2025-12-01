#!/usr/bin/env python3
"""
AuraOS Terminal - English to Command AI Terminal
Converts natural language to terminal commands and executes them.

Modes:
  1. AI Mode (Default): English -> Terminal Commands
     - "show me all python files" -> find . -name "*.py"
     - "how much disk space do I have" -> df -h
     - "list large files" -> find . -size +100M
  
  2. Chat Mode: Direct conversation with Ollama
     - Chat with AI models running locally
  
  3. Regular Mode: Standard terminal
     - Direct shell command execution
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
import re
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

# Built-in English to Command mappings (works offline)
COMMAND_PATTERNS = {
    # File operations
    r"list\s*(all\s*)?(files|directories|folders)?": "ls -la",
    r"show\s*(all\s*)?(files|directories|folders)?": "ls -la",
    r"show\s*hidden\s*files": "ls -la",
    r"(find|search|show)\s*(all\s*)?python\s*files": 'find . -name "*.py" -type f 2>/dev/null',
    r"(find|search|show)\s*(all\s*)?javascript\s*files": 'find . -name "*.js" -type f 2>/dev/null',
    r"(find|search|show)\s*(all\s*)?text\s*files": 'find . -name "*.txt" -type f 2>/dev/null',
    r"(find|search)\s*large\s*files": 'find . -size +100M -type f 2>/dev/null | head -20',
    r"(find|search)\s*files\s*(larger|bigger)\s*than\s*(\d+)\s*(mb|gb|kb)?": lambda m: f'find . -size +{m.group(3)}{(m.group(4) or "M")[0].upper()} -type f 2>/dev/null',
    r"count\s*(all\s*)?(files|lines)": "find . -type f | wc -l",
    r"show\s*current\s*(directory|folder|path)": "pwd",
    r"(what|where)\s*(is|am)\s*(the\s*)?(current\s*)?(directory|folder|path|i)": "pwd",
    r"go\s*to\s*home": "cd ~",
    r"(go|change)\s*(to\s*)?(directory\s*)?(.+)": lambda m: f'cd {m.group(4).strip()}',
    
    # System info
    r"(show|check|what\s*is)\s*(the\s*)?(disk|storage)\s*(space|usage)?": "df -h",
    r"how\s*much\s*(disk\s*)?(space|storage)": "df -h",
    r"(show|check|what\s*is)\s*(the\s*)?(memory|ram)\s*(usage)?": "free -h",
    r"how\s*much\s*(memory|ram)": "free -h",
    r"(show|what)\s*(is\s*)?(the\s*)?(cpu|processor)\s*(info|usage)?": "top -bn1 | head -10",
    r"(show|list)\s*(running\s*)?processes": "ps aux | head -20",
    r"who\s*(is|am)\s*(logged\s*in|i)": "whoami",
    r"what\s*(time|date)\s*(is\s*it)?": "date",
    r"(show|check)\s*(system\s*)?(info|information)": "uname -a && lsb_release -a 2>/dev/null",
    r"(show|check)\s*(uptime|how\s*long)": "uptime",
    
    # Network
    r"(show|what\s*is|check)\s*(my\s*)?(ip|address)": "ip addr show | grep -oP '(?<=inet ).*(?=/)'",
    r"(ping|check)\s*(connection\s*to\s*)?google": "ping -c 3 google.com",
    r"(check|test)\s*(internet|network|connection)": "ping -c 3 8.8.8.8",
    r"(show|list)\s*(network\s*)?(ports|connections)": "netstat -tuln 2>/dev/null || ss -tuln",
    
    # Git
    r"(show|check)\s*(git\s*)?(status)": "git status",
    r"(show|list)\s*(git\s*)?(branches)": "git branch -a",
    r"(show|list)\s*(git\s*)?(log|history)": "git log --oneline -10",
    r"(show|what\s*is)\s*(the\s*)?(current\s*)?(branch)": "git branch --show-current",
    
    # Docker
    r"(show|list)\s*(docker\s*)?(containers)": "docker ps -a",
    r"(show|list)\s*(docker\s*)?(images)": "docker images",
    
    # Package management
    r"(update|upgrade)\s*(system|packages)?": "sudo apt update && sudo apt upgrade -y",
    r"install\s+(.+)": lambda m: f'sudo apt install -y {m.group(1).strip()}',
    
    # File content
    r"(show|cat|read|display)\s+(the\s*)?(contents?\s*of\s*)?(.+\.[\w]+)": lambda m: f'cat {m.group(4).strip()}',
    r"(head|first\s*\d*\s*lines)\s*(of\s*)?(.+)": lambda m: f'head -20 {m.group(3).strip()}',
    r"(tail|last\s*\d*\s*lines)\s*(of\s*)?(.+)": lambda m: f'tail -20 {m.group(3).strip()}',
    
    # Misc
    r"(clear|cls)\s*(screen|terminal)?": "clear",
    r"(exit|quit|close)\s*(terminal)?": "exit",
    r"(make|create)\s*(a\s*)?(new\s*)?(directory|folder)\s+(named\s+)?(.+)": lambda m: f'mkdir -p {m.group(6).strip()}',
    r"(remove|delete)\s+(file\s+)?(.+)": lambda m: f'rm -i {m.group(3).strip()}',
    r"(copy|cp)\s+(.+)\s+to\s+(.+)": lambda m: f'cp {m.group(2).strip()} {m.group(3).strip()}',
    r"(move|mv)\s+(.+)\s+to\s+(.+)": lambda m: f'mv {m.group(2).strip()} {m.group(3).strip()}',
}


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
        self.pending_command = None
        self.awaiting_confirmation = False
        
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
            self.append("⚡ AuraOS Terminal - English to Command\n", "system")
            self.append("Say what you want in plain English!\n\n", "system")
            self.append("Examples (try these!):\n", "info")
            self.append("  • show me all files           → ls -la\n", "output")
            self.append("  • find python files           → find . -name \"*.py\"\n", "output")
            self.append("  • how much disk space         → df -h\n", "output")
            self.append("  • check memory usage          → free -h\n", "output")
            self.append("  • show running processes      → ps aux\n", "output")
            self.append("  • what's my IP address        → ip addr\n", "output")
            self.append("  • open firefox                → [launches Firefox]\n", "output")
            self.append("  • create folder named test    → mkdir -p test\n\n", "output")
            self.append("Works offline for common commands.\n", "success")
            self.append("Complex requests use AI inference.\n", "info")
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
        
        # Handle confirmation for pending commands
        if self.awaiting_confirmation:
            if text.lower() in ('y', 'yes'):
                self.awaiting_confirmation = False
                cmd = self.pending_command
                self.pending_command = None
                self.append(f"✓ Executing: {cmd}\n\n", "success")
                threading.Thread(target=self._run_translated_command, args=(cmd,), daemon=True).start()
            elif text.lower() in ('n', 'no'):
                self.awaiting_confirmation = False
                self.pending_command = None
                self.append("✗ Command cancelled.\n\n", "warning")
                self.update_status("Ready", "#6db783")
            else:
                self.append("Please enter 'y' or 'n'\n", "info")
            self.input_field.delete(0, tk.END)
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
    
    def english_to_command(self, text):
        """
        Convert English text to a terminal command using pattern matching.
        Returns (command, confidence) tuple. Confidence is 'high', 'medium', or None.
        """
        text_lower = text.lower().strip()
        
        # Try built-in patterns first (offline, fast)
        for pattern, command in COMMAND_PATTERNS.items():
            match = re.search(pattern, text_lower)
            if match:
                if callable(command):
                    try:
                        cmd = command(match)
                        return (cmd, 'high')
                    except:
                        continue
                else:
                    return (command, 'high')
        
        return (None, None)
    
    def execute_ai_task(self, request_text):
        """
        AI Mode: Convert English to terminal command and execute.
        Uses pattern matching for common commands, falls back to inference server.
        """
        self.is_processing = True
        self.update_status("Translating...", "#00ff88")
        
        # Step 1: Try local pattern matching (fast, offline)
        command, confidence = self.english_to_command(request_text)
        
        if command and confidence == 'high':
            self.append(f"📝 Translated: {request_text}\n", "info")
            self.append(f"⚡ Command: ", "ai")
            self.append(f"{command}\n\n", "output")
            
            # Ask for confirmation for dangerous commands
            dangerous = ['rm ', 'sudo ', 'mv ', 'dd ', 'mkfs', '> /', 'chmod', 'chown']
            if any(d in command for d in dangerous):
                self.append("⚠️ This command may modify files. Execute? (y/n)\n", "warning")
                self.pending_command = command
                self.awaiting_confirmation = True
                self.is_processing = False
                self.update_status("Awaiting confirmation", "#dcdcaa")
                return
            
            # Execute directly
            self._run_translated_command(command)
            return
        
        # Step 2: Check for app launch commands (direct execution)
        request_lower = request_text.lower().strip()
        app_commands = {
            "open firefox": ["firefox"],
            "launch firefox": ["firefox"],
            "start firefox": ["firefox"],
            "open browser": ["firefox"],
            "open terminal": ["xfce4-terminal"],
            "open file manager": ["thunar"],
            "open files": ["thunar"],
        }
        
        for pattern, cmd in app_commands.items():
            if pattern in request_lower:
                self.append(f"📝 Translated: {request_text}\n", "info")
                self.append(f"⚡ Command: {' '.join(cmd)}\n\n", "output")
                try:
                    env = os.environ.copy()
                    env["DISPLAY"] = env.get("DISPLAY", ":99")
                    subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
                    self.append(f"✓ Launched {cmd[0]}\n\n", "success")
                    self.log_event("AI_DIRECT", f"Executed: {' '.join(cmd)}")
                except Exception as e:
                    self.append(f"✗ Failed: {e}\n\n", "error")
                self.is_processing = False
                self.update_status("Ready", "#6db783")
                return
        
        # Step 3: Try AI inference for complex requests
        self.append(f"🤔 Analyzing: {request_text}\n", "info")
        self.append("⟳ Asking AI for command suggestion...\n", "info")
        
        try:
            # Build a prompt to get a terminal command
            prompt = f"""Convert this English request to a single Linux terminal command.
Request: {request_text}
Reply with ONLY the command, no explanation. If you cannot convert it, reply with: CANNOT_CONVERT"""
            
            response = requests.post(
                f"{INFERENCE_URL}/generate",
                json={"prompt": prompt},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_command = result.get("response", "").strip()
                
                # Clean up the response
                ai_command = ai_command.replace("```bash", "").replace("```", "").strip()
                ai_command = ai_command.split('\n')[0].strip()  # Take first line only
                
                if ai_command and "CANNOT_CONVERT" not in ai_command and len(ai_command) < 500:
                    self.append(f"📝 AI suggests: ", "ai")
                    self.append(f"{ai_command}\n\n", "output")
                    self.append("Execute this command? (y/n)\n", "warning")
                    self.pending_command = ai_command
                    self.awaiting_confirmation = True
                    self.is_processing = False
                    self.update_status("Awaiting confirmation", "#dcdcaa")
                    return
                else:
                    self.append("✗ Could not translate to a command.\n", "error")
                    self.append("  Try being more specific, or use Regular mode.\n\n", "info")
            else:
                self.append(f"✗ AI Error: {response.text[:100]}\n", "error")
                
        except requests.exceptions.ConnectionError:
            self.append("✗ Inference server offline. Using pattern matching only.\n", "warning")
            self.append("  Start server: ./auraos.sh inference start\n\n", "info")
        except Exception as e:
            self.append(f"✗ Error: {e}\n", "error")
        
        self.is_processing = False
        self.update_status("Ready", "#6db783")
    
    def _run_translated_command(self, command):
        """Execute a translated command"""
        try:
            self.update_status("Executing...", "#00ff88")
            
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=60, cwd=os.path.expanduser("~")
            )
            
            if result.stdout:
                self.append(result.stdout, "output")
            
            if result.returncode == 0:
                if not result.stdout:
                    self.append("✓ Command executed successfully\n", "success")
                self.log_event("AI_EXEC", f"{command} (success)")
            else:
                if result.stderr:
                    self.append(f"⚠ {result.stderr}", "warning")
                self.append(f"✗ Exit code: {result.returncode}\n", "error")
                
            self.append("\n", "output")
            
        except subprocess.TimeoutExpired:
            self.append("✗ Command timed out (60s limit)\n\n", "error")
        except Exception as e:
            self.append(f"✗ Error: {e}\n\n", "error")
        
        self.is_processing = False
        self.update_status("Ready", "#6db783")

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
