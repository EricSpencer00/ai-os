# AuraOS - Autonomous AI Daemon

AuraOS is an autonomous AI daemon that can understand natural language intents, generate shell scripts, and execute them safely. It features self-improvement capabilities, allowing it to learn from errors and improve over time.

## Key Features

- **Natural Language Processing**: Understand user intents and translate them into executable scripts
- **Adaptive Learning**: Self-improvement mechanism that learns from errors
- **Memory System**: Remember previous commands and their results to improve future script generation
- **Secure Execution**: Sandboxed script execution with security checks
- **Plugin Architecture**: Easily extendable with new capabilities

## Architecture

AuraOS is built on a modular architecture with the following components:

- **Core Engine**: Main daemon logic, route handling, and plugin management
- **Plugin System**: Extensible plugin architecture for handling different types of tasks
- **Decision Engine**: Determines which plugin should handle a specific intent
- **Self-Improvement Engine**: Monitors errors, attempts to resolve missing abilities
- **Memory System**: Tracks command history and provides context for future commands
- **Security Layer**: Ensures safe execution of generated scripts

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Pip package manager

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/username/ai-os.git
   cd ai-os
   ```

2. Install dependencies:
   ```bash
   pip install -r auraos_daemon/requirements.txt
   ```

3. Create a configuration file:
   ```bash
   cp auraos_daemon/config.sample.json auraos_daemon/config.json
   ```

4. Edit the configuration file to add your API keys and preferences

### Starting the Daemon

```bash
cd auraos_daemon
python main.py
```

The daemon will start and listen on port 5050 by default.
