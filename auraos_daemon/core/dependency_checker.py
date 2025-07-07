"""
Dependency checker for AuraOS Autonomous AI Daemon v8
Checks for required dependencies before execution and attempts to install them
"""
import subprocess
import sys
import importlib
import logging

# List of required packages for the core system
CORE_DEPENDENCIES = ["flask", "requests"]

# Dependencies for each plugin
PLUGIN_DEPENDENCIES = {
    "shell": [],
    "selenium_automation": ["selenium", "webdriver_manager"],
    "window_manager": ["pyautogui"]
}

def check_and_install_dependencies(plugin_name=None):
    """
    Check for required dependencies and install missing ones
    If plugin_name is provided, only check dependencies for that plugin
    Otherwise check all core dependencies
    """
    dependencies_to_check = []
    
    # Add core dependencies
    if plugin_name is None:
        dependencies_to_check.extend(CORE_DEPENDENCIES)
    
    # Add plugin-specific dependencies
    if plugin_name is not None and plugin_name in PLUGIN_DEPENDENCIES:
        dependencies_to_check.extend(PLUGIN_DEPENDENCIES[plugin_name])
    elif plugin_name is None:
        # Check all plugin dependencies
        for plugin_deps in PLUGIN_DEPENDENCIES.values():
            dependencies_to_check.extend(plugin_deps)
    
    # Remove duplicates
    dependencies_to_check = list(set(dependencies_to_check))
    
    missing_dependencies = []
    for dependency in dependencies_to_check:
        try:
            importlib.import_module(dependency)
            logging.debug(f"Dependency check: {dependency} is installed")
        except ImportError:
            logging.warning(f"Dependency check: {dependency} is missing")
            missing_dependencies.append(dependency)
    
    # Install missing dependencies
    if missing_dependencies:
        logging.info(f"Installing missing dependencies: {', '.join(missing_dependencies)}")
        for dependency in missing_dependencies:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", dependency], 
                               check=True, capture_output=True)
                logging.info(f"Successfully installed {dependency}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to install {dependency}: {e.stderr.decode()}")
    
    return len(missing_dependencies) == 0
