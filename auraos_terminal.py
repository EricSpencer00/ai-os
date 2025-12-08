#!/usr/bin/env python3
"""
AuraOS Terminal - HARDENED VERSION
English to Bash with defensive extraction, binary fallbacks, injection detection, and safe execution
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
import shlex
import pty
import select
import time
import signal
import fcntl
import random
import struct

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

    @staticmethod
    def _clean_shell_output(text: str) -> str:
        """Strip ANSI escape codes and trim whitespace for clearer display."""
        if not text:
            return ""
        ansi_escape = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
        return ansi_escape.sub("", text).strip()
    
    @staticmethod
    def _clean_shell_noise(text: str, command: str = "") -> str:
        """Remove bash prompts, command echoes, and shell artifacts from output.
        
        This cleans up output to show only the actual command results,
        hiding bash-5.1$ prompts, printf commands, pwd, markers, etc.
        """
        if not text:
            return ""
        
        # First pass: Remove bash prompts from ANYWHERE in the text
        # This handles cases where prompt appears mid-line like: bash-5.1$ [output
        text = re.sub(r'bash-[\d.]+\$ ', '', text)
        text = re.sub(r'sh-[\d.]+\$ ', '', text)
        text = re.sub(r'zsh-[\d.]+\$ ', '', text)
        # Also handle case without space after $
        text = re.sub(r'bash-[\d.]+\$', '', text)
        text = re.sub(r'sh-[\d.]+\$', '', text)
        text = re.sub(r'zsh-[\d.]+\$', '', text)
        
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip printf commands (internal markers)
            if stripped.startswith("printf '") or stripped.startswith('printf "'):
                continue
            
            # Skip internal variable assignments (__e__=$?)
            if stripped.startswith('__e__=') or stripped == '__e__=$?':
                continue
            
            # Skip lines containing our internal markers
            if '__CMD_START_' in stripped or '__CMD_END_' in stripped:
                continue
            if '__STATUS__' in stripped:
                continue
            
            # Skip the exact command we ran (echoed back)
            if command and stripped == command.strip():
                continue
            
            # Skip pwd command echo
            if stripped == 'pwd':
                continue
            
            # Skip standalone empty brackets/prompts and empty lines
            if stripped in ['[]', '()', '']:
                continue
            
            clean_lines.append(line)
        
        # Strip leading/trailing empty lines
        result = '\n'.join(clean_lines)
        return result.strip()
    
    def _init_shell(self):
        """Initialize persistent PTY shell session using openpty() + fork/exec"""
        try:
            # Ensure DISPLAY is set for X11 (important when launched from GUI)
            if 'DISPLAY' not in os.environ:
                os.environ['DISPLAY'] = ':99'
            
            # Create a PTY pair (master, slave)
            master_fd, slave_fd = pty.openpty()
            
            # Fork a child process
            self.shell_pid = os.fork()
            
            if self.shell_pid == 0:
                # ===== CHILD PROCESS =====
                try:
                    # Close master fd in child (we only need slave)
                    os.close(master_fd)
                    
                    # Create a new session (detach from parent's controlling terminal)
                    os.setsid()
                    
                    # Duplicate slave fd to stdin/stdout/stderr
                    os.dup2(slave_fd, 0)  # stdin
                    os.dup2(slave_fd, 1)  # stdout  
                    os.dup2(slave_fd, 2)  # stderr
                    
                    # Close the original slave fd (no longer needed after dup2)
                    os.close(slave_fd)
                    
                    # Configure terminal attributes
                    import termios
                    
                    # Set terminal size
                    rows, cols = 24, 80
                    fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
                    
                    # Get and configure terminal attributes - DISABLE ECHO to hide shell noise
                    try:
                        attrs = termios.tcgetattr(0)
                        # attrs[3] is c_lflag (local flags)
                        # DISABLE ECHO - we don't want to see commands echoed back
                        # Keep ICANON for line-buffered input
                        attrs[3] &= ~termios.ECHO  # Turn OFF echo
                        attrs[3] |= termios.ICANON  # Keep line buffering
                        # attrs[6] is cc (control characters)
                        attrs[6][termios.VMIN] = 0    # Non-blocking read
                        attrs[6][termios.VTIME] = 0   # No timeout
                        termios.tcsetattr(0, termios.TCSANOW, attrs)
                    except:
                        pass  # Terminal attributes may not be fully available
                    
                    # Set environment variables
                    os.environ['LINES'] = str(rows)
                    os.environ['COLUMNS'] = str(cols)
                    
                    # Execute bash interactively
                    # +H disables history expansion for more reliable output parsing
                    os.execvp("bash", ["bash", "--noprofile", "--norc", "-i", "+H"])
                    # If execvp succeeds, this line is never reached
                    # If execvp fails, the exception is caught below
                    
                except (OSError, ValueError) as child_err:
                    # If exec fails, write error to stderr and exit
                    print(f"[SHELL_INIT_ERROR] {child_err}", file=sys.stderr)
                    sys.exit(127)
                    
            else:
                # ===== PARENT PROCESS =====
                # Close slave fd in parent (we only need master)
                os.close(slave_fd)
                self.shell_fd = master_fd
                
                # Set master fd to non-blocking for reading output
                flags = fcntl.fcntl(self.shell_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.shell_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                
                # Give the shell a moment to initialize
                time.sleep(0.5)
                
                # Verify shell process is still alive
                try:
                    # Check if child is still running (non-blocking wait)
                    pid_result, status = os.waitpid(self.shell_pid, os.WNOHANG)
                    
                    if pid_result == self.shell_pid:
                        # Shell exited immediately (error)
                        exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                        print(f"[ERROR] Shell process exited immediately with code {exit_code}", file=sys.stderr)
                        self.shell_pid = None
                        self.shell_fd = None
                        try:
                            os.close(master_fd)
                        except:
                            pass
                except ChildProcessError:
                    # This is expected if child is still running
                    pass
                
                print(f"[DEBUG] Shell initialized successfully: pid={self.shell_pid}, fd={self.shell_fd}", file=sys.stderr)
                    
        except Exception as e:
            import traceback
            print(f"[ERROR] Failed to initialize shell: {e}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
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
    
    def _request_password(self):
        """Show a simple password input dialog for sudo commands"""
        import tkinter.simpledialog as simpledialog
        password = simpledialog.askstring("Password Required", "Enter password:", show='*')
        return password

    def _run_subprocess_fallback(self, command, timeout=60):
        """Fallback execution path when PTY shell is unavailable: use subprocess.run."""
        try:
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
            return proc.returncode, proc.stdout or "", proc.stderr or "", os.getcwd()
        except Exception as e:
            return 1, "", str(e), os.getcwd()

    def _should_try_sudo(self, command):
        """Heuristic: decide whether to attempt running command with sudo.
        Targets package managers, systemctl, chown/chmod on system paths, snap, and writing to /opt or /usr."""
        low = command.lower()
        triggers = ['apt-get', 'apt ', 'dnf ', 'yum ', 'pacman', 'systemctl', 'snap', 'add-apt-repository', 'chown ', 'chmod ', 'mount ', 'umount ', 'mkfs', '/opt/', '/usr/', 'iptables', 'ufw', 'service ', 'reboot']
        for t in triggers:
            if t in low:
                return True
        return False

    def _attempt_with_sudo(self, command, timeout=60):
        """Try to run given command with sudo. First try non-interactive sudo, then prompt for password if needed."""
        try:
            # If command already contains sudo, just run it
            if command.strip().startswith('sudo'):
                return self._run_in_shell(command, timeout=timeout)

            # Try non-interactive sudo first
            sudo_try = f"sudo -n {command}"
            code, out, err, cwd = self._run_in_shell(sudo_try, timeout=10)
            if code == 0:
                return code, out, err, cwd

            # If non-interactive sudo failed due to password, prompt
            password = self._request_password()
            if not password:
                return 1, "", "sudo password required but not provided", os.getcwd()

            # Safely quote password and command
            safe_pw = shlex.quote(password)
            # Use -S to read password from stdin, -p '' to suppress prompt
            full_cmd = f"echo {safe_pw} | sudo -S -p '' {command}"
            return self._run_in_shell(full_cmd, timeout=timeout)
        except Exception as e:
            return 1, "", str(e), os.getcwd()
        
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
        self.append_text("[Terminal] English to Bash - Auto Recovery (Hardened)\n", "info")
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
        """Build the system prompt for command generation (strict output format, with platform info)"""
        import platform
        os_name = platform.system()
        
        platform_guidance = ""
        if os_name == 'Darwin':
            platform_guidance = """
