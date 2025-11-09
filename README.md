# AuraOS — VM GUI & Automation

Status: experimental (2025-11-09)

This repository contains automation and provisioning helpers to create a graphical Ubuntu VM that runs the AuraOS automation stack. The focus is on a reproducible developer flow for macOS (where QEMU was unreliable) using Multipass, plus a GUI bootstrap that installs XFCE, VNC, accessibility tools, and a small automation agent.

This README explains what the repo currently does, how to set it up, how to open the GUI, and recommended next steps and security considerations.

## What this repository provides today

- `start_vm_and_bootstrap.sh` — top-level launcher. Prefers Multipass (on macOS) and falls back to the QEMU path if available. Use `--gui` to request the GUI bootstrap.
- `start_vm_with_multipass.sh` — Multipass-specific VM creation and cloud-init wrapper (used by the top-level launcher).
- `vm_resources/gui-bootstrap.sh` — cloud-init / bootstrap script that installs:
  - XFCE desktop (`xfce4`), Xvfb, `x11vnc`, `scrot`, `xdotool`, `tesseract-ocr`, `orca`, `espeak-ng`.
  - noVNC (cloned to `/opt/novnc` and exposed via a systemd service on port 6080).
  - A Python GUI automation agent (Flask) at `/opt/auraos/gui_agent/` (default port 8765, localhost only).
  - A headless agent skeleton (`/opt/auraos/gui_agent/headless_agent.py`) listening on 127.0.0.1:8766 (disabled by default).
  - Systemd units: `auraos-x11vnc.service`, `auraos-novnc.service`, `auraos-gui-agent.service`, and an optional `auraos-headless-agent.service` (disabled).
- `open_vm_gui.sh` — host helper for macOS:
  - Ensures your public SSH key is installed into the VM (so passwordless SSH works).
  - Sets up SSH tunnels for:
    - VNC client: host:5901 -> VM:5900
    - GUI agent: host:8765 -> VM:8765
    - noVNC: host:6080 -> VM:6080 (browser access)
  - Attempts to open the browser at `http://localhost:6080` (noVNC) and/or a local VNC client.

Other files of interest:
- `vm_resources/bootstrap.sh` — original (non-GUI) bootstrap used by the QEMU path.
- `VM_GUI_PLAN.md` — design notes and planned feature list (accessibility-first, headless fast path, API keys, etc.).

## Quick start (macOS, recommended)

Prerequisites on host:

- Multipass installed (snap/multipass binary) — used for reliable VM creation on macOS.
- SSH key pair in `~/.ssh/id_rsa.pub` (or update `open_vm_gui.sh` to point to a different key).
- Optional: TigerVNC Viewer (for a better VNC client than macOS Screen Sharing).

Steps:

1. Launch the GUI VM (Multipass path):

```bash
# from repo root
./start_vm_and_bootstrap.sh --gui
```

This will create the `auraos-multipass` instance (or reuse it), run cloud-init with `vm_resources/gui-bootstrap.sh`, and provision the GUI stack. Creating the VM may take a few minutes the first time.

2. Open the GUI and agent from the host:

```bash
./open_vm_gui.sh
```

This script will:
- Ensure your public SSH key is copied into the VM (so SSH tunnels can be created).
- Create SSH tunnels for VNC (host:5901), GUI agent (8765), and noVNC (6080).
- Open the browser at http://localhost:6080 (noVNC) if available, and attempt to open TigerVNC for native client.

Default credentials and endpoints (temporary)

- VNC password (bootstrap default): `auraos123` — stored in the VM at `/home/ubuntu/.vnc/passwd` (encoded format used by x11vnc).
- GUI agent (Flask) endpoint (tunneled): `http://localhost:8765` on host after running `open_vm_gui.sh`.
- noVNC (browser): `http://localhost:6080` on host after running `open_vm_gui.sh`.

Verify desktop is visible

- Open `http://localhost:6080` in your browser (noVNC) or connect TigerVNC to `localhost:5901` and enter the VNC password.
- If you see a black screen, try restarting the services in the VM (instructions below) — the bootstrap now starts Xvfb, generates an Xauthority file, starts an XFCE session, and launches x11vnc with `-noxdamage -nowf -ncache 10` flags to avoid virtual-display damage issues.

## Useful VM commands (host)

Replace `auraos-multipass` with the instance name if you changed it.

Reload systemd and restart GUI services:

```bash
multipass exec auraos-multipass -- sudo systemctl daemon-reload
multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service auraos-novnc.service auraos-gui-agent.service || true

# check status / logs
multipass exec auraos-multipass -- sudo systemctl status auraos-x11vnc.service --no-pager
multipass exec auraos-multipass -- sudo journalctl -u auraos-x11vnc.service -n 200 --no-pager
```

Ensure VNC password exists (the host helper will create it if missing):

