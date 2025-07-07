"""
AuraOS Autonomous AI Daemon v8
Main entrypoint. Starts the daemon.

Features:
- Natural language intent processing
- Automatic script generation and execution
- Self-healing output validation and script improvement
- Memory-based learning from past commands
- Security-focused command execution
- Comprehensive error handling and recovery
- Self-improvement through error analysis
"""
import logging
from core.daemon import AuraOSDaemon

def main():
    logging.info("Starting AuraOS Autonomous AI Daemon v8")
    logging.info("Output validation and auto-improvement enabled")
    daemon = AuraOSDaemon()
    daemon.run()

if __name__ == "__main__":
    main()
