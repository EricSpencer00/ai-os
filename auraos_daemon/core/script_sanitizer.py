"""
Script sanitizer for AuraOS Autonomous AI Daemon v8
Pre-checks scripts for common compatibility issues before execution
"""
import re
import os
import logging
import json
from core.output_validator import OutputValidator

class ScriptSanitizer:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_validator = OutputValidator(config)
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.commands_dir = os.path.join(self.base_dir, "commands")
        
    def sanitize(self, script, intent):
        """
        Pre-process and sanitize scripts before execution
        
        Args:
            script: The script to sanitize
            intent: The original user intent
            
        Returns:
            dict: Sanitization results with the sanitized script
        """
        # Check for common issues
        issues = self._check_compatibility_issues(script)
        
        # If we found issues, try to fix them
        if issues:
            logging.warning(f"Script has compatibility issues: {', '.join(issues)}")
            
            # First, check if we have a pre-built command for this intent
            prebuilt_script = self._find_prebuilt_command(intent)
            if prebuilt_script:
                logging.info(f"Using prebuilt command for intent: {intent[:50]}...")
                return {
                    "sanitized": True,
                    "script": prebuilt_script,
                    "issues": issues,
                    "source": "prebuilt"
                }
            
            # Otherwise, fix the script using the output validator
            fixed_script = self._fix_script(script, issues, intent)
            if fixed_script and fixed_script != script:
                return {
                    "sanitized": True,
                    "script": fixed_script,
                    "issues": issues,
                    "source": "auto-fixed"
                }
        
        # Return the original script if no issues or couldn't fix
        return {
            "sanitized": False,
            "script": script,
            "issues": issues,
            "source": "original"
        }
    
    def _check_compatibility_issues(self, script):
        """Check for common compatibility issues in scripts"""
        issues = []
        
        # Check for grep -P usage (not supported in macOS)
        if re.search(r'grep\s+-[a-zA-Z]*P', script):
            issues.append("grep -P not supported in macOS")
        
        # Check for other Linux-specific commands
        if re.search(r'\b(apt|apt-get|yum|dnf)\b', script):
            issues.append("Linux package manager used")
            
        # Check for systemd commands
        if re.search(r'\b(systemctl|journalctl)\b', script):
            issues.append("systemd commands not available in macOS")
            
        # Check for readlink -f
        if 'readlink -f' in script:
            issues.append("readlink -f not supported in macOS")
            
        # Check for other GNU-specific tools/options
        if re.search(r'\bfind\s+.*\s+-printf\b', script):
            issues.append("find -printf not supported in macOS")
            
        # Check for script portability issues
        if '/proc/' in script:
            issues.append("/proc filesystem not available in macOS")
        
        # Check for bash-specific features if using sh
        if script.startswith('#!/bin/sh') and '[[' in script:
            issues.append("Using bash-specific syntax with sh shebang")
            
        return issues
    
    def _find_prebuilt_command(self, intent):
        """Look for a prebuilt command matching the intent"""
        intent_lower = intent.lower()
        
        # Map of keywords to prebuilt commands
        intent_map = {
            "president": "web/get_president.sh",
            "us president": "web/get_president.sh",
            "current president": "web/get_president.sh",
            "who is president": "web/get_president.sh",
        }
        
        # Check if any keywords match
        for keyword, command_path in intent_map.items():
            if keyword in intent_lower:
                full_path = os.path.join(self.commands_dir, command_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r') as f:
                        return f.read()
        
        return None
    
    def _fix_script(self, script, issues, intent):
        """Attempt to fix script issues automatically"""
        # Use the output validator to generate an improved script
        fake_error = "; ".join(issues)
        improvement = self.output_validator.auto_improve_script(intent, script, "", fake_error)
        
        if improvement and improvement.get('improved', False):
            return improvement.get('script', script)
            
        # Basic fixes for common issues if the validator couldn't help
        fixed_script = script
        
        # Replace grep -P with alternatives
        if 'grep -P not supported' in fake_error:
            # Replace grep -P with grep -E where possible
            fixed_script = re.sub(r'grep\s+-([a-zA-Z]*)P', r'grep -\1E', fixed_script)
            
            # More complex Perl regex might need sed or awk
            if 'grep -oP' in script:
                logging.warning("Script uses grep -oP which needs manual fixing")
        
        return fixed_script
