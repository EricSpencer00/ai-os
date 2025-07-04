#!/usr/bin/env python3
# system/info.py - Print basic system info
import platform, json

def main():
    info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }
    print(json.dumps(info))

if __name__ == "__main__":
    main()
