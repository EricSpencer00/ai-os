"""
AuraOS Autonomous AI Daemon v8
Main entrypoint. Starts the daemon.
"""
from core.daemon import AuraOSDaemon

def main():
    daemon = AuraOSDaemon()
    daemon.run()

if __name__ == "__main__":
    main()
