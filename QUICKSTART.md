# AuraOS Quick Start Guide

Get up and running with AuraOS AI automation in under 10 minutes!

## Quick Install (M1 Mac)

```bash
# 1. Install system dependencies
brew install qemu ollama

# 2. Install Python dependencies
cd /Users/eric/GitHub/ai-os/auraos_daemon
pip3 install -r requirements.txt

# 3. Download local LLM model
ollama pull gemma:2b

# 4. Start Ollama service
brew services start ollama

# 5. Configure AuraOS
cp config.sample.json config.json
# Edit config.json and add your GROQ_API_KEY
# Set "OLLAMA.enabled": true

# 6. Start AuraOS daemon
python3 main.py
```

## Test It Out

In a new terminal:

```bash
# Test 1: Simple shell command
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{"intent": "list all python files in current directory"}' | jq

# Test 2: Browser automation
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{"intent": "open website https://github.com"}' | jq

# Test 3: Window management
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{"intent": "list running apps"}' | jq

# Test 4: VM management (after VM setup)
curl -X POST http://localhost:5050/generate_script \
  -H "Content-Type: application/json" \
  -d '{"intent": "create vm test-vm ubuntu"}' | jq
```

## What You Get

✅ **VM Automation** - QEMU ARM64 virtual machines for isolated automation  
✅ **Browser Control** - Selenium-powered web automation  
✅ **Window Management** - macOS app and window control  
✅ **Local LLM** - Fast responses with Ollama  
✅ **Cloud LLM** - Powerful responses with Groq  
✅ **Smart Routing** - Automatically picks the best LLM  
✅ **Memory** - Learns from past commands  
✅ **Self-Improvement** - Auto-installs missing packages  

## Architecture Overview

```
┌──────────────────────────────────────────┐
│         Natural Language Intent          │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│        Decision Engine (Routing)         │
│  • VM operations → vm_manager            │
│  • Browser tasks → selenium_automation   │
│  • App control → window_manager          │
│  • Shell commands → shell                │
└──────────────┬───────────────────────────┘
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
   ┌──────┬────────┬──────┐
   │  VM  │Browser │Window│
   │ QEMU │Selenium│ macOS│
   └──────┴────────┴──────┘
```

## Examples

### Create and Use a VM

```bash
# Create VM
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "create vm automation-box ubuntu"}'

# Start VM
curl -X POST http://localhost:5050/execute_script \
  -d '{"script": "", "context": {"script_type": "vm_start", "vm_name": "automation-box"}}'

# Run command in VM
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "execute in vm automation-box: apt update && apt install -y curl"}'
```

### Browser Automation

```bash
# Search Google
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "search google for python tutorials"}'

# Take screenshot
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "take screenshot as github-homepage.png"}'
```

### Window Control

```bash
# Open app
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "open safari"}'

# Move window
curl -X POST http://localhost:5050/generate_script \
  -d '{"intent": "move window to 100 100"}'
```

## Next Steps

1. 📖 Read [VM_SETUP.md](VM_SETUP.md) for detailed VM configuration
2. 🔧 Customize `config.json` for your preferences
3. 🚀 Build custom automation workflows
4. 🧠 Train with more commands to improve memory

## Troubleshooting

**Ollama not responding?**
```bash
brew services restart ollama
curl http://localhost:11434/api/tags
```

**QEMU not found?**
```bash
brew install qemu
qemu-system-aarch64 --version
```

**Selenium crashes?**
```bash
pip3 install --upgrade selenium webdriver-manager
brew install --cask google-chrome
```

**Permission errors?**
```bash
# Grant Terminal accessibility permissions:
# System Settings → Privacy & Security → Accessibility
```

## Help & Support

- 📚 Full docs: [README.md](README.md)
- 🐛 Issues: https://github.com/EricSpencer00/ai-os/issues
- 💬 Discussions: https://github.com/EricSpencer00/ai-os/discussions

Happy automating! 🎉
