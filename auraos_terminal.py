#!/usr/bin/env python3
"""
AuraOS Terminal - Enhanced AI Integration
Features:
- Direct AI button (auto-appends "ai-")
- No confirmation screens (auto-execution for safe operations)
- Screen context capture for last 5 minutes
- Full AI pipeline integration with daemon
- Improved UX and feedback
"""
import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import sys
import os
import shutil
from datetime import datetime
import logging
import json

# Import enhanced AI components
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'auraos_daemon'))
try:
    from core.ai_handler import EnhancedAIHandler
    from core.screen_context import ScreenCaptureManager
    AI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI components not available: {e}")
    AI_AVAILABLE = False


class AuraOSTerminal:
    """Enhanced terminal with integrated AI capabilities"""
    
    def __init__(self, root, cli_mode=False):
        self.cli_mode = cli_mode
        self.ai_handler = None
        
        if not cli_mode:
            self.root = root
            self.root.title("AuraOS Terminal")
            self.root.geometry("1200x800")
            self.root.configure(bg='#0a0e27')
            self.command_history = []
            self.history_index = -1
            self.show_command_panel = False
            self.ai_running = False
            
            # Initialize AI handler
            if AI_AVAILABLE:
                try:
                    daemon_config = self._load_daemon_config()
                    self.ai_handler = EnhancedAIHandler(daemon_config)
                except Exception as e:
                    logging.warning(f"Could not initialize AI handler: {e}")
            
            self.create_widgets()
            self.log_event("STARTUP", "Terminal initialized")
        else:
            self.run_cli_mode()
    
    def _load_daemon_config(self):
        """Load daemon configuration"""
        config_path = os.path.expanduser("~/.auraos/config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f)
        return {}
    
    def log_event(self, action, message):
        """Log events to file"""
        try:
            log_path = "/tmp/auraos_terminal.log"
            with open(log_path, "a") as f:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                f.write(f"[{ts}] {action}: {message}\n")
        except:
            pass
    
    def create_widgets(self):
        """Create GUI widgets"""
        # ===== TOP FRAME =====
        top_frame = tk.Frame(self.root, bg='#1a1e37', height=60)
        top_frame.pack(fill='x')
        
        # Menu button
        menu_btn = tk.Button(
            top_frame, text="☰ Menu", command=self.toggle_command_panel,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=10, pady=10
        )
        menu_btn.pack(side='left', padx=10, pady=8)
        
        # AI button (NEW)
        ai_btn = tk.Button(
            top_frame, text="⚡ AI", command=self.focus_input_for_ai,
            bg='#00ff88', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=15, pady=10
        )
        ai_btn.pack(side='left', padx=5, pady=8)
        
        # Title
        title = tk.Label(
            top_frame, text="⚡ AuraOS Terminal", font=('Arial', 14, 'bold'),
            fg='#00d4ff', bg='#1a1e37'
        )
        title.pack(side='left', padx=20, pady=8)
        
        # Status indicator
        self.status_label = tk.Label(
            top_frame, text="Ready", font=('Arial', 10),
            fg='#6db783', bg='#1a1e37'
        )
        self.status_label.pack(side='right', padx=20, pady=8)
        
        # ===== MAIN FRAME =====
        main_frame = tk.Frame(self.root, bg='#0a0e27')
        main_frame.pack(fill='both', expand=True)
        
        self.cmd_panel = tk.Frame(main_frame, bg='#1a1e37', width=250)
        
        # Output area
        self.output_area = scrolledtext.ScrolledText(
            main_frame, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
            font=('Menlo', 11), insertbackground='#00d4ff',
            relief='flat', padx=15, pady=15
        )
        self.output_area.pack(fill='both', expand=True, padx=0, pady=0)
        self.output_area.config(state='disabled')
        
        # Configure tags
        self.output_area.tag_config("system", foreground="#00d4ff", font=('Menlo', 11, 'bold'))
        self.output_area.tag_config("user", foreground="#4ec9b0", font=('Menlo', 11, 'bold'))
        self.output_area.tag_config("ai", foreground="#00ff88", font=('Menlo', 11, 'bold'))
        self.output_area.tag_config("output", foreground="#d4d4d4", font=('Menlo', 10))
        self.output_area.tag_config("error", foreground="#f48771", font=('Menlo', 10, 'bold'))
        self.output_area.tag_config("success", foreground="#6db783", font=('Menlo', 10, 'bold'))
        self.output_area.tag_config("info", foreground="#9cdcfe", font=('Menlo', 10))
        self.output_area.tag_config("warning", foreground="#dcdcaa", font=('Menlo', 10, 'bold'))
        
        # Welcome message
        self.append_output("⚡ AuraOS Terminal\n", "system")
        self.append_output("AI-Powered Command Interface with Auto-Execution\n\n", "system")
        self.append_output("Features:\n", "info")
        self.append_output("  • Click ⚡ AI button to enter AI mode (auto-appends 'ai-')\n", "info")
        self.append_output("  • Safe tasks auto-execute (no confirmation needed)\n", "info")
        self.append_output("  • Screen context captured for AI awareness\n", "info")
        self.append_output("  • Use ☰ Menu for options\n\n", "info")
        
        # ===== INPUT FRAME =====
        input_frame = tk.Frame(self.root, bg='#1a1e37', height=80)
        input_frame.pack(fill='x', padx=0, pady=0)
        
        # Prompt label
        self.prompt_label = tk.Label(
            input_frame, text="→ ", font=('Menlo', 12, 'bold'),
            fg='#00d4ff', bg='#1a1e37'
        )
        self.prompt_label.pack(side='left', padx=(15, 0), pady=10)
        
        # Input field
        self.input_field = tk.Entry(
            input_frame, bg='#2d3547', fg='#ffffff',
            font=('Menlo', 12), insertbackground='#00d4ff',
            relief='flat', bd=0
        )
        self.input_field.pack(side='left', fill='both', expand=True, ipady=10, padx=(5, 10), pady=10)
        self.input_field.bind('<Return>', lambda e: self.execute_command())
        self.input_field.bind('<Up>', self.history_up)
        self.input_field.bind('<Down>', self.history_down)
        self.input_field.bind('<Escape>', lambda e: self.input_field.delete(0, tk.END))
        
        # Button frame
        btn_frame = tk.Frame(input_frame, bg='#1a1e37')
        btn_frame.pack(side='right', padx=10, pady=10)
        
        self.execute_btn = tk.Button(
            btn_frame, text="Send", command=self.execute_command,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=12, pady=6
        )
        self.execute_btn.pack(side='left', padx=5)
    
    def focus_input_for_ai(self):
        """Focus input field and set AI mode indicator"""
        self.input_field.delete(0, tk.END)
        self.input_field.insert(0, "ai- ")
        self.prompt_label.config(text="⚡ ", fg='#00ff88')
        self.input_field.focus()
        self.input_field.icursor(tk.END)
    
    def toggle_command_panel(self):
        """Toggle command panel visibility"""
        if self.cmd_panel.winfo_ismapped():
            self.cmd_panel.pack_forget()
        else:
            self.create_command_panel()
            self.cmd_panel.pack(side='left', fill='y', before=self.output_area, padx=0, pady=0)
    
    def create_command_panel(self):
        """Create command reference panel"""
        self.cmd_panel.destroy()
        self.cmd_panel = tk.Frame(self.root.winfo_children()[1], bg='#1a1e37', width=300)
        
        title = tk.Label(
            self.cmd_panel, text="Commands & Help", font=('Arial', 12, 'bold'),
            fg='#00d4ff', bg='#1a1e37'
        )
        title.pack(padx=10, pady=10, fill='x')
        
        help_text = scrolledtext.ScrolledText(
            self.cmd_panel, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
            font=('Menlo', 9), height=40, width=35, relief='flat'
        )
        help_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        content = """AI MODE (Click ⚡ or type 'ai- '):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Auto-executes if safe
• No confirmation needed
• Full daemon integration
• Screen context aware
• Examples:
  ai- install python dependencies
  ai- create backup of logs
  ai- find large files and compress

REGULAR COMMANDS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
help       Show this help
clear      Clear screen
history    Command history
status     System status
health     Health check
exit       Close terminal

BUILT-IN SHORTCUTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
↑/↓        Navigate history
Esc        Clear input
Enter      Execute

SAFETY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Destructive operations
  are blocked
✓ All actions logged
✓ Easy recovery available

DAEMON INTEGRATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Location:
  ~/auraos_daemon/

Config:
  ~/.auraos/config.json

Logs:
  /tmp/auraos_*.log
"""
        help_text.insert(tk.END, content)
        help_text.config(state='disabled')
    
    def append_output(self, text, tag="output"):
        """Append text to output area"""
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, text, tag)
        self.output_area.see(tk.END)
        self.output_area.config(state='disabled')
        self.root.update_idletasks()
    
    def update_status(self, status_text, color='#6db783'):
        """Update status indicator"""
        self.status_label.config(text=status_text, fg=color)
        self.root.update_idletasks()
    
    def execute_command(self):
        """Execute user command or AI task"""
        command = self.input_field.get().strip()
        if not command:
            return
        
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # Determine if this is AI mode
        is_ai_mode = command.lower().startswith('ai-')
        
        if is_ai_mode:
            # Strip 'ai-' prefix
            task = command[3:].strip()
            self.append_output(f"⚡ {command}\n", "ai")
            self.input_field.delete(0, tk.END)
            self.prompt_label.config(text="→ ", fg='#00d4ff')
            threading.Thread(target=self.handle_ai_task, args=(task,), daemon=True).start()
        else:
            # Regular command
            self.append_output(f"→ {command}\n", "user")
            self.input_field.delete(0, tk.END)
            
            if command.lower() in ['exit', 'quit']:
                self.log_event("EXIT", "User closed terminal")
                self.root.quit()
            elif command.lower() == 'clear':
                self.output_area.config(state='normal')
                self.output_area.delete(1.0, tk.END)
                self.output_area.config(state='disabled')
            elif command.lower() == 'help':
                self.show_help()
            elif command.lower() == 'history':
                self.show_history()
            elif command.lower() == 'status':
                self.show_status()
            else:
                threading.Thread(target=self.run_command, args=(command,), daemon=True).start()
    
    def handle_ai_task(self, task_text):
        """Handle AI task with no confirmation"""
        if not self.ai_handler:
            self.append_output("✗ AI handler not available\n", "error")
            self.log_event("AI_ERROR", "Handler not initialized")
            return
        
        try:
            self.update_status("AI Processing...", "#00ff88")
            self.append_output("Processing request...\n", "info")
            
            # Process through full AI pipeline
            result = self.ai_handler.process_ai_request(task_text, auto_execute=True)
            
            # Display result
            self._display_ai_result(result)
            
            self.update_status("Ready", "#6db783")
            self.log_event("AI_SUCCESS", f"Task: {task_text[:50]}")
            
        except Exception as e:
            self.append_output(f"✗ AI Error: {str(e)}\n", "error")
            self.update_status("Error", "#f48771")
            self.log_event("AI_ERROR", str(e))
    
    def _display_ai_result(self, result):
        """Display AI pipeline result"""
        status = result.get('status', 'unknown')
        
        # Show pipeline steps
        for step in result.get('steps', []):
            step_status = "✓" if step['status'] == 'success' else "✗" if step['status'] == 'error' else "⚠"
            self.append_output(f"{step_status} {step['name']}: {step.get('status')}\n", 
                             'success' if step['status'] == 'success' else 'error' if step['status'] == 'error' else 'warning')
        
        # Show execution result if available
        if 'execution' in result:
            exec_info = result['execution']
            exit_code = exec_info.get('exit_code', -1)
            
            self.append_output("\n=== Execution Output ===\n", "info")
            
            if exit_code == 0:
                self.append_output(f"✓ Success (exit code: {exit_code})\n", "success")
            else:
                self.append_output(f"✗ Failed (exit code: {exit_code})\n", "error")
            
            if exec_info.get('stdout'):
                self.append_output(exec_info['stdout'], "output")
            
            if exec_info.get('stderr'):
                self.append_output(f"Errors:\n{exec_info['stderr']}\n", "error")
            
            self.append_output(f"Duration: {exec_info.get('duration_seconds', 0):.2f}s\n\n", "info")
        
        # Show reasoning
        if result.get('reasoning'):
            self.append_output(f"Reasoning: {result['reasoning']}\n\n", "info")
        
        # Show final status
        if status == 'completed':
            self.append_output("✓ Task completed successfully\n", "success")
        elif status == 'blocked':
            self.append_output(f"⚠ Task blocked: {result.get('reason', 'Unknown')}\n", "warning")
        elif status == 'failed':
            self.append_output(f"✗ Task failed: {result.get('reason', 'Unknown')}\n", "error")
    
    def run_command(self, command):
        """Execute regular shell command"""
        try:
            self.update_status("Running...", "#9cdcfe")
            self.append_output("⟳ Running...\n", "info")
            
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, cwd=os.path.expanduser('~')
            )
            
            if result.stdout:
                self.append_output(result.stdout, "output")
            
            if result.returncode == 0:
                if not result.stdout:
                    self.append_output("✓ Success\n", "success")
            else:
                if result.stderr:
                    self.append_output(result.stderr, "error")
                else:
                    self.append_output(f"✗ Exit code: {result.returncode}\n", "error")
            
            self.append_output("\n", "output")
            self.update_status("Ready", "#6db783")
            self.log_event("COMMAND", f"Executed: {command} (exit: {result.returncode})")
        
        except subprocess.TimeoutExpired:
            self.append_output("✗ Command timed out (30s limit)\n", "error")
            self.update_status("Timeout", "#f48771")
            self.log_event("TIMEOUT", f"Command exceeded 30s: {command}")
        except Exception as e:
            self.append_output(f"✗ Error: {str(e)}\n", "error")
            self.update_status("Error", "#f48771")
            self.log_event("ERROR", str(e))
    
    def show_help(self):
        """Show help text"""
        help_text = """
⚡ AuraOS Terminal - Quick Start

AI MODE (Recommended):
  1. Click ⚡ AI button
  2. Type your request in plain English
  3. Task auto-executes if safe (no confirmation needed)
  4. Results displayed with reasoning and output

Examples:
  • ai- install python dependencies
  • ai- create backup of important files
  • ai- find and list processes using high CPU
  • ai- download and extract latest release

FEATURES:
  ✓ Natural language understanding
  ✓ Screen context aware (captures last 5 minutes)
  ✓ Auto-execution for safe operations
  ✓ Comprehensive safety checks
  ✓ Detailed logging and history
  ✓ Failed command recovery suggestions

REGULAR SHELL:
  Just type your command normally (without ai- prefix)
  Example: ls -la, git status, python script.py

KEYBOARD SHORTCUTS:
  • Up/Down arrows: Navigate history
  • Escape: Clear input
  • Enter: Execute

LOGS & DEBUG:
  Terminal log: /tmp/auraos_terminal.log
  AI execution log: /tmp/auraos_ai.log
  Screen captures: /tmp/auraos_screenshots/

For more info, check the ☰ Menu
"""
        self.append_output(help_text + "\n", "info")
    
    def show_history(self):
        """Show command history"""
        if not self.command_history:
            self.append_output("No history yet.\n\n", "info")
            return
        
        self.append_output("Command History (last 20):\n", "info")
        for i, cmd in enumerate(self.command_history[-20:], max(1, len(self.command_history)-19)):
            tag = "ai" if cmd.startswith("ai-") else "user"
            self.append_output(f"  {i}. {cmd}\n", tag)
        self.append_output("\n", "output")
    
    def show_status(self):
        """Show system status"""
        status_info = """
System Status:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Terminal: AuraOS Terminal
Mode: Enhanced AI Integration
AI Handler: """ + ("✓ Available" if self.ai_handler else "✗ Unavailable") + """
Commands Executed: """ + str(len(self.command_history)) + """

Daemon Status: Check with 'health' command

Log Files:
  /tmp/auraos_terminal.log
  /tmp/auraos_*.log

Type 'help' for more information
"""
        self.append_output(status_info + "\n", "info")
    
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
    
    def run_cli_mode(self):
        """Run in CLI mode (no GUI)"""
        print("⚡ AuraOS Terminal")
        print("Type 'help' for usage, 'exit' to quit\n")
        
        while True:
            try:
                command = input("→ ").strip()
                if not command:
                    continue
                
                if command.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                
                if command.lower().startswith('ai-'):
                    task = command[3:].strip()
                    if self.ai_handler:
                        result = self.ai_handler.process_ai_request(task, auto_execute=True)
                        print(json.dumps(result, indent=2))
                    else:
                        print("✗ AI handler not available")
                    continue
                
                if command.lower() == 'help':
                    print("""
AuraOS Terminal - CLI Mode

Usage:
  Regular command: type shell command directly
  AI command: ai- <your request in English>
  
Examples:
  ai- install python packages
  ai- create backup
  ls -la
  git status
""")
                    continue
                
                # Regular shell command
                result = subprocess.run(
                    command, shell=True, cwd=os.path.expanduser('~')
                )
            
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break


if __name__ == "__main__":
    if "--cli" in sys.argv:
        app = AuraOSTerminal(None, cli_mode=True)
    else:
        root = tk.Tk()
        app = AuraOSTerminal(root)
        root.mainloop()
