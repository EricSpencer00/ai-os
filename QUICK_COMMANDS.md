# AuraOS v2 — Quick Command Reference

Essential commands for getting started with the new architecture.

## 🚀 Quick Start (5 minutes)

```bash
# 1. One-command setup
cd ~/GitHub/ai-os
bash tools/v2_setup.sh

# 2. Test all components
python3 tools/demo_v2_architecture.py

# 3. Read the guide
cat V2_README.md
```

## 📋 Essential Commands

### Setup & Installation
```bash
# Full setup (dependencies, models, tools)
bash tools/v2_setup.sh

# Setup with minimal output
bash tools/v2_setup.sh 2>/dev/null

# Install just WebSocket agent in running VM
multipass exec auraos-multipass -- bash tools/install_ws_agent.sh
```

### Testing & Verification
```bash
# Run interactive demo (tests all components)
python3 tools/demo_v2_architecture.py

# Test specific components
python3 tools/demo_v2_architecture.py --steps 1
python3 tools/demo_v2_architecture.py --no-ws    # Skip WebSocket
python3 tools/demo_v2_architecture.py --no-vision  # Skip LLaVA

# Test delta detection
python3 -c "
from auraos_daemon.core.screen_diff import ScreenDiffDetector
detector = ScreenDiffDetector()
result = detector.capture_and_diff()
print(f'Changed regions: {len(result[\"changed_regions\"])}')
"

# Test local planner
python3 -c "
from auraos_daemon.core.local_planner import LocalPlanner
planner = LocalPlanner()
actions = planner.plan('click desktop', 'Ubuntu desktop with taskbar')
print(f'Planned {len(actions)} actions')
"

# Test WebSocket agent (quick)
python3 - <<'PY'
from auraos_daemon.core.ws_agent import WebSocketAgent
agent = WebSocketAgent()
print('connect()', agent.connect())
try:
  if getattr(agent, 'is_connected', lambda: True)():
    agent.click(100, 100)
finally:
  try:
    agent.disconnect()
  except Exception:
    pass
PY
```

### VM Health & Recovery
```bash
# Check VM health
./auraos.sh health

# Run VM wake check
bash tools/vm_wake_check.sh

# Watch wake check logs
tail -f logs/vm_wake_check.log

# Check VM processes
multipass list
multipass info auraos-multipass

# SSH into VM
multipass exec auraos-multipass -- bash

# Check WebSocket agent in VM
multipass exec auraos-multipass -- systemctl status auraos-ws-agent

# Restart WebSocket agent
multipass exec auraos-multipass -- systemctl restart auraos-ws-agent

# Watch agent logs
multipass exec auraos-multipass -- journalctl -u auraos-ws-agent -f
```

### macOS Wake Check Setup
```bash
# Install LaunchAgent for automatic wake checks
cp tools/com.auraos.vm-wake-check.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.auraos.vm-wake-check.plist

# Verify it's loaded
launchctl list | grep auraos

# Unload if needed
launchctl unload ~/Library/LaunchAgents/com.auraos.vm-wake-check.plist

# Manual trigger of wake check
launchctl start com.auraos.vm-wake-check
```

### Port Forwarding
```bash
# Enable all port forwarders
./auraos.sh forward start

# Disable all port forwarders
./auraos.sh forward stop

# Check forwarding status
./auraos.sh forward status

# Check specific ports
netstat -an | grep 5901   # VNC
netstat -an | grep 6080   # noVNC
netstat -an | grep 6789   # WebSocket
netstat -an | grep 8765   # GUI agent
```

### Logs & Debugging
```bash
# View v2 setup log
cat logs/v2_setup.log

# View VM wake check log
cat logs/vm_wake_check.log
tail -f logs/vm_wake_check.log

# View VM bootstrap log
cat logs/bootstrap.log

# View VM logs (SSH in first)
multipass exec auraos-multipass -- cat /var/log/auraos/bootstrap_done

# Check if bootstrap completed
multipass exec auraos-multipass -- test -f /var/log/auraos/bootstrap_done && echo "Done" || echo "Not done"
```

## 📖 Documentation Commands

