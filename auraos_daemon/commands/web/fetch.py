#!/usr/bin/env python3
# web/fetch.py - Fetch a web page
import sys, json
try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests module not installed"}))
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: fetch.py <url>"}))
        sys.exit(1)
    url = sys.argv[1]
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        print(json.dumps({"status": r.status_code, "content": r.text[:1000]}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
