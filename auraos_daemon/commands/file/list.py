#!/usr/bin/env python3
# file/list.py - List files in a directory
import os, sys, json

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    try:
        files = os.listdir(path)
        print(json.dumps({"files": files}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
