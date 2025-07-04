#!/usr/bin/env python3
# file/search.py - Search for text in files in a directory
import os, sys, json, re

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: search.py <directory> <pattern>"}))
        sys.exit(1)
    directory, pattern = sys.argv[1], sys.argv[2]
    matches = []
    for root, _, files in os.walk(directory):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if re.search(pattern, line):
                            matches.append({"file": fpath, "line": i, "text": line.strip()})
            except Exception:
                continue
    print(json.dumps({"matches": matches}))

if __name__ == "__main__":
    main()
