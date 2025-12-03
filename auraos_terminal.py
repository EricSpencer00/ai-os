#!/usr/bin/env python3
"""
AuraOS Terminal - English to Bash GUI with TerminalGPT-style Resilience
Persistent PTY shell with true terminal context and self-healing retry logic
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
import pty
import select
import time
import signal
import fcntl

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
        
        # Initialize persistent shell session
        self.shell_pid = None
        self.shell_fd = None
        self._init_shell()
        
        self.is_processing = False
        self.conversation_history = []  # Track conversation for context
        self.retry_count = 0
        self.max_retries = MAX_RETRIES
        self.setup_ui()
        
        # Handle cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._cleanup_and_exit)
    
    def _init_shell(self):
        """Initialize persistent PTY shell session"""
        try:
            self.shell_pid, self.shell_fd = pty.forkpty()
            if self.shell_pid == 0:
                # Child process - start bash
                os.execvp("bash", ["bash", "--noprofile", "--norc"])
                sys.exit(0)
            else:
                # Parent process - set non-blocking mode
                flags = fcntl.fcntl(self.shell_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.shell_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        except Exception as e:
            print(f"Failed to initialize shell: {e}")
            self.shell_pid = None
            self.shell_fd = None
    
    def _cleanup_and_exit(self):
        """Clean up shell and exit"""
        if self.shell_pid:
            try:
                os.kill(self.shell_pid, signal.SIGTERM)
            except:
                pass
        self.root.destroy()
        
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
        """Build the system prompt for command generation (from TerminalGPT, with strict output format)"""
        return """You are a highly capable shell command generator that converts plain-English requests into fully self-contained, executable shell commands for a Unix-like environment. You must produce all necessary commands so that the user never needs to perform any manual steps.

CRITICAL: Your response must contain ONLY the bash command(s). No explanations, no preamble, no descriptions.

Core Requirements:
1. Completeness: Generate complete commands that include any prerequisite steps (e.g., if a referenced folder does not exist, include a command such as `mkdir -p` to create it).

2. Always consider dependencies, file/directory existence, and command safety.

3. No Placeholders: Do not use placeholders like `/path/to/folder` or `<argument>`. All paths and arguments must be explicitly specified.

4. Multiple Commands: If more than one command is required, list each command on a separate line in the correct execution order.

5. Edge Cases: Use flags for non-interactive execution if needed. Your response should consist solely of the final command(s) ready for execution.

OUTPUT FORMAT (CRITICAL):
- Start directly with the command
- No introductory text whatsoever
- No markdown, code fences, or formatting
- Chain any commands separated by newlines
- If unsafe or cannot convert: output only "CANNOT_CONVERT"

EXAMPLE CORRECT OUTPUT:
mkdir -p /home/user/project
cd /home/user/project
git clone https://github.com/EricSpencer00/ai-os.git

EXAMPLE WRONG OUTPUT (DO NOT DO THIS):
"Here is the command to clone the repository:
git clone https://github.com/username/repo.git"

REMEMBER: Output ONLY the command(s). Nothing else."""

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

    def _analyze_command_result(self, command, stdout, stderr, exit_code, cwd=""):
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

    def _extract_command_from_response(self, response_text):
        """Extract the actual command from potentially verbose AI response"""
        # First, prefer extracting content from fenced code blocks if present
        try:
            fenced_match = re.search(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", response_text, flags=re.S)
            if fenced_match:
                # Use the inner contents of the first fenced block
                response_text = fenced_match.group(1)

            # Remove any remaining triple-backticks and inline backticks
            response_text = re.sub(r"```", "", response_text)
            response_text = re.sub(r"`([^`]+)`", r"\1", response_text)
        except Exception:
            # If regex fails for any reason, fall back to original text
            pass

        lines = response_text.strip().split('\n')

        # Filter out empty lines, comments and formatting language markers
        command_lines = []
        desc_patterns = [
            'here is', 'this command', 'to accomplish', 'to convert',
            'example:', 'output:', 'note:', 'first,', 'then,', 'finally,',
            'the command', 'you can', 'alternatively', 'use:', 'try:',
            'run:', 'execute:', 'the bash', 'a command'
        ]

        for line in lines:
            line = line.strip()

            # Skip empty or comment lines
            if not line or line.startswith('#'):
                continue

            line_lower = line.lower()

            # Skip lines that are just a language marker (e.g., 'bash', 'shell')
            if line_lower in ('bash', 'sh', 'shell'):
                continue

            # Skip leftover fence markers
            if line.startswith('```'):
                continue

            # Skip obvious description patterns
            if any(line_lower.startswith(p) or line_lower.endswith(p) for p in desc_patterns):
                continue

            # Handle lines that prefix the command (e.g., "Command: ...")
            if re.match(r'^(command:|to fix:)', line_lower):
                parts = line.split(':', 1)[1].strip()
                # Strip any surrounding backticks or language tokens
                parts = re.sub(r"^```[a-zA-Z0-9_+-]*", "", parts)
                parts = parts.replace('`', '').strip()
                if parts:
                    command_lines.append(parts)
                continue

            # Looks like a real command line — strip stray backticks and append
            cleaned = line.replace('`', '').strip()
            if cleaned:
                command_lines.append(cleaned)

        # Return joined command lines if any
        if command_lines:
            return '\n'.join(command_lines)
        return ""

    def _generate_command(self, user_request, error_analysis=None):
        """Generate a bash command using AI, with context for recovery"""
        try:
            # Build the prompt - include context from error_analysis including cwd
            if error_analysis:
                # Error recovery mode: use AI analysis to craft fix with full context
                cwd_context = f"Current directory: {error_analysis.get('cwd', '~')}\n" if error_analysis.get('cwd') else ""
                prompt = f"""Fix this command that failed:
