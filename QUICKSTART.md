# AuraOS Quick Start Guide

Get AuraOS running with AI vision automation in 3 commands.

## Installation (First Time)

```bash
# Install everything: Homebrew, Multipass, Ollama, Python deps, vision model
./auraos.sh install
```

This installs:
- Multipass (Ubuntu VM manager)
- Ollama (local LLM runtime)
- LLaVA 13B vision model
- Python virtual environment with all dependencies

**Time:** ~10-15 minutes (depending on internet speed for model download)

## VM Setup (First Time)

```bash
# Create Ubuntu VM with XFCE desktop, VNC, noVNC, automation agent
./auraos.sh vm-setup
```

This creates:
- Ubuntu 22.04 VM (2 CPUs, 4GB RAM, 20GB disk)
- XFCE desktop environment
- VNC server (x11vnc) on port 5900
- noVNC web server on port 6080
- GUI automation agent on port 8765
- SSH port forwarding for all services

**Time:** ~5-10 minutes

## Verify Everything Works

```bash
# Run comprehensive health check
./auraos.sh health
```

Should show all 7 checks passing:
- ✓ VM running
- ✓ x11vnc running
- ✓ noVNC running
- ✓ VNC password exists
- ✓ Port 5900 listening
- ✓ Port 6080 listening
- ✓ Web server responding

## Access the Desktop

Open in your browser: **http://localhost:6080/vnc.html**

Password: `auraos123`

You should see an Ubuntu XFCE desktop!

## Try AI Automation

```bash
# Screenshot
./auraos.sh screenshot
# Saves to /tmp/auraos_screenshot.png

# AI automation tasks
./auraos.sh automate "click on the file manager icon"
./auraos.sh automate "click on Firefox"
./auraos.sh automate "open applications menu"
```

**How it works:**
1. Captures screenshot from VM
2. Sends to Ollama LLaVA vision model
3. Model analyzes image and returns coordinates
4. Clicks at those coordinates using xdotool

**Timing:** ~15-20 seconds per task

## Common Commands

```bash
./auraos.sh help              # Show all commands
./auraos.sh status            # VM and service status
./auraos.sh health            # Full health check
./auraos.sh gui-reset         # Reset VNC if not working
./auraos.sh restart           # Restart all services
./auraos.sh logs              # View agent logs
./auraos.sh screenshot        # Capture screen
./auraos.sh keys list         # Show API keys
```

## Troubleshooting

### Black Screen in VNC
```bash
./auraos.sh gui-reset
```

### Vision Model Not Working
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Reconfigure vision model
./auraos.sh keys ollama llava:13b llava:13b
```

### VM Won't Start
```bash
# Check multipass
multipass list

# Restart VM
multipass restart auraos-multipass
```

### Port Already in Use
```bash
# Kill existing SSH tunnels
pkill -f "ssh.*5901:localhost:5900"
pkill -f "ssh.*6080:localhost:6080"

# Re-run vm-setup
./auraos.sh vm-setup
```

## Next Steps

1. **Explore the Desktop**: Open noVNC and navigate around XFCE
2. **Test Different Automations**: Try various click commands
3. **Check the Logs**: See what the vision model is seeing
4. **Build Workflows**: Chain multiple automation tasks

## What Gets Installed

**On macOS Host:**
- Homebrew (if not present)
- Multipass VM manager
- Ollama LLM runtime
- LLaVA 13B vision model
- Python 3 virtual environment

**In Ubuntu VM:**
- XFCE4 desktop
- Xvfb (virtual display)
- x11vnc (VNC server)
- noVNC (web VNC client)
- xdotool (GUI automation)
- Python GUI agent (Flask API)

**Disk Usage:**
- LLaVA 13B model: ~7.4 GB
- Ubuntu VM disk: 20 GB (sparse, grows as needed)
- Python packages: ~500 MB

## Default Settings

- **VM Name:** `auraos-multipass`
- **VNC Password:** `auraos123`
- **VM SSH:** `ubuntu` / `auraos123`
- **noVNC URL:** http://localhost:6080/vnc.html
- **VNC Port:** 5901 (tunneled from VM's 5900)
- **GUI Agent:** http://localhost:8765

## Advanced

### Manual VM Control

```bash
# SSH into VM
multipass shell auraos-multipass

# Run commands in VM
multipass exec auraos-multipass -- <command>

# Stop VM
multipass stop auraos-multipass

# Start VM
multipass start auraos-multipass

# Delete VM (careful!)
multipass delete auraos-multipass
multipass purge
```

### Vision Model Options

```bash
# Try different model (faster but less accurate)
ollama pull minicpm-v
./auraos.sh keys ollama minicpm-v minicpm-v

# Use cloud APIs (optional, requires API keys)
./auraos.sh keys add openai sk-...
./auraos.sh keys add anthropic sk-ant-...
```

## Full Command Reference

Run `./auraos.sh help` for complete documentation.

---

**That's it!** You now have AI-powered desktop automation running locally.
