#!/usr/bin/env python3
"""
AuraOS Vision - Screenshot AI Assistant
See your screen and control it with AI
"""
import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import os
import base64
import json
import requests
from PIL import ImageGrab, Image
import io

def get_inference_url():
    """Get the correct inference server URL based on environment."""
    if os.path.exists("/opt/auraos"):
        return "http://192.168.2.1:8081"
    return "http://localhost:8081"

INFERENCE_URL = get_inference_url()

class AuraOSVision:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraOS Vision")
        self.root.geometry("1000x800")
        self.root.configure(bg='#0a0e27')
        
        self.is_processing = False
        self.setup_ui()
        
    def setup_ui(self):
        # Title Bar
        title_frame = tk.Frame(self.root, bg='#1a1e37', height=60)
        title_frame.pack(fill='x')
        
        title = tk.Label(
            title_frame, text="👁️ AuraOS Vision - Screenshot AI",
            font=('Arial', 16, 'bold'), fg='#00ff88', bg='#1a1e37'
        )
        title.pack(side='left', padx=20, pady=15)
        
        self.status_label = tk.Label(
            title_frame, text="Ready", font=('Arial', 10),
            fg='#6db783', bg='#1a1e37'
        )
        self.status_label.pack(side='right', padx=20, pady=15)
        
        # Main Content
        main_frame = tk.Frame(self.root, bg='#0a0e27')
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Output Area
        output_label = tk.Label(
            main_frame, text="AI Analysis:", font=('Arial', 10),
            fg='#9cdcfe', bg='#0a0e27'
        )
        output_label.pack(anchor='w')
        
        self.output_area = scrolledtext.ScrolledText(
            main_frame, wrap=tk.WORD, bg='#0a0e27', fg='#d4d4d4',
            font=('Menlo', 10), relief='flat', padx=10, pady=10, height=15
        )
        self.output_area.pack(fill='both', expand=True, pady=(5, 15))
        self.output_area.config(state='disabled')
        
        # Configure tags
        self.output_area.tag_config('info', foreground='#9cdcfe')
        self.output_area.tag_config('success', foreground='#6db783')
        self.output_area.tag_config('error', foreground='#f48771')
        self.output_area.tag_config('vision', foreground='#00ff88')
        
        # Input Area
        input_frame = tk.Frame(self.root, bg='#1a1e37')
        input_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        prompt_label = tk.Label(
            input_frame, text="Ask about screen:", font=('Menlo', 10, 'bold'),
            fg='#00ff88', bg='#1a1e37'
        )
        prompt_label.pack(anchor='w', pady=(0, 5))
        
        self.input_field = tk.Entry(
            input_frame, bg='#2d3547', fg='#ffffff',
            font=('Menlo', 11), insertbackground='#00d4ff',
            relief='flat', bd=0
        )
        self.input_field.pack(fill='x', ipady=10)
        self.input_field.bind('<Return>', lambda e: self.analyze())
        
        # Buttons
        btn_frame = tk.Frame(self.root, bg='#1a1e37')
        btn_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        screenshot_btn = tk.Button(
            btn_frame, text="📸 Take Screenshot", command=self.take_screenshot,
            bg='#00d4ff', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=20, pady=8
        )
        screenshot_btn.pack(side='left', padx=5)
        
        analyze_btn = tk.Button(
            btn_frame, text="🤔 Analyze", command=self.analyze,
            bg='#00ff88', fg='#0a0e27', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=20, pady=8
        )
        analyze_btn.pack(side='left', padx=5)
        
        clear_btn = tk.Button(
            btn_frame, text="Clear", command=self.clear_output,
            bg='#2d3547', fg='#ffffff', font=('Arial', 10, 'bold'),
            relief='flat', cursor='hand2', padx=20, pady=8
        )
        clear_btn.pack(side='left', padx=5)
        
        # Welcome
        self.append_text("👁️ AuraOS Vision - Screenshot AI\n", "vision")
        self.append_text("Analyze your screen with AI\n\n", "info")
        self.append_text("Features:\n", "info")
        self.append_text("  • Take screenshots\n", "success")
        self.append_text("  • Ask about what you see\n", "success")
        self.append_text("  • Get AI insights\n\n", "success")
        
        self.screenshot_data = None
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
        
    def take_screenshot(self):
        """Take a screenshot"""
        if self.is_processing:
            return
            
        self.is_processing = True
        self.status_label.config(text="Taking screenshot...", fg='#dcdcaa')
        self.append_text("\n📸 Capturing screen...\n", "info")
        
        threading.Thread(target=self._take_screenshot, daemon=True).start()
        
    def _take_screenshot(self):
        """Take screenshot in background"""
        try:
            # Take screenshot
            screenshot = ImageGrab.grab()
            
            # Convert to base64
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            self.screenshot_data = base64.b64encode(img_byte_arr.getvalue()).decode()
            
            self.append_text("✓ Screenshot captured\n", "success")
        except Exception as e:
            self.append_text(f"❌ Error capturing screenshot: {e}\n", "error")
            
        self.is_processing = False
        self.status_label.config(text="Ready", fg='#6db783')
        
    def analyze(self):
        """Analyze screenshot with AI"""
        if self.is_processing:
            return
            
        if not self.screenshot_data:
            self.append_text("❌ No screenshot taken. Click 'Take Screenshot' first.\n", "error")
            return
            
        question = self.input_field.get().strip()
        if not question:
            self.append_text("❌ Enter a question about the screenshot\n", "error")
            return
            
        self.input_field.delete(0, tk.END)
        self.append_text(f"\nYou: {question}\n", "vision")
        self.is_processing = True
        self.status_label.config(text="Analyzing...", fg='#dcdcaa')
        
        threading.Thread(target=self._analyze, args=(question,), daemon=True).start()
        
    def _analyze(self, question):
        """Analyze screenshot with AI"""
        try:
            self.append_text("🤔 Analyzing with vision AI...\n", "info")
            
            # Send to inference server
            prompt = f"""You are analyzing a screenshot. Answer this question: {question}

Be concise and direct. Focus on what's visible and relevant to the question."""
            
            response = requests.post(
                f"{INFERENCE_URL}/generate",
                json={
                    "prompt": prompt,
                    "image": f"data:image/png;base64,{self.screenshot_data}"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get("response", "").strip()
                self.append_text(f"\n💡 AI: {analysis}\n", "success")
            else:
                self.append_text(f"❌ Server error: {response.text[:100]}\n", "error")
                
        except requests.exceptions.ConnectionError:
            self.append_text("❌ Cannot reach inference server\n", "error")
            self.append_text(f"  URL: {INFERENCE_URL}\n", "info")
        except Exception as e:
            self.append_text(f"❌ Error: {str(e)}\n", "error")
            
        self.is_processing = False
        self.status_label.config(text="Ready", fg='#6db783')

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraOSVision(root)
    root.mainloop()
