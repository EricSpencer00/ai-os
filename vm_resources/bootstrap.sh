#!/bin/bash
# AuraOS VM Bootstrap Script
# This script sets up a fresh VM with the setup screen and required components

set -e

echo "╔════════════════════════════════════════╗"
echo "║   AuraOS VM Bootstrap Installer        ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Guard: ensure we're on a Debian/Ubuntu-like system with apt-get.
# If apt-get is not available (for example when accidentally running on macOS),
# fail early with a helpful message so we don't try to run package manager commands.
if ! command -v apt-get >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: apt-get not found.${NC}"
    echo "This bootstrap script is intended to run inside a Debian/Ubuntu VM (uses apt-get)."
    echo "You're running on $(uname -s)."
    echo ""
    echo "Options:" 
    echo "  - Run this script inside the VM (recommended)."
    echo "  - Use the host 'vm_manager' plugin to transfer and run the bootstrap inside the VM."
    echo "  - If you need a macOS-adapted bootstrap, ask and I can add a --mac branch (not implemented)."
    exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo $0"
    exit 1
fi

echo -e "${BLUE}Step 1/6: Updating system packages...${NC}"
apt-get update -qq
apt-get upgrade -y -qq
echo -e "${GREEN}✓${NC} System updated"
echo ""

echo -e "${BLUE}Step 2/6: Installing required packages...${NC}"
apt-get install -y -qq \
    python3 \
    python3-pip \
    openssh-server \
    curl \
    wget \
    git \
    vim \
    net-tools \
    htop \
    jq
echo -e "${GREEN}✓${NC} Packages installed"
echo ""

echo -e "${BLUE}Step 3/6: Configuring SSH...${NC}"
# Enable and start SSH
systemctl enable ssh
systemctl start ssh

# Configure SSH for key-based auth
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# Allow password authentication for initial setup
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh

echo -e "${GREEN}✓${NC} SSH configured and running"
echo ""

echo -e "${BLUE}Step 4/6: Creating AuraOS directories...${NC}"
# Create AuraOS directories
mkdir -p /var/auraos
mkdir -p /opt/auraos
mkdir -p /home/auraos

# Set permissions
chmod 777 /var/auraos
chmod 755 /opt/auraos

echo -e "${GREEN}✓${NC} Directories created"
echo ""

echo -e "${BLUE}Step 5/6: Installing setup screen...${NC}"

# Download setup screen if it exists remotely, or copy from local
SETUP_SCREEN="/opt/auraos/setup_screen.py"

# Create the setup screen directly
cat > "$SETUP_SCREEN" << 'SETUP_EOF'
#!/usr/bin/env python3
"""
AuraOS Setup Screen - VM Edition
"""
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("/var/auraos")
USER_DATA_FILE = DATA_DIR / "user_data.json"
SESSION_FILE = DATA_DIR / "session.json"

