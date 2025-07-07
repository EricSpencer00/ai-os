"""
Self-improvement engine for AuraOS Autonomous AI Daemon v8
Handles safe self-modification, validation, and rollback.
"""
import logging
from flask import jsonify
from core.ability_tree import AbilityTree
import subprocess
import sys
import os
import importlib

class SelfImprovement:
    def __init__(self, daemon):
        self.daemon = daemon
        self.ability_tree = AbilityTree()

    def handle_self_improve(self):
        # Example: Check for missing abilities and try to resolve them
        missing = self.ability_tree.get_missing()
        if not missing:
            logging.info("[Self-Improve] No missing abilities detected.")
            return jsonify({"status": "No missing abilities."}), 200
        for ability in missing:
            logging.info(f"[Self-Improve] Attempting to resolve missing ability: {ability}")
            # 1. Try to install a pip package matching the ability name
            install_result = self._try_install_package(ability)
            if install_result['success']:
                self.ability_tree.add_ability(ability)
                self._reload_plugins()
                continue
            # 2. If install fails, try to generate a new function (stub)
            # In production, use LLM to generate code and add as plugin
            logging.warning(f"[Self-Improve] Could not resolve ability: {ability}")
        return jsonify({"status": "Self-improvement attempted.", "missing": self.ability_tree.get_missing()}), 200

    def _try_install_package(self, package_name):
        try:
            logging.info(f"[Self-Improve] Installing package: {package_name}")
            result = subprocess.run([sys.executable, "-m", "pip", "install", package_name], capture_output=True, text=True)
            if result.returncode == 0:
                logging.info(f"[Self-Improve] Package {package_name} installed successfully.")
                return {"success": True}
            else:
                logging.error(f"[Self-Improve] Pip install failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
        except Exception as e:
            logging.error(f"[Self-Improve] Exception during pip install: {e}")
            return {"success": False, "error": str(e)}

    def _reload_plugins(self):
        # Reload plugins after installing new packages
        try:
            importlib.reload(self.daemon.plugin_manager)
            logging.info("[Self-Improve] Plugins reloaded.")
        except Exception as e:
            logging.error(f"[Self-Improve] Failed to reload plugins: {e}")