```bash
# From host (open_vm_gui.sh will call this automatically)
./open_vm_gui.sh
```

To enable the headless (CLI) agent inside the VM (optional):

```bash
multipass exec auraos-multipass -- sudo systemctl enable --now auraos-headless-agent.service
multipass exec auraos-multipass -- sudo systemctl status auraos-headless-agent.service --no-pager
```

The headless agent listens on `127.0.0.1:8766` by default inside the VM.

## Security notes / caveats

- The current bootstrap is experimental. The default VNC password `auraos123` is intentionally simple for testing. Change it before exposing the VM to untrusted networks.
- noVNC is installed and runs unencrypted by default on port 6080. The host helper uses SSH tunnels to limit exposure, but for production you should enable TLS and/or firewall rules.
- The automation agent (Flask) runs as a simple local service. For production, run behind a secure WSGI server, add API keys or auth, and firewall/proxy it so it's not exposed publicly.
- Systemd unit reloads sometimes require interactive polkit auth if attempted as a non-root user — the host helper uses `sudo systemctl` via Multipass where possible.

## Troubleshooting

- Black screen in VNC:
  - Ensure the X session and x11vnc are running: `multipass exec auraos-multipass -- ps aux | egrep 'Xvfb|x11vnc|xfce4'`.
  - Restart auraos-x11vnc.service: `multipass exec auraos-multipass -- sudo systemctl restart auraos-x11vnc.service` and check logs.

- noVNC not reachable:
  - Confirm `auraos-novnc.service` is active: `multipass exec auraos-multipass -- sudo systemctl status auraos-novnc.service`.
  - Confirm port is listening inside VM: `multipass exec auraos-multipass -- ss -ltnp | egrep ':6080|:5900'`.

## Files and where to look in this repo

- `start_vm_and_bootstrap.sh` — convenience launcher (multipass preferred).
- `vm_resources/gui-bootstrap.sh` — the main GUI install script (cloud-init friendly).
- `open_vm_gui.sh` — macOS helper that copies your SSH key, creates tunnels, and opens the GUI.
- `VM_GUI_PLAN.md` — roadmap and design notes (accessibility-first, headless fast-path, security hardening).

## Next steps / roadmap

Short-term:

- Harden the GUI agent (API keys, TLS, WSGI server).
- Add optional cloud-init switches to select headless vs. full GUI during create-time.
- Improve the open_vm_gui.sh UX (auto-detect installed VNC viewers, retry tunnels, health checks).

Medium-term:

- Integrate AT-SPI (Orca) access for better accessibility-first automation.
- Add a resilient systemd drop-in that guarantees Xvfb + XFCE + x11vnc start and auto-recovery.
- Add tests and verification scripts for the headless agent and GUI agent endpoints.

If you'd like, I can now:

1. Restart the VM services and verify `auraos-novnc.service` and `auraos-x11vnc.service` status/logs. (recommended)
2. Harden noVNC (TLS/token) and add a small README section with commands to rotate the VNC password.

Tell me which action to do next or request edits to this README.

---
Generated on 2025-11-09 by the repo automation helper.
# AuraOS - Autonomous AI Daemon

AuraOS is an autonomous AI daemon that can understand natural language intents, generate shell scripts, and execute them safely in isolated environments. It features self-improvement capabilities, VM isolation, browser automation, window management, and intelligent LLM routing between local and cloud models.

## 🌟 Key Features

- **VM Isolation**: QEMU ARM64 virtual machines for safe, isolated automation on M1 Macs
- **Browser Automation**: Selenium-powered web automation and scraping
- **Window Management**: Native macOS app and window control
- **Dual LLM System**: Intelligent routing between local Ollama and cloud Groq API
- **Natural Language Processing**: Understand user intents and translate them into executable scripts
- **Adaptive Learning**: Self-improvement mechanism that learns from errors
- **Memory System**: Remember previous commands and their results to improve future script generation
- **Secure Execution**: Sandboxed script execution with security checks
- **Plugin Architecture**: Easily extendable with new capabilities

## 🏗️ Architecture

AuraOS is built on a modular architecture with the following components:

- **Core Engine**: Main daemon logic, route handling, and plugin management
- **LLM Router**: Intelligent selection between local (Ollama) and cloud (Groq) models
- **Plugin System**: Extensible plugin architecture for different automation types
  - **VM Manager**: QEMU virtual machine lifecycle and automation
  - **Selenium**: Browser automation and web scraping
  - **Window Manager**: macOS window and application control
  - **Shell**: Safe shell command execution
- **Decision Engine**: Routes intents to the appropriate plugin
- **Self-Improvement Engine**: Monitors errors, attempts to resolve missing abilities
- **Memory System**: Tracks command history and provides context for future commands
- **Security Layer**: Ensures safe execution of generated scripts

## 🚀 Quick Start

