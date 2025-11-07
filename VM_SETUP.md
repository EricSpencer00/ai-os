# AuraOS VM Setup Guide for ARM64 M1 Macs

This guide will help you set up QEMU virtual machines with AuraOS for isolated AI automation.

## Prerequisites

- macOS with Apple Silicon (M1/M2/M3)
- Homebrew package manager
- Python 3.8+
- At least 8GB free disk space

## 1. Install QEMU for ARM64

### Install via Homebrew

```bash
brew install qemu
```

### Verify Installation

```bash
qemu-system-aarch64 --version
```

You should see output like: `QEMU emulator version 8.x.x`

## 2. Install AuraOS Dependencies

```bash
cd /Users/eric/GitHub/ai-os/auraos_daemon
pip3 install -r requirements.txt
```

### macOS-Specific Dependencies

The following will be installed automatically on macOS:
- `pyobjc-framework-Cocoa` - For window management
- `pyobjc-framework-Quartz` - For display management

### Optional: Install cliclick for advanced automation

```bash
brew install cliclick
```

## 3. Set Up Ollama (Local LLM)

### Install Ollama on Mac Mini or MacBook

```bash
brew install ollama
```

### Download a Local Model

For fast responses, use a small model:

```bash
# Option 1: Gemma 2B (recommended for M1 with 8GB)
ollama pull gemma:2b

# Option 2: Phi-3 Mini (very fast)
ollama pull phi3:mini

# Option 3: TinyLlama (smallest, fastest)
ollama pull tinyllama
```

### Start Ollama Server

```bash
# Start in background
ollama serve &

# Or use brew services
brew services start ollama
```

### Verify Ollama is Running

```bash
curl http://localhost:11434/api/tags
```

## 4. Configure AuraOS

### Create Configuration File

```bash
cd /Users/eric/GitHub/ai-os/auraos_daemon
cp config.sample.json config.json
```

### Edit config.json

Add your API keys and configure Ollama:

```json
{
  "GROQ_API_KEY": "your-groq-api-key-here",
  "OLLAMA": {
    "enabled": true,
    "host": "localhost",
    "port": 11434,
    "model": "gemma:2b"
  },
  "LLM_ROUTING": {
    "prefer_local": true,
    "complexity_threshold": 50,
    "fallback_to_cloud": true
  },
  "VM": {
    "headless": true,
    "default_memory": "2048",
    "default_cpus": "2",
    "ssh_user": "auraos",
    "ssh_password": "auraos123"
  },
  "PLUGINS": {
    "shell": {
      "enabled": true,
      "max_execution_time": 30
    },
    "selenium_automation": {
      "enabled": true,
      "headless": false,
      "browser": "chrome"
    },
    "window_manager": {
      "enabled": true
    },
    "vm_manager": {
      "enabled": true
    }
  }
}
```

## 5. Download VM Images (ARM64)

### Option A: Ubuntu Server ARM64

```bash
# Create VM images directory
mkdir -p ~/AuraOS_VMs/images

# Download Ubuntu 22.04 ARM64
cd ~/AuraOS_VMs/images
curl -L https://cdimage.ubuntu.com/releases/22.04/release/ubuntu-22.04.3-live-server-arm64.iso \
  -o ubuntu-22.04-arm64.iso
```

### Option B: Debian ARM64

```bash
cd ~/AuraOS_VMs/images
curl -L https://cdimage.debian.org/debian-cd/current/arm64/iso-cd/debian-12.2.0-arm64-netinst.iso \
  -o debian-12-arm64.iso
```

### Option C: Alpine Linux ARM64 (Lightweight)

```bash
cd ~/AuraOS_VMs/images
curl -L https://dl-cdn.alpinelinux.org/alpine/v3.18/releases/aarch64/alpine-virt-3.18.4-aarch64.iso \
  -o alpine-arm64.iso
```

## 6. Create Your First VM

### Using AuraOS API

Start the daemon:

```bash
cd /Users/eric/GitHub/ai-os/auraos_daemon
python3 main.py
```

In another terminal, create a VM:

```bash
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "create vm test-vm ubuntu",
    "context": {}
  }'
```

### Manual QEMU Creation

```bash
# Create a disk image
qemu-img create -f qcow2 ~/AuraOS_VMs/images/test-vm.qcow2 20G

# Start VM with Ubuntu ISO
qemu-system-aarch64 \
  -M virt \
  -cpu cortex-a72 \
  -m 2048 \
  -smp 2 \
  -drive file=~/AuraOS_VMs/images/test-vm.qcow2,if=virtio,format=qcow2 \
  -cdrom ~/AuraOS_VMs/images/ubuntu-22.04-arm64.iso \
  -device virtio-net-pci,netdev=net0 \
  -netdev user,id=net0,hostfwd=tcp::2222-:22 \
  -vnc :0 \
  -boot d
```

