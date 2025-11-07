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
