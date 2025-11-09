#!/usr/bin/env python3
"""AuraOS API Key Manager - Secure key storage and rotation for AI services

Supports:
- Multiple AI providers (Groq, OpenAI, Anthropic, local Ollama)
- Encrypted key storage using Fernet symmetric encryption
- Key rotation and versioning
- Automatic fallback to local Ollama when no cloud keys available
"""
import os
import json
import base64
from pathlib import Path
from typing import Dict, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from datetime import datetime

class KeyManager:
    """Manages API keys for AI services with encryption and rotation"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize key manager
        
        Args:
            config_dir: Directory to store encrypted keys (default: ~/.auraos/keys)
        """
        self.config_dir = Path(config_dir or os.path.expanduser("~/.auraos/keys"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.keys_file = self.config_dir / "keys.enc"
        self.master_key_file = self.config_dir / "master.key"
        
        # Initialize encryption
        self.cipher = self._init_encryption()
        
        # Load existing keys
        self.keys = self._load_keys()
    
    def _init_encryption(self) -> Fernet:
        """Initialize or load encryption key"""
        if self.master_key_file.exists():
            with open(self.master_key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate new master key
            key = Fernet.generate_key()
            with open(self.master_key_file, 'wb') as f:
                f.write(key)
            # Secure the master key file
            os.chmod(self.master_key_file, 0o600)
        
        return Fernet(key)
    
    def _load_keys(self) -> Dict:
        """Load and decrypt stored keys"""
        if not self.keys_file.exists():
            return {
                "providers": {},
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
        
        try:
            with open(self.keys_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            print(f"Warning: Could not decrypt keys file: {e}")
            return {"providers": {}, "metadata": {}}
    
    def _save_keys(self):
        """Encrypt and save keys to disk"""
        self.keys["metadata"]["last_updated"] = datetime.now().isoformat()
        
        json_data = json.dumps(self.keys, indent=2)
        encrypted_data = self.cipher.encrypt(json_data.encode('utf-8'))
        
        with open(self.keys_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Secure the keys file
        os.chmod(self.keys_file, 0o600)
    
    def add_key(self, provider: str, api_key: str, metadata: Optional[Dict] = None):
        """Add or update an API key for a provider
        
        Args:
            provider: Provider name (e.g., 'groq', 'openai', 'anthropic')
            api_key: The API key to store
            metadata: Optional metadata (e.g., {'model': 'llama3-70b', 'rate_limit': 30})
        """
        if provider not in self.keys["providers"]:
            self.keys["providers"][provider] = {
                "keys": [],
                "active_key_index": 0,
                "metadata": metadata or {}
            }
        
        # Add new key with timestamp
        key_entry = {
            "key": api_key,
            "added": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.keys["providers"][provider]["keys"].append(key_entry)
        self.keys["providers"][provider]["active_key_index"] = len(
            self.keys["providers"][provider]["keys"]
        ) - 1
        
        self._save_keys()
        print(f"✓ Added API key for {provider}")
    
    def get_key(self, provider: str) -> Optional[str]:
        """Get the active API key for a provider
        
        Args:
            provider: Provider name
            
        Returns:
            API key string or None if not found
        """
        if provider not in self.keys["providers"]:
            return None
        
        provider_data = self.keys["providers"][provider]
        if not provider_data["keys"]:
            return None
        
        active_index = provider_data.get("active_key_index", 0)
        return provider_data["keys"][active_index]["key"]
    
    def rotate_key(self, provider: str, new_key: str, metadata: Optional[Dict] = None):
        """Rotate to a new API key for a provider
        
        Args:
            provider: Provider name
            new_key: New API key
            metadata: Optional metadata for the new key
        """
        self.add_key(provider, new_key, metadata)
        print(f"✓ Rotated API key for {provider}")
    
    def list_providers(self) -> List[str]:
        """List all configured providers"""
        return list(self.keys["providers"].keys())
    
    def remove_provider(self, provider: str):
        """Remove all keys for a provider
        
        Args:
            provider: Provider name to remove
        """
        if provider in self.keys["providers"]:
            del self.keys["providers"][provider]
            self._save_keys()
            print(f"✓ Removed provider: {provider}")
        else:
            print(f"Provider {provider} not found")
    
    def get_provider_info(self, provider: str) -> Optional[Dict]:
        """Get information about a provider (without exposing keys)
        
        Args:
            provider: Provider name
            
        Returns:
            Dict with provider info (number of keys, metadata, etc.)
        """
        if provider not in self.keys["providers"]:
            return None
        
        provider_data = self.keys["providers"][provider]
        return {
            "provider": provider,
            "num_keys": len(provider_data["keys"]),
            "active_key_index": provider_data.get("active_key_index", 0),
            "metadata": provider_data.get("metadata", {}),
            "keys_info": [
                {
                    "added": key["added"],
                    "metadata": key.get("metadata", {})
                }
                for key in provider_data["keys"]
            ]
        }
    
    def enable_ollama(self, base_url: str = "http://localhost:11434", 
                     model: str = "gemma:2b"):
        """Configure local Ollama as a provider
        
        Args:
            base_url: Ollama API base URL
            model: Default model to use
        """
        self.keys["providers"]["ollama"] = {
            "keys": [{"key": "local", "added": datetime.now().isoformat()}],
            "active_key_index": 0,
            "metadata": {
                "base_url": base_url,
                "model": model,
                "local": True
            }
        }
        self._save_keys()
        print(f"✓ Enabled local Ollama (model: {model})")
    
    def get_ollama_config(self) -> Optional[Dict]:
        """Get Ollama configuration if enabled"""
        if "ollama" in self.keys["providers"]:
            return self.keys["providers"]["ollama"].get("metadata", {})
        return None


def main():
    """CLI interface for key management"""
    import sys
    
    km = KeyManager()
    
    if len(sys.argv) < 2:
        print("AuraOS API Key Manager")
        print("\nUsage:")
        print("  python key_manager.py add <provider> <api_key>")
        print("  python key_manager.py get <provider>")
        print("  python key_manager.py list")
        print("  python key_manager.py info <provider>")
        print("  python key_manager.py remove <provider>")
        print("  python key_manager.py enable-ollama [model]")
        print("\nProviders: groq, openai, anthropic, ollama")
        return
    
    command = sys.argv[1]
    
    if command == "add":
        if len(sys.argv) < 4:
            print("Usage: add <provider> <api_key>")
            return
        provider = sys.argv[2]
        api_key = sys.argv[3]
        km.add_key(provider, api_key)
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: get <provider>")
            return
        provider = sys.argv[2]
        key = km.get_key(provider)
        if key:
            # Only show first/last 4 chars for security
            masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"
            print(f"{provider}: {masked}")
        else:
            print(f"No key found for {provider}")
    
    elif command == "list":
        providers = km.list_providers()
        if providers:
            print("Configured providers:")
            for p in providers:
                info = km.get_provider_info(p)
                local = " (local)" if info.get("metadata", {}).get("local") else ""
                print(f"  - {p}{local}: {info['num_keys']} key(s)")
        else:
            print("No providers configured")
    
    elif command == "info":
        if len(sys.argv) < 3:
            print("Usage: info <provider>")
            return
        provider = sys.argv[2]
        info = km.get_provider_info(provider)
        if info:
            print(json.dumps(info, indent=2))
        else:
            print(f"Provider {provider} not found")
    
    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: remove <provider>")
            return
        provider = sys.argv[2]
        km.remove_provider(provider)
    
    elif command == "enable-ollama":
        model = sys.argv[2] if len(sys.argv) > 2 else "gemma:2b"
        km.enable_ollama(model=model)
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
