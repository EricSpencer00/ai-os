#!/usr/bin/env python3
"""
AuraOS Browser - Perplexity Comet-Inspired AI Browser
Features:
  - ChatGPT-like search interface
  - Firefox integration for web browsing
  - AI-powered search and recommendations
  - Conversation history
  - Smart web navigation
"""
import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import sys
import os
import json
import webbrowser
import shutil
import requests
from datetime import datetime
from pathlib import Path

# Smart URL detection: use host gateway IP when running inside VM
def get_agent_url():
    """Get the correct GUI agent URL - always localhost since agent runs locally."""
    return "http://localhost:8765"

AGENT_URL = get_agent_url()


class AuraOSBrowser:
    """AI-powered browser with Firefox integration"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Browser")
        self.root.geometry("1100x800")
        self.root.configure(bg='#0a0e27')
        
        # Enable proper window manager integration for resize/drag
        self.root.resizable(True, True)
        self.root.minsize(800, 500)
        
        # State
        self.search_history = []
        self.history_index = -1
        self.firefox_pid = None
        self.is_processing = False
        self.app_install_cache = {}  # Cache for app availability checks
        
        self.setup_ui()
        self.log_event("STARTUP", "AuraOS Browser initialized")
    
    def setup_ui(self):
        """Setup user interface"""
        # Top bar
        top_frame = tk.Frame(self.root, bg='#1a1e37', height=70)
        top_frame.pack(fill='x')
        
        # Open Firefox button
        firefox_btn = tk.Button(
            top_frame, text="[Web] Firefox", command=self.open_firefox,
            bg='#ff7f50', fg='#ffffff', font=('Arial', 11, 'bold'),
            relief='flat', cursor='hand2', padx=15, pady=12
        )
        firefox_btn.pack(side='left', padx=10, pady=10)
        
        # Title
        self.title_label = tk.Label(
            top_frame, text="AuraOS Browser - AI Search", 
            font=('Arial', 16, 'bold'), fg='#00ff88', bg='#1a1e37'
        )
        self.title_label.pack(side='left', padx=20, pady=10)
        
        # Status
        self.status_label = tk.Label(
            top_frame, text="Ready", font=('Arial', 10),
            fg='#6db783', bg='#1a1e37'
        )
        self.status_label.pack(side='right', padx=20, pady=10)
        
        # Main content
        main_frame = tk.Frame(self.root, bg='#0a0e27')
        main_frame.pack(fill='both', expand=True)
        
        # Left panel: Chat history
        left_panel = tk.Frame(main_frame, bg='#1a1e37', width=350)
        left_panel.pack(side='left', fill='both', padx=0, pady=0)
        
        history_title = tk.Label(
            left_panel, text="Search History", font=('Arial', 12, 'bold'),
            fg='#00d4ff', bg='#1a1e37'
        )
        history_title.pack(padx=10, pady=10)
        
        self.history_display = scrolledtext.ScrolledText(
            left_panel, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
            font=('Menlo', 9), relief='flat', padx=10, pady=10
        )
        self.history_display.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        self.history_display.config(state='disabled')
        
        self.append_history("Welcome to AuraOS Browser!", "system")
        self.append_history("\nYour search history will appear here.", "info")
        
        # Right panel: Main content
        right_panel = tk.Frame(main_frame, bg='#0a0e27')
        right_panel.pack(side='right', fill='both', expand=True)
        
        # Search/chat display
        self.output_area = scrolledtext.ScrolledText(
            right_panel, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
            font=('Menlo', 11), insertbackground='#00d4ff',
            relief='flat', padx=15, pady=15
        )
        self.output_area.pack(fill='both', expand=True)
        self.output_area.config(state='disabled')
        
        # Setup text tags
        self._setup_text_tags()
        
        # Welcome message
        self.show_welcome()
        
        # Input frame
        input_frame = tk.Frame(self.root, bg='#1a1e37', height=100)
        input_frame.pack(fill='x')
        
        # Search prompt
        prompt_label = tk.Label(
            input_frame, text="Search: ", font=('Menlo', 12, 'bold'),
            fg='#00ff88', bg='#1a1e37'
        )
        prompt_label.pack(side='left', padx=(15, 0), pady=10)
        
        # Search input
        self.search_input = tk.Entry(
            input_frame, bg='#2d3547', fg='#ffffff',
            font=('Menlo', 12), insertbackground='#00d4ff',
            relief='flat', bd=0
        )
        self.search_input.pack(side='left', fill='both', expand=True, 
                               ipady=12, padx=(5, 10), pady=10)
        self.search_input.bind('<Return>', lambda e: self.search())
        self.search_input.bind('<Up>', self.history_up)
        self.search_input.bind('<Down>', self.history_down)
        self.search_input.bind('<Escape>', lambda e: self.search_input.delete(0, tk.END))
        
        # Button frame
        btn_frame = tk.Frame(input_frame, bg='#1a1e37')
        btn_frame.pack(side='right', padx=10, pady=10)
        
        search_btn = tk.Button(
            btn_frame, text="Search", command=self.search,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 11, 'bold'),
            relief='flat', cursor='hand2', padx=15, pady=8
        )
        search_btn.pack(side='left', padx=5)
        
        clear_btn = tk.Button(
            btn_frame, text="Clear", command=self.clear_chat,
            bg='#9cdcfe', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=12, pady=8
        )
        clear_btn.pack(side='left', padx=5)
        
        # Focus search input
        self.search_input.focus()
    
    def ensure_app_installed(self, app_name):
        """
        Smart app installer - checks if app is installed and installs if needed.
        Works on Linux VMs (Ubuntu/Debian).
        
        Args:
            app_name: Name of app to check/install (e.g., 'firefox', 'chromium')
        
        Returns:
            bool: True if app is available, False if installation failed
        """
        # Check cache first
        if app_name in self.app_install_cache:
            return self.app_install_cache[app_name]
        
        try:
            # Check if app is already installed
            if shutil.which(app_name):
                self.app_install_cache[app_name] = True
                return True
            
            # App not found locally - try to install via GUI Agent
            self.append(f"[*] {app_name.title()} not found. Installing via smart installer...\n", "info")
            self.log_event("APP_INSTALL_START", f"Installing {app_name}")
            
            # Send install request to GUI Agent
            install_query = f"install {app_name} application"
            response = requests.post(
                f"{AGENT_URL}/ask",
                json={"query": install_query},
                timeout=300  # Allow up to 5 minutes for installation
            )
            
            if response.status_code == 200:
                result = response.json()
                executed = result.get("executed", [])
                
                # Verify installation
                if shutil.which(app_name):
                    self.append(f"[OK] {app_name.title()} installed successfully!\n", "success")
                    self.app_install_cache[app_name] = True
                    self.log_event("APP_INSTALL_SUCCESS", app_name)
                    return True
                else:
                    self.append(f"[!] Installation attempted but {app_name} still not found.\n", "warning")
                    self.log_event("APP_INSTALL_VERIFY_FAILED", app_name)
                    self.app_install_cache[app_name] = False
                    return False
            else:
                self.append(f"[X] Failed to install {app_name}: {response.text[:100]}\n", "error")
                self.log_event("APP_INSTALL_ERROR", f"{app_name}: {response.text[:50]}")
                self.app_install_cache[app_name] = False
                return False
                
        except requests.exceptions.ConnectionError:
            self.append(f"[X] Cannot reach installer: GUI Agent offline\n", "error")
            self.log_event("APP_INSTALL_CONNECTION_ERROR", app_name)
            self.app_install_cache[app_name] = False
            return False
        except Exception as e:
            self.append(f"[X] Installation error: {str(e)}\n", "error")
            self.log_event("APP_INSTALL_EXCEPTION", f"{app_name}: {str(e)}")
            self.app_install_cache[app_name] = False
            return False
    
    def _perform_install_on_vm(self, app_name):
        """
        Direct VM installation using multipass (fallback method).
        Installs app via apt-get inside the Multipass VM.
        """
        try:
            # Map common app names to package names
            app_map = {
                "firefox": "firefox",
                "chromium": "chromium-browser",
                "chrome": "chromium-browser",
                "git": "git",
                "python": "python3",
                "node": "nodejs",
                "npm": "npm",
                "docker": "docker.io",
            }
            
            package_name = app_map.get(app_name.lower(), app_name.lower())
            
            # Try multipass install
            cmd = [
                "multipass", "exec", "auraos-multipass", "--",
                "sudo", "bash", "-c",
                f"apt-get update -qq && apt-get install -y {package_name}"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception:
            return False
    
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
            "link": {"foreground": "#569cd6", "font": ('Menlo', 10, 'underline')},
        }
        for tag_name, config in tags.items():
            self.output_area.tag_config(tag_name, **config)
        
        # History display tags
        self.history_display.tag_config("system", foreground="#00d4ff", font=('Menlo', 9, 'bold'))
        self.history_display.tag_config("search", foreground="#00ff88", font=('Menlo', 9, 'bold'))
        self.history_display.tag_config("info", foreground="#9cdcfe", font=('Menlo', 9))
    
    def show_welcome(self):
        """Show welcome message"""
        self.output_area.config(state='normal')
        self.output_area.delete(1.0, tk.END)
        self.output_area.config(state='disabled')
        
        self.append("AuraOS Browser\n", "system")
        self.append("Perplexity Comet-Inspired AI Search\n\n", "system")
        self.append("Search for anything:\n", "info")
        self.append("  • python tutorials\n", "output")
        self.append("  • how to set up a docker container\n", "output")
        self.append("  • latest news on artificial intelligence\n", "output")
        self.append("  • compare python vs javascript for web development\n", "output")
        self.append("  • machine learning best practices\n\n", "output")
        self.append("Features:\n", "info")
        self.append("  [Web] Firefox integration - open results in browser\n", "output")
        self.append("  ⚡ AI-powered search recommendations\n", "output")
        self.append("  💬 Conversation history on the left\n", "output")
        self.append("  📚 Follow-up questions and related topics\n\n", "output")
        self.append("Type your search query and press Enter to begin!\n", "success")
    
    def search(self):
        """Perform AI search"""
        if self.is_processing:
            return
        
        query = self.search_input.get().strip()
        if not query:
            return
        
        self.search_history.append(query)
        self.history_index = len(self.search_history)
        self.search_input.delete(0, tk.END)
        
        # Add to history display
        self.append_history(f"\n[Q] {query}", "search")
        
        # Display search request
        self.append(f"[Search] {query}\n\n", "ai")
        
        # Run search in thread
        threading.Thread(target=self._perform_search, args=(query,), daemon=True).start()
    
    def _perform_search(self, query):
        """Perform actual search - opens Firefox with search URL directly"""
        try:
            self.is_processing = True
            self.update_status("Searching...", "#00ff88")
            
            # Build search URL (use DuckDuckGo for privacy)
            import urllib.parse
            search_url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
            
            self.append(f"[*] Searching for: {query}\n", "info")
            self.append(f"[*] Opening: {search_url}\n", "info")
            
            # Try direct Firefox launch first
            if shutil.which("firefox"):
                try:
                    env = os.environ.copy()
                    env["DISPLAY"] = env.get("DISPLAY", ":99")
                    
                    subprocess.Popen(
                        ["firefox", search_url],
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    self.append("[OK] Search opened in Firefox\n", "success")
                    self.log_event("SEARCH_SUCCESS", f"Direct: {query[:60]}")
                    self.is_processing = False
                    self.update_status("Ready", "#6db783")
                    return
                except Exception as e:
                    self.append(f"[!] Direct launch failed: {e}\n", "warning")
            
            # Fallback to GUI Agent
            self.append("[*] Trying via GUI Agent...\n", "info")
            try:
                search_request = f"open firefox and navigate to {search_url}"
                response = requests.post(
                    f"{AGENT_URL}/ask",
                    json={"query": search_request},
                    timeout=180
                )
                
                if response.status_code == 200:
                    result = response.json()
                    executed = result.get("executed", [])
                    self.append(f"[OK] Agent executed {len(executed)} actions.\n", "success")
                    for action in executed:
                        act = action.get("action", {})
                        self.append(f"  - {act}\n", "output")
                    self.log_event("SEARCH_SUCCESS", f"Agent search: {query[:60]}")
                else:
                    self.append(f"[X] Agent Error: {response.text}\n", "error")
                    self.log_event("SEARCH_ERROR", response.text)
                    
            except requests.exceptions.ConnectionError:
                self.append("[X] Cannot reach GUI Agent\n", "error")
                self.append(f"\n  Fallback: Open Firefox manually and go to:\n", "info")
                self.append(f"  {search_url}\n\n", "info")
                self.log_event("SEARCH_EXCEPTION", "Connection refused")
            except requests.exceptions.Timeout:
                self.append("[X] Request timed out\n", "error")
                self.log_event("SEARCH_EXCEPTION", "Timeout")
                
        except Exception as e:
            self.append(f"[X] Unexpected error: {e}\n", "error")
            self.log_event("SEARCH_EXCEPTION", str(e))
            
        self.is_processing = False
        self.update_status("Ready", "#6db783")

    def open_firefox(self, url=None):
        """Open Firefox browser - direct launch with proper environment"""
        try:
            self.update_status("Opening Firefox...", "#ff7f50")
            self.append("[*] Starting Firefox...\n", "info")
            
            # Build command
            firefox_cmd = ["firefox"]
            if url:
                firefox_cmd.append(url)
            
            # Set proper environment for snap Firefox
            env = os.environ.copy()
            env["DISPLAY"] = env.get("DISPLAY", ":99")
            env["XDG_RUNTIME_DIR"] = "/run/user/1000"
            env["HOME"] = os.path.expanduser("~")
            
            # Check if firefox is available
            if shutil.which("firefox"):
                try:
                    subprocess.Popen(
                        firefox_cmd,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    self.append("[OK] Firefox launched\n", "success")
                    self.update_status("Ready", "#6db783")
                    self.log_event("FIREFOX_OPENED", "direct launch")
                    return
                except Exception as e:
                    self.append(f"[!] Launch failed: {e}\n", "warning")
                    self.log_event("FIREFOX_DIRECT_FAILED", str(e))
            
            # Fallback: Try via GUI Agent
            self.append("[*] Trying via GUI Agent...\n", "info")
            try:
                query = f"open firefox{' and navigate to ' + url if url else ''}"
                response = requests.post(
                    f"{AGENT_URL}/ask",
                    json={"query": query},
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    executed = result.get("executed", [])
                    self.append(f"[OK] Firefox via agent\n", "success")
                    self.log_event("FIREFOX_OPENED", "via agent")
                else:
                    self.append(f"[X] Agent Error: {response.text}\n", "error")
                    self.log_event("FIREFOX_ERROR", response.text)
            except requests.exceptions.ConnectionError:
                self.append("[X] GUI Agent not reachable\n", "error")
                self.append("  Firefox may not be installed. Run:\n", "info")
                self.append("  sudo apt-get install -y firefox\n", "info")
                self.log_event("FIREFOX_ERROR", "Connection refused")
                
            self.update_status("Ready", "#6db783")
        
        except Exception as e:
            self.append(f"[X] Error opening Firefox: {str(e)}\n", "error")
            self.update_status("Error", "#f48771")
            self.log_event("FIREFOX_ERROR", str(e))
    
    def clear_chat(self):
        """Clear chat history"""
        self.output_area.config(state='normal')
        self.output_area.delete(1.0, tk.END)
        self.output_area.config(state='disabled')
        self.show_welcome()
        self.search_input.focus()
    
    def append(self, text, tag="output"):
        """Append text to output area"""
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, text, tag)
        self.output_area.see(tk.END)
        self.output_area.config(state='disabled')
        self.root.update_idletasks()
    
    def append_history(self, text, tag="info"):
        """Append text to history display"""
        self.history_display.config(state='normal')
        self.history_display.insert(tk.END, text, tag)
        self.history_display.see(tk.END)
        self.history_display.config(state='disabled')
        self.root.update_idletasks()
    
    def update_status(self, text, color='#6db783'):
        """Update status label"""
        self.status_label.config(text=text, fg=color)
        self.root.update_idletasks()
    
    def history_up(self, event):
        """Navigate search history up"""
        if self.search_history and self.history_index > 0:
            self.history_index -= 1
            self.search_input.delete(0, tk.END)
            self.search_input.insert(0, self.search_history[self.history_index])
    
    def history_down(self, event):
        """Navigate search history down"""
        if self.history_index < len(self.search_history) - 1:
            self.history_index += 1
            self.search_input.delete(0, tk.END)
            self.search_input.insert(0, self.search_history[self.history_index])
        elif self.history_index == len(self.search_history) - 1:
            self.history_index = len(self.search_history)
            self.search_input.delete(0, tk.END)
    
    def log_event(self, action, message):
        """Log event to file"""
        try:
            log_path = "/tmp/auraos_browser.log"
            with open(log_path, "a") as f:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                f.write(f"[{ts}] {action}: {message}\n")
        except:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSBrowser(root)
    root.mainloop()