### Install OS in VM

1. Connect via VNC: `open vnc://localhost:5900`
2. Follow Ubuntu installation wizard
3. Set username: `auraos`, password: `auraos123`
4. Install OpenSSH server when prompted
5. Reboot after installation

### Boot from Disk (After Installation)

```bash
qemu-system-aarch64 \
  -M virt \
  -cpu cortex-a72 \
  -m 2048 \
  -smp 2 \
  -drive file=~/AuraOS_VMs/images/test-vm.qcow2,if=virtio,format=qcow2 \
  -device virtio-net-pci,netdev=net0 \
  -netdev user,id=net0,hostfwd=tcp::2222-:22 \
  -vnc :0 \
  -nographic
```

## 7. Test VM Automation

### Start VM via AuraOS

```bash
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "start vm test-vm",
    "context": {}
  }' | jq

# Then execute
curl -X POST http://localhost:5050/execute_script \
  -H "Content-Type: application/json" \
  -d '{
    "script": "echo Starting VM test-vm",
    "context": {
      "script_type": "vm_start",
      "vm_name": "test-vm"
    }
  }' | jq
```

### Execute Command in VM

```bash
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "execute in vm test-vm: ls -la /home",
    "context": {}
  }' | jq
```

## 8. Test Browser Automation

```bash
# Navigate to a website
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "open website https://www.google.com",
    "context": {}
  }' | jq

# Execute the script
curl -X POST http://localhost:5050/execute_script \
  -H "Content-Type: application/json" \
  -d '{
    "script": "{\"action\": \"navigate\", \"url\": \"https://www.google.com\"}",
    "context": {
      "script_type": "selenium"
    }
  }' | jq
```

## 9. Test Window Management

```bash
# List running apps
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "list apps",
    "context": {}
  }' | jq

# Launch Safari
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "open Safari",
    "context": {}
  }' | jq
```

## 10. Architecture Notes for ARM64

### Key Differences from Intel

1. **Machine Type**: Use `-M virt` instead of `-M q35` or `-M pc`
2. **CPU**: Use ARM cores like `cortex-a72`, not x86 CPUs
3. **Boot**: ARM64 VMs may need UEFI firmware
4. **Performance**: Native ARM64 performance on M1 Macs

### QEMU Performance Tips

```bash
# Use multiple cores
-smp 2

# Allocate sufficient memory
-m 2048

# Use virtio drivers for best performance
-device virtio-net-pci
-drive if=virtio
```

### SSH into VM

```bash
# From host machine
ssh -p 2222 auraos@localhost
```

## 11. Troubleshooting

### Ollama Not Starting

```bash
# Check if running
ps aux | grep ollama

# Restart
brew services restart ollama

# Check logs
tail -f ~/Library/Logs/Homebrew/ollama.log
```

### QEMU VM Won't Boot

```bash
# Check QEMU logs
qemu-system-aarch64 ... -serial stdio

# Verify disk image
qemu-img info ~/AuraOS_VMs/images/test-vm.qcow2
```

### SSH Connection Refused

```bash
# Ensure SSH is running in VM (via VNC console)
sudo systemctl status ssh
sudo systemctl start ssh

# Check port forwarding
netstat -an | grep 2222
```

### Browser Automation Fails

```bash
# Install Chrome
brew install --cask google-chrome

# Or use Firefox
brew install --cask firefox

# Update WebDriver
pip3 install --upgrade selenium webdriver-manager
```

## 12. Performance Optimization

### For 8GB Mac Mini

- Use lightweight VMs (Alpine Linux)
- Limit VM memory to 1GB: `-m 1024`
- Use headless mode for browsers
- Prefer local Ollama for simple tasks

### For 16GB MacBook Pro

- Can run multiple VMs simultaneously
- Use 2-4GB per VM: `-m 2048` or `-m 4096`
- Run both Ollama and Groq concurrently

## 13. Next Steps

1. ✅ Create VM templates for common use cases
2. ✅ Set up automated browser testing workflows
3. ✅ Configure LLM routing preferences
4. ✅ Build custom automation scripts
5. ✅ Explore self-improvement capabilities

## Resources

- QEMU ARM64 Documentation: https://www.qemu.org/docs/master/system/target-arm.html
- Ollama Documentation: https://github.com/ollama/ollama
- AuraOS GitHub: https://github.com/EricSpencer00/ai-os

---

**Ready to automate!** 🚀