PLATFORM: macOS
- Use ifconfig or networksetup instead of 'ip'
- Use netstat, lsof, or netstat -tuln instead of 'ss'
- Use 'brew install <pkg>' instead of 'apt-get' if package management needed
- Use 'last reboot' or 'who -b' for reboot info"""
        elif os_name == 'Linux':
            platform_guidance = """
PLATFORM: Linux
- Use 'ip' for network configuration
- Use 'ss' or 'netstat' for listening ports
- Use 'apt-get' or 'apt' for package management
- Use 'who -b' for reboot time"""
        
        return f"""You are a highly capable shell command generator that converts plain-English requests into fully self-contained, executable shell commands for a Unix-like environment. You must produce all necessary commands so that the user never needs to perform any manual steps.{platform_guidance}

CRITICAL: Your response must contain ONLY the bash command(s). No explanations, no preamble, no descriptions.

Core Requirements:
1. Completeness: Generate complete commands that include any prerequisite steps.
2. Always consider dependencies, file/directory existence, and command safety.
3. No Placeholders: All paths and arguments must be explicitly specified.
4. Multiple Commands: If more than one command is required, list each command on a separate line.
5. Edge Cases: Use flags for non-interactive execution if needed.

OUTPUT FORMAT (CRITICAL):
- Start directly with the command
- No introductory text whatsoever
- No markdown, code fences, or formatting
- If unsafe or cannot convert: output only "CANNOT_CONVERT"

