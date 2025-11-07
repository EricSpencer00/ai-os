#!/usr/bin/env python3
"""
AuraOS Setup Screen
Runs inside QEMU VMs to configure user settings and preferences
Persists data across sessions in /var/auraos/user_data.json
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Configuration
DATA_DIR = Path("/var/auraos")
USER_DATA_FILE = DATA_DIR / "user_data.json"
SESSION_FILE = DATA_DIR / "session.json"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

class SetupScreen:
    def __init__(self):
        self.user_data = self.load_user_data()
        self.session = self.load_session()
        self.is_first_run = not self.user_data.get("setup_completed", False)
    
    def load_user_data(self):
        """Load persistent user data"""
        if USER_DATA_FILE.exists():
            try:
                with open(USER_DATA_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading user data: {e}")
                return self.get_default_user_data()
        return self.get_default_user_data()
    
    def get_default_user_data(self):
        """Default user data structure"""
        return {
            "setup_completed": False,
            "user_name": "",
            "preferences": {
                "theme": "dark",
                "automation_level": "medium",
                "auto_update": True,
                "notifications": True
            },
            "automation_tasks": [],
            "history": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    def save_user_data(self):
        """Save user data to disk"""
        self.user_data["updated_at"] = datetime.now().isoformat()
        try:
            with open(USER_DATA_FILE, 'w') as f:
                json.dump(self.user_data, f, indent=2)
            # Make readable by all users
            os.chmod(USER_DATA_FILE, 0o644)
        except Exception as e:
            print(f"Error saving user data: {e}")
    
    def load_session(self):
        """Load current session data"""
        if SESSION_FILE.exists():
            try:
                with open(SESSION_FILE, 'r') as f:
                    session = json.load(f)
                session["sessions_count"] = session.get("sessions_count", 0) + 1
                session["last_access"] = datetime.now().isoformat()
                return session
            except Exception as e:
                print(f"Error loading session: {e}")
                return self.get_default_session()
        return self.get_default_session()
    
    def get_default_session(self):
        """Default session structure"""
        return {
            "session_id": int(time.time()),
            "sessions_count": 1,
            "started_at": datetime.now().isoformat(),
            "last_access": datetime.now().isoformat()
        }
    
    def save_session(self):
        """Save session data"""
        try:
            with open(SESSION_FILE, 'w') as f:
                json.dump(self.session, f, indent=2)
            os.chmod(SESSION_FILE, 0o644)
        except Exception as e:
            print(f"Error saving session: {e}")
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self):
        """Print the setup screen header"""
        self.clear_screen()
        print("=" * 70)
        print("                    AuraOS VM Setup Screen")
        print("=" * 70)
        print()
        if not self.is_first_run:
            print(f"Welcome back, {self.user_data.get('user_name', 'User')}!")
            print(f"Session #{self.session['sessions_count']}")
            print(f"Last access: {self.session['last_access'][:19]}")
        else:
            print("Welcome! Let's set up your AuraOS automation environment.")
        print()
        print("-" * 70)
        print()
    
    def get_input(self, prompt, default=None):
        """Get user input with optional default"""
        if default:
            prompt = f"{prompt} [{default}]: "
        else:
            prompt = f"{prompt}: "
        
        value = input(prompt).strip()
        return value if value else default
    
    def initial_setup(self):
        """Run initial setup wizard"""
        self.print_header()
        print("🚀 Initial Setup Wizard\n")
        
        # Get user name
        user_name = self.get_input("What's your name?", "User")
        self.user_data["user_name"] = user_name
        
        # Get preferences
        print("\n📋 Preferences:")
        
        theme = self.get_input("Theme (dark/light)", "dark")
        self.user_data["preferences"]["theme"] = theme
        
        automation = self.get_input("Automation level (low/medium/high)", "medium")
        self.user_data["preferences"]["automation_level"] = automation
        
        auto_update = self.get_input("Enable auto-updates? (yes/no)", "yes")
        self.user_data["preferences"]["auto_update"] = auto_update.lower() in ['yes', 'y']
        
        notifications = self.get_input("Enable notifications? (yes/no)", "yes")
        self.user_data["preferences"]["notifications"] = notifications.lower() in ['yes', 'y']
        
        # Mark setup as completed
        self.user_data["setup_completed"] = True
        self.save_user_data()
        
        print("\n✅ Setup completed successfully!")
        print("\nPress Enter to continue to main menu...")
        input()
    
    def show_main_menu(self):
        """Display main menu"""
        while True:
            self.print_header()
            print("📋 Main Menu\n")
            print("1. View Settings")
            print("2. Edit Preferences")
            print("3. Manage Automation Tasks")
            print("4. View History")
            print("5. System Information")
            print("6. Export/Import Configuration")
            print("7. Reset Setup")
            print("0. Exit")
            print()
            
            choice = self.get_input("Select an option", "0")
            
            if choice == "1":
                self.view_settings()
            elif choice == "2":
                self.edit_preferences()
            elif choice == "3":
                self.manage_tasks()
            elif choice == "4":
                self.view_history()
            elif choice == "5":
                self.show_system_info()
            elif choice == "6":
                self.export_import_menu()
            elif choice == "7":
                self.reset_setup()
            elif choice == "0":
                self.exit_setup()
                break
            else:
                print("Invalid option. Press Enter to continue...")
                input()
    
    def view_settings(self):
        """View current settings"""
        self.print_header()
        print("⚙️  Current Settings\n")
        
        print(f"User Name: {self.user_data.get('user_name')}")
        print(f"\nPreferences:")
        for key, value in self.user_data.get('preferences', {}).items():
            print(f"  - {key.replace('_', ' ').title()}: {value}")
        
        print(f"\nSetup Completed: {self.user_data.get('setup_completed')}")
        print(f"Created: {self.user_data.get('created_at', 'Unknown')[:19]}")
        print(f"Updated: {self.user_data.get('updated_at', 'Unknown')[:19]}")
        
        print(f"\nAutomation Tasks: {len(self.user_data.get('automation_tasks', []))}")
        print(f"History Entries: {len(self.user_data.get('history', []))}")
        
        print("\nPress Enter to return to menu...")
        input()
    
    def edit_preferences(self):
        """Edit user preferences"""
        self.print_header()
        print("✏️  Edit Preferences\n")
        
        prefs = self.user_data.get('preferences', {})
        
        print("1. Theme:", prefs.get('theme'))
        print("2. Automation Level:", prefs.get('automation_level'))
        print("3. Auto-Update:", prefs.get('auto_update'))
        print("4. Notifications:", prefs.get('notifications'))
        print("0. Back to menu")
        print()
        
        choice = self.get_input("Select preference to edit", "0")
        
        if choice == "1":
            theme = self.get_input("Theme (dark/light)", prefs.get('theme'))
            prefs['theme'] = theme
        elif choice == "2":
            level = self.get_input("Automation level (low/medium/high)", prefs.get('automation_level'))
            prefs['automation_level'] = level
        elif choice == "3":
            auto = self.get_input("Auto-update (yes/no)", "yes" if prefs.get('auto_update') else "no")
            prefs['auto_update'] = auto.lower() in ['yes', 'y']
        elif choice == "4":
            notif = self.get_input("Notifications (yes/no)", "yes" if prefs.get('notifications') else "no")
            prefs['notifications'] = notif.lower() in ['yes', 'y']
        
        if choice in ['1', '2', '3', '4']:
            self.user_data['preferences'] = prefs
            self.save_user_data()
            print("\n✅ Preferences updated!")
            time.sleep(1)
    
    def manage_tasks(self):
        """Manage automation tasks"""
        self.print_header()
        print("🤖 Automation Tasks\n")
        
        tasks = self.user_data.get('automation_tasks', [])
        
        if tasks:
            for i, task in enumerate(tasks, 1):
                status = "✓" if task.get('enabled') else "✗"
                print(f"{i}. [{status}] {task.get('name')}: {task.get('description')}")
        else:
            print("No automation tasks configured.")
        
        print("\nOptions:")
        print("1. Add new task")
        print("2. Toggle task")
        print("3. Remove task")
        print("0. Back to menu")
        print()
        
        choice = self.get_input("Select option", "0")
        
        if choice == "1":
            name = self.get_input("Task name")
            if name:
                desc = self.get_input("Description")
                schedule = self.get_input("Schedule (e.g., 'daily', 'hourly')", "manual")
                
                task = {
                    "name": name,
                    "description": desc,
                    "schedule": schedule,
                    "enabled": True,
                    "created_at": datetime.now().isoformat()
                }
                
                if 'automation_tasks' not in self.user_data:
                    self.user_data['automation_tasks'] = []
                
                self.user_data['automation_tasks'].append(task)
                self.save_user_data()
                print("\n✅ Task added!")
                time.sleep(1)
        
        elif choice == "2" and tasks:
            task_num = self.get_input(f"Task number (1-{len(tasks)})")
            try:
                idx = int(task_num) - 1
                if 0 <= idx < len(tasks):
                    tasks[idx]['enabled'] = not tasks[idx].get('enabled', True)
                    self.save_user_data()
                    print("\n✅ Task toggled!")
                    time.sleep(1)
            except ValueError:
                pass
        
        elif choice == "3" and tasks:
            task_num = self.get_input(f"Task number to remove (1-{len(tasks)})")
            try:
                idx = int(task_num) - 1
                if 0 <= idx < len(tasks):
                    tasks.pop(idx)
                    self.save_user_data()
                    print("\n✅ Task removed!")
                    time.sleep(1)
            except ValueError:
                pass
    
    def view_history(self):
        """View action history"""
        self.print_header()
        print("📜 Action History\n")
        
        history = self.user_data.get('history', [])
        
        if history:
            for i, entry in enumerate(reversed(history[-20:]), 1):
                timestamp = entry.get('timestamp', 'Unknown')[:19]
                action = entry.get('action', 'Unknown')
                print(f"{i}. [{timestamp}] {action}")
        else:
            print("No history entries yet.")
        
        print("\nPress Enter to return to menu...")
        input()
    
    def show_system_info(self):
        """Show system information"""
        self.print_header()
        print("💻 System Information\n")
        
        try:
            # Get system info
            import platform
            import socket
            
            print(f"Hostname: {socket.gethostname()}")
            print(f"Platform: {platform.system()} {platform.release()}")
            print(f"Architecture: {platform.machine()}")
            print(f"Python: {platform.python_version()}")
            
            # Disk usage
            import shutil
            total, used, free = shutil.disk_usage("/")
            print(f"\nDisk Usage:")
            print(f"  Total: {total // (2**30)} GB")
            print(f"  Used: {used // (2**30)} GB")
            print(f"  Free: {free // (2**30)} GB")
            
            # Memory info (Linux only)
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if 'MemTotal' in line or 'MemAvailable' in line:
                            print(f"  {line}")
            except:
                pass
            
        except Exception as e:
            print(f"Error getting system info: {e}")
        
        print("\nPress Enter to return to menu...")
        input()
    
    def export_import_menu(self):
        """Export/Import configuration"""
        self.print_header()
        print("💾 Export/Import Configuration\n")
        
        print("1. Export configuration")
        print("2. Import configuration")
        print("0. Back to menu")
        print()
        
        choice = self.get_input("Select option", "0")
        
        if choice == "1":
            export_file = self.get_input("Export file path", "/tmp/auraos_config.json")
            try:
                with open(export_file, 'w') as f:
                    json.dump(self.user_data, f, indent=2)
                print(f"\n✅ Configuration exported to {export_file}")
            except Exception as e:
                print(f"\n❌ Export failed: {e}")
            time.sleep(2)
        
        elif choice == "2":
            import_file = self.get_input("Import file path", "/tmp/auraos_config.json")
            try:
                with open(import_file, 'r') as f:
                    imported_data = json.load(f)
                self.user_data = imported_data
                self.save_user_data()
                print(f"\n✅ Configuration imported from {import_file}")
            except Exception as e:
                print(f"\n❌ Import failed: {e}")
            time.sleep(2)
    
    def reset_setup(self):
        """Reset setup to defaults"""
        self.print_header()
        print("⚠️  Reset Setup\n")
        
        confirm = self.get_input("Are you sure you want to reset? This will delete all data! (yes/no)", "no")
        
        if confirm.lower() == "yes":
            self.user_data = self.get_default_user_data()
            self.save_user_data()
            self.is_first_run = True
            print("\n✅ Setup reset complete!")
            time.sleep(1)
            self.initial_setup()
    
    def log_action(self, action):
        """Log an action to history"""
        if 'history' not in self.user_data:
            self.user_data['history'] = []
        
        entry = {
            "action": action,
            "timestamp": datetime.now().isoformat()
        }
        
        self.user_data['history'].append(entry)
        
        # Keep only last 100 entries
        if len(self.user_data['history']) > 100:
            self.user_data['history'] = self.user_data['history'][-100:]
        
        self.save_user_data()
    
    def exit_setup(self):
        """Exit the setup screen"""
        self.save_session()
        self.log_action("Exited setup screen")
        self.print_header()
        print("👋 Goodbye!")
        print("\nYour settings have been saved.")
        print()
    
    def run(self):
        """Main run loop"""
        try:
            if self.is_first_run:
                self.initial_setup()
            
            self.log_action("Accessed setup screen")
            self.show_main_menu()
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            self.exit_setup()
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main entry point"""
    # Check if running as root for directory creation
    if os.geteuid() != 0 and not DATA_DIR.exists():
        print("Note: Run with sudo for first-time setup to create /var/auraos")
        print("Or create the directory manually: sudo mkdir -p /var/auraos && sudo chmod 777 /var/auraos")
        print()
    
    setup = SetupScreen()
    setup.run()

if __name__ == "__main__":
    main()
