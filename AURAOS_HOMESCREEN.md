# AuraOS Home Screen & Branding Guide

**Status:** ✅ **ACTIVE**  
**Last Updated:** November 9, 2025

---

## Overview

The AuraOS Home Screen is a custom dashboard that provides quick access to AuraOS features and applications. It replaces the default Ubuntu desktop environment with an AuraOS-branded experience.

### Features

✅ **Custom Branding**
- AuraOS logo and color scheme (#00d4ff cyan, #0a0e27 dark blue)
- Custom desktop background
- Branded hostname and system information

✅ **Quick Access Dashboard**
- 🖥️ AuraOS Terminal - AI-powered command interface
- 📁 File Manager - Browse and manage files
- 🌐 Web Browser - Internet access
- ⚙️ System Settings - Configure your system

✅ **Auto-Launch**
- Starts automatically on desktop login
- No manual intervention needed
- Always accessible from desktop shortcuts

✅ **System Information**
- Real-time clock display
- Hostname and uptime information
- System status at a glance

---

## Installation

### Location

| Component | Path |
|-----------|------|
| Main Application | `/opt/auraos/bin/auraos_homescreen.py` |
| Launcher Command | `/usr/local/bin/auraos-home` |
| Autostart Entry | `~/.config/autostart/auraos-homescreen.desktop` |
| Desktop Shortcuts | `~/Desktop/AuraOS_*.desktop` |

### Auto-Start Configuration

The home screen is configured to launch automatically 2 seconds after desktop login:

```desktop
[Desktop Entry]
Type=Application
Name=AuraOS Home
Exec=auraos-home
X-GNOME-Autostart-Delay=2
```

---

## Usage

### Launching Manually

```bash
# From terminal
auraos-home

# Or click desktop shortcut
# "AuraOS Home" icon on desktop
```

### Quick Actions

The home screen provides 4 main action buttons:

1. **🖥️ Terminal** - Launches AuraOS Terminal (AI command interface)
2. **📁 Files** - Opens Thunar file manager
3. **🌐 Browser** - Opens Firefox web browser
4. **⚙️ Settings** - Opens XFCE settings manager

### Interface Layout

```
┌─────────────────────────────────────────┐
│    ⚡ AuraOS                            │
│    AI-Powered Operating System          │
├─────────────────────────────────────────┤
│                                         │
│    ┌──────────┐    ┌──────────┐        │
│    │ Terminal │    │  Files   │        │
│    └──────────┘    └──────────┘        │
│                                         │
│    ┌──────────┐    ┌──────────┐        │
│    │ Browser  │    │ Settings │        │
│    └──────────┘    └──────────┘        │
│                                         │
├─────────────────────────────────────────┤
│ 🖥️ auraos • up 2 hours    12:34 PM    │
│                           Nov 9, 2025   │
└─────────────────────────────────────────┘
```

---

## Desktop Configuration

### Hostname

The system hostname is set to `auraos` (not `auraos-multipass` or `ubuntu`):

```bash
# Verify hostname
hostname
# Output: auraos

# View in /etc/hostname
cat /etc/hostname
# Output: auraos
```

### Background

Custom dark blue background configured via XFCE settings:

- **Color:** #0a0e27 (deep dark blue)
- **Style:** Solid color
- **Configuration:** `~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml`

### Desktop Shortcuts

Three desktop shortcuts are created:

1. **AuraOS Terminal** - Launch AI terminal
2. **AuraOS Home** - Launch dashboard
3. **Standard XFCE shortcuts** - Trash, File Manager

---

## Customization

### Changing Colors

Edit `/opt/auraos/bin/auraos_homescreen.py`:

```python
# Background color
self.root.configure(bg='#0a0e27')  # Change this

# Accent color (cyan)
fg='#00d4ff'  # Change this

# Button colors
bg='#1a1e37'  # Dark blue-gray
activebackground='#2a2e47'  # Lighter on hover
```

### Adding Quick Actions

Add new buttons to the `actions` list:

```python
actions = [
    ("🖥️ Terminal", "AuraOS Terminal", self.launch_terminal),
    ("📁 Files", "File Manager", self.launch_files),
    ("🌐 Browser", "Web Browser", self.launch_browser),
    ("⚙️ Settings", "System Settings", self.launch_settings),
    # Add your custom action here:
    ("📝 Editor", "Text Editor", self.launch_editor),
]

# Then implement the function:
def launch_editor(self):
    subprocess.Popen(['mousepad'], start_new_session=True)
```

### Disabling Auto-Start

To prevent the home screen from launching automatically:

```bash
# Remove or disable autostart entry
mv ~/.config/autostart/auraos-homescreen.desktop \
   ~/.config/autostart/auraos-homescreen.desktop.disabled
```

---

## Troubleshooting

### Home Screen Not Launching

**Check if file exists:**
```bash
ls -la /opt/auraos/bin/auraos_homescreen.py
ls -la /usr/local/bin/auraos-home
```

**Test manual launch:**
```bash
auraos-home
# Check for error messages
```

**Check autostart configuration:**
```bash
cat ~/.config/autostart/auraos-homescreen.desktop
```

### Desktop Shows Ubuntu Instead of AuraOS

**Verify hostname:**
```bash
hostname
# Should show: auraos
```

**If showing wrong hostname, fix it:**
```bash
echo "auraos" | sudo tee /etc/hostname
sudo sed -i 's/ubuntu/auraos/g' /etc/hosts
sudo reboot
```

**Check desktop background:**
```bash
cat ~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml
# Should contain AuraOS color configuration
```

### Buttons Not Working

**Check if dependencies are installed:**
```bash
# Terminal
which auraos-terminal

# File manager
which thunar

# Browser
which firefox

# Settings
which xfce4-settings-manager
```

**Install missing components:**
```bash
sudo apt update
sudo apt install thunar firefox xfce4-settings
```

### Home Screen Crashes

**View error logs:**
```bash
# Check system logs
journalctl -xe | grep -i auraos

# Run manually to see errors
python3 /opt/auraos/bin/auraos_homescreen.py
```

**Common fixes:**
```bash
# Reinstall dependencies
sudo apt install python3-tk

# Check permissions
ls -la /opt/auraos/bin/auraos_homescreen.py
# Should be executable
```

---

## Integration with AuraOS

### Terminal Integration

The home screen provides quick access to the AuraOS Terminal, which offers:
- Voice and text command input
- AI-powered command execution
- Command history
- Modern interface

Launch via home screen button or:
```bash
auraos-terminal
```

### Desktop Workflow

Typical workflow:
1. **VNC connect** → Desktop loads → Home screen appears automatically
2. **Click Terminal** → Open AuraOS AI terminal
3. **Click Files** → Browse filesystem
4. **Click Browser** → Access web resources
5. **Click Settings** → Configure system

### Command Line Access

All AuraOS tools accessible from terminal:

```bash
# Launch home screen
auraos-home

# Launch terminal
auraos-terminal

# Health check
./auraos.sh health

# Port forwarding
./auraos.sh forward status
```

---

## Technical Details

### Technology Stack

- **Language:** Python 3
- **GUI Framework:** Tkinter (built-in)
- **Desktop Environment:** XFCE4
- **Window System:** X11 (Xvfb)
- **VNC Server:** x11vnc

### System Requirements

- **RAM:** ~50-100 MB (for home screen)
- **Python:** 3.8+ with tkinter
- **Display:** X11 display server
- **Desktop:** XFCE4 or compatible

### Performance

- **Startup Time:** 1-2 seconds
- **Memory Usage:** ~50 MB
- **CPU Usage:** <1% idle
- **Response Time:** Instant button clicks

### File Structure

```
/opt/auraos/
├── bin/
│   ├── auraos_homescreen.py    # Main application
│   └── auraos_terminal.py      # Terminal app
└── gui_agent/                  # GUI automation

/usr/local/bin/
├── auraos-home                 # Home launcher
└── auraos-terminal             # Terminal launcher

~/.config/
├── autostart/
│   └── auraos-homescreen.desktop    # Auto-start
└── xfce4/
    └── xfconf/xfce-perchannel-xml/
        └── xfce4-desktop.xml        # Background
```

---

## Development

### Source Code Location

Main application: `/opt/auraos/bin/auraos_homescreen.py`

### Modifying the Interface

1. Edit the Python file directly:
   ```bash
   sudo nano /opt/auraos/bin/auraos_homescreen.py
   ```

2. Test changes:
   ```bash
   auraos-home
   ```

3. Restart desktop to apply:
   ```bash
   sudo systemctl restart auraos-x11vnc.service
   ```

### Adding Features

The application uses Tkinter - standard Python GUI framework. Examples:

**Add status indicators:**
```python
status = tk.Label(text="System: Online", fg='#00ff00')
status.pack()
```

**Add more buttons:**
```python
btn = tk.Button(text="My App", command=my_function)
btn.pack()
```

**Custom dialogs:**
```python
from tkinter import messagebox
messagebox.showinfo("AuraOS", "Hello!")
```

---

## Branding Guidelines

### Color Palette

| Element | Color | Hex Code | Usage |
|---------|-------|----------|-------|
| Primary | Cyan | `#00d4ff` | Logo, accents, highlights |
| Background | Dark Blue | `#0a0e27` | Main background |
| Secondary BG | Blue-Gray | `#1a1e37` | Buttons, panels |
| Hover | Light Gray | `#2a2e47` | Button hover state |
| Text | White | `#ffffff` | Primary text |
| Muted Text | Gray | `#888888` | Secondary text |

### Typography

- **Logo:** Arial 48pt Bold
- **Headings:** Arial 16pt
- **Body:** Arial 12pt
- **Status:** Arial 10pt

### Icons

Use emoji for quick visual recognition:
- ⚡ Lightning bolt (energy, power)
- 🖥️ Computer (system, desktop)
- 📁 Folder (files)
- 🌐 Globe (web, internet)
- ⚙️ Gear (settings)

---

## Comparison: Ubuntu vs AuraOS

| Feature | Ubuntu Default | AuraOS |
|---------|---------------|---------|
| Hostname | ubuntu/multipass | auraos |
| Background | Orange/Purple | Dark Blue |
| Login Screen | Required | Auto-logged in |
| Dashboard | None | Custom home screen |
| Terminal | Basic xterm | AI-powered terminal |
| Branding | Ubuntu | AuraOS |

---

## Support

### Getting Help

**Documentation:**
- Main: `README.md`
- Terminal: `AURAOS_TERMINAL.md`
- Desktop: `DESKTOP_ACCESS.md` (this file)
- Setup: `SETUP_VERIFICATION.md`

**Commands:**
```bash
# System health
./auraos.sh health

# Desktop status
./auraos.sh status

# View logs
./auraos.sh logs

# Restart GUI
./auraos.sh gui-reset
```

### Quick Diagnostics

```bash
# Check if home screen is running
pgrep -f auraos_homescreen

# Test manual launch
auraos-home

# View autostart entries
ls ~/.config/autostart/

# Check hostname
hostname && cat /etc/hostname
```

---

## Summary

The AuraOS Home Screen provides:

✅ Branded desktop experience (no more Ubuntu branding)  
✅ Quick access to AuraOS features  
✅ Auto-launching on desktop startup  
✅ System information display  
✅ Easy customization and extension  

**Status:** Fully operational and auto-starting on every desktop login.

**Access:** http://localhost:6080/vnc.html (password: auraos123)

---

**End of AuraOS Home Screen Guide**