class SetupScreen:
    def __init__(self):
        self.user_data = self.load_user_data()
        self.session = self.load_session()
        self.is_first_run = not self.user_data.get("setup_completed", False)
    
    def load_user_data(self):
        if USER_DATA_FILE.exists():
            try:
                with open(USER_DATA_FILE, 'r') as f:
                    return json.load(f)
            except:
                return self.get_default_user_data()
        return self.get_default_user_data()
    
    def get_default_user_data(self):
        return {
            "setup_completed": False,
            "user_name": "",
            "vm_name": os.uname().nodename,
            "preferences": {
                "theme": "dark",
                "automation_level": "medium"
            },
            "automation_tasks": [],
            "history": [],
            "created_at": datetime.now().isoformat()
        }
    
    def save_user_data(self):
        self.user_data["updated_at"] = datetime.now().isoformat()
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(self.user_data, f, indent=2)
        os.chmod(USER_DATA_FILE, 0o644)
    
    def load_session(self):
        if SESSION_FILE.exists():
            try:
                with open(SESSION_FILE, 'r') as f:
                    session = json.load(f)
                session["sessions_count"] = session.get("sessions_count", 0) + 1
                return session
            except:
                return {"sessions_count": 1, "started_at": datetime.now().isoformat()}
        return {"sessions_count": 1, "started_at": datetime.now().isoformat()}
    
    def save_session(self):
        with open(SESSION_FILE, 'w') as f:
            json.dump(self.session, f, indent=2)
    
    def clear_screen(self):
        os.system('clear')
    
    def print_header(self):
        self.clear_screen()
        print("=" * 60)
        print("          AuraOS VM Setup Screen")
        print("=" * 60)
        if not self.is_first_run:
            print(f"\nWelcome back, {self.user_data.get('user_name', 'User')}!")
            print(f"Session #{self.session['sessions_count']}")
        print("-" * 60)
        print()
    
    def initial_setup(self):
        self.print_header()
        print("🚀 Initial Setup\n")
        
        user_name = input("What's your name? [User]: ").strip() or "User"
        self.user_data["user_name"] = user_name
        
        self.user_data["setup_completed"] = True
        self.save_user_data()
        
        print("\n✅ Setup completed!")
        input("\nPress Enter to continue...")
    
    def main_menu(self):
        while True:
            self.print_header()
            print("1. View Settings")
            print("2. System Info")
            print("0. Exit\n")
            
            choice = input("Select option [0]: ").strip() or "0"
            
            if choice == "1":
                self.view_settings()
            elif choice == "2":
                self.show_system_info()
            elif choice == "0":
                break
    
    def view_settings(self):
        self.print_header()
        print("⚙️  Settings\n")
        print(f"User: {self.user_data.get('user_name')}")
        print(f"VM: {self.user_data.get('vm_name')}")
        print(f"Sessions: {self.session.get('sessions_count')}")
        input("\nPress Enter to continue...")
    
    def show_system_info(self):
        self.print_header()
        print("💻 System Info\n")
        os.system("hostname")
        os.system("uname -a")
        input("\nPress Enter to continue...")
    
    def run(self):
        try:
            if self.is_first_run:
                self.initial_setup()
            self.main_menu()
            self.save_session()
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    setup = SetupScreen()
    setup.run()
SETUP_EOF

chmod +x "$SETUP_SCREEN"

# Create convenience symlink
ln -sf "$SETUP_SCREEN" /usr/local/bin/auraos-setup

echo -e "${GREEN}✓${NC} Setup screen installed"
echo ""

echo -e "${BLUE}Step 6/6: Creating startup script...${NC}"

# Create a script to run setup on login
cat > /etc/profile.d/auraos-welcome.sh << 'PROFILE_EOF'
# AuraOS Welcome Message
if [ -n "$SSH_CONNECTION" ] || [ "$USER" = "auraos" ]; then
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║       Welcome to AuraOS VM             ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
    echo "Run 'auraos-setup' to configure your environment"
    echo ""
fi
PROFILE_EOF

chmod +x /etc/profile.d/auraos-welcome.sh

echo -e "${GREEN}✓${NC} Startup script created"
echo ""

# Create auraos user if it doesn't exist
if ! id "auraos" &>/dev/null; then
    echo -e "${BLUE}Creating auraos user...${NC}"
    useradd -m -s /bin/bash auraos
    echo "auraos:auraos123" | chpasswd
    
    # Add to sudo group
    usermod -aG sudo auraos
    
    # Allow passwordless sudo for convenience
    echo "auraos ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/auraos
    chmod 440 /etc/sudoers.d/auraos
    
    echo -e "${GREEN}✓${NC} User 'auraos' created (password: auraos123)"
    echo ""
fi

# Create motd
cat > /etc/motd << 'MOTD_EOF'

╔════════════════════════════════════════════════════════════╗
║                    AuraOS Automation VM                    ║
║                                                            ║
║  This VM is managed by AuraOS AI Daemon                   ║
║                                                            ║
║  Commands:                                                 ║
║    auraos-setup     - Run setup screen                     ║
║    htop            - System monitor                        ║
║    systemctl status ssh - Check SSH status                 ║
║                                                            ║
║  Default credentials: auraos / auraos123                   ║
╚════════════════════════════════════════════════════════════╝

MOTD_EOF

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     Bootstrap Complete! 🎉              ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}AuraOS VM is ready!${NC}"
echo ""
echo "Summary:"
echo "  • Setup screen installed: /opt/auraos/setup_screen.py"
echo "  • Command: auraos-setup"
echo "  • User data: /var/auraos/user_data.json"
echo "  • SSH enabled on port 22"
echo "  • Default user: auraos / auraos123"
echo ""
echo "Next steps:"
echo "  1. Exit this shell and SSH into the VM"
echo "  2. Run 'auraos-setup' to configure your environment"
echo "  3. Your settings will persist across reboots"
echo ""
echo "From host machine:"
echo "  ssh -p 2222 auraos@localhost"
echo ""
