#!/usr/bin/env python3
"""Headless terminal demo and replay tool for AuraOS Terminal

Usage:
  python3 tools/terminal_demo.py                # pretty-print action log (if exists)
  python3 tools/terminal_demo.py --replay      # POST requests to Vision Agent for replay
  python3 tools/terminal_demo.py --sample      # run a short sample demo (sends queries)

The script reads `/tmp/auraos_terminal_actions.jsonl` (JSON Lines) produced by
`auraos_terminal.py` and prints a human-readable transcript. With `--replay`
it will attempt to re-send the original `request` values to the Vision Agent at
`http://localhost:8765/ask` and show the responses. Use with caution — replay
only re-sends requests; it does not attempt to replay low-level UI actions.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

LOG_PATH = Path('/tmp/auraos_terminal_actions.jsonl')
AGENT_URL = 'http://localhost:8765/ask'


def load_actions(path=LOG_PATH):
    if not path.exists():
        return []
    out = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def pretty_print(actions):
    if not actions:
        print('No action log found at', LOG_PATH)
        return
    for i, item in enumerate(actions, 1):
        ts = item.get('ts') or ''
        req = item.get('request')
        acts = item.get('actions')
        print(f'[{i}] {ts} — request: {req}')
        if acts:
            print('   actions:')
            for a in acts:
                try:
                    print('    -', json.dumps(a, ensure_ascii=False))
                except Exception:
                    print('    -', str(a))
        else:
            print('   (no structured actions)')
        print()


def replay(actions, url=AGENT_URL, wait=1.0):
    if requests is None:
        print('requests library not available; cannot replay')
        return
    if not actions:
        print('No actions to replay')
        return
    for i, item in enumerate(actions, 1):
        req = item.get('request')
        if not req:
            continue
        print(f'Replaying [{i}] request: {req}')
        try:
            resp = requests.post(url, json={'query': req}, timeout=60)
            print('  status:', resp.status_code)
            try:
                print('  body:', json.dumps(resp.json(), indent=2, ensure_ascii=False))
            except Exception:
                print('  body (text):', resp.text[:1000])
        except Exception as e:
            print('  error:', e)
        time.sleep(wait)


def run_sample(url=AGENT_URL):
    if requests is None:
        print('requests library not available; cannot run sample')
        return
    seq = [
        'hi',
        "make an officelibre excel sheet with top 10 presidents' elections by popular vote",
        'create new excel sheet'
    ]
    for i, q in enumerate(seq, 1):
        print(f'Sample [{i}] -> {q}')
        try:
            r = requests.post(url, json={'query': q}, timeout=60)
            print('  status:', r.status_code)
            try:
                print('  body:', json.dumps(r.json(), indent=2, ensure_ascii=False))
            except Exception:
                print('  body (text):', r.text[:1000])
        except Exception as e:
            print('  error:', e)
        time.sleep(1.0)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--replay', action='store_true', help='Replay requests to Vision Agent')
    p.add_argument('--sample', action='store_true', help='Run a short sample demo by sending queries')
    args = p.parse_args()

    actions = load_actions()
    if args.sample:
        print('Running sample demo (sending queries to Vision Agent)...')
        run_sample()
        sys.exit(0)

    if args.replay:
        print('Replaying requests to Vision Agent...')
        replay(actions)
        sys.exit(0)

    # default: pretty-print
    pretty_print(actions)