See [QUICKSTART.md](QUICKSTART.md) for a 10-minute setup guide.

### Prerequisites

- macOS with Apple Silicon (M1/M2/M3) or Intel
- Python 3.8 or higher
- Homebrew package manager

### Installation

1. **Install system dependencies:**
   ```bash
   brew install qemu ollama
   ```

2. **Clone the repository:**
   ```bash
   git clone https://github.com/EricSpencer00/ai-os.git
   cd ai-os
   ```

3. **Install Python dependencies:**
   ```bash
   pip3 install -r auraos_daemon/requirements.txt
   ```

4. **Set up local LLM:**
   ```bash
   ollama pull gemma:2b
   brew services start ollama
   ```

5. **Create configuration:**
   ```bash
   cd auraos_daemon
   cp config.sample.json config.json
   # Edit config.json to add your Groq API key and configure settings
   ```

6. **Start the daemon:**
   ```bash
   python3 main.py
   ```

The daemon will start and listen on port 5050 by default.

## 💡 Usage Examples

### Shell Commands
```bash
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{"intent": "find all Python files larger than 1MB"}'
```

### VM Management
```bash
# Create a VM
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "create vm test-vm ubuntu"}'

# Execute command in VM
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "execute in vm test-vm: ls -la"}'
```

### Browser Automation
```bash
# Navigate to website
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "open website https://github.com"}'

# Search Google
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "search google for AI automation"}'
```

### Window Management
```bash
# Launch application
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "open Safari"}'

# List running apps
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "list all running applications"}'
```

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 10 minutes
- **[VM_SETUP.md](VM_SETUP.md)** - Complete VM setup guide for ARM64
- **[plan.md](plan.md)** - Original project vision and roadmap

## 🎯 Architecture for M1 Macs

AuraOS is optimized for Apple Silicon with:
- Native ARM64 QEMU virtual machines
- Local Ollama models for fast, private AI responses
- Intelligent LLM routing to balance speed vs. capability
- macOS-native window and app automation

### LLM Routing Strategy

```
Simple Request (< complexity threshold)
    ↓
Local Ollama (fast, private)
    │
    ├─ Success → Return
    └─ Failure → Fallback to Groq Cloud

Complex Request (≥ complexity threshold)
    ↓
Groq Cloud (powerful, slower)
    │
    ├─ Success → Return
    └─ Failure → Fallback to Ollama
```

## 🔌 Plugin System

### Available Plugins

| Plugin | Status | Description |
|--------|--------|-------------|
| **shell** | ✅ Production | Safe shell command execution |
| **vm_manager** | ✅ Production | QEMU VM lifecycle and automation |
| **selenium_automation** | ✅ Production | Browser automation and web scraping |
| **window_manager** | ✅ Production | macOS window and app control |

### Creating Custom Plugins

Create a new file in `auraos_daemon/plugins/your_plugin.py`:

```python
class Plugin:
    name = "your_plugin"
    
    def generate_script(self, intent, context):
        # Generate script from intent
        return jsonify({"script_type": "custom", "script": script}), 200
    
    def execute(self, script, context):
        # Execute the script
        return jsonify({"output": result}), 200
```

## 🔒 Security

AuraOS includes multiple security layers:
- Command sanitization and validation
- Restricted file system access (Downloads folder only for writes)
- Blocked dangerous patterns (rm -rf, sudo, etc.)
- VM isolation for untrusted operations
- URL validation for web requests
- Configurable security policies

## 🧠 Self-Improvement

AuraOS can improve itself by:
- Detecting missing capabilities
- Automatically installing required packages
- Learning from command history
- Validating and improving script outputs
- Rolling back failed improvements

## 🛠️ Configuration

Edit `config.json` to customize:

```json
{
  "GROQ_API_KEY": "your-key",
  "OLLAMA": {
    "enabled": true,
    "model": "gemma:2b"
  },
  "LLM_ROUTING": {
    "prefer_local": true,
    "complexity_threshold": 50
  },
  "VM": {
    "headless": true,
    "default_memory": "2048"
  }
}
```

## 📊 System Requirements

### Minimum (M1 Mac Mini 8GB)
- 8GB RAM
- 20GB free disk space
- macOS 12.0+

### Recommended (M1 MacBook Pro 16GB)
- 16GB RAM
- 50GB free disk space
- macOS 13.0+

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is open source. See LICENSE for details.

## 🙏 Acknowledgments

- Built with inspiration from the AuraOS vision in `plan.md`
- Powered by Groq, Ollama, QEMU, and Selenium
- Designed for Apple Silicon Macs

## 🔗 Links

- **GitHub**: https://github.com/EricSpencer00/ai-os
- **Issues**: https://github.com/EricSpencer00/ai-os/issues
- **Discussions**: https://github.com/EricSpencer00/ai-os/discussions

---

**Ready to automate your world!** 🚀
