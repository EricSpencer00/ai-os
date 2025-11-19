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

class AuraOSLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS")
        self.root.geometry("600x400")
        self.root.configure(bg='#0a0e27')
        
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
        subprocess.Popen([sys.executable, "auraos_terminal.py"])
        self.status_label.config(text="System Ready", fg='#6db783')

    def launch_browser(self):
        self.status_label.config(text="Launching Browser...", fg='#ff7f50')
        subprocess.Popen([sys.executable, "auraos_browser.py"])
        self.status_label.config(text="System Ready", fg='#6db783')

    def launch_vision_os(self):
        self.status_label.config(text="Starting Vision Desktop...", fg='#00ff88')
        # Start daemon if not running?
        # Open VNC
        webbrowser.open("http://localhost:6080/vnc.html")
        self.status_label.config(text="Vision Desktop Opened", fg='#6db783')

    def launch_settings(self):
        self.status_label.config(text="Opening Settings...", fg='#9cdcfe')
        subprocess.Popen([sys.executable, "auraos_onboarding.py"])
        self.status_label.config(text="System Ready", fg='#6db783')

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSLauncher(root)
    root.mainloop()
