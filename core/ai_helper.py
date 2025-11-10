#!/usr/bin/env python3
"""AI helper utilities for AuraOS.

Provides a minimal OpenAI-compatible call (uses OPENAI_API_KEY env var) and
helpers to interpret user requests into safe, actionable commands.

This module is conservative: it will refuse to execute clearly dangerous
commands (like rm -rf or shell chaining) and requests confirmation when
commands cannot be confidently classified as safe.
"""
import os
import json
import shlex
import urllib.request
import urllib.error
import getpass

from . import key_store

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-3.5-turbo"


def call_ai_system(user_prompt, system_prompt=None, model=DEFAULT_MODEL, timeout=15):
    """Call OpenAI ChatCompletions API and return the assistant text.

    If OPENAI_API_KEY is not set or the network call fails, return None.
    """
    # Determine provider and key: prefer explicit provider in env, then key_store default
    provider = os.environ.get("PROVIDER", None)
    if not provider:
        provider = key_store.get_default_provider()

    # If provider-specific key exists in key_store, use it; otherwise fall back to env var
    api_key = None
    if provider:
        api_key = key_store.get_key(provider)

    if not api_key:
        # legacy: use OPENAI_API_KEY env var
        api_key = OPENAI_API_KEY

    if not api_key:
        return None

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 512,
    }

    data = json.dumps(payload).encode("utf-8")
    # If provider is openrouter or openai, prefer using the OpenAI python SDK (openai.OpenAI)
    provider_l = provider.lower() if provider else "openai"
    if provider_l in ("openrouter", "openai"):
        try:
            # Lazy import the OpenAI client (the package name is `openai` which provides OpenAI)
            from openai import OpenAI as _OpenAI

            base_url = "https://api.openai.com/v1"
            if provider_l == "openrouter":
                base_url = "https://openrouter.ai/api/v1"

            client = _OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": "user", "content": user_prompt}],
                temperature=0.0,
                max_tokens=512,
                # NOTE: some SDKs may reject unknown kwargs; keep minimal
            )
            # SDK returns choices[0].message.content or choices[0].delta.content for streams
            try:
                return response.choices[0].message.content
            except Exception:
                # Fallback to dict-style access
                j = json.loads(response._response.text) if hasattr(response, "_response") else None
                if j:
                    return j.get("choices", [])[0].get("message", {}).get("content")
                return None
        except Exception:
            # Fall back to direct HTTP POST below
            pass

    # Fallback: generic HTTP POST to OpenAI-compatible endpoint (uses api_key)
    req = urllib.request.Request(OPENAI_API_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            j = json.loads(body)
            # Extract assistant content if present
            return j.get("choices", [])[0].get("message", {}).get("content")
    except Exception:
        return None


def interpret_request_to_json(request_text):
    """Ask the AI to interpret a natural language request and return JSON.

    The returned JSON should follow this shape:

      "confirm_required": true|false
    }

    If AI cannot be called, fall back to a very small heuristic parser.
    """
    system = (
        "You are an assistant that converts short user automation requests into a single safe shell command. "
        "Respond ONLY with a JSON object with keys: action, command (optional), explanation, confirm_required. "
        "action must be one of: run_command, advice, ask_user. "
        "If generating a command, prefer simple, single-program commands without shell operators like &&, ;, |, >. "
        "If the command might be destructive (file deletion, format, network access), set confirm_required to true."
    )

    ai_response = call_ai_system(request_text, system_prompt=system)
    if ai_response:
        # Try to extract JSON from the AI response
        try:
            # Find first { ... }
            start = ai_response.find('{')
            if start != -1:
                json_part = ai_response[start:]
                parsed = json.loads(json_part)
                return parsed
        except Exception:
            pass

    # Fallback heuristic
    rt = request_text.lower()
    if "open firefox" in rt:
        return {"action": "run_command", "command": "firefox", "explanation": "Open Firefox browser", "confirm_required": False}
    if rt.startswith("find") or rt.startswith("search") or "find files" in rt:
        # build a safe find command searching home directory
        q = request_text.replace('find files', '').replace('search', '').strip()
        q = q if q else "*"
        cmd = f"bash -lc \"find ~ -type f -iname '*{q}*' 2>/dev/null | head -n 200\""
        return {"action": "run_command", "command": cmd, "explanation": "Search for files matching query in home directory", "confirm_required": False}

    # Default: ask user for clarification
    return {"action": "ask_user", "explanation": "I couldn't confidently map that request to a safe automated action. Please rephrase or provide more details.", "confirm_required": True}

def is_command_safe(command):
    """Naive safety check for a single command string.

    Returns (safe: bool, reason: str).
    """
    if not command or not isinstance(command, str):
        return False, "Empty or invalid command"

    low = command.lower()
    for tok in ("rm", "shutdown", "reboot", "init 0", ":(){" , "mkfs", "dd "):
        if tok in low:
            return False, f"Disallowed token: {tok}"

    # Disallow shell chaining characters
    for t in [";", "&&", "|", "$(" , "`"]:
        if t in command:
            return False, f"Shell chaining or substitution detected: {t}"

    # If it's a bash -lc wrapper, still allow but be conservative
    if command.strip().startswith("bash -lc"):
        # Allow only find-based searches produced by our fallback
        if "find ~" in command:
            return True, "Allowed home find"
        return False, "bash -lc wrapper detected and not recognized as safe"

    # Otherwise allow safe binaries (simple heuristic): allow if first token is in allowlist
    try:
        parts = shlex.split(command)
        if not parts:
            return False, "Could not parse command"
        allow = {"firefox", "find", "ls", "cat", "grep", "head", "tail", "cp", "mv", "mkdir", "tar", "unzip", "xdg-open", "python3"}
        first = os.path.basename(parts[0])
        if first in allow:
            return True, "Allowed program"
        else:
            return False, f"Program '{first}' not in allowlist"
    except Exception as e:
        return False, f"Parse error: {e}"


def sanitize_command(command_text):
    """Sanitize a multi-line command response from an LLM.

    - Splits on newlines
    - Strips whitespace
    - Blocks obviously suspicious tokens like '..' in paths
    - Returns a list of cleaned command lines or None if blocked
    """
    if not command_text or not isinstance(command_text, str):
        return None

    lines = command_text.strip().split('\n')
    cleaned = []
    for line in lines:
        ln = line.strip()
        if not ln:
            continue
        # block path traversal
        if '..' in ln:
            return None
        cleaned.append(ln)

    return cleaned if cleaned else None


def run_command(commands, shell=True):
    """Execute a list of commands sequentially.

    Returns (stdout_combined, stderr_combined, exit_code).
    This function is a conservative executor: it runs each command using
    subprocess and aggregates output. If shell=True, commands are run
    through the shell; otherwise run as args list.
    """
    import subprocess
    all_out = []
    all_err = []
    exit_code = 0

    for cmd in commands:
        try:
            if shell:
                p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            else:
                # accept list form or string
                if isinstance(cmd, str):
                    import shlex
                    parts = shlex.split(cmd)
                else:
                    parts = cmd
                p = subprocess.run(parts, capture_output=True, text=True)

            if p.stdout:
                all_out.append(p.stdout)
            if p.stderr:
                all_err.append(p.stderr)
            exit_code = p.returncode
            # If a command fails, stop executing further commands
            if p.returncode != 0:
                break

        except Exception as e:
            all_err.append(str(e))
            exit_code = 1
            break

    return "\n".join(all_out).strip(), "\n".join(all_err).strip(), exit_code