REMEMBER: Output ONLY the command(s). Nothing else."""

    def _extract_command_from_response(self, response_text):
        """Extract command from AI response. Aggressively defensive against markup and injection."""
        original_text = response_text
        
        # Strip code fences with optional language markers: ```bash, ``` bash, ``` etc.
        response_text = re.sub(r"```\s*(?:[a-zA-Z0-9_+-]*)", "", response_text)
        
        # Remove inline backticks: `cmd` -> cmd
        response_text = re.sub(r"`([^`]*)`", r"\1", response_text)
        
        # Strip any remaining backticks
        response_text = response_text.replace('`', '')
        
        lines = response_text.strip().split('\n')
        
        command_lines = []
        
        # Aggressive preamble/description patterns to skip
        desc_patterns = [
            'here is', 'this command', 'to accomplish', 'to convert',
            'example:', 'output:', 'note:', 'first,', 'then,', 'finally,',
            'the command', 'you can', 'alternatively', 'use:', 'try:',
            'run:', 'execute:', 'the bash', 'a command', 'to check',
            'result:', 'note that', 'if you', 'you need to', 'make sure',
            'first run', 'then', 'after that', 'next', 'to do this',
            'option:', 'you should', 'remember to', 'important:', 'step'
        ]
        
        for line in lines:
            line = line.strip()
            
            # Skip empty or comment lines
            if not line or line.startswith('#'):
                continue
            
            line_lower = line.lower()
            
            # Skip language marker lines (bash, python, etc)
            if line_lower in ('bash', 'sh', 'shell', 'zsh', 'ksh', 'python', 'ruby', 'javascript', 'node'):
                continue
            
            # Skip obvious preamble patterns
            if any(line_lower.startswith(p) or line_lower.endswith(p) for p in desc_patterns):
                continue
            
            # Skip lines that end with colon and don't contain command-like chars
            if line.endswith(':') and not any(c in line for c in ['/', '-', '$', '~', '|', '&', ';']):
                continue
            
            # Handle "Command: ..." or "To fix: ..." patterns
            if re.match(r'^(command:|to fix:)', line_lower):
                parts = line.split(':', 1)[1].strip()
                if parts:
                    command_lines.append(parts)
                continue
            
            # This line looks like a real command
            if line:
                command_lines.append(line)
        
        result = '\n'.join(command_lines) if command_lines else ""
        
        # Debug log if extraction was non-trivial
        if len(original_text) > 50 or '`' in original_text or '```' in original_text:
            import sys
            print(f"[DEBUG] Extraction: {repr(original_text[:100])} -> {repr(result[:100])}", file=sys.stderr)
        
        return result

    def _suggest_fallback(self, binary):
        """Suggest a fallback binary name for common tools (platform-aware)."""
        import platform
        is_mac = platform.system() == 'Darwin'
        
        fallbacks = {
            'python': 'python3',
            'pip': 'pip3',
            'node': 'nodejs',
            'ip': 'ifconfig' if is_mac else 'ip',
            'ss': 'netstat' if is_mac else 'ss',
        }
        return fallbacks.get(binary, binary)
    
    def _validate_command_safe(self, command):
        """Validate command: detect injection patterns, resolve binaries with fallbacks."""
        if not command or not command.strip():
            return False, "Empty command", ""
        
        # Check for injection patterns
        injection_patterns = [r"\$\(", r"\$\{", r"`;.*`"]
        for pattern in injection_patterns:
            if re.search(pattern, command):
                return False, f"Injection pattern: {pattern}", ""
        
        lines = command.strip().split('\n')
        corrected_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            tokens = line.split(None, 1)
            if not tokens:
                continue
            
            binary = tokens[0]
            args = tokens[1] if len(tokens) > 1 else ""
            
            # Strip any remaining backticks from binary name
            binary = binary.strip('`')
            
            # Resolve binary with fallbacks (python->python3, pip->pip3, etc)
            resolved = self._resolve_binary(binary)
            if not resolved:
                hint = self._suggest_fallback(binary)
                return False, f"Command not found: {binary} (try: {hint})", ""
            
            corrected_lines.append(f"{resolved} {args}".strip())
        
        if not corrected_lines:
            return False, "No valid commands", ""
        
        return True, "", '\n'.join(corrected_lines)
    
    def _resolve_binary(self, binary):
        """Resolve binary path; try common fallbacks including platform-specific (python->python3, ip->ifconfig on macOS, etc)."""
        import platform
        is_mac = platform.system() == 'Darwin'
        
        fallbacks_map = {
            'python': ['python3', 'python'],
            'pip': ['pip3', 'pip'],
            'node': ['nodejs', 'node'],
            'ip': (['ifconfig', 'networksetup'] if is_mac else ['ip']),
            'ss': (['netstat', 'lsof'] if is_mac else ['ss', 'netstat']),
        }
        
        candidates = [binary] + fallbacks_map.get(binary, [])
        
        for candidate in candidates:
            try:
                result = subprocess.run(
                    f"command -v {candidate}",
                    shell=True,
                    capture_output=True,
                    timeout=2,
                    text=True
                )
                if result.returncode == 0:
                    # Return the resolved path (last token from command -v output)
                    return result.stdout.strip().split()[-1]
            except:
                pass
        
        return None

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
        """Analyze if a command succeeded or failed, provide recovery hints for common errors."""
        # Check for sudo password prompt in output
        combined_output = stdout + stderr
        if "[sudo]" in combined_output or "password" in combined_output.lower() or "Password:" in combined_output:
            return {
                "success": False,
                "reason": "password_required",
                "issue": "Command requires password input",
                "hint": "User needs to enter password"
            }
        
        if exit_code == 0:
            return {"success": True, "reason": "exit code 0", "issue": "", "hint": ""}
        
        if exit_code != 0 and not stderr and stdout:
            return {"success": True, "reason": "exit code non-zero but has output", "issue": "", "hint": ""}
        
        # Check for common permission denied patterns
        if "permission denied" in stderr.lower() or "permission denied" in stdout.lower():
            return {
                "success": False,
                "reason": "permission_denied",
                "issue": stderr[:200] if stderr else stdout[:200],
                "hint": "Permission denied. Try with 'sudo' or check file permissions with 'ls -l'"
            }
        
        # Provide specific hints for common failures
        hint = ""
        if exit_code == 127:
            hint = "Command not found. Try: use python3 instead of python, pip3 instead of pip, nodejs instead of node."
        elif exit_code == 126:
            hint = "Permission denied. Consider adding 'chmod +x' first or use sudo."
        elif exit_code == 1:
            hint = "General failure. Check the error message above for details."
        elif exit_code == 2:
            hint = "Misuse of shell command. Check syntax and argument usage."
        
        return {
            "success": False,
            "reason": f"exit code {exit_code}",
            "issue": stderr[:200] if stderr else "No error output",
            "hint": hint
        }

    def _generate_command(self, user_request, error_analysis=None):
        """Generate a bash command using AI, with context for recovery and hints."""
        try:
            if error_analysis:
                cwd_context = f"Current directory: {error_analysis.get('cwd', '~')}\n" if error_analysis.get('cwd') else ""
                hint = error_analysis.get('hint', '')
                hint_text = f"HINT TO FIX: {hint}\n" if hint else ""
                prompt = f"""Fix this command that failed:
