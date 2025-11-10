#!/usr/bin/env python3
"""Quick tests for AI terminal integrations.

This script runs simple, deterministic checks that don't require real API keys
or network access where possible. It prints results for manual inspection.
"""
import os
import sys
import json
import traceback

# Ensure repo root is on sys.path so `core` package (top-level modules) can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import key_store, ai_helper


def test_key_store():
    print("\n== key_store tests ==")
    path = key_store.get_store_path()
    print("store path:", path)
    # ensure clean
    try:
        key_store.remove_key("__testprov__")
    except Exception:
        pass

    key_store.set_key("__testprov__", "fakekey123")
    got = key_store.get_key("__testprov__")
    print("set/get key ->", got)
    assert got == "fakekey123"
    key_store.remove_key("__testprov__")
    print("removed test key")


def test_interpret_fallbacks():
    print("\n== interpret_request_to_json fallbacks ==")
    cases = [
        ("open firefox", "firefox"),
        ("find files notes", "find ~"),
    ]
    for inp, expected in cases:
        try:
            res, provider = ai_helper.interpret_request_to_json(inp)
            cmd = res.get('command') or ''
            print(f"input: {inp!r} -> action: {res.get('action')}, command: {cmd!r}, provider: {provider}")
            assert res.get("action") == "run_command"
            # If the provider produced a response, the exact command may vary; check presence of expected token
            assert expected.split()[0] in cmd or expected in cmd or (expected == 'find ~' and 'find' in cmd)
        except AssertionError:
            print("  FAILED for", inp)
            traceback.print_exc()


def test_get_ai_response():
    print("\n== get_ai_response basic test ==")
    # Try a harmless prompt; on most dev machines without keys/ollama this will return success False
    r = ai_helper.get_ai_response("Say hello in one sentence.")
    print("result:", json.dumps(r, indent=2))


if __name__ == '__main__':
    print("Running quick AI integration checks...")
    try:
        test_key_store()
        test_interpret_fallbacks()
        test_get_ai_response()
        print("\nAll quick tests finished.")
    except Exception as e:
        print("ERROR during tests:", e)
        traceback.print_exc()
        raise
