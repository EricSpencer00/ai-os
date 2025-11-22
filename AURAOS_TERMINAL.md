# AuraOS Terminal - ChatGPT-style Command Interface

**Status:** ✅ Installed and Ready  
**Location:** `/opt/auraos/bin/auraos_terminal.py`  
**Date:** November 22, 2025

---

## Overview


AuraOS Terminal is a ChatGPT-style terminal application for Ubuntu, supporting:
- **Text Input** — Type commands directly
- **Voice Input** — Speak commands (if enabled)
- **GUI Interface** — Modern, dark-themed chat terminal
- **CLI Mode** — Traditional shell mode

The terminal executes system commands and AI tasks, displaying results in a chat-like interface. Direct Ollama chat integration is planned for next release.

---

## Features

### 💬 Text Input
- Type any system command
- Command history navigation (Up/Down arrows)
- Enter key to execute
- Full shell command support

### 🎤 Voice Input (Optional)
- Speak commands into microphone
- Google Speech Recognition integration
- Automatic noise detection
- Real-time transcription display

### 🎨 GUI Interface
- Dark theme (easy on the eyes)
- Color-coded output (system, input, output, errors, success)
- Scrollable output display
- Responsive buttons
- Status bar with command status

### ⚙️ Built-in Commands
- `help` - Show available commands
- `history` - Display recent command history (last 20)
- `clear` - Clear the output display
- Plus any system command (ls, pwd, echo, etc.)

### 📝 History Management
- Automatic history saving to `~/.auraos_history`
- Persistent across sessions
- Arrow key navigation

---

## Installation

### Automatic Installation (via AuraOS setup)
```bash
./auraos.sh terminal-setup
```

### Manual Installation
```bash
# Install dependencies
pip3 install SpeechRecognition pyaudio

# Run the setup script
bash /tmp/setup_auraos_terminal_service.sh
```

---

## Usage

### Launch GUI Terminal
```bash
auraos-terminal
```

or

```bash
python3 /opt/auraos/bin/auraos_terminal.py
```

### Launch CLI Terminal (no GUI)
```bash
auraos-terminal --cli
```

or

```bash
python3 /opt/auraos/bin/auraos_terminal.py --cli
```

---

## GUI Interface Guide

### Buttons

| Button | Function |
|--------|----------|
| 📤 Execute (Enter) | Run command from text input |
| 🎤 Speak | Listen for voice command (if available) |
| 🗑️ Clear | Clear the output display |
| ❌ Exit | Close the application |

### Text Colors

| Color | Meaning |
|-------|---------|
| Green | System messages and success messages |
| Cyan | Input commands (what you typed) |
| White | Command output |
| Red | Error messages |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Execute command |
| Up Arrow | Previous command in history |
| Down Arrow | Next command in history |
| Ctrl+C | Interrupt running command (if using CLI) |

---

## Example Commands

### Basic Commands
```
pwd                    # Print working directory
ls                     # List files
whoami                 # Current user
date                   # Current date/time
echo "Hello AuraOS"    # Print text
```

### System Information
```
uname -a               # System information
lsb_release -a         # Ubuntu version
df -h                  # Disk space usage
free -h                # Memory usage
```

### File Operations
```
mkdir test             # Create directory
touch file.txt         # Create file
cat file.txt           # Display file content
cp source dest         # Copy file
mv source dest         # Move file
```

### System Utilities
```
ps aux                 # Running processes
top                    # System monitor (exit with q)
curl https://...       # Download from URL
wget https://...       # Download file
```

### Automation
```
./auraos.sh health     # Check system health
./auraos.sh automate   # Run AI automation
```

---

## Voice Commands Examples

If speech recognition is available:

1. Click "🎤 Speak" button
2. Speak clearly (e.g., "list files" or "show date")
3. System transcribes and displays the command
4. Command executes automatically

### Voice Command Examples
- "help" → Shows help menu
- "list directory" → `ls`
- "show date" → `date`
- "who am I" → `whoami`
- "make directory test" → `mkdir test`

---

## Configuration

### History File
- **Location:** `~/.auraos_history`
- **Format:** One command per line
- **Persistence:** Automatically saved with each command

### Display Settings
- **Font:** Courier 11pt (GUI), Courier 10pt (Output)
- **Resolution:** 800x600 (minimum)
- **Theme:** Dark (1e1e1e background)

### Voice Recognition
- **Service:** Google Cloud Speech Recognition
- **Audio Input:** System microphone
- **Timeout:** 10 seconds of silence
- **Language:** English (default)

---

## Troubleshooting

### "Speech recognition not available"
**Cause:** PyAudio or SpeechRecognition not installed  
**Solution:**
```bash
pip3 install SpeechRecognition pyaudio
```

