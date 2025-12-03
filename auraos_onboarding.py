#!/usr/bin/env python3
"""
AuraOS Onboarding & Startup Screen
Provides a polished, sci-fi "Real OS" startup experience.
Runs on every VM boot to show the AuraOS branding before launching the main interface.
"""
import tkinter as tk
import time
import threading
import sys
import os
import subprocess
import random

# Check file to track first-run vs subsequent boots
FIRST_RUN_FLAG = os.path.expanduser("~/.auraos_first_run_complete")

class AuraOSOnboarding:
    def __init__(self, skip_to_launcher=False):
        self.root = tk.Tk()
        self.root.title("AuraOS")
        self.skip_to_launcher = skip_to_launcher
        
        # Fullscreen and black background
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-type', 'normal')  # Ensure proper window decorations
        self.root.configure(bg='black')
        self.root.bind("<Escape>", lambda e: self.skip_animation())
        self.root.bind("<Return>", lambda e: self.skip_animation())
        self.root.bind("<space>", lambda e: self.skip_animation())
        
        # Override window manager close
        self.root.protocol("WM_DELETE_WINDOW", self.skip_animation)
        
        # Raise window above all others
        self.root.lift()
        self.root.attributes('-topmost', True)
        
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
        
        # Animated particles (stars in background)
        self.particles = []
        for _ in range(50):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.randint(1, 3)
            p = self.canvas.create_oval(x, y, x+size, y+size, fill='#003322', outline='')
            self.particles.append((p, random.uniform(0.5, 2)))
        
        self.logo_text = self.canvas.create_text(
            self.center_x, self.center_y - 60,
            text="AURA OS",
            font=('Courier', 72, 'bold'),
            fill='#00ff88',
            anchor='center'
        )
        
        self.subtitle_text = self.canvas.create_text(
            self.center_x, self.center_y + 40,
            text="NEURAL INTERFACE INITIALIZING...",
            font=('Courier', 16),
            fill='#008844',
            anchor='center'
        )
        
        self.status_text = self.canvas.create_text(
            self.center_x, self.height - 80,
            text="",
            font=('Courier', 12),
            fill='#444444',
            anchor='center'
        )
        
        # Skip hint
        self.skip_hint = self.canvas.create_text(
            self.center_x, self.height - 40,
            text="Press any key to skip",
            font=('Courier', 10),
            fill='#333333',
            anchor='center'
        )
        
        # Progress bar
        self.progress_width = 500
        self.progress_height = 6
        self.progress_bg = self.canvas.create_rectangle(
            self.center_x - 250, self.center_y + 100,
            self.center_x + 250, self.center_y + 106,
            fill='#111111', outline='#002211'
        )
        self.progress_fg = self.canvas.create_rectangle(
            self.center_x - 250, self.center_y + 100,
            self.center_x - 250, self.center_y + 106,
            fill='#00ff88', outline=''
        )
        
        # Glow effect rectangle behind progress
        self.glow = self.canvas.create_rectangle(
            self.center_x - 252, self.center_y + 98,
            self.center_x - 248, self.center_y + 108,
            fill='', outline='#00ff44', width=2
        )
        
        self.animation_skipped = False
        
        # Start initialization
        if skip_to_launcher:
            self.steps = [
                ("AuraOS Ready.", 0.3),
            ]
        else:
            self.steps = [
                ("Loading Kernel Modules...", 0.4),
                ("Mounting Neural Filesystem...", 0.5),
                ("Initializing Vision Cortex...", 0.8),
                ("Starting GUI Agent...", 0.6),
                ("Calibrating Screen Monitor...", 0.4),
                ("Connecting to AI Backend...", 0.5),
                ("AuraOS Ready.", 0.5)
            ]
        
        self.current_step = 0
        self.root.after(300, self.animate_particles)
        self.root.after(500, self.run_step)
    
    def skip_animation(self):
        """Skip the animation and go directly to launcher"""
        self.animation_skipped = True
        self.finish()
        
    def animate_particles(self):
        """Subtle particle animation"""
        if self.animation_skipped:
            return
        for p, speed in self.particles:
            self.canvas.move(p, 0, speed)
            coords = self.canvas.coords(p)
            if coords and coords[1] > self.height:
                # Reset to top
                self.canvas.coords(p, coords[0], -5, coords[0]+2, -3)
        self.root.after(50, self.animate_particles)
        
    def update_progress(self, percent):
        width = 500 * percent
        self.canvas.coords(
            self.progress_fg,
            self.center_x - 250, self.center_y + 100,
            self.center_x - 250 + width, self.center_y + 106
        )
        # Update glow
        self.canvas.coords(
            self.glow,
            self.center_x - 252, self.center_y + 98,
            self.center_x - 250 + width + 2, self.center_y + 108
        )
        
    def run_step(self):
        if self.animation_skipped:
            return
            
        if self.current_step < len(self.steps):
            text, duration = self.steps[self.current_step]
            self.canvas.itemconfig(self.status_text, text=text)
            
            # Update progress
            self.update_progress((self.current_step + 1) / len(self.steps))
            
            # Check agent on specific step
            if "Vision Cortex" in text or "GUI Agent" in text:
                self.check_agent_async()
            
            self.current_step += 1
            self.root.after(int(duration * 1000), self.run_step)
        else:
            self.finish()
    
    def check_agent_async(self):
        """Check agent status in background thread"""
        def _check():
            try:
                import requests
                requests.get("http://localhost:8765/health", timeout=2)
                self.root.after(0, lambda: self.canvas.itemconfig(
                    self.status_text, text="Vision Cortex: ONLINE", fill='#00ff88'))
            except:
                self.root.after(0, lambda: self.canvas.itemconfig(
                    self.status_text, text="Vision Cortex: STANDBY", fill='#888844'))
        threading.Thread(target=_check, daemon=True).start()

    def finish(self):
        """Transition to AuraOS Launcher"""
        self.canvas.itemconfig(self.subtitle_text, text="INITIALIZATION COMPLETE", fill='#00ff88')
        self.canvas.itemconfig(self.skip_hint, text="")
        
        # Mark first run as complete
        try:
            with open(FIRST_RUN_FLAG, 'w') as f:
                f.write(str(time.time()))
        except:
            pass
        
        self.root.after(800, self.launch_home)
        
    def launch_home(self):
        """Launch AuraOS Launcher (fullscreen overlay) and close onboarding"""
        try:
            # Find the launcher script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            launcher_paths = [
                os.path.join(script_dir, "auraos_launcher.py"),
                "/opt/auraos/bin/auraos_launcher.py",
                os.path.join(os.path.expanduser("~"), "auraos_launcher.py"),
            ]
            
            launcher_path = None
            for path in launcher_paths:
                if os.path.exists(path):
                    launcher_path = path
                    break
            
            if launcher_path:
                env = os.environ.copy()
                env['DISPLAY'] = env.get('DISPLAY', ':99')
                subprocess.Popen(
                    [sys.executable, launcher_path, '--fullscreen'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    start_new_session=True
                )
            else:
                print("Warning: Could not find auraos_launcher.py")
        except Exception as e:
            print(f"Failed to launch AuraOS Home: {e}")
        
        # Close onboarding
        self.root.destroy()

def main():
    # Ensure DISPLAY is set
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':99'
    
    # Check if this is first run or subsequent boot
    skip_animation = os.path.exists(FIRST_RUN_FLAG) and '--force' not in sys.argv
    
    # But if --skip is passed, always skip
    if '--skip' in sys.argv:
        skip_animation = True
    
    # If --force is passed, always show full animation
    if '--force' in sys.argv:
        skip_animation = False
        
    app = AuraOSOnboarding(skip_to_launcher=skip_animation)
    app.root.mainloop()

if __name__ == "__main__":
    main()
