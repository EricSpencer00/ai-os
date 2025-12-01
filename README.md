![aura-os-ss.png](aura-os-ss.png)
# AuraOS — AI-Powered OS Automation

**Status:** Experimental (2025-11-09)

AuraOS provides AI-powered automation for Ubuntu desktop environments through vision-based screen understanding and automated interactions. The system uses local vision models (Ollama LLaVA) to understand what's on screen and perform tasks like clicking icons, opening applications, and navigating interfaces.

## Quick Start (3 Commands)

**Prerequisites:** macOS with Apple Silicon (M1/M2/M3) recommended

```bash
# 1. Install all dependencies (Homebrew, Multipass, Ollama, Python packages)
./auraos.sh install

# 2. Create and configure Ubuntu VM with desktop environment
./auraos.sh vm-setup

# 3. Verify everything is working
./auraos.sh health
```

That's it! Your Ubuntu desktop is now accessible at: **http://localhost:6080/vnc.html** (password: `auraos123`)

🖥️ **Desktop boots directly to XFCE** - No login screen, ready to use immediately!

## Usage Examples

### AuraOS Terminal (AI-Powered)

The terminal is the easiest way to interact with the system using natural language:

```bash
# Launch terminal
./auraos.sh setup-terminal    # First time only
auraos-terminal              # Or: python auraos_terminal.py

# Example AI commands (click ⚡ AI button or type "ai-"):
ai- install python dependencies
ai- backup important files
ai- find large log files and compress them
ai- list running processes using high CPU

# Regular shell commands also work:
help              # Show available commands
ls                # List files
whoami            # Current user
date              # Show date/time
```

**Key Features:**
- ⚡ **AI Button**: One-click access to natural language mode
- 🚀 **Auto-Execute**: Safe tasks run without confirmation
- 📸 **Screen Context**: AI understands last 5 minutes of activity
- 🔒 **Safe**: Dangerous operations blocked automatically
- 📝 **Logged**: All actions tracked with full audit trail

See `TERMINAL_README.md` for detailed terminal guide.

### AI Automation

```bash
# Click on desktop icons by description
./auraos.sh automate "click on the Firefox icon"
./auraos.sh automate "click on file manager"
./auraos.sh automate "open the applications menu"

# Capture screenshot
./auraos.sh screenshot
```

### System Management

```bash
# Check system health (7 comprehensive checks)
./auraos.sh health

# View VM and service status
./auraos.sh status

# Complete clean restart of GUI services
./auraos.sh gui-reset
```

## What AuraOS Does

- **AI Vision Automation**: Uses LLaVA 13B vision model to understand desktop screenshots
- **Automated Ubuntu Desktop**: Full XFCE desktop via browser (noVNC)
- **Screen Interaction**: Click, type, navigate using natural language
- **Local Processing**: Runs entirely on your Mac - no cloud required
- **Easy Setup**: Three commands to get started

## How It Works

1. **Screenshot Capture**: VM desktop captured via GUI agent
2. **Vision Analysis**: Ollama LLaVA analyzes and describes UI elements
3. **Coordinate Extraction**: Model identifies element locations
4. **Action Execution**: xdotool performs clicks at coordinates

**Pipeline Timing:** ~15-20 seconds per task (mostly vision analysis)

## Health check (MVP)

After starting the daemon you can verify the service and LLM availability with:

```bash
# start the daemon (from repo root) — this helper will create/activate the venv if needed
./auraos_daemon/run.sh &

# then check health
curl http://localhost:5050/health | jq
```

The `/health` endpoint reports whether the local Ollama router is available and lists loaded plugins. This is useful for smoke tests and CI.

## Preventing the VM from locking the screen (5-minute lock)

If your VM goes to a lock screen after a short idle time (e.g. 5 minutes), run the helper script included in the repo to disable session blanking and common locker daemons inside the VM.

To apply the fix (from the host):

```bash
# Copy the helper into the VM and run it as root (replace VM name and user if different)
multipass transfer vm_resources/disable_screensaver.sh auraos-multipass:/tmp/disable_screensaver.sh
multipass exec auraos-multipass -- sudo bash /tmp/disable_screensaver.sh ubuntu

# Alternatively (pipe it directly):
#sudo multipass exec auraos-multipass -- bash -s ubuntu < vm_resources/disable_screensaver.sh
```

Re-login to the VM desktop (or reboot) for autostart changes to fully apply. This helper creates a small autostart entry that runs xset to disable blanking and DPMS and attempts to stop common locker daemons (light-locker, xscreensaver, xss-lock).

## All Commands

Run `./auraos.sh help` for full command list. Key commands:

- `install` - Install all dependencies
- `vm-setup` - Create Ubuntu VM
- `health` - System health check
- `forward start|stop|status` - Manage port forwarders
- `automate "<task>"` - AI automation
- `screenshot` - Capture desktop
- `gui-reset` - Reset VNC/noVNC
- `keys` - Manage API keys

## Default Credentials

**VNC Password:** `auraos123`  
**VM SSH:** `ubuntu` / `auraos123`

⚠️ **Security Note:** Development defaults - change for production use

## Troubleshooting

### Port Forwarders Not Working
```bash
# Check forwarder status
./auraos.sh forward status

# Restart forwarders
./auraos.sh forward stop
./auraos.sh forward start
```

### VNC Not Working
```bash
./auraos.sh gui-reset
```

### Vision Returning Wrong Coords
```bash
./auraos.sh keys ollama llava:13b llava:13b
```

### VM Not Starting
```bash
multipass list
multipass restart auraos-multipass
```

## System Requirements

- macOS 11+ (Apple Silicon recommended)
- 8GB RAM (4GB for VM)
- 30GB free disk space


## Documentation

- Run `./auraos.sh help` for all commands
- [QUICKSTART.md](QUICKSTART.md) — Fast setup guide
- [AURAOS_TERMINAL.md](AURAOS_TERMINAL.md) — ChatGPT-style terminal with voice & text commands
- [DESKTOP_ACCESS.md](DESKTOP_ACCESS.md) — Desktop access methods and troubleshooting
- [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md) — System verification results
- [VM_SETUP.md](VM_SETUP.md) — VM details
- [IMPLEMENTATION.md](IMPLEMENTATION.md) — Technical docs
- [TERMINAL_README.md](TERMINAL_README.md) — Terminal usage and features
- [TERMINAL_V3_SETUP.md](TERMINAL_V3_SETUP.md) — Terminal v3 setup
- [TERMINAL_V3_ARCHITECTURE.md](TERMINAL_V3_ARCHITECTURE.md) — Terminal v3 architecture
- [TERMINAL_V3_QUICKREF.md](TERMINAL_V3_QUICKREF.md) — Terminal v3 quick reference
- [TEST_PLAN.md](TEST_PLAN.md) — Testing plan and procedures

## License

MIT License
