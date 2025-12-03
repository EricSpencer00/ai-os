#!/usr/bin/env python3
"""
AuraOS Terminal - English to Bash GUI with TerminalGPT-style Resilience
Automatic error recovery: if a command fails, AI generates a corrected command
"""
import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import sys
import os
import requests
import re
import json

# Smart URL detection: use host gateway IP when running inside VM
def get_inference_url():
    """Get the correct inference server URL based on environment."""
    if os.path.exists("/opt/auraos"):
        return "http://192.168.2.1:8081"
    return "http://localhost:8081"

INFERENCE_URL = get_inference_url()

# Configuration
AUTO_RETRY_ERRORS = True
MAX_RETRIES = 3

class AuraOSTerminal:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Terminal")
        self.root.geometry("900x700")
        self.root.configure(bg='#0a0e27')
        
        # Enable proper window manager integration for resize/drag
        self.root.resizable(True, True)
        self.root.minsize(600, 400)
        # Enable window decorations (title bar with close button)
        try:
            self.root.attributes('-type', 'normal')
        except:
            pass  # -type not supported on all window managers
        
        self.is_processing = False
        self.conversation_history = []  # Track conversation for context
        self.retry_count = 0
        self.max_retries = MAX_RETRIES
        self.setup_ui()
        
    def setup_ui(self):
        # Title Bar
        title_frame = tk.Frame(self.root, bg='#1a1e37', height=60)
        title_frame.pack(fill='x')
        
        title = tk.Label(
            title_frame, text="[Terminal] English to Bash - Auto-Recovery",
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
        self.output_area.tag_config('ai', foreground='#dcdcaa')
        self.output_area.tag_config('retry', foreground='#ff7f50')
        
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
        self.append_text("[Terminal] English to Bash - Auto Recovery\n", "info")
        self.append_text("If a command fails, the AI will automatically try to fix it\n\n", "info")
        self.append_text("Examples:\n", "info")
        self.append_text("  • show me all files\n", "command")
        self.append_text("  • find python files\n", "command")
        self.append_text("  • how much disk space\n", "command")
        self.append_text("  • install nodejs\n\n", "command")
        self.append_text(f"Auto-retry enabled: {MAX_RETRIES} attempts\n", "ai")
        
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
        self.conversation_history = []
        
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
        self.retry_count = 0
        
        threading.Thread(target=self._convert_and_execute, args=(text,), daemon=True).start()
        
    def _build_system_prompt(self):
        """Build the system prompt for command generation (from TerminalGPT)"""
        return """You are a highly capable shell command generator that converts plain-English requests into fully self-contained, executable shell commands for a Unix-like environment. You must produce all necessary commands so that the user never needs to perform any manual steps.

Completeness: Generate complete commands that include any prerequisite steps (e.g., if a referenced folder does not exist, include a command such as `mkdir -p` to create it).

Clarity & Safety: If the request is ambiguous, incomplete, or potentially dangerous (e.g., commands that could result in data loss or system instability), ask for clarification before proceeding.

No Placeholders: Do not use placeholders like `/path/to/folder` or `<argument>`. All paths and arguments must be explicitly specified.

Formatting: Output only the final command(s) without any extra commentary, markdown formatting, code fences, or additional text.

Multiple Commands: If more than one command is required, list each command on a separate line in the correct execution order.

Edge Cases: Always consider dependencies, file/directory existence, and command safety (e.g., using flags for non-interactive execution if needed). Your response should consist solely of the final command(s) ready for execution."""

    def _validate_command(self, command):
        """Validate command for dangerous patterns"""
        dangerous_patterns = [
            'rm -rf /',  # Recursive delete root
            ':(){:|:&};:',  # Bash fork bomb
            'mkfs',  # Format filesystem
            'dd if=/dev/zero',  # Destructive writes
        ]
        
        cmd_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in cmd_lower:
                return False, f"Potentially dangerous pattern detected: {pattern}"
        
        return True, ""

    def _analyze_command_result(self, command, stdout, stderr, exit_code):
        """Analyze if a command succeeded or failed"""
        # Simple heuristic: exit code 0 almost always means success
        # Only use AI for ambiguous cases (exit code != 0 but might have partial success)
        if exit_code == 0:
            return {"success": True, "reason": "exit code 0", "issue": ""}
        
        # For non-zero exit codes with no stderr, still consider it might be partial success
        if exit_code != 0 and not stderr and stdout:
            return {"success": True, "reason": "exit code non-zero but has output", "issue": ""}
        
        # Actual failure
        return {
            "success": False,
            "reason": f"exit code {exit_code}",
            "issue": stderr[:200] if stderr else "No error output"
        }

    def _generate_recovery_command(self, user_request, command_executed, analysis):
        """Use AI to generate a recovery command based on failure analysis"""
        try:
            recovery_prompt = f"""The user requested: {user_request}

The command that failed: {command_executed}

Failure analysis: {analysis.get('issue', 'Unknown error')}

Based on the failure, generate ONE alternative bash command that will:
1. Work around the reported issue
2. Accomplish the original user request
3. Handle common failure modes proactively

Output ONLY the bash command, nothing else."""
            
            self.append_text("[*] Analyzing failure and crafting recovery...\n", "info")
            
            response = requests.post(
                f"{INFERENCE_URL}/generate",
                json={"prompt": self._build_system_prompt() + f"\n\n{recovery_prompt}"},
                timeout=15
            )
            
            if response.status_code == 200:
                command = response.json().get("response", "").strip()
                command = command.split('\n')[0].strip()
                
                if command and len(command) < 500:
                    return command
            
            return None
        except:
            return None

    def _generate_command(self, user_request, error_analysis=None):
        """Generate a bash command using AI"""
        try:
            # Build the prompt
            if error_analysis:
                # Error recovery mode: use AI analysis to craft fix
                prompt = f"""The previous command failed:
Issue: {error_analysis.get('issue', 'Unknown')}
Reason: {error_analysis.get('reason', 'Unknown')}

Original request: {user_request}

Please provide a corrected command that will work around this specific error."""
            else:
                prompt = f"""Convert this request to a bash command: {user_request}"""
            
            self.append_text("[?] Generating command...\n", "info")
            
            response = requests.post(
                f"{INFERENCE_URL}/generate",
                json={"prompt": self._build_system_prompt() + f"\n\nRequest: {prompt}"},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                command = result.get("response", "").strip()
                # Get first line (handle multi-line responses)
                command = command.split('\n')[0].strip()
                
                if command and "CANNOT_CONVERT" not in command and len(command) < 2000:
                    # Validate command safety
                    is_safe, reason = self._validate_command(command)
                    if not is_safe:
                        self.append_text(f"[!] Safety check failed: {reason}\n", "error")
                        return None
                    
                    return command
                else:
                    self.append_text("[X] Could not generate valid command\n", "error")
                    return None
            else:
                self.append_text(f"[X] Server error: {response.text[:100]}\n", "error")
                return None
                
        except requests.exceptions.Timeout:
            self.append_text("[X] AI request timeout\n", "error")
            return None
        except requests.exceptions.ConnectionError:
            self.append_text(f"[X] Cannot reach inference server: {INFERENCE_URL}\n", "error")
            return None
        except Exception as e:
            self.append_text(f"[X] Error: {str(e)}\n", "error")
            return None

    def _convert_and_execute(self, user_request):
        """Convert English to bash and execute with AI-driven error recovery"""
        try:
            error_analysis = None
            
            while self.retry_count < self.max_retries:
                # Generate command (with AI analysis for recovery attempts)
                command = self._generate_command(user_request, error_analysis)
                if not command:
                    break
                
                self.append_text(f"Command: {command}\n", "command")
                
                # Execute (safely, with proper timeout and working directory)
                self.append_text("[*] Executing...\n", "info")
                try:
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=os.path.expanduser("~")
                    )
                except subprocess.TimeoutExpired:
                    self.append_text("[X] Command timed out after 30 seconds\n", "error")
                    break
                except Exception as e:
                    self.append_text(f"[X] Execution error: {str(e)}\n", "error")
                    break
                
                # Display output
                if result.stdout:
                    self.append_text(f"{result.stdout}\n", "info")
                
                # Result analysis: simple heuristic, not expensive AI call
                analysis = self._analyze_command_result(
                    command, 
                    result.stdout, 
                    result.stderr, 
                    result.returncode
                )
                
                # Check if command succeeded
                if analysis.get("success"):
                    self.append_text(f"[OK] Command succeeded\n", "success")
                    self.status_label.config(text="Ready", fg='#6db783')
                    self.is_processing = False
                    return
                else:
                    # Command failed - prepare for intelligent recovery
                    failure_reason = analysis.get("reason", "Unknown error")
                    failure_issue = analysis.get("issue", result.stderr or "No error details")
                    
                    if AUTO_RETRY_ERRORS and self.retry_count < self.max_retries - 1:
                        self.retry_count += 1
                        self.append_text(
                            f"[!] Command failed: {failure_reason}\n",
                            "error"
                        )
                        self.append_text(
                            f"[*] Attempt {self.retry_count + 1}/{self.max_retries}...\n",
                            "retry"
                        )
                        
                        # Prepare analysis for next iteration
                        error_analysis = {
                            "reason": failure_reason,
                            "issue": failure_issue[:200],
                            "output": result.stdout[:100] if result.stdout else ""
                        }
                        self.status_label.config(text=f"Retrying... ({self.retry_count}/{self.max_retries})", fg='#ff7f50')
                        continue
                    else:
                        # Max retries exceeded
                        self.append_text(
                            f"[X] Failed after {self.max_retries} attempts\n",
                            "error"
                        )
                        if failure_issue:
                            self.append_text(f"Error: {failure_issue}\n", "error")
                        break
                
        except Exception as e:
            self.append_text(f"[X] Unexpected error: {str(e)}\n", "error")
            
        self.is_processing = False
        self.status_label.config(text="Ready", fg='#6db783')

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSTerminal(root)
    root.mainloop()
