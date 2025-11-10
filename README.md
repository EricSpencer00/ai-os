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

### AuraOS Terminal (New!)

```bash
# Launch ChatGPT-style terminal
auraos-terminal

# Or use CLI mode
auraos-terminal --cli

# Example commands:
help              # Show available commands
ls                # List files
whoami            # Current user
date              # Show date/time
```

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
- `QUICKSTART.md` - Fast setup guide
- `AURAOS_TERMINAL.md` - **NEW:** ChatGPT-style terminal with voice & text commands
- `DESKTOP_ACCESS.md` - Desktop access methods and troubleshooting
- `SETUP_VERIFICATION.md` - Detailed system verification results
- `VM_SETUP.md` - VM details
- `IMPLEMENTATION.md` - Technical docs

## License

MIT License
