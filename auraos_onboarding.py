#!/usr/bin/env python3
"""
AuraOS Onboarding - Setup & Configuration
Features:
  - System Health Check
  - API Key Management
  - VM Setup & Repair
  - Launch AuraOS
"""
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import json
import os
import sys
import threading
import shutil

class AuraOSOnboarding:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Setup")
        self.root.geometry("800x600")
        self.root.configure(bg='#0a0e27')
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background='#0a0e27')
        self.style.configure("TLabel", background='#0a0e27', foreground='#d4d4d4', font=('Arial', 11))
        self.style.configure("TButton", font=('Arial', 11, 'bold'), background='#00d4ff', foreground='#0a0e27')
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg='#1a1e37', height=80)
        header_frame.pack(fill='x')
        
        title = tk.Label(
            header_frame, text="✨ AuraOS Setup", 
            font=('Arial', 24, 'bold'), fg='#00ff88', bg='#1a1e37'
        )
        title.pack(pady=20)
        
        # Main Content
        main_frame = tk.Frame(self.root, bg='#0a0e27', padx=40, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # 1. System Status Section
        status_frame = tk.LabelFrame(main_frame, text="System Status", bg='#0a0e27', fg='#00d4ff', font=('Arial', 12, 'bold'))
        status_frame.pack(fill='x', pady=10, ipady=10)
        
        self.status_labels = {}
        checks = ["Multipass", "Ollama", "Python Environment", "VM Status"]
        
        for check in checks:
            row = tk.Frame(status_frame, bg='#0a0e27')
            row.pack(fill='x', padx=20, pady=5)
            lbl = tk.Label(row, text=f"{check}:", width=20, anchor='w', bg='#0a0e27', fg='#d4d4d4')
            lbl.pack(side='left')
            stat = tk.Label(row, text="Checking...", fg='#9cdcfe', bg='#0a0e27')
            stat.pack(side='left')
            self.status_labels[check] = stat
            
        refresh_btn = tk.Button(status_frame, text="Run Health Check", command=self.run_health_check, bg='#2d3547', fg='white')
        refresh_btn.pack(anchor='e', padx=20, pady=5)

        # 2. API Keys Section
        keys_frame = tk.LabelFrame(main_frame, text="API Configuration", bg='#0a0e27', fg='#00d4ff', font=('Arial', 12, 'bold'))
        keys_frame.pack(fill='x', pady=10, ipady=10)
        
        tk.Label(keys_frame, text="OpenAI Key:", bg='#0a0e27', fg='#d4d4d4').grid(row=0, column=0, padx=20, pady=10, sticky='w')
        self.openai_entry = tk.Entry(keys_frame, width=40, bg='#2d3547', fg='white', insertbackground='white')
        self.openai_entry.grid(row=0, column=1, padx=10, pady=10)
        
        tk.Label(keys_frame, text="Anthropic Key:", bg='#0a0e27', fg='#d4d4d4').grid(row=1, column=0, padx=20, pady=10, sticky='w')
        self.anthropic_entry = tk.Entry(keys_frame, width=40, bg='#2d3547', fg='white', insertbackground='white')
        self.anthropic_entry.grid(row=1, column=1, padx=10, pady=10)
        
        save_btn = tk.Button(keys_frame, text="Save Keys", command=self.save_keys, bg='#00ff88', fg='#0a0e27')
        save_btn.grid(row=2, column=1, sticky='e', padx=10, pady=10)
        
        # 3. Actions
        action_frame = tk.Frame(main_frame, bg='#0a0e27')
        action_frame.pack(fill='x', pady=20)
        
        self.repair_btn = tk.Button(action_frame, text="🔧 Repair / Setup VM", command=self.repair_vm, bg='#ff7f50', fg='white', font=('Arial', 12, 'bold'), padx=20, pady=10)
        self.repair_btn.pack(side='left', padx=10)
        
        self.launch_btn = tk.Button(action_frame, text="🚀 Launch AuraOS", command=self.launch_os, bg='#00d4ff', fg='#0a0e27', font=('Arial', 12, 'bold'), padx=20, pady=10)
        self.launch_btn.pack(side='right', padx=10)
        
        # Initial check
        self.root.after(1000, self.run_health_check)

    def run_health_check(self):
        threading.Thread(target=self._check_system, daemon=True).start()
        
    def _check_system(self):
        # Check Multipass
        mp = shutil.which("multipass")
        self.update_status("Multipass", "Installed" if mp else "Not Found", "#00ff88" if mp else "#f48771")
        
        # Check Ollama
        ol = shutil.which("ollama")
        self.update_status("Ollama", "Installed" if ol else "Not Found", "#00ff88" if ol else "#f48771")
        
        # Check Python
        self.update_status("Python Environment", "Active", "#00ff88")
        
        # Check VM
        try:
            res = subprocess.run(["multipass", "info", "auraos-multipass"], capture_output=True, text=True)
            if res.returncode == 0:
                if "Running" in res.stdout:
                    self.update_status("VM Status", "Running", "#00ff88")
                else:
                    self.update_status("VM Status", "Stopped", "#ff7f50")
            else:
                self.update_status("VM Status", "Not Created", "#f48771")
        except:
            self.update_status("VM Status", "Error", "#f48771")

    def update_status(self, key, text, color):
        def _update():
            self.status_labels[key].config(text=text, fg=color)
        self.root.after(0, _update)

    def save_keys(self):
        openai = self.openai_entry.get().strip()
        anthropic = self.anthropic_entry.get().strip()
        
        if not openai and not anthropic:
            messagebox.showwarning("Warning", "Please enter at least one API key.")
            return
            
        # Use auraos.sh to save keys
        auraos_path = shutil.which("auraos.sh") or os.path.join(os.getcwd(), "auraos.sh")
        if auraos_path:
            if openai:
                subprocess.run([auraos_path, "keys", "add", "openai", openai])
            if anthropic:
                subprocess.run([auraos_path, "keys", "add", "anthropic", anthropic])
            messagebox.showinfo("Success", "API Keys saved successfully!")
        else:
            messagebox.showerror("Error", "auraos.sh not found!")

    def repair_vm(self):
        ans = messagebox.askyesno("Confirm", "This will attempt to create or repair the AuraOS VM. It may take several minutes. Continue?")
        if ans:
            threading.Thread(target=self._run_repair, daemon=True).start()
            
    def _run_repair(self):
        self.repair_btn.config(state='disabled', text="Repairing...")
        auraos_path = shutil.which("auraos.sh") or os.path.join(os.getcwd(), "auraos.sh")
        
        try:
            # Check if VM exists
            vm_exists = False
            try:
                res = subprocess.run(["multipass", "list"], capture_output=True, text=True)
                if "auraos-multipass" in res.stdout:
                    vm_exists = True
            except FileNotFoundError:
                messagebox.showerror("Error", "Multipass not found. Please install it first.")
                return

            if vm_exists:
                # Ask user if they want to recreate
                recreate = messagebox.askyesno("VM Exists", "The AuraOS VM already exists. Do you want to delete and recreate it? (Recommended for repair)")
                if recreate:
                    self.update_status("VM Status", "Deleting...", "#ff7f50")
                    subprocess.run(["multipass", "stop", "auraos-multipass"], capture_output=True)
                    subprocess.run(["multipass", "delete", "auraos-multipass"], capture_output=True)
                    subprocess.run(["multipass", "purge"], capture_output=True)
                else:
                    # If not recreating, we might just want to re-run setup to fix services?
                    # But auraos.sh vm-setup will prompt if we don't delete.
                    # So we can't easily run it without hanging if we don't delete.
                    messagebox.showinfo("Info", "Skipping VM recreation. To fix services without recreating, try 'Run Health Check' or use the terminal.")
                    return

            self.update_status("VM Status", "Setting up...", "#9cdcfe")
            
            # Run setup - now it shouldn't prompt because VM is gone (if recreated) or we skipped
            # We use Popen to capture output in real-time if we wanted, but here we just wait
            proc = subprocess.Popen([auraos_path, "vm-setup"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = proc.communicate()
            
            if proc.returncode == 0:
                messagebox.showinfo("Success", "VM Setup Complete!")
                self.update_status("VM Status", "Running", "#00ff88")
            else:
                messagebox.showerror("Error", f"Setup failed:\n{stderr}\n\nOutput:\n{stdout}")
                self.update_status("VM Status", "Error", "#f48771")
                
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.update_status("VM Status", "Error", "#f48771")
        finally:
            self.root.after(0, lambda: self.repair_btn.config(state='normal', text="🔧 Repair / Setup VM"))
            self.run_health_check()

    def launch_os(self):
        self.root.destroy()
        # Launch the main launcher or terminal
        # For now, we'll exit with code 0 so the parent script knows to proceed, 
        # or we can launch the launcher directly if we merge them.
        print("LAUNCH_REQUESTED")

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSOnboarding(root)
    root.mainloop()
