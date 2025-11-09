ps aux | egrep 'qemu-system|qemu-kvm' | egrep -v 'egrep|grep'
ps -o pid,ppid,cmd -p 20926 2>/dev/null || true
root             21896 100.2  0.2 452699744 117600 s005  R+    1:32PM   0:06.48 qemu-system-aarch64 -machine virt,highmem=on -cpu cortex-a72 -accel hvf -m 16384 -smp 6 -drive if=virtio,file=/Users/eric/GitHub/ai-os/images/auraos-vm.qcow2,discard=unmap,cache=writeback -drive if=none,file=/Users/eric/GitHub/ai-os/images/seed.iso,id=cidata,format=raw -device virtio-blk-device,drive=cidata -netdev user,id=net0,hostfwd=tcp::2222-:22 -device virtio-net-device,netdev=net0 -overcommit mem-lock=off -serial file:/Users/eric/GitHub/ai-os/logs/qemu_serial.log
  PID  PPID
ls
Applications			fullscan.nmap			n8n.log
AuraOS_VMs			fullscan.xml			Pictures
bin				GitHub				Public
Desktop				Library				scripts
Documents			LLC				Setup Guide In-Editor Tutorial
Downloads			Movies
fullscan.gnmap			Music
cd GitHub/ai-os
# QEMU stdout/stderr log
tail -n 500 logs/qemu.log

# QEMU serial log (if not attached to your terminal)
tail -n 500 logs/qemu_serial.log
zsh: command not found: #
zsh: unknown file attribute: i
ls -l images/seed.iso images/user-data images
head -n 160 images/user-data
-rw-r--r--@ 1 root  staff  921600 Nov  7 14:57 images/seed.iso
-rw-r--r--@ 1 eric  staff   13930 Nov  9 13:32 images/user-data

images:
total 1294672
-rw-r--r--@ 1 root  staff     196928 Nov  7 14:57 auraos-vm.qcow2
-rw-r--r--@ 1 eric  staff         49 Nov  9 13:32 meta-data
-rw-r--r--@ 1 root  staff     921600 Nov  7 14:57 seed.iso
-rw-r--r--@ 1 eric  staff  661728768 Nov  7 12:58 ubuntu-jammy-arm64-base.img
-rw-r--r--@ 1 eric  staff      13930 Nov  9 13:32 user-data
#cloud-config
users:
  - name: auraos
    gecos: AuraOS User
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: users, admin
    lock_passwd: false
    passwd: "$6$37a66ea67b12$lPZPaWiYJT/MHmrg60d.CWFqENgjJPkUc2ppljwRuyMpuBKX4q4/Dszgp2EslOt6kQp102Y59rrNbGVp6Keep1"
ssh_pwauth: true
chpasswd:
  list: |
    auraos:auraos123
  expire: False
ssh_authorized_keys:
  - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCwUfFowjH1jCBiDJUNfELYc+ZQ6nFH9BkK2X5JfYg1ai0Frj5HEDRe8MIgE0BHCGpMFuB+In6eTvXWGtJQQ7i/GSOqp867N6wWj6TCr0/dT+QAeR2OgvsN7mYimlppUpmPyLh6AQK+9LC7Lt4GQIz/LxnOvVVzKWHV36el7SCHmJWqDkl++M5EHPudEPDCzWk1HoRzLuGu2hAzNr6NH4pe8KudfvI4/L8jCJnyPaeYFXNR6H55Dt7vAJN94hs5w5hGDy2tpQs/O4mI93usG55PTxzl9I0kuoyo9BcMYpcPl64eaqHbYu1Uck0UR9Ldzr0MFR+NzsSnJn/zCBWw4Ug8LKs8fYNxiPrORj2Vy7fmtH0/25ShPImEQU69mE87S4zl+ZjlVRC1df0E0BHDvfQj0DpNv7sY7xy+lfeHWem6j+HSb94PukzR5smW3vV0/rbO2ahHgozVjjS3+9q3zRbglq6LPcStnndz/5iQCeNv9yfYaDYBKWBIBXkMpLHge9EcZC+tJY5yIxfIlzikx/58M85qh9DPF3wx546SOS634lUEtajSwp3z4Dnx6/UXkoFq1ffBqANM2wLYNe/8qnzBTwFGqnaAHvSPDYVcLTINxtRqfkEsUIsx4OeACsQL7E4LwGMe1aWidub302x7EshadGnw2nySO/GJ88r/In2b9Q== espencer2@luc.edu
