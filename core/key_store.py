"""Simple per-user API key store for Aurora OS AI integrations.

Stores provider keys in a JSON file under the user's home directory with
restricted permissions. This is intentionally lightweight (no encryption) but
writes the file with 0o600 permissions. Callers should avoid printing keys.

API:
  get_store_path() -> path
  get_key(provider) -> key or None
  set_key(provider, key)
  list_providers() -> list
  remove_key(provider)
  set_default_provider(provider)
  get_default_provider() -> provider or None
"""
import json
import os
from typing import Optional


def get_store_path() -> str:
    d = os.path.expanduser("~/.auraos")
    if not os.path.isdir(d):
        try:
            os.makedirs(d, exist_ok=True)
            # Try to limit permissions on the directory
            try:
                os.chmod(d, 0o700)
            except Exception:
                pass
        except Exception:
            # Fallback to home dir
            return os.path.expanduser("~/.auraos_api_keys.json")
    return os.path.join(d, "api_keys.json")


def _load_store() -> dict:
    path = get_store_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_store(d: dict):
    path = get_store_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    try:
        os.replace(tmp, path)
    except Exception:
        # best-effort
        os.rename(tmp, path)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def get_key(provider: str) -> Optional[str]:
    if not provider:
        return None
    s = _load_store()
    return s.get("keys", {}).get(provider)


def set_key(provider: str, key: str):
    if not provider or not key:
        raise ValueError("provider and key are required")
    s = _load_store()
    keys = s.get("keys", {})
    keys[provider] = key
    s["keys"] = keys
    _save_store(s)


def list_providers() -> list:
    s = _load_store()
    return list(s.get("keys", {}).keys())


def remove_key(provider: str):
    s = _load_store()
    keys = s.get("keys", {})
    if provider in keys:
        del keys[provider]
        s["keys"] = keys
        _save_store(s)


def set_default_provider(provider: Optional[str]):
    s = _load_store()
    s["default_provider"] = provider
    _save_store(s)


def get_default_provider() -> Optional[str]:
    s = _load_store()
    return s.get("default_provider")