```bash
# Quick start & index
cat V2_README.md

# Full architecture reference
cat ARCHITECTURE_V2.md

# Integration guide (for developers)
cat V2_INTEGRATION_GUIDE.md

# Implementation summary
cat V2_IMPLEMENTATION_SUMMARY.md

# This delivery report
cat COMPLETION_SUMMARY.md

# Quick commands (this file)
cat QUICK_COMMANDS.md
```

## 🔧 Configuration

### Enable/Disable v2 Features
```bash
# Edit configuration
nano auraos_daemon/config.json

# Key settings:
{
  "INFERENCE": {
    "use_delta_detection": true,        # Enable/disable delta detection
    "use_local_planner": true,          # Enable/disable local planner
    "use_websocket_agent": true,        # Enable/disable WebSocket agent
    "vision_only_on_demand": true       # Only use vision when needed
  }
}
```

### Tune Performance
```bash
# Delta detection settings
{
  "PERCEPTION": {
    "grid_size": 64,        # Smaller = finer granularity, more compute
    "delta_threshold": 20,  # Higher = less sensitive to noise
    "max_regions": 10       # Limit regions sent to LLM
  }
}

# Planning settings
{
  "PLANNING": {
    "local_planner_model": "mistral",  # Or "phi", "neural-chat"
    "local_planner_timeout": 30
  }
}

# Control settings
{
  "CONTROL": {
    "ws_connection_timeout": 10,
    "ws_action_timeout": 5,
    "action_retry_count": 2
  }
}
```

## 🐛 Troubleshooting Quick Fixes

### "Delta detection not working"
```bash
# Check scrot
apt-get install scrot

# Test manually
DISPLAY=:1 scrot /tmp/test.png && echo "OK" || echo "FAILED"
```

### "Local planner returns empty"
```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Pull model
ollama pull mistral
```

### "WebSocket agent not responding"
```bash
# Check service
multipass exec auraos-multipass -- systemctl status auraos-ws-agent

# Restart
multipass exec auraos-multipass -- systemctl restart auraos-ws-agent

# Check port
nc -zv 127.0.0.1 6789
```

### "VM doesn't recover after sleep"
```bash
# Manual wake check
bash tools/vm_wake_check.sh

# Check LaunchAgent
launchctl list com.auraos.vm-wake-check

# View logs
tail -f logs/vm_wake_check.log
```

## 🚀 Integration Workflow

```bash
# Phase 1: Foundation (Week 1)
bash tools/v2_setup.sh
python3 tools/demo_v2_architecture.py
cat V2_README.md

# Phase 2: Testing (Week 2)
cat V2_INTEGRATION_GUIDE.md
# (Add v2 config to config.json)
# (Import modules in daemon)

# Phase 3: Integration (Week 3)
# (Replace screenshot calls with delta detection)
# (Use local planner as default)
# (Switch to WebSocket agent)

# Phase 4: Verification
./auraos.sh health
bash tools/vm_wake_check.sh
python3 tools/demo_v2_architecture.py
```

## 📊 Monitoring Performance

```bash
# Before (v1) — estimate from logs
# After (v2) — measure actual times

# Monitor inference loop (if available)
# Check logs for:
#   - Delta detection time
#   - Planner response time
#   - Action execution time
#   - Total cycle time

# Compare:
# v1: 5-10 seconds per cycle
# v2: 600ms-1.2 seconds per cycle
# Target: 10-12x speedup
```

## 💾 Backup & Recovery

```bash
# Backup current config
cp auraos_daemon/config.json auraos_daemon/config.json.backup

# Backup VM state
multipass export auraos-multipass > ~/auraos-vm-backup.qcow2

# Restore VM from backup
multipass delete -p auraos-multipass
multipass import ~/auraos-vm-backup.qcow2 auraos-multipass
```

## 🔗 Useful Resources

- **Architecture Guide**: `ARCHITECTURE_V2.md`
- **Integration Guide**: `V2_INTEGRATION_GUIDE.md`
- **Quick Start**: `V2_README.md`
- **Demo Script**: `python3 tools/demo_v2_architecture.py --help`
- **Setup Script**: `bash tools/v2_setup.sh --help` (if available)

---

**Version**: 2.0  
**Last Updated**: 2025-11-09  
**For Help**: See relevant documentation file above
