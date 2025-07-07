"""
Memory module for AuraOS Autonomous AI Daemon v8
Provides storage for previous commands and results to improve context
"""
import json
import os
import time
from collections import deque

class Memory:
    def __init__(self, max_items=50):
        self.max_items = max_items
        self.command_history = deque(maxlen=max_items)
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.memory_file = os.path.join(self.base_dir, "command_memory.json")
        self._load_memory()
    
    def _load_memory(self):
        """Load memory from file if it exists"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.command_history = deque(data['command_history'], maxlen=self.max_items)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading memory: {e}")
                # Initialize with empty memory if file is corrupted
                self.command_history = deque(maxlen=self.max_items)
    
    def _save_memory(self):
        """Save memory to file"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump({
                    'command_history': list(self.command_history)
                }, f)
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def add_command(self, intent, script, result=None, error=None):
        """
        Add a command to memory
        
        Args:
            intent: User's original intent
            script: Generated script
            result: Output of the script (optional)
            error: Error from execution (optional)
        """
        entry = {
            'timestamp': time.time(),
            'intent': intent,
            'script': script,
            'result': result,
            'error': error
        }
        self.command_history.append(entry)
        self._save_memory()
    
    def get_recent_commands(self, count=5):
        """Get the most recent commands"""
        return list(self.command_history)[-count:]
    
    def get_similar_commands(self, intent, count=3):
        """Find similar previous commands based on intent"""
        # Very basic similarity - just check for common words
        intent_words = set(intent.lower().split())
        similar_commands = []
        
        for entry in reversed(self.command_history):
            entry_words = set(entry['intent'].lower().split())
            # Calculate Jaccard similarity
            if len(intent_words) > 0 and len(entry_words) > 0:
                similarity = len(intent_words.intersection(entry_words)) / len(intent_words.union(entry_words))
                if similarity > 0.3:  # Threshold for similarity
                    similar_commands.append(entry)
                    if len(similar_commands) >= count:
                        break
        
        return similar_commands
    
    def get_context_for_intent(self, intent):
        """Generate context from memory for a new intent"""
        similar_commands = self.get_similar_commands(intent)
        context = ""
        
        if similar_commands:
            context += "Previous similar commands:\n"
            for cmd in similar_commands:
                context += f"- User asked: '{cmd['intent']}'\n"
                context += f"  Script: {cmd['script']}\n"
                if cmd.get('error'):
                    context += f"  Error: {cmd['error']}\n"
                if cmd.get('result'):
                    result_preview = cmd['result'][:100] + "..." if len(cmd['result']) > 100 else cmd['result']
                    context += f"  Result: {result_preview}\n"
        
        return context
