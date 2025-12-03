#!/usr/bin/env python3
"""
AuraOS Launcher - Main Dashboard
The primary interface for AuraOS that overlays the XFCE desktop.
Supports fullscreen mode to completely replace the Ubuntu desktop experience.
"""
import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys
import threading
import webbrowser
import shutil
from datetime import datetime

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
    def __init__(self, root, fullscreen=False):
        self.root = root
        self.fullscreen = fullscreen
        self.root.title("AuraOS")
        self.root.configure(bg='#0a0e27')
        
        # Set DISPLAY for VM environment
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":99"
        
        # Enable proper window manager integration for resize/drag
        self.root.resizable(True, True)
        self.root.minsize(600, 400)
        
        # Enable window decorations (title bar with close button)
        try:
            self.root.attributes('-type', 'normal')
        except:
            pass  # -type not supported on all window managers
        
        if fullscreen:
            # Fullscreen mode - completely overlay XFCE
            self.root.attributes('-fullscreen', True)
            self.root.attributes('-topmost', True)
            # Bind Escape to toggle fullscreen (but don't close)
            self.root.bind('<Escape>', self.toggle_fullscreen)
            self.root.bind('<F11>', self.toggle_fullscreen)
        else:
            self.root.geometry("900x700")
            # Normal window - allow window manager decorations
            self.root.attributes('-topmost', False)
        
        # Handle window close - minimize instead of close in fullscreen
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.setup_ui()
        self.update_clock()
        
    def toggle_fullscreen(self, event=None):
        """Toggle between fullscreen and windowed mode"""
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)
        self.root.attributes('-topmost', self.fullscreen)
        
    def on_close(self):
        """Handle window close - ask before closing in fullscreen"""
        if self.fullscreen:
            if messagebox.askyesno("AuraOS", "Exit AuraOS interface?\n\nThis will show the Ubuntu desktop."):
                self.root.destroy()
        else:
            self.root.destroy()
        
    def setup_ui(self):
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Main container
        main_container = tk.Frame(self.root, bg='#0a0e27')
        main_container.pack(fill='both', expand=True)
        
        # Header
        header = tk.Frame(main_container, bg='#0a0e27')
        header.pack(fill='x', pady=(50, 20))
        
        # Logo
        logo = tk.Label(
            header, text="⚡ AuraOS", 
            font=('Arial', 48, 'bold'), fg='#00ff88', bg='#0a0e27'
        )
        logo.pack()
        
        subtitle = tk.Label(
            header, text="AI-Powered Operating System", 
            font=('Arial', 14), fg='#9cdcfe', bg='#0a0e27'
        )
        subtitle.pack(pady=(5, 0))
        
        # Clock display
        self.clock_label = tk.Label(
            header, text="", 
            font=('Arial', 12), fg='#666666', bg='#0a0e27'
        )
        self.clock_label.pack(pady=(20, 0))
        
        # App Grid
        grid_frame = tk.Frame(main_container, bg='#0a0e27')
        grid_frame.pack(expand=True, pady=30)
        
        # Define apps with icons and colors
        apps = [
            ("🖥️", "Terminal", "AI-Powered Terminal", self.launch_terminal, '#00d4ff'),
            ("🌐", "Browser", "Web Browser", self.launch_browser, '#ff7f50'),
            ("👁️", "Vision", "Vision Desktop", self.launch_vision_os, '#00ff88'),
            ("📁", "Files", "File Manager", self.launch_files, '#ffd700'),
            ("⚙️", "Settings", "System Settings", self.launch_settings, '#888888'),
            ("🔌", "Ubuntu", "Show Ubuntu Desktop", self.show_ubuntu_desktop, '#dd4814'),
        ]
        
        # Create app buttons in a 3x2 grid
        for i, (icon, name, desc, handler, color) in enumerate(apps):
            row = i // 3
            col = i % 3
            
            btn_frame = tk.Frame(grid_frame, bg='#0a0e27')
            btn_frame.grid(row=row, column=col, padx=20, pady=20)
            
            btn = tk.Button(
                btn_frame, text=icon,
                font=('Arial', 36),
                width=4, height=2,
                bg='#1a1e37', fg=color,
                activebackground='#2a2e47', activeforeground=color,
                relief='flat', cursor='hand2',
                command=handler
            )
            btn.pack()
            
            label = tk.Label(
                btn_frame, text=name,
                font=('Arial', 12, 'bold'), fg='#ffffff', bg='#0a0e27'
            )
            label.pack(pady=(5, 0))
            
            desc_label = tk.Label(
                btn_frame, text=desc,
                font=('Arial', 9), fg='#666666', bg='#0a0e27'
            )
            desc_label.pack()
        
        # Status bar at bottom
        status_bar = tk.Frame(main_container, bg='#1a1e37', height=40)
        status_bar.pack(fill='x', side='bottom')
        
        self.status_label = tk.Label(
            status_bar, text="System Ready", 
            font=('Arial', 10), fg='#6db783', bg='#1a1e37'
        )
        self.status_label.pack(side='left', padx=20, pady=10)
        
        # Fullscreen hint
        if self.fullscreen:
            hint = tk.Label(
                status_bar, text="Press ESC or F11 to toggle windowed mode",
                font=('Arial', 9), fg='#444444', bg='#1a1e37'
            )
            hint.pack(side='right', padx=20, pady=10)

    def update_clock(self):
        """Update the clock display"""
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")
        self.clock_label.config(text=f"{time_str}  •  {date_str}")
        self.root.after(1000, self.update_clock)

    def launch_terminal(self):
        self.status_label.config(text="Launching Terminal...", fg='#00d4ff')
        self.root.update_idletasks()
        
        def _launch():
            try:
                terminal_path = find_app_path("auraos_terminal.py")
                if terminal_path:
                    subprocess.Popen(
                        [sys.executable, terminal_path],
                        env=os.environ.copy(),
                        start_new_session=True
                    )
                    self.status_label.config(text="System Ready", fg='#6db783')
                else:
                    # Fallback to xfce4-terminal
                    subprocess.Popen(['xfce4-terminal'], start_new_session=True)
                    self.status_label.config(text="System Ready", fg='#6db783')
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
                    # Fallback: try Firefox
                    firefox_path = shutil.which("firefox")
                    if firefox_path:
                        env = os.environ.copy()
                        env["DISPLAY"] = env.get("DISPLAY", ":99")
                        subprocess.Popen(
                            [firefox_path],
                            env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                    else:
                        raise FileNotFoundError("No browser found")
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
                    subprocess.Popen(
                        [sys.executable, vision_path],
                        env=os.environ.copy(),
                        start_new_session=True
                    )
                else:
                    # Fallback: open in browser
                    firefox_path = shutil.which("firefox")
                    if firefox_path:
                        subprocess.Popen(
                            [firefox_path, "http://localhost:6080/vnc.html"],
                            env=os.environ.copy(),
                            start_new_session=True
                        )
                self.status_label.config(text="System Ready", fg='#6db783')
            except Exception as e:
                self.status_label.config(text=f"Error: {str(e)[:30]}", fg='#ff0000')
        
        threading.Thread(target=_launch, daemon=True).start()

    def launch_files(self):
        self.status_label.config(text="Opening File Manager...", fg='#ffd700')
        self.root.update_idletasks()
        
        def _launch():
            try:
                # Open the correct home directory for the auraos user
                home_dir = os.path.expanduser("~")
                
                # Try thunar first (XFCE file manager) with correct path
                if shutil.which("thunar"):
                    subprocess.Popen(['thunar', home_dir], start_new_session=True)
                elif shutil.which("nautilus"):
                    subprocess.Popen(['nautilus', home_dir], start_new_session=True)
                elif shutil.which("pcmanfm"):
                    subprocess.Popen(['pcmanfm', home_dir], start_new_session=True)
                else:
                    raise FileNotFoundError("No file manager found")
                self.status_label.config(text="System Ready", fg='#6db783')
            except Exception as e:
                self.status_label.config(text=f"Error: {str(e)[:30]}", fg='#ff0000')
        
        threading.Thread(target=_launch, daemon=True).start()

    def launch_settings(self):
        self.status_label.config(text="Opening Settings...", fg='#9cdcfe')
        self.root.update_idletasks()
        
        def _launch():
            try:
                if shutil.which("xfce4-settings-manager"):
                    subprocess.Popen(["xfce4-settings-manager"], start_new_session=True)
                else:
                    raise FileNotFoundError("No settings app found")
                self.status_label.config(text="System Ready", fg='#6db783')
            except Exception as e:
                self.status_label.config(text=f"Error: {str(e)[:30]}", fg='#ff0000')
        
        threading.Thread(target=_launch, daemon=True).start()
    
    def show_ubuntu_desktop(self):
        """Minimize the launcher to show the underlying Ubuntu desktop"""
        self.status_label.config(text="Showing Ubuntu Desktop...", fg='#dd4814')
        self.root.update_idletasks()
        
        # Exit fullscreen and iconify
        self.root.attributes('-fullscreen', False)
        self.root.attributes('-topmost', False)
        self.fullscreen = False
        self.root.iconify()
        
        self.status_label.config(text="System Ready", fg='#6db783')


def main():
    # Check for fullscreen flag
    fullscreen = '--fullscreen' in sys.argv or '-f' in sys.argv
    
    # Set DISPLAY if not set
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':99'
    
    root = tk.Tk()
    app = AuraOSLauncher(root, fullscreen=fullscreen)
    root.mainloop()

if __name__ == "__main__":
    main()