package_update: false
package_upgrade: false
write_files:
  - path: /tmp/bootstrap.sh
    permissions: '0755'
    owner: root:root
    content: |
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
# try key or interactive password (will prompt)
ssh -vvv -p 2222 auraos@localhost

# force password auth (prompts for password)
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -p 2222 auraos@localhost
zsh: unknown file attribute: i
debug1: OpenSSH_10.0p2, LibreSSL 3.3.6
debug3: Running on Darwin 25.0.0 Darwin Kernel Version 25.0.0: Wed Sep 17 21:41:45 PDT 2025; root:xnu-12377.1.9~141/RELEASE_ARM64_T6000 arm64
debug3: Started with: ssh -vvv -p 2222 auraos@localhost
debug1: Reading configuration data /Users/eric/.ssh/config
debug1: Reading configuration data /etc/ssh/ssh_config
debug3: /etc/ssh/ssh_config line 22: Including file /etc/ssh/ssh_config.d/100-macos.conf depth 0
debug1: Reading configuration data /etc/ssh/ssh_config.d/100-macos.conf
debug1: /etc/ssh/ssh_config.d/100-macos.conf line 1: Applying options for *
debug3: /etc/ssh/ssh_config.d/100-macos.conf line 3: Including file /etc/ssh/crypto.conf depth 1
debug1: Reading configuration data /etc/ssh/crypto.conf
debug3: kex names ok: [ecdh-sha2-nistp256]
debug3: expanded UserKnownHostsFile '~/.ssh/known_hosts' -> '/Users/eric/.ssh/known_hosts'
debug3: expanded UserKnownHostsFile '~/.ssh/known_hosts2' -> '/Users/eric/.ssh/known_hosts2'
debug1: Authenticator provider $SSH_SK_PROVIDER did not resolve; disabling
debug3: channel_clear_timeouts: clearing
debug1: Connecting to localhost port 2222.
debug1: Connection established.
debug1: identity file /Users/eric/.ssh/id_rsa type 0
debug1: identity file /Users/eric/.ssh/id_rsa-cert type -1
debug1: identity file /Users/eric/.ssh/id_ecdsa type -1
debug1: identity file /Users/eric/.ssh/id_ecdsa-cert type -1
debug1: identity file /Users/eric/.ssh/id_ecdsa_sk type -1
debug1: identity file /Users/eric/.ssh/id_ecdsa_sk-cert type -1
debug1: identity file /Users/eric/.ssh/id_ed25519 type -1
debug1: identity file /Users/eric/.ssh/id_ed25519-cert type -1
debug1: identity file /Users/eric/.ssh/id_ed25519_sk type -1
debug1: identity file /Users/eric/.ssh/id_ed25519_sk-cert type -1
debug1: identity file /Users/eric/.ssh/id_xmss type -1
debug1: identity file /Users/eric/.ssh/id_xmss-cert type -1
debug1: Local version string SSH-2.0-OpenSSH_10.0
ssh -p 2222 auraos@localhost 'sudo cloud-init status --long; sudo tail -n 200 /var/log/cloud-init.log; sudo tail -n 200 /var/log/cloud-init-output.log'
^C
scp -P 2222 vm_resources/bootstrap.sh auraos@localhost:/tmp/bootstrap.sh
ssh -t -p 2222 auraos@localhost 'sudo bash /tmp/bootstrap.sh'

