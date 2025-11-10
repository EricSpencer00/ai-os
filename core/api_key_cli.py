"""Simple CLI to onboard AI API keys for AuraOS.

Prompts the user for provider and key (masked). Stores using `core.key_store`.
Designed to be run interactively (e.g., from setup or by the user).
"""
import sys
import getpass
from . import key_store


def choose_provider_prompt() -> str:
    choices = ["openrouter", "openai", "huggingface", "other"]
    print("Select AI provider:")
    for i, c in enumerate(choices, start=1):
        print(f"  {i}) {c}")

    while True:
        sel = input("Enter number (1-4): ").strip()
        if not sel:
            continue
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except Exception:
            pass
        print("Invalid selection. Try again.")


def run_onboarding():
    print("AI Provider Onboarding - store API key for system use")
    provider = choose_provider_prompt()
    print(f"Enter API key for provider '{provider}'. This will be stored locally with restricted permissions.")
    key = getpass.getpass("API Key: ")
    if not key:
        print("No key entered, aborting.")
        return 1
    key_store.set_key(provider, key)
    print(f"Saved key for provider '{provider}'.")

    set_default = input("Set this provider as the default for AI calls? (y/N): ").strip().lower()
    if set_default in ("y", "yes"):
        key_store.set_default_provider(provider)
        print(f"Provider '{provider}' set as default.")

    print("Onboarding complete.")
    return 0


if __name__ == '__main__':
    sys.exit(run_onboarding())
