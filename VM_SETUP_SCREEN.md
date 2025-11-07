# AuraOS VM Setup Screen Guide

## Overview

The AuraOS Setup Screen is an interactive configuration interface that runs **inside QEMU virtual machines**. It allows you to configure automation preferences, manage tasks, and persist user settings across VM sessions.

### Key Features

✅ **Persistent Storage** - Settings saved to `/var/auraos/user_data.json`  
✅ **Session Tracking** - Remembers previous sessions and login count  
✅ **User Preferences** - Theme, automation level, notifications  
✅ **Task Management** - Create and manage automation tasks  
✅ **History Tracking** - View action history  
✅ **Export/Import** - Backup and restore configurations  

---

## Quick Start

### 1. Start a VM

```bash
# From host machine
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{"intent": "start vm my-automation-box"}'

# Execute the start command (get from response)
curl -X POST http://localhost:5050/execute_script \
  -H "Content-Type: application/json" \
  -d '{
    "script": "",
    "context": {
      "script_type": "vm_start",
      "vm_name": "my-automation-box"
    }
  }'
```

### 2. Bootstrap the VM (First Time Only)

```bash
# Install setup screen in the VM
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{"intent": "bootstrap vm my-automation-box"}'

# Execute bootstrap
curl -X POST http://localhost:5050/execute_script \
  -H "Content-Type: application/json" \
  -d '{
    "script": "",
    "context": {
      "script_type": "vm_bootstrap",
      "vm_name": "my-automation-box"
    }
  }'
```

This will:
- Install Python and required packages
- Set up SSH
- Create `/var/auraos` directory
- Install setup screen at `/opt/auraos/setup_screen.py`
- Create `auraos` user (password: `auraos123`)

### 3. SSH into the VM

```bash
# Default port is 2222
ssh -p 2222 auraos@localhost
```

### 4. Run Setup Screen

Inside the VM:

```bash
auraos-setup
```

Or directly:

```bash
/opt/auraos/setup_screen.py
```

---

## Setup Screen Interface

### First Run (Initial Setup)

```
==============================================================
                AuraOS VM Setup Screen
==============================================================

Welcome! Let's set up your AuraOS automation environment.

--------------------------------------------------------------

🚀 Initial Setup Wizard

What's your name? [User]: Eric

📋 Preferences:
Theme (dark/light) [dark]: dark
Automation level (low/medium/high) [medium]: high
Enable auto-updates? (yes/no) [yes]: yes
Enable notifications? (yes/no) [yes]: yes

✅ Setup completed successfully!

Press Enter to continue to main menu...
```

### Main Menu

```
==============================================================
                AuraOS VM Setup Screen
==============================================================

Welcome back, Eric!
Session #5
Last access: 2025-11-07 15:30:22

--------------------------------------------------------------

📋 Main Menu

1. View Settings
2. Edit Preferences
3. Manage Automation Tasks
4. View History
5. System Information
6. Export/Import Configuration
7. Reset Setup
0. Exit

Select an option [0]:
```

---

## Menu Options

### 1. View Settings

Displays current configuration:

```
⚙️  Current Settings

User Name: Eric

Preferences:
  - Theme: dark
  - Automation Level: high
  - Auto Update: True
  - Notifications: True

Setup Completed: True
Created: 2025-11-07 12:00:00
Updated: 2025-11-07 15:30:22

Automation Tasks: 3
History Entries: 15

Press Enter to return to menu...
```

### 2. Edit Preferences

Modify individual settings:

```
✏️  Edit Preferences

1. Theme: dark
2. Automation Level: high
3. Auto-Update: True
4. Notifications: True
0. Back to menu

Select preference to edit [0]: 2
Automation level (low/medium/high) [high]: medium

✅ Preferences updated!
```

### 3. Manage Automation Tasks

Create, enable/disable, or remove automation tasks:

```
🤖 Automation Tasks

1. [✓] Daily Backup: Backup important files daily
2. [✓] Web Scraping: Scrape news sites hourly
3. [✗] Email Automation: Send automated emails

Options:
1. Add new task
2. Toggle task
3. Remove task
0. Back to menu

Select option [0]: 1
Task name: GitHub Sync
Description: Sync code to GitHub
Schedule (e.g., 'daily', 'hourly') [manual]: hourly

✅ Task added!
```

