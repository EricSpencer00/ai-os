"""
Intent mapper for special commands in AuraOS
Maps specific intents directly to pre-built commands
"""
import os
import re
import logging

class IntentMapper:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.commands_dir = os.path.join(self.base_dir, "commands")
        self.mappings = self._load_mappings()
        
    def _load_mappings(self):
        """Load the intent to command mappings"""
        return {
            # Web-related intents
            
            # System-related intents
            r"(?i).*\b(system|cpu|memory|disk)\s+.*\b(info|information|status|usage)\b.*": "system/info.sh",
            
            # File-related intents
            r"(?i).*\b(list|find|search)\s+.*\b(files|folders|directories)\b.*": "file/list.sh",
        }
        
    def get_command_for_intent(self, intent):
        """
        Find a pre-built command that matches the given intent
        
        Args:
            intent: The user's natural language intent
            
        Returns:
            str: Path to the command script if found, None otherwise
        """
        for pattern, command_path in self.mappings.items():
            if re.match(pattern, intent):
                full_path = os.path.join(self.commands_dir, command_path)
                if os.path.exists(full_path):
                    logging.info(f"Found pre-built command for intent: {intent[:50]}...")
                    with open(full_path, 'r') as f:
                        return f.read()
                else:
                    logging.warning(f"Mapped command not found: {full_path}")
        
        return None
