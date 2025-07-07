"""
Logging utility for AuraOS Autonomous AI Daemon v8
Provides centralized logging configuration and helper functions
"""
import logging
import os
import time
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

class AuraLogger:
    def __init__(self, config=None):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Default config values
        self.log_level = logging.INFO
        self.log_file = os.path.join(self.base_dir, "aura_os.log")
        self.max_size_mb = 10
        self.backup_count = 3
        
        # Override with config if provided
        if config and 'LOGGING' in config:
            log_config = config['LOGGING']
            level_str = log_config.get('level', 'INFO')
            self.log_level = getattr(logging, level_str)
            self.log_file = os.path.join(self.base_dir, log_config.get('file', 'aura_os.log'))
            self.max_size_mb = log_config.get('max_size_mb', 10)
            self.backup_count = log_config.get('backup_count', 3)
        
        # Set up the logger
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure the logging system"""
        # Create handler for rotating file
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_size_mb * 1024 * 1024,
            backupCount=self.backup_count
        )
        
        # Create console handler
        console_handler = logging.StreamHandler()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(module)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add formatter to handlers
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Get the root logger and configure it
        logger = logging.getLogger()
        logger.setLevel(self.log_level)
        
        # Remove existing handlers if any
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add the handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logging.info("Logging system initialized")
    
    def get_logger(self, name=None):
        """Get a logger instance with the given name"""
        return logging.getLogger(name)
    
    def log_execution(self, script, result):
        """Log script execution with detailed information"""
        logger = self.get_logger("execution")
        logger.info(f"Script executed: {script[:100]}{'...' if len(script) > 100 else ''}")
        logger.debug(f"Return code: {result.returncode}")
        
        if result.stdout:
            stdout_preview = result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout
            logger.debug(f"Output: {stdout_preview}")
        
        if result.stderr and result.returncode != 0:
            logger.warning(f"Error output: {result.stderr}")
    
    def log_api_call(self, api_name, status_code=None, error=None):
        """Log API calls with performance metrics"""
        logger = self.get_logger("api")
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "api": api_name,
            "status_code": status_code,
            "error": error
        }
        
        if error:
            logger.error(f"API call to {api_name} failed: {error}")
        else:
            logger.info(f"API call to {api_name} completed with status {status_code}")
        
        # Write to structured log for potential analysis
        structured_log_path = os.path.join(self.base_dir, "api_calls.log")
        with open(structured_log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def log_security_event(self, event_type, details, severity="WARNING"):
        """Log security-related events"""
        logger = self.get_logger("security")
        level = getattr(logging, severity, logging.WARNING)
        
        logger.log(level, f"Security event [{event_type}]: {details}")
        
        # Also write to a dedicated security log
        security_log_path = os.path.join(self.base_dir, "security_events.log")
        with open(security_log_path, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"{timestamp} - {severity} - {event_type} - {details}\n")

# Global logger instance
aura_logger = None

def init_logger(config=None):
    """Initialize the global logger instance"""
    global aura_logger
    aura_logger = AuraLogger(config)
    return aura_logger

def get_logger():
    """Get the global logger instance, initializing if needed"""
    global aura_logger
    if aura_logger is None:
        aura_logger = AuraLogger()
    return aura_logger
