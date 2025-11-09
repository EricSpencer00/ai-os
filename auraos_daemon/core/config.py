"""
Config loader for AuraOS Autonomous AI Daemon v8
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any


class AuraConfig:
    """Configuration manager for AuraOS"""
    
    def __init__(self, config_path: str = None):
        """Initialize config manager
        
        Args:
            config_path: Optional path to config.json
        """
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    return json.load(f)
            else:
                logging.warning(f"Config file not found: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "llm_provider": "groq",
            "fallback_llm": "ollama",
            "model": "mixtral-8x7b-32768",
            "log_level": "INFO"
        }
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value"""
        self.config[key] = value
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")


def load_config():
    """Legacy function for backward compatibility"""
    config = AuraConfig()
    return config.config
