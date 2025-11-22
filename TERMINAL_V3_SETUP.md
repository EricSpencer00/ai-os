# AuraOS Terminal v3.0 — Setup & Deployment Guide

## Quick Start

### 1. Prerequisites
```bash
# Python 3.8+
python3 --version

# Required packages
pip install flask requests pillow
```

### 2. Installation

```bash
# Clone/update repo
cd ~/ai-os

# Copy terminal to desired location
cp auraos_terminal_v3.py ~/bin/auraos-terminal
chmod +x ~/bin/auraos-terminal

# Ensure daemon is running
cd auraos_daemon
python main.py &
```

### 3. First Run

**GUI Mode (Recommended):**
```bash
python auraos_terminal_v3.py
```

**CLI Mode:**
```bash
python auraos_terminal_v3.py --cli
```

## Architecture Components Setup

### Step 1: Screen Context System

The screen context system automatically initializes on terminal start:

```python
# Automatically created:
- /tmp/auraos_screenshots/     (rolling screenshot storage)
- /tmp/auraos_screen_context.db (SQLite database)

# Rotating cleanup:
- Max 100 screenshots
- Automatic pruning of old entries
- Hash-based deduplication
```

**Manual Setup (if needed):**
```bash
mkdir -p /tmp/auraos_screenshots
chmod 755 /tmp/auraos_screenshots
```

### Step 2: Daemon Configuration

**Create config file:**
```bash
mkdir -p ~/.auraos
cat > ~/.auraos/config.json << 'EOF'
{
  "daemon": {
    "host": "localhost",
    "port": 5000,
    "timeout": 30
  },
  "screen_capture": {
    "enabled": true,
    "output_dir": "/tmp/auraos_screenshots",
    "max_screenshots": 100,
    "hash_dedup": true
  },
  "ai": {
    "auto_execute": true,
    "timeout_seconds": 300,
    "safety_level": "strict",
    "require_confirmation": false
  },
  "logging": {
    "level": "INFO",
    "file": "/tmp/auraos_terminal_v3.log"
  }
}
EOF
```

### Step 3: Daemon Service

**For systemd (Linux):**
```bash
cat > ~/.config/systemd/user/auraos-daemon.service << 'EOF'
[Unit]
Description=AuraOS Autonomous Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /path/to/auraos_daemon/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user enable auraos-daemon
systemctl --user start auraos-daemon
```

**For macOS (LaunchAgent):**
```bash
cat > ~/Library/LaunchAgents/com.auraos.daemon.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.auraos.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/auraos_daemon/main.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>

launchctl load ~/Library/LaunchAgents/com.auraos.daemon.plist
```

## Usage Examples

### Example 1: Auto-Execute Safe Task

```
User clicks [⚡ AI]
Input field: "ai- _"

User types: "create backup of documents"

✓ [1] Screen Capture: Success
✓ [2] Script Generation: tar -czf ~/backups/docs.tgz ~/Documents
✓ [3] Safety Validation: Safe
⟳ [4] Executing: tar -czf ~/backups/docs.tgz ~/Documents
✓ Output: Created backup.tgz (Size: 234 MB)
✓ [5] Validation: Backup file exists
✓ Task completed successfully
```

### Example 2: Blocked Dangerous Operation

```
User: "ai- delete all temporary files"

✓ [1] Screen Capture: Success
✓ [2] Script Generation: rm -rf /tmp/*
⚠ [3] Safety Validation: BLOCKED
✗ Dangerous pattern detected: rm -rf with wildcards

Suggestion: Did you mean to:
  • Archive files instead of deleting?
  • Use safer filters (find + delete)?
  • Manually review before deletion?
```

### Example 3: Regular Shell Command

```
User: "git status"

Output: On branch dev
        Your branch is up to date...
```

## Troubleshooting

### Issue: AI Handler Not Available

**Check daemon is running:**
```bash
curl http://localhost:5000/health
```

**If not running:**
```bash
cd ~/ai-os/auraos_daemon
python main.py &
```

### Issue: Screenshots Not Captured

**Check directory permissions:**
```bash
ls -la /tmp/auraos_screenshots
```

**Check screencapture tool:**
```bash
# macOS
which screencapture

# Linux
which scrot
```

### Issue: Safety Check Too Strict

**Adjust in config:**
```json
{
  "ai": {
    "safety_level": "moderate"
  }
}
```

## Performance Tuning

### Memory Usage

```bash
# Monitor screen context memory
du -sh /tmp/auraos_screenshots
sqlite3 /tmp/auraos_screen_context.db ".tables"
```

### Database Optimization