### 4. View History

See recent actions:

```
📜 Action History

1. [2025-11-07 15:30] Accessed setup screen
2. [2025-11-07 15:25] Exited setup screen
3. [2025-11-07 15:20] Updated preferences
4. [2025-11-07 14:45] Added automation task: GitHub Sync
5. [2025-11-07 14:30] Accessed setup screen

Press Enter to return to menu...
```

### 5. System Information

View VM details:

```
💻 System Information

Hostname: auraos-vm-1
Platform: Linux 5.15.0-56-generic
Architecture: aarch64
Python: 3.10.6

Disk Usage:
  Total: 20 GB
  Used: 5 GB
  Free: 15 GB

Press Enter to return to menu...
```

### 6. Export/Import Configuration

Backup or restore settings:

```
💾 Export/Import Configuration

1. Export configuration
2. Import configuration
0. Back to menu

Select option [0]: 1
Export file path [/tmp/auraos_config.json]: /tmp/my_settings.json

✅ Configuration exported to /tmp/my_settings.json
```

### 7. Reset Setup

Clear all data and start fresh:

```
⚠️  Reset Setup

Are you sure you want to reset? This will delete all data! (yes/no) [no]: yes

✅ Setup reset complete!
```

---

## Data Persistence

### Storage Locations

| File | Path | Purpose |
|------|------|---------|
| User Data | `/var/auraos/user_data.json` | Preferences, tasks, settings |
| Session Data | `/var/auraos/session.json` | Session count, timestamps |
| Setup Screen | `/opt/auraos/setup_screen.py` | Application binary |

### User Data Structure

```json
{
  "setup_completed": true,
  "user_name": "Eric",
  "vm_name": "auraos-vm-1",
  "preferences": {
    "theme": "dark",
    "automation_level": "high",
    "auto_update": true,
    "notifications": true
  },
  "automation_tasks": [
    {
      "name": "Daily Backup",
      "description": "Backup important files daily",
      "schedule": "daily",
      "enabled": true,
      "created_at": "2025-11-07T12:00:00"
    }
  ],
  "history": [
    {
      "action": "Accessed setup screen",
      "timestamp": "2025-11-07T15:30:22"
    }
  ],
  "created_at": "2025-11-07T12:00:00",
  "updated_at": "2025-11-07T15:30:22"
}
```

### Session Persistence

Data persists across:
- ✅ VM reboots
- ✅ SSH disconnections
- ✅ Setup screen exits
- ✅ Daemon restarts

Data is lost when:
- ❌ VM disk is deleted
- ❌ `/var/auraos` is manually removed
- ❌ "Reset Setup" is executed

---

## API Integration

### Get User Data from Host

```bash
# Query VM user preferences from host machine
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{"intent": "get user data from vm my-automation-box"}'

# Execute
curl -X POST http://localhost:5050/execute_script \
  -H "Content-Type: application/json" \
  -d '{
    "script": "",
    "context": {
      "script_type": "vm_get_user_data",
      "vm_name": "my-automation-box"
    }
  }'
```

Response:
```json
{
  "vm_name": "my-automation-box",
  "user_data": {
    "user_name": "Eric",
    "preferences": {
      "theme": "dark",
      "automation_level": "high"
    },
    "automation_tasks": [...]
  }
}
```

### Execute Commands Based on User Preferences

```bash
# Example: Use automation level from VM
AUTOMATION_LEVEL=$(curl -s ... | jq -r '.user_data.preferences.automation_level')

if [ "$AUTOMATION_LEVEL" == "high" ]; then
    # Run intensive automation
fi
```

---

## Advanced Usage

### Automate Setup Screen

Create a script to pre-configure settings:

```bash
#!/bin/bash
# Inside VM

# Create user data
cat > /var/auraos/user_data.json << 'EOF'
{
  "setup_completed": true,
  "user_name": "Automation Bot",
  "preferences": {
    "theme": "dark",
    "automation_level": "high",
    "auto_update": true
  },
  "automation_tasks": [],
  "history": [],
  "created_at": "$(date -Iseconds)"
}
EOF

chmod 644 /var/auraos/user_data.json
```

