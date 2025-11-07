"""
Window manager plugin for AuraOS Autonomous AI Daemon v8
macOS window and application automation
"""
import os
import sys
import json
import subprocess
import logging
import time
from flask import jsonify

# Platform-specific imports
if sys.platform == 'darwin':
    try:
        from AppKit import NSWorkspace, NSRunningApplication, NSApplicationActivationOptions
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID,
            kCGWindowName,
            kCGWindowOwnerName,
            kCGWindowBounds
        )
        MACOS_AVAILABLE = True
    except ImportError:
        MACOS_AVAILABLE = False
        logging.warning("macOS frameworks not available. Window manager will use fallback methods.")
else:
    MACOS_AVAILABLE = False

# Also try pyautogui as fallback
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


class Plugin:
    name = "window_manager"
    
    def __init__(self):
        self.platform = sys.platform
        self.use_applescript = self.platform == 'darwin'
    
    def generate_script(self, intent, context):
        """Generate window management script from intent"""
        intent_lower = intent.lower()
        
        # Classify window management intent
        if any(k in intent_lower for k in ["open", "launch", "start", "run"]):
            return self._generate_launch_script(intent)
        elif any(k in intent_lower for k in ["close", "quit", "kill"]):
            return self._generate_close_script(intent)
        elif any(k in intent_lower for k in ["list", "show", "windows", "apps"]):
            return self._generate_list_script(intent)
        elif any(k in intent_lower for k in ["activate", "focus", "switch to"]):
            return self._generate_activate_script(intent)
        elif any(k in intent_lower for k in ["move", "position", "resize"]):
            return self._generate_move_script(intent)
        elif any(k in intent_lower for k in ["click", "press"]):
            return self._generate_click_script(intent)
        elif any(k in intent_lower for k in ["type", "enter", "input"]):
            return self._generate_type_script(intent)
        else:
            help_text = """
Window Manager Commands:
- open/launch <app> - Open an application
- close/quit <app> - Close an application
- list apps/windows - Show running applications
- activate/focus <app> - Bring app to front
- move window to <x>,<y> - Move active window
- click at <x>,<y> - Click at coordinates
- type <text> - Type text
"""
            return jsonify({"script_type": "info", "script": help_text}), 200
    
    def _generate_launch_script(self, intent):
        """Generate script to launch an application"""
        # Extract app name
        app_name = intent.lower()
        for word in ["open", "launch", "start", "run", "application", "app"]:
            app_name = app_name.replace(word, "")
        app_name = app_name.strip()
        
        script = {
            "action": "launch",
            "app_name": app_name,
            "description": f"Launch {app_name}"
        }
        return jsonify({"script_type": "window_manager", "script": json.dumps(script)}), 200
    
    def _generate_close_script(self, intent):
        """Generate script to close an application"""
        app_name = intent.lower()
        for word in ["close", "quit", "kill", "application", "app"]:
            app_name = app_name.replace(word, "")
        app_name = app_name.strip()
        
        script = {
            "action": "close",
            "app_name": app_name,
            "description": f"Close {app_name}"
        }
        return jsonify({"script_type": "window_manager", "script": json.dumps(script)}), 200
    
    def _generate_list_script(self, intent):
        """Generate script to list apps/windows"""
        script = {
            "action": "list",
            "description": "List running applications"
        }
        return jsonify({"script_type": "window_manager", "script": json.dumps(script)}), 200
    
    def _generate_activate_script(self, intent):
        """Generate script to activate/focus an app"""
        app_name = intent.lower()
        for word in ["activate", "focus", "switch to", "bring to front"]:
            app_name = app_name.replace(word, "")
        app_name = app_name.strip()
        
        script = {
            "action": "activate",
            "app_name": app_name,
            "description": f"Activate {app_name}"
        }
        return jsonify({"script_type": "window_manager", "script": json.dumps(script)}), 200
    
    def _generate_move_script(self, intent):
        """Generate script to move/resize window"""
        # Extract coordinates
        import re
        coords = re.findall(r'\d+', intent)
        
        if len(coords) >= 2:
            x, y = int(coords[0]), int(coords[1])
            width = int(coords[2]) if len(coords) > 2 else None
            height = int(coords[3]) if len(coords) > 3 else None
        else:
            x, y, width, height = 100, 100, None, None
        
        script = {
            "action": "move",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "description": f"Move window to ({x}, {y})"
        }
        return jsonify({"script_type": "window_manager", "script": json.dumps(script)}), 200
    
    def _generate_click_script(self, intent):
        """Generate script to click at coordinates"""
        import re
        coords = re.findall(r'\d+', intent)
        
        if len(coords) >= 2:
            x, y = int(coords[0]), int(coords[1])
        else:
            x, y = 100, 100
        
        script = {
            "action": "click",
            "x": x,
            "y": y,
            "description": f"Click at ({x}, {y})"
        }
        return jsonify({"script_type": "window_manager", "script": json.dumps(script)}), 200
    
    def _generate_type_script(self, intent):
        """Generate script to type text"""
        text = intent.lower()
        for word in ["type", "enter", "input", "write"]:
            text = text.replace(word, "")
        text = text.strip()
        
        script = {
            "action": "type",
            "text": text,
            "description": f"Type '{text}'"
        }
        return jsonify({"script_type": "window_manager", "script": json.dumps(script)}), 200

    def execute(self, script, context):
        """Execute window management commands"""
        try:
            # Parse script JSON
            if isinstance(script, str):
                script_data = json.loads(script)
            else:
                script_data = script
            
            action = script_data.get("action")
            
            if action == "launch":
                return self._execute_launch(script_data)
            elif action == "close":
                return self._execute_close(script_data)
            elif action == "list":
                return self._execute_list(script_data)
            elif action == "activate":
                return self._execute_activate(script_data)
            elif action == "move":
                return self._execute_move(script_data)
            elif action == "click":
                return self._execute_click(script_data)
            elif action == "type":
                return self._execute_type(script_data)
            else:
                return jsonify({"error": f"Unknown action: {action}"}), 400
                
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Invalid JSON script: {e}"}), 400
        except Exception as e:
            logging.error(f"Window manager execution error: {e}")
            return jsonify({"error": str(e)}), 500
    
    def _execute_launch(self, script_data):
        """Launch an application"""
        app_name = script_data.get("app_name", "")
        
        if self.use_applescript:
            # Use AppleScript on macOS
            applescript = f'tell application "{app_name}" to activate'
            try:
                subprocess.run(['osascript', '-e', applescript], check=True, capture_output=True)
                return jsonify({"output": f"Launched {app_name}"}), 200
            except subprocess.CalledProcessError as e:
                # Try with .app extension
                try:
                    applescript = f'tell application "{app_name}.app" to activate'
                    subprocess.run(['osascript', '-e', applescript], check=True, capture_output=True)
                    return jsonify({"output": f"Launched {app_name}"}), 200
                except subprocess.CalledProcessError:
                    # Try with open command
                    try:
                        subprocess.run(['open', '-a', app_name], check=True, capture_output=True)
                        return jsonify({"output": f"Launched {app_name}"}), 200
                    except subprocess.CalledProcessError as e:
                        return jsonify({"error": f"Failed to launch {app_name}: {e.stderr.decode()}"}), 500
        else:
            return jsonify({"error": "Launch not implemented for this platform"}), 501
    
    def _execute_close(self, script_data):
        """Close an application"""
        app_name = script_data.get("app_name", "")
        
        if self.use_applescript:
            applescript = f'tell application "{app_name}" to quit'
            try:
                subprocess.run(['osascript', '-e', applescript], check=True, capture_output=True)
                return jsonify({"output": f"Closed {app_name}"}), 200
            except subprocess.CalledProcessError as e:
                return jsonify({"error": f"Failed to close {app_name}: {e.stderr.decode()}"}), 500
        else:
            return jsonify({"error": "Close not implemented for this platform"}), 501
    
    def _execute_list(self, script_data):
        """List running applications"""
        if MACOS_AVAILABLE:
            workspace = NSWorkspace.sharedWorkspace()
            apps = workspace.runningApplications()
            
            app_list = []
            for app in apps:
                app_name = app.localizedName()
                if app_name and not app.isHidden():
                    app_list.append(app_name)
            
            output = "Running applications:\n" + "\n".join(f"  - {app}" for app in sorted(app_list))
            return jsonify({"output": output, "apps": app_list}), 200
        elif self.use_applescript:
            # Fallback to AppleScript
            applescript = 'tell application "System Events" to get name of (processes where background only is false)'
            try:
                result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True, check=True)
                apps = result.stdout.strip().split(', ')
                output = "Running applications:\n" + "\n".join(f"  - {app}" for app in apps)
                return jsonify({"output": output, "apps": apps}), 200
            except subprocess.CalledProcessError as e:
                return jsonify({"error": f"Failed to list apps: {e.stderr}"}), 500
        else:
            return jsonify({"error": "List not implemented for this platform"}), 501
    
    def _execute_activate(self, script_data):
        """Activate/focus an application"""
        app_name = script_data.get("app_name", "")
        
        if self.use_applescript:
            applescript = f'tell application "{app_name}" to activate'
            try:
                subprocess.run(['osascript', '-e', applescript], check=True, capture_output=True)
                return jsonify({"output": f"Activated {app_name}"}), 200
            except subprocess.CalledProcessError as e:
                return jsonify({"error": f"Failed to activate {app_name}: {e.stderr.decode()}"}), 500
        else:
            return jsonify({"error": "Activate not implemented for this platform"}), 501
    
    def _execute_move(self, script_data):
        """Move or resize a window"""
        x = script_data.get("x", 0)
        y = script_data.get("y", 0)
        width = script_data.get("width")
        height = script_data.get("height")
        
        if self.use_applescript:
            # Move and resize the frontmost window
            if width and height:
                applescript = f'''
                tell application "System Events"
                    tell (first process whose frontmost is true)
                        set position of window 1 to {{{x}, {y}}}
                        set size of window 1 to {{{width}, {height}}}
                    end tell
                end tell
                '''
            else:
                applescript = f'''
                tell application "System Events"
                    tell (first process whose frontmost is true)
                        set position of window 1 to {{{x}, {y}}}
                    end tell
                end tell
                '''
            
            try:
                subprocess.run(['osascript', '-e', applescript], check=True, capture_output=True)
                return jsonify({"output": f"Moved window to ({x}, {y})"}), 200
            except subprocess.CalledProcessError as e:
                return jsonify({"error": f"Failed to move window: {e.stderr.decode()}"}), 500
        else:
            return jsonify({"error": "Move not implemented for this platform"}), 501
    
    def _execute_click(self, script_data):
        """Click at specific coordinates"""
        x = script_data.get("x", 0)
        y = script_data.get("y", 0)
        
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.click(x, y)
                return jsonify({"output": f"Clicked at ({x}, {y})"}), 200
            except Exception as e:
                return jsonify({"error": f"Click failed: {str(e)}"}), 500
        elif self.use_applescript:
            # Use cliclick if installed
            try:
                subprocess.run(['cliclick', f'c:{x},{y}'], check=True, capture_output=True)
                return jsonify({"output": f"Clicked at ({x}, {y})"}), 200
            except FileNotFoundError:
                return jsonify({
                    "error": "cliclick not found. Install with: brew install cliclick",
                    "hint": "Or install pyautogui: pip install pyautogui"
                }), 500
            except subprocess.CalledProcessError as e:
                return jsonify({"error": f"Click failed: {e.stderr.decode()}"}), 500
        else:
            return jsonify({"error": "Click not implemented for this platform"}), 501
    
    def _execute_type(self, script_data):
        """Type text"""
        text = script_data.get("text", "")
        
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.write(text)
                return jsonify({"output": f"Typed '{text}'"}), 200
            except Exception as e:
                return jsonify({"error": f"Type failed: {str(e)}"}), 500
        elif self.use_applescript:
            # Use AppleScript keystroke
            applescript = f'''
            tell application "System Events"
                keystroke "{text}"
            end tell
            '''
            try:
                subprocess.run(['osascript', '-e', applescript], check=True, capture_output=True)
                return jsonify({"output": f"Typed '{text}'"}), 200
            except subprocess.CalledProcessError as e:
                return jsonify({"error": f"Type failed: {e.stderr.decode()}"}), 500
        else:
            return jsonify({"error": "Type not implemented for this platform"}), 501