```bash
# Analyze and optimize
sqlite3 /tmp/auraos_screen_context.db << 'EOF'
ANALYZE;
VACUUM;
EOF
```

## Log Files

All activities logged to `/tmp/`:

```
/tmp/auraos_terminal_v3.log      # Main terminal events
/tmp/auraos_ai.log                # AI handler execution
/tmp/auraos_daemon.log            # Daemon activity
/tmp/auraos_launcher.log          # Legacy (if running)
```

**View recent logs:**
```bash
tail -f /tmp/auraos_terminal_v3.log
```

**Search for errors:**
```bash
grep -i error /tmp/auraos_*.log | head -20
```

## Integration with Existing Workflow

### Connecting to Daemon Plugins

The terminal automatically uses existing daemon plugins:

```
AIHandler.process_ai_request()
    ↓
AIHandler._generate_script()
    ↓ (HTTP POST to daemon)
Daemon.handle_generate_script()
    ↓
DecisionEngine.handle_generate_script()
    ↓
    ├─ VM Manager (vm_manager plugin)
    ├─ Selenium Automation (selenium_automation plugin)
    ├─ Window Manager (window_manager plugin)
    └─ Shell (default plugin)
```

### Using with Existing Commands

Your existing `./auraos.sh` commands work alongside v3.0:

```bash
# Still works:
./auraos.sh health
./auraos.sh gui-reset
./auraos.sh daemon-logs

# New way (from terminal):
ai- check system health
ai- restart GUI services
```

## Development & Customization

### Custom Safety Rules

Edit `EnhancedAIHandler._validate_script()`:

```python
def _validate_script(self, script: str, intent: str) -> Dict:
    # Add your custom patterns
    dangerous_patterns = [
        'rm -rf /',
        # Add more patterns...
    ]
    
    # Your logic here
```

### Custom Plugins

Extend daemon with new plugins:

```python
# auraos_daemon/plugins/custom_plugin.py
class CustomPlugin:
    def generate_script(self, intent, context):
        # Use context (includes recent screenshots)
        return {
            'script': '...',
            'reasoning': '...'
        }
```

### Screen Context Processing

Add OCR or vision analysis:

```python
# core/screen_context.py
def analyze_screenshot(self, file_path: str) -> str:
    # Use pytesseract or vision API
    text = extract_text(file_path)
    return text
```

## Security Best Practices

### Secrets Management

Never include secrets in requests:

```python
# ❌ BAD
"script": "AWS_KEY=sk_xxx ./script.sh"

# ✅ GOOD
"script": "source ~/.aws/config && ./script.sh"
```

### Audit Trail

Enable verbose logging:

```json
{
  "logging": {
    "level": "DEBUG",
    "include_script": true,
    "include_output": true
  }
}
```

Review regularly:
```bash
grep "AI_EXEC" /tmp/auraos_terminal_v3.log
```

## Production Deployment

### System Requirements

- **CPU**: Multi-core for concurrent operations
- **RAM**: 512 MB minimum (1 GB recommended)
- **Disk**: 1 GB for screenshots + database
- **Network**: Local network access to daemon

### High Availability

Run daemon with systemd:

```ini
[Service]
Type=simple
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
```

### Monitoring

```bash
# Health check endpoint
curl http://localhost:5000/health | jq .

# Monitor performance
watch -n 5 'ps aux | grep auraos'

# Disk usage
watch -n 10 'du -sh /tmp/auraos_*'
```

## Updating

### Update Terminal

```bash
cd ~/ai-os
git pull origin dev
cp auraos_terminal_v3.py ~/bin/auraos-terminal
# Restart terminal
```

### Update Daemon

```bash
cd ~/ai-os/auraos_daemon
git pull origin dev
systemctl --user restart auraos-daemon
```

## Rollback

If issues occur:

```bash
# Revert to v2.0
cp auraos_terminal_clean.py ~/bin/auraos-terminal

# Keep logs for debugging
tar -czf /tmp/auraos_logs_backup.tgz /tmp/auraos_*.log
```

## Support

For issues or questions:

1. Check logs: `/tmp/auraos_terminal_v3.log`
2. Test daemon: `curl http://localhost:5000/health`
3. Verify config: `cat ~/.auraos/config.json`
4. Review architecture: `TERMINAL_V3_ARCHITECTURE.md`

## Next Steps

1. ✅ Terminal v3.0 installed
2. ✅ Screen context system active
3. ✅ Daemon integrated
4. 👉 **Start using AI mode:**
   - Click ⚡ AI button
   - Type natural language request
   - Watch auto-execution
5. 📊 Monitor and tune based on usage
6. 🔧 Customize safety rules as needed
