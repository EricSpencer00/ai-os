"""
Security utilities for AuraOS Autonomous AI Daemon v8
Provides functions for input sanitization and security checks
"""
import re
import os
import shlex

def sanitize_command(command):
    """
    Sanitize a shell command to prevent command injection
    Returns sanitized command or None if potentially dangerous
    """
    # List of dangerous patterns
    dangerous_patterns = [
        r';\s*rm\s+-rf', # Attempts to delete files 
        r'>\s*/etc/', # Writing to system directories
        r'>\s*/usr/', # Writing to system directories
        r'>\s*/var/', # Writing to system directories
        r'>\s*/boot', # Writing to system directories
        r'>\s*/bin', # Writing to system directories
        r'>\s*/sbin', # Writing to system directories
        r'sudo\s+rm', # Privileged delete
        r'curl\s+.*\s+\|\s+sh', # Piping downloaded content to shell
        r'wget\s+.*\s+\|\s+sh', # Piping downloaded content to shell
    ]
    
    # Check for dangerous patterns
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return None
    
    # Restrict commands to user's home directory and downloads
    home_dir = os.path.expanduser('~')
    downloads_dir = os.path.join(home_dir, 'Downloads')
    
    # Ensure all file operations are restricted to home or downloads
    if any(op in command for op in ['>', '>>', 'touch', 'mkdir', 'cp', 'mv']):
        # Make sure the command operates only in allowed directories
        if not (home_dir in command or downloads_dir in command):
            # Force operations to downloads dir by modifying paths
            command = modify_paths_to_downloads(command)
    
    return command

def modify_paths_to_downloads(command):
    """
    Modify command to ensure all file operations occur in Downloads directory
    """
    # This is a simplistic implementation - in a real system you'd use
    # more robust parsing and modification of the command
    downloads_dir = os.path.expanduser('~/Downloads')
    
    # Split command into parts
    try:
        parts = shlex.split(command)
    except ValueError:
        # If shlex can't parse it, it might be malformed or have unclosed quotes
        return f"cd {downloads_dir} && {command}"
    
    # Prepend cd to downloads
    return f"cd {downloads_dir} && {command}"

def is_safe_url(url):
    """
    Check if a URL is safe to access
    """
    # Check for local network or localhost access
    if re.search(r'(localhost|127\.0\.0\.1|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|::1)', url):
        # Only allow localhost for the self-reflection API
        if 'localhost:5050' in url:
            return True
        return False
    
    # Check for valid http/https scheme
    if not url.startswith(('http://', 'https://')):
        return False
    
    # Blacklist of potentially dangerous domains
    dangerous_domains = [
        'evil.com',
        'malware.com',
        # Add more as needed
    ]
    
    # Extract domain
    domain_match = re.search(r'https?://([^/]+)', url)
    if domain_match:
        domain = domain_match.group(1)
        if any(bad_domain in domain for bad_domain in dangerous_domains):
            return False
    
    return True