Original request: {user_request}
{cwd_context}Error: {error_analysis.get('issue', 'Unknown')}
Previous output: {error_analysis.get('output', '')}

Output ONLY a new bash command to fix this. NOTHING ELSE."""
            else:
                prompt = f"""{user_request}"""
            
            self.append_text("[?] Generating command...\n", "info")
            
            response = requests.post(
                f"{INFERENCE_URL}/generate",
                json={"prompt": self._build_system_prompt() + f"\n\n{prompt}"},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "").strip()
                
                # Extract command from potentially verbose response
                command = self._extract_command_from_response(response_text)
                
                if command and "CANNOT_CONVERT" not in command and len(command) < 2000:
                    # Validate command safety
                    is_safe, reason = self._validate_command(command)
                    if not is_safe:
                        self.append_text(f"[!] Safety check failed: {reason}\n", "error")
                        return None
                    
                    return command
                else:
                    if not command or "CANNOT_CONVERT" in command:
                        self.append_text("[X] Could not generate valid command\n", "error")
                    else:
                        self.append_text(f"[X] Command too long ({len(command)} chars)\n", "error")
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

    def _run_in_shell(self, command, timeout=30):
        """
        Execute command in persistent PTY shell and capture output.
        This maintains shell state (cwd, env, created files) across calls.
        """
        if not self.shell_fd:
            return 1, "", "Shell not initialized", ""
        
        try:
            # Get current working directory before executing
            pwd_cmd = "pwd\n"
            os.write(self.shell_fd, pwd_cmd.encode())
            time.sleep(0.1)
            cwd = self._read_shell_output(timeout=2).strip().split('\n')[-1]
            
            # Write command with status markers for clean output capture
            marker_start = f"__START_{int(time.time() * 1000)}__"
            marker_end = f"__END_{int(time.time() * 1000)}__"
            full_command = f"echo '{marker_start}'\n{command}\necho '__STATUS__'$?'__/STATUS__'\necho '{marker_end}'\n"
            
            os.write(self.shell_fd, full_command.encode())
            
            # Capture output with timeout
            output = self._read_shell_output(timeout=timeout)
            
            # Parse output between markers
            if marker_start in output and marker_end in output:
                start_idx = output.find(marker_start) + len(marker_start)
                end_idx = output.find(marker_end)
                captured = output[start_idx:end_idx].strip()
                
                # Extract exit status
                status_match = re.search(r"__STATUS__(\d+)__/STATUS__", captured)
                exit_code = int(status_match.group(1)) if status_match else 0
                
                # Remove status line from output
                result_output = re.sub(r"__STATUS__\d+__/STATUS__\n?", "", captured)
                
                return exit_code, result_output, "", cwd
            else:
                # Fallback if markers not found
                return 0, output, "", cwd
                
        except Exception as e:
            return 1, "", str(e), ""
    
    def _read_shell_output(self, timeout=5):
        """Read available output from shell with timeout"""
        if not self.shell_fd:
            return ""
        
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            ready, _, _ = select.select([self.shell_fd], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(self.shell_fd, 4096)
                    if chunk:
                        output += chunk.decode('utf-8', errors='ignore')
                    else:
                        break
                except (OSError, IOError):
                    break
            else:
                # Small delay to avoid busy-waiting
                time.sleep(0.05)
        
        return output

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
                    # Use persistent PTY shell instead of subprocess
                    exit_code, stdout, stderr, cwd = self._run_in_shell(command, timeout=30)
                except Exception as e:
                    self.append_text(f"[X] Execution error: {str(e)}\n", "error")
                    break
                
                # Display output
                if stdout:
                    self.append_text(f"{stdout}\n", "info")
                
                # Result analysis: simple heuristic, not expensive AI call
                analysis = self._analyze_command_result(
                    command, 
                    stdout, 
                    stderr, 
                    exit_code,
                    cwd
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
                    failure_issue = analysis.get("issue", stderr or "No error details")
                    
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
                        
                        # Prepare analysis for next iteration (include cwd context)
                        error_analysis = {
                            "reason": failure_reason,
                            "issue": failure_issue[:200],
                            "output": stdout[:100] if stdout else "",
                            "cwd": cwd
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
