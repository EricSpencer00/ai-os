#!/usr/bin/env python3
"""
AuraOS Onboarding & Startup Screen
Provides a polished, sci-fi "Real OS" startup experience.
"""
import tkinter as tk
import time
import threading
import sys
import os
import subprocess
import requests
import random

class AuraOSOnboarding:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AuraOS Initialization")
        
        # Fullscreen and black background
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='black')
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        
        # Center content
        self.width = self.root.winfo_screenwidth()
        self.height = self.root.winfo_screenheight()
        
        self.canvas = tk.Canvas(
            self.root, width=self.width, height=self.height,
            bg='black', highlightthickness=0
        )
        self.canvas.pack(fill='both', expand=True)
        
        # Logo/Title
        self.center_x = self.width // 2
        self.center_y = self.height // 2
        
        self.logo_text = self.canvas.create_text(
            self.center_x, self.center_y - 50,
            text="AURA OS",
            font=('Courier', 60, 'bold'),
            fill='#00ff88',
            anchor='center'
        )
        
        self.subtitle_text = self.canvas.create_text(
            self.center_x, self.center_y + 30,
            text="NEURAL INTERFACE INITIALIZING...",
            font=('Courier', 18),
            fill='#008844',
            anchor='center'
        )
        
        self.status_text = self.canvas.create_text(
            self.center_x, self.height - 100,
            text="System Check...",
            font=('Courier', 14),
            fill='#444444',
            anchor='center'
        )
        
        # Progress bar
        self.progress_width = 400
        self.progress_height = 4
        self.progress_bg = self.canvas.create_rectangle(
            self.center_x - 200, self.center_y + 80,
            self.center_x + 200, self.center_y + 84,
            fill='#111111', outline=''
        )
        self.progress_fg = self.canvas.create_rectangle(
            self.center_x - 200, self.center_y + 80,
            self.center_x - 200, self.center_y + 84,
            fill='#00ff88', outline=''
        )
        
        # Start initialization
        self.steps = [
            ("Loading Kernel Modules...", 0.5),
            ("Mounting Neural Filesystem...", 0.8),
            ("Connecting to Vision Cortex...", 1.5),
            ("Starting GUI Agent...", 1.0),
            ("Calibrating Screen Monitor...", 0.5),
            ("AuraOS Ready.", 0.5)
        ]
        
        self.current_step = 0
        self.root.after(500, self.run_step)
        
    def update_progress(self, percent):
        width = 400 * percent
        self.canvas.coords(
            self.progress_fg,
            self.center_x - 200, self.center_y + 80,
            self.center_x - 200 + width, self.center_y + 84
        )
        
    def run_step(self):
        if self.current_step < len(self.steps):
            text, duration = self.steps[self.current_step]
            self.canvas.itemconfig(self.status_text, text=text)
            
            # Simulate "typing" effect or processing
            self.update_progress((self.current_step + 1) / len(self.steps))
            
            # Real check for Agent on specific step
            if "Vision Cortex" in text:
                self.check_agent()
            
            self.current_step += 1
            self.root.after(int(duration * 1000), self.run_step)
        else:
            self.finish()
            
    def check_agent(self):
        # Try to ping the agent
        try:
            requests.get("http://localhost:8765/health", timeout=1)
            self.canvas.itemconfig(self.status_text, text="Vision Cortex: ONLINE", fill='#00ff88')
        except:
            self.canvas.itemconfig(self.status_text, text="Vision Cortex: OFFLINE (Retrying...)", fill='#ff4444')

    def finish(self):
        # Launch AuraOS Home after brief delay
        self.canvas.itemconfig(self.subtitle_text, text="INITIALIZATION COMPLETE")
        self.root.after(1000, self.launch_home)
        
    def launch_home(self):
        """Launch AuraOS Home and close onboarding"""
        try:
            # Launch AuraOS Home launcher
            subprocess.Popen([sys.executable, "/opt/auraos/bin/auraos_launcher.py"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Failed to launch AuraOS Home: {e}")
        
        # Close onboarding
        self.root.destroy()

if __name__ == "__main__":
    # Ensure DISPLAY is set
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':0'
        
    app = AuraOSOnboarding()
    app.root.mainloop()