### Run Setup Screen Non-Interactively

```python
#!/usr/bin/env python3
from setup_screen import SetupScreen
import json

# Load setup screen
setup = SetupScreen()

# Programmatically modify settings
setup.user_data["preferences"]["automation_level"] = "high"
setup.user_data["automation_tasks"].append({
    "name": "Auto Task",
    "description": "Automated task",
    "schedule": "daily",
    "enabled": True
})

# Save
setup.save_user_data()
print("Configuration updated programmatically!")
```

### Backup User Data to Host

```bash
# Inside VM
scp /var/auraos/user_data.json user@host:/backup/

# From host (reverse)
scp -P 2222 auraos@localhost:/var/auraos/user_data.json ./backup/
```

---

## Troubleshooting

### Setup Screen Not Found

```bash
# Check if installed
ls -la /opt/auraos/setup_screen.py

# Re-bootstrap if needed
curl -X POST http://localhost:5050/execute_script \
  -d '{"script": "", "context": {"script_type": "vm_bootstrap", "vm_name": "my-vm"}}'
```

### Permission Denied

```bash
# Inside VM
sudo chmod 777 /var/auraos
sudo chmod 644 /var/auraos/user_data.json
```

### Data Not Persisting

```bash
# Check file permissions
ls -la /var/auraos/

# Ensure directory exists
sudo mkdir -p /var/auraos
sudo chmod 777 /var/auraos
```

### SSH Connection Fails

```bash
# Check VM is running
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "list vms"}'

# Check SSH service in VM (via VNC or console)
sudo systemctl status ssh
sudo systemctl restart ssh
```

---

## Best Practices

### 1. Regular Backups

```bash
# Export configuration weekly
auraos-setup
# Select option 6 → 1 (Export)
```

### 2. Document Task Configurations

```bash
# Inside setup screen, add detailed descriptions
Task name: Database Backup
Description: Backs up PostgreSQL to S3 bucket 'prod-backups' daily at 2 AM
```

### 3. Use Descriptive VM Names

```bash
# Good
bootstrap vm web-scraper-prod
bootstrap vm data-pipeline-dev

# Bad
bootstrap vm vm1
bootstrap vm test
```

### 4. Monitor Session Count

High session counts may indicate:
- Frequent VM restarts (possible stability issues)
- Multiple users accessing same VM
- Automation scripts calling setup screen

---

## Integration Examples

### Example 1: Conditional Automation Based on User Preferences

```python
# On host machine
import requests
import json

# Get VM user data
response = requests.post('http://localhost:5050/execute_script', json={
    'script': '',
    'context': {
        'script_type': 'vm_get_user_data',
        'vm_name': 'automation-vm'
    }
})

user_data = response.json().get('user_data', {})
automation_level = user_data.get('preferences', {}).get('automation_level', 'low')

# Adjust automation based on user preference
if automation_level == 'high':
    # Run aggressive automation
    run_intensive_tasks()
elif automation_level == 'medium':
    # Run moderate automation
    run_standard_tasks()
else:
    # Minimal automation
    run_basic_tasks()
```

### Example 2: Multi-VM Orchestration

```bash
#!/bin/bash
# Orchestrate multiple VMs based on their configurations

VMS=("scraper-1" "scraper-2" "processor")

for vm in "${VMS[@]}"; do
    USER_DATA=$(curl -s -X POST http://localhost:5050/execute_script \
        -d "{\"script\":\"\",\"context\":{\"script_type\":\"vm_get_user_data\",\"vm_name\":\"$vm\"}}")
    
    ENABLED=$(echo "$USER_DATA" | jq -r '.user_data.preferences.auto_update')
    
    if [ "$ENABLED" == "true" ]; then
        echo "Updating $vm..."
        # Execute update command
    fi
done
```

---

## Summary

The AuraOS Setup Screen provides:

✅ **Isolated Configuration** - Each VM has independent settings  
✅ **Persistent Storage** - Settings survive reboots  
✅ **User Tracking** - Session history and preferences  
✅ **API Integration** - Query settings from host  
✅ **Task Management** - Configure automation workflows  
✅ **Easy Backup** - Export/import configurations  

**Ready to configure your automation VMs!** 🚀