### Voice input not working
**Cause:** Microphone not detected or Permission denied  
**Solution:**
```bash
# Check microphone
arecord -l

# Run with CLI mode instead
auraos-terminal --cli
```

### GUI won't open
**Cause:** DISPLAY not set or no X server  
**Solution:**
```bash
# Set display explicitly
DISPLAY=:1 auraos-terminal

# Or use CLI mode
auraos-terminal --cli
```

### Commands not executing
**Cause:** Command syntax error or missing executable  
**Solution:**
1. Check command syntax
2. Verify the command exists: `which command_name`
3. Check file permissions for scripts

### Timeout on commands
**Cause:** Command taking longer than 30 seconds  
**Solution:**
- Break command into smaller tasks
- Use background execution: `command &`
- Check for hung processes

---

## Auto-Start Configuration

### Enable Auto-Launch (at boot)
```bash
sudo systemctl enable auraos-terminal.service
```

### Disable Auto-Launch
```bash
sudo systemctl disable auraos-terminal.service
```

### View Auto-Start Status
```bash
sudo systemctl status auraos-terminal.service
```

### Manual Start/Stop
```bash
# Start service
sudo systemctl start auraos-terminal.service

# Stop service
sudo systemctl stop auraos-terminal.service

# View logs
sudo systemctl logs auraos-terminal.service -f
```

---

## Technical Details

### Architecture
```
┌─────────────────────────────────────┐
│     AuraOS Terminal GUI/CLI         │
├─────────────────────────────────────┤
│  Input Handler (Text/Voice)         │
├─────────────────────────────────────┤
│  Command Executor (subprocess)      │
├─────────────────────────────────────┤
│  Output Display (colored)           │
├─────────────────────────────────────┤
│  History Manager (persistence)      │
└─────────────────────────────────────┘
```

### Dependencies
- **Python 3.6+** - Core runtime
- **tkinter** - GUI framework (included with Python)
- **SpeechRecognition** - Voice recognition (optional)
- **PyAudio** - Microphone input (optional)
- **Google Cloud Speech API** - Speech-to-text (optional)

### File Locations
- **Binary:** `/opt/auraos/bin/auraos_terminal.py`
- **Launcher:** `/usr/local/bin/auraos-terminal`
- **Service:** `/etc/systemd/system/auraos-terminal.service`
- **Desktop Entry:** `/opt/auraos/auraos-terminal.desktop`
- **History:** `~/.auraos_history`

### Process Information
- **Type:** GUI Application (Tkinter)
- **Mode:** Single-threaded GUI, multi-threaded execution
- **Memory:** ~50-100MB (depends on history size)
- **CPU:** Low (idle), varies with command execution

---

## Performance Characteristics

### Startup Time
- **GUI Mode:** 2-3 seconds
- **CLI Mode:** <1 second

### Command Execution
- **Typical:** <1 second
- **Timeout:** 30 seconds
- **Max Output:** Unlimited (scrollable)

### History Storage
- **Per Command:** ~100 bytes average
- **Max Stored:** Limited by disk space
- **Typical Size:** 50-500KB per month

---

## Security Considerations

### Command Execution
- ✅ All commands execute with user permissions
- ✅ No privilege escalation by default
- ⚠️ Use `sudo` prefix for admin commands (with password)
- ⚠️ History file contains all commands (readable to user only)

### Voice Input
- ✅ Audio sent to Google Cloud Speech API
- ⚠️ Transcription logged locally in history
- ⚠️ Consider privacy implications of voice input

### Recommendations
- Run as non-root user (default: ubuntu)
- Disable voice input if privacy critical
- Clear history if needed: `rm ~/.auraos_history`
- Use SSH keys instead of passwords for automation

---

## Integration with AuraOS

### Related Commands
```bash
./auraos.sh automate "..."     # AI automation
./auraos.sh screenshot          # Capture desktop
./auraos.sh health              # System health
./auraos.sh logs                # View logs
```

### Environment Integration
- Full shell environment available
- Access to all installed tools
- Direct execution of AuraOS commands
- Integration with system automation

---

## Support & Help

### In-Application Help
```bash
# Type in the terminal
help                # Show available commands
history             # Show recent commands
```

### Command Help
```bash
# System command help
man command_name          # Manual pages
command --help            # Help option
```

### Troubleshooting
```bash
# Check installation
which auraos-terminal
python3 /opt/auraos/bin/auraos_terminal.py --help

# View logs
tail ~/.auraos_history
```

---

## Future Enhancements

Potential improvements:
- Command autocomplete
- Syntax highlighting for specific commands
- Themes (light/dark modes)
- Custom key bindings
- Remote execution support
- Integration with AI models for command suggestions
- Real-time system monitoring dashboard

---

## License

AuraOS Terminal is part of the AuraOS project.  
See main repository for license information.

---

**Version:** 1.0  
**Last Updated:** November 9, 2025  
**Status:** Production Ready
