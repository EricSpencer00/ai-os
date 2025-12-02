#!/usr/bin/env python3
"""
AuraOS Launcher - Main Dashboard
"""
import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys
import threading
import webbrowser
import shutil

def find_app_path(app_name):
    """Find the path to an AuraOS application"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Search paths in order of preference
    search_paths = [
        os.path.join(script_dir, app_name),  # Same directory as launcher
        os.path.join("/opt/auraos/bin", app_name),  # VM install location
        os.path.join(os.path.expanduser("~"), "auraos", app_name),  # User home
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            return path
    
    return None

class AuraOSLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS")
        self.root.geometry("600x400")
        self.root.configure(bg='#0a0e27')
        
        # Set DISPLAY for VM environment
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":99"
        
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title = tk.Label(
            self.root, text="AuraOS", 
            font=('Arial', 32, 'bold'), fg='#00ff88', bg='#0a0e27'
        )
        title.pack(pady=(40, 10))
        
        subtitle = tk.Label(
            self.root, text="AI-Powered Operating System", 
            font=('Arial', 12), fg='#9cdcfe', bg='#0a0e27'
        )
        subtitle.pack(pady=(0, 40))
        
        # Buttons Frame
        btn_frame = tk.Frame(self.root, bg='#0a0e27')
        btn_frame.pack(expand=True)
        
        # 1. Terminal
        term_btn = tk.Button(
            btn_frame, text="💻 AI Terminal", command=self.launch_terminal,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 14, 'bold'),
            width=20, pady=10, relief='flat', cursor='hand2'
        )
        term_btn.grid(row=0, column=0, padx=10, pady=10)
        
        # 2. Browser
        browser_btn = tk.Button(
            btn_frame, text="🌐 AI Browser", command=self.launch_browser,
            bg='#ff7f50', fg='#ffffff', font=('Arial', 14, 'bold'),
            width=20, pady=10, relief='flat', cursor='hand2'
        )
        browser_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # 3. Vision OS (VNC)
        vision_btn = tk.Button(
            btn_frame, text="👁️ Vision Desktop", command=self.launch_vision_os,
            bg='#00ff88', fg='#0a0e27', font=('Arial', 14, 'bold'),
            width=20, pady=10, relief='flat', cursor='hand2'
        )
        vision_btn.grid(row=1, column=0, padx=10, pady=10)
        
        # 4. Settings
        settings_btn = tk.Button(
            btn_frame, text="⚙️ Settings", command=self.launch_settings,
            bg='#2d3547', fg='#ffffff', font=('Arial', 14, 'bold'),
            width=20, pady=10, relief='flat', cursor='hand2'
        )
        settings_btn.grid(row=1, column=1, padx=10, pady=10)
        
        # Status Bar
        self.status_label = tk.Label(
            self.root, text="System Ready", 
            font=('Arial', 10), fg='#6db783', bg='#0a0e27'
        )
        self.status_label.pack(side='bottom', pady=10)

    def launch_terminal(self):
        self.status_label.config(text="Launching Terminal...", fg='#00d4ff')
        self.root.update_idletasks()
        
        def _launch():
            try:
                terminal_path = find_app_path("auraos_terminal.py")
                if terminal_path:
                    # Terminal is now a Tkinter GUI app, launch directly
                    subprocess.Popen(
                        [sys.executable, terminal_path],
                        env=os.environ.copy(),
                        start_new_session=True
                    )
                    self.status_label.config(text="System Ready", fg='#6db783')
                else:
                    raise FileNotFoundError("auraos_terminal.py not found")
            except Exception as e:
                self.status_label.config(text=f"Error: {str(e)[:30]}", fg='#ff0000')
        
        threading.Thread(target=_launch, daemon=True).start()

    def launch_browser(self):
        self.status_label.config(text="Launching Browser...", fg='#ff7f50')
        self.root.update_idletasks()
        
        def _launch():
            try:
                browser_path = find_app_path("auraos_browser.py")
                if browser_path:
                    subprocess.Popen(
                        [sys.executable, browser_path],
                        env=os.environ.copy(),
                        start_new_session=True
                    )
                else:
                    # Fallback: try Firefox directly
                    if shutil.which("firefox"):
                        subprocess.Popen(["firefox"], start_new_session=True)
                    else:
                        raise FileNotFoundError("No browser application found")
                self.status_label.config(text="System Ready", fg='#6db783')
            except Exception as e:
                self.status_label.config(text=f"Error: {str(e)[:30]}", fg='#ff0000')
        
        threading.Thread(target=_launch, daemon=True).start()

    def launch_vision_os(self):
        self.status_label.config(text="Launching Vision Desktop...", fg='#00ff88')
        self.root.update_idletasks()
        
        def _launch():
            try:
                vision_path = find_app_path("auraos_vision.py")
                if vision_path:
                    # Launch the Vision app directly
                    subprocess.Popen(
                        [sys.executable, vision_path],
                        env=os.environ.copy(),
                        start_new_session=True
                    )
                    self.status_label.config(text="System Ready", fg='#6db783')
                else:
                    # Fallback: open VNC in browser
                    import webbrowser as wb
                    vnc_url = "http://localhost:6080/vnc.html"
                    if shutil.which("firefox"):
                        subprocess.Popen(
                            ["firefox", vnc_url],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                    else:
                        wb.open(vnc_url)
                    self.status_label.config(text="System Ready", fg='#6db783')
            except Exception as e:
                self.status_label.config(text=f"Error: {str(e)[:30]}", fg='#ff0000')
        
        threading.Thread(target=_launch, daemon=True).start()

    def launch_settings(self):
        self.status_label.config(text="Opening Settings...", fg='#9cdcfe')
        self.root.update_idletasks()
        
        def _launch():
            try:
                settings_path = find_app_path("auraos_onboarding.py")
                if settings_path:
                    subprocess.Popen(
                        [sys.executable, settings_path],
                        env=os.environ.copy(),
                        start_new_session=True
                    )
                else:
                    # Fallback: try system settings
                    if shutil.which("xfce4-settings-manager"):
                        subprocess.Popen(["xfce4-settings-manager"], start_new_session=True)
                    else:
                        raise FileNotFoundError("No settings application found")
                self.status_label.config(text="System Ready", fg='#6db783')
            except Exception as e:
                self.status_label.config(text=f"Error: {str(e)[:30]}", fg='#ff0000')
        
        threading.Thread(target=_launch, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSLauncher(root)
    root.mainloop()