Original request: {user_request}
{cwd_context}{hint_text}Error: {error_analysis.get('issue', 'Unknown')}
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
                    # Validate command safety (dangerous patterns)
                    is_safe, reason = self._validate_command(command)
                    if not is_safe:
                        self.append_text(f"[!] Safety check failed: {reason}\n", "error")
                        return None
                    
                    # Try to resolve binaries early (catch missing commands before execution)
                    is_valid, err, corrected = self._validate_command_safe(command)
                    if not is_valid:
                        self.append_text(f"[!] Command validation failed: {err}\n", "error")
                        return None
                    if corrected:
                        command = corrected
                    
                    return command
                else:
                    if not command or "CANNOT_CONVERT" in command:
                        self.append_text("❌ Could not generate valid command\n", "error")
                    else:
                        self.append_text(f"❌ Command too long ({len(command)} chars)\n", "error")
                    return None
            else:
                self.append_text(f"❌ Server error: {response.text[:100]}\n", "error")
                return None
                
        except requests.exceptions.Timeout:
            self.append_text("⏱️ AI request timeout\n", "error")
            return None
        except requests.exceptions.ConnectionError:
            self.append_text(f"🔌 Cannot reach inference server: {INFERENCE_URL}\n", "error")
            return None
        except Exception as e:
            self.append_text(f"❌ Error: {str(e)}\n", "error")
            return None

    def _run_in_shell(self, command, timeout=30):
        """
        Execute command in persistent PTY shell and capture output safely.
        Validates command, resolves binaries with fallbacks, escapes safely.
        """
        if not self.shell_fd or self.shell_pid is None or self.shell_pid <= 0:
            # If PTY shell not available, fall back to subprocess.run to ensure commands still execute.
            print(f"[WARN] PTY shell unavailable, falling back to subprocess for: {command[:80]}", file=sys.stderr)
            return self._run_subprocess_fallback(command, timeout=max(30, timeout))
        
        try:
            # Pre-exec validation: detect injections and resolve binaries
            is_valid, err, corrected = self._validate_command_safe(command)
            if not is_valid:
                return 1, "", err, ""
            
            if corrected:
                command = corrected
            
            # Get current working directory before executing
            pwd_cmd = "pwd\n"
            os.write(self.shell_fd, pwd_cmd.encode())
            time.sleep(0.1)
            cwd = self._read_shell_output(timeout=1).strip().split('\n')[-1]
            
            # Use unique markers to avoid collision (PID + random UUID)
            marker_uuid = f"{os.getpid()}_{random.randint(100000, 999999)}"
            marker_start = f"__CMD_START_{marker_uuid}__"
            marker_end = f"__CMD_END_{marker_uuid}__"
            
            # Build safe command using printf (avoids echo interpretation)
            # Capture exit code safely in a variable
            full_command = (
                f"printf '%s\\n' '{marker_start}'\n"
                f"{command}\n"
                f"__e__=$?\n"
                f"printf '__STATUS__%s__/STATUS__\\n' \"$__e__\"\n"
                f"printf '%s\\n' '{marker_end}'\n"
            )
            
            # Debug logging
            import sys
            print(f"[DEBUG] Executing: {repr(command[:80])}", file=sys.stderr)
            
            os.write(self.shell_fd, full_command.encode())
            
            # Capture output with timeout, exit early when end marker is found
            output = self._read_shell_output(timeout=min(timeout, 10), end_marker=marker_end)
            print(f"[DEBUG] Output length: {len(output)}, looking for markers", file=sys.stderr)
            
            # Parse output between markers
            if marker_start in output and marker_end in output:
                start_idx = output.find(marker_start) + len(marker_start)
                end_idx = output.find(marker_end)
                captured = output[start_idx:end_idx].strip()
                
                # Extract exit status
                status_match = re.search(r"__STATUS__(\d+)__/STATUS__", captured)
                exit_code = int(status_match.group(1)) if status_match else 0
                
                # Remove status line and clean up any shell noise from output
                result_output = re.sub(r"__STATUS__\d+__/STATUS__\n?", "", captured)
                
                # Remove bash prompts, command echoes, and other shell noise
                result_output = self._clean_shell_noise(result_output, command)
                
                return exit_code, result_output, "", cwd
            else:
                print(f"[DEBUG] Markers not found in output", file=sys.stderr)
                return 0, output, "", cwd
                
        except Exception as e:
            import traceback
            print(f"[DEBUG] Exception: {e}\n{traceback.format_exc()}", file=sys.stderr)
            return 1, "", str(e), ""
    
    def _read_shell_output(self, timeout=5, end_marker=None):
        """Read available output from shell with timeout and optional end marker detection"""
        if not self.shell_fd:
            return ""
        
        output = ""
        start_time = time.time()
        no_data_count = 0
        
        while time.time() - start_time < timeout:
            try:
                ready, _, _ = select.select([self.shell_fd], [], [], 0.05)
                if ready:
                    chunk = os.read(self.shell_fd, 4096)
                    if chunk:
                        output += chunk.decode('utf-8', errors='ignore')
                        no_data_count = 0  # Reset counter when we get data
                        
                        # If end marker is specified and found, stop early
                        if end_marker and end_marker in output:
                            break
                    else:
                        break
                else:
                    # No data available right now
                    no_data_count += 1
                    
                    # If we have data and haven't received anything in 3 iterations,
                    # assume command is done
                    if output and no_data_count >= 3:
                        break
                    
                    time.sleep(0.01)
            except (OSError, IOError):
                break
        
        return output

    def _convert_and_execute(self, user_request):
        """Convert English to bash and execute with AI-driven error recovery"""
        try:
            error_analysis = None
            
            while self.retry_count < self.max_retries:
                # Generate command
                command = self._generate_command(user_request, error_analysis)
                if not command:
                    break
                
                self.append_text(f"Command: {command}\n", "command")
                
                # Execute
                self.append_text("⚡ Executing...\n", "info")
                try:
                    exit_code, stdout, stderr, cwd = self._run_in_shell(command, timeout=30)
                except Exception as e:
                    self.append_text(f"❌ Execution error: {str(e)}\n", "error")
                    break
                
                # Display output (cleaned for readability)
                if stdout:
                    clean_stdout = self._clean_shell_output(stdout)
                    if clean_stdout:
                        self.append_text(f"{clean_stdout}\n", "info")
                
                # Result analysis
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
                    self.retry_count = 0  # CRITICAL: Reset retry counter on success
                    return
                else:
                    # Command failed - prepare for recovery
                    failure_reason = analysis.get("reason", "Unknown error")
                    failure_issue = analysis.get("issue", stderr or "No error details")
                    failure_hint = analysis.get("hint", "")
                    
                    # Special handling for password prompts and permission issues
                    if failure_reason == "password_required":
                        self.append_text(f"\n🔐 Password required:\n", "info")
                        self.append_text(f"Command: {command}\n\n", "command")

                        # Show password input field
                        password = self._request_password()
                        if password:
                            # Re-run with password via sudo -S (read from stdin)
                            self.append_text(f"[*] Retrying with password...\n", "info")
                            try:
                                safe_pw = shlex.quote(password)
                                full_cmd = f"echo {safe_pw} | sudo -S -p '' {command.replace('sudo ', '')}"
                                exit_code, stdout, stderr, cwd = self._run_in_shell(full_cmd, timeout=30)

                                if stdout:
                                    clean = self._clean_shell_output(stdout)
                                    if clean:
                                        self.append_text(f"{clean}\n", "info")

                                if exit_code == 0:
                                    self.append_text(f"[OK] Command succeeded\n", "success")
                                    self.status_label.config(text="Ready", fg='#6db783')
                                    self.is_processing = False
                                    self.retry_count = 0
                                    return
                            except Exception as e:
                                self.append_text(f"[!] Password execution failed: {e}\n", "error")
                        else:
                            self.append_text(f"[!] Password entry cancelled\n", "error")

                        # Fall through to retry logic

                    # If permission denied or heuristics say this likely needs sudo, try automatically
                    if failure_reason == 'permission_denied' or self._should_try_sudo(command):
                        self.append_text(f"[!] Detected permission issue or privileged action. Trying with sudo...\n", "info")
                        try:
                            code, out, err, cwd = self._attempt_with_sudo(command, timeout=30)
                            if out:
                                clean = self._clean_shell_output(out)
                                if clean:
                                    self.append_text(f"{clean}\n", "info")
                            if code == 0:
                                self.append_text(f"[OK] Command succeeded with sudo\n", "success")
                                self.status_label.config(text="Ready", fg='#6db783')
                                self.is_processing = False
                                self.retry_count = 0
                                return
                            else:
                                self.append_text(f"[!] Sudo attempt failed: {err}\n", "error")
                                # feed this into error_analysis for AI retry
                                error_analysis = {
                                    'reason': 'sudo_attempt_failed',
                                    'issue': (err or out)[:200],
                                    'output': out[:100] if out else '',
                                    'hint': 'Tried sudo, still failed',
                                    'cwd': cwd
                                }
                                # continue to retry via AI below
                        except Exception as e:
                            self.append_text(f"[!] Sudo attempt exception: {e}\n", "error")
                    
                    if AUTO_RETRY_ERRORS and self.retry_count < self.max_retries - 1:
                        self.retry_count += 1
                        self.append_text(
                            f"[!] Command failed: {failure_reason}\n",
                            "error"
                        )
                        self.append_text(
                            f"🔄 Attempt {self.retry_count + 1}/{self.max_retries}...\n",
                            "retry"
                        )
                        
                        # Prepare analysis for next iteration (include hint from analyzer)
                        error_analysis = {
                            "reason": failure_reason,
                            "issue": failure_issue[:200],
                            "output": stdout[:100] if stdout else "",
                            "hint": failure_hint,  # CRITICAL: Pass hint to AI for recovery
                            "cwd": cwd
                        }
                        self.status_label.config(text=f"Retrying... ({self.retry_count}/{self.max_retries})", fg='#ff7f50')
                        continue
                    else:
                        # Max retries exceeded
                        self.append_text(
                            f"❌ Failed after {self.max_retries} attempts\n",
                            "error"
                        )
                        if failure_issue:
                            self.append_text(f"Error: {failure_issue}\n", "error")
                        break
                
        except Exception as e:
            self.append_text(f"❌ Unexpected error: {str(e)}\n", "error")
            
        self.is_processing = False
        self.status_label.config(text="Ready", fg='#6db783')

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSTerminal(root)
    root.mainloop()
