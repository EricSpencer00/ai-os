# AuraOS Terminal - User Guide

## Quick Start

Launch the terminal with:

```bash
python auraos_terminal.py
```

Or if installed:

```bash
~/.local/bin/auraos-terminal
```

## Features

### ⚡ AI Mode (Recommended)

Click the **⚡ AI** button or type `ai-` followed by your request:

```
⚡ ai- install python dependencies
⚡ ai- backup important files
⚡ ai- find large log files and compress them
```

**Benefits:**
- Natural language understanding
- Screen context aware (sees last 5 minutes)
- Auto-executes if safe (no confirmation needed)
- Full safety validation and logging

### Regular Shell Commands

Type any shell command normally:

```
→ ls -la
→ git status
→ python script.py
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `help` | Show help and examples |
| `history` | View recent commands |
| `status` | System information |
| `clear` | Clear terminal |
| `exit` | Close terminal |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| ↑ / ↓ | Navigate command history |
| Esc | Clear input field |
| Enter | Execute command |

## AI Examples

```bash
# File operations
ai- find all pdf files larger than 1GB
ai- compress images in ~/Downloads
ai- backup database to external drive

# System management  
ai- list running processes using > 50% CPU
ai- check disk space and suggest cleanup
ai- install and configure nginx

# Development
ai- install project dependencies
ai- run tests and show failures
ai- initialize git repo with proper .gitignore
```

## Safety

✓ Destructive operations are blocked
✓ All actions are logged with timestamps
✓ Easy command recovery available
✓ Multi-layer safety validation

## Daemon Integration

The terminal works best with the daemon running:

```bash
cd ~/auraos_daemon
python main.py
```

Daemon handles:
- Script generation (NLP → bash)
- Safety validation
- Context awareness
- Execution tracking

## Logs

Terminal logs are written to: `/tmp/auraos_terminal.log`

View live logs:

```bash
tail -f /tmp/auraos_terminal.log
```

## Configuration

Create `~/.auraos/config.json` to customize:

```json
{
  "log_level": "INFO",
  "auto_execute_timeout": 300,
  "max_screenshot_history": 100,
  "daemon_url": "http://localhost:5000"
}
```

## Troubleshooting

### "AI handler not available"

Ensure daemon is running:

```bash
curl http://localhost:5000/health
```

If not running:

```bash
cd ~/auraos_daemon && python main.py &
```

### Terminal won't launch

Check Python dependencies:

```bash
python3 -c "import tkinter, requests, flask"
```

Install if missing:

```bash
pip install flask requests pillow
```

### Command history not working

Check permissions on log directory:

```bash
mkdir -p /tmp/auraos_screenshots
chmod 777 /tmp/auraos_screenshots
```

## CLI Mode

Run without GUI:

```bash
python auraos_terminal.py --cli
```

Useful for:
- Headless servers
- SSH sessions
- Scripting
- Testing

Example:

```bash
python auraos_terminal.py --cli << EOF
ai- list files
help
exit
EOF
```

## System Integration

### macOS (Launchd)

Create `~/Library/LaunchAgents/com.auraos.terminal.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.auraos.terminal</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/opt/auraos/auraos_terminal.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/auraos_terminal.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/auraos_terminal_error.log</string>
</dict>
</plist>
```

Load with:

```bash
launchctl load ~/Library/LaunchAgents/com.auraos.terminal.plist
```

### Linux (Systemd)

The `setup-terminal` command installs the service automatically.

Manual installation:

```bash
cp vm_resources/systemd/auraos-terminal.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable auraos-terminal.service
systemctl --user start auraos-terminal.service
```

## Performance

- **Memory:** ~50-100 MB
- **CPU:** Minimal until task execution
- **Disk:** ~10 MB (logs + screenshots)
- **Network:** Only when daemon communication needed

## Privacy & Security

- All commands logged locally
- No data sent off-device (unless daemon configured)
- Full control over what gets executed
- Easy audit trail review

---

For advanced configuration, see: `TERMINAL_SETUP.md`
For architecture details, see: `TERMINAL_ARCHITECTURE.md`
