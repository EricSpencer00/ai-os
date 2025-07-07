"""
Plugin manager for AuraOS Autonomous AI Daemon v8
Discovers, loads, and manages plugins/tools.
"""
import importlib
import os
import logging
from flask import request, jsonify

class PluginManager:
    def __init__(self, config):
        self.config = config
        self.plugins = {}
        self.plugins_dir = os.path.join(os.path.dirname(__file__), '..', 'plugins')
        self._discover_plugins()

    def _discover_plugins(self):
        for fname in os.listdir(self.plugins_dir):
            if fname.endswith('.py') and fname != '__init__.py':
                plugin_name = fname[:-3]
                try:
                    module = importlib.import_module(f'plugins.{plugin_name}')
                    if hasattr(module, 'Plugin'):
                        self.plugins[plugin_name] = module.Plugin()
                        logging.info(f"Loaded plugin: {plugin_name}")
                except Exception as e:
                    logging.error(f"Failed to load plugin {plugin_name}: {e}")

    def get_plugin(self, name):
        return self.plugins.get(name)

    def handle_execute_script(self):
        data = request.get_json(force=True)
        script = data.get("script")
        context = data.get("context", {})
        # Use a plugin (e.g., shell or python) to execute the script
        plugin = self.get_plugin('shell')
        if not plugin:
            return jsonify({"error": "Shell plugin not found."}), 500
        return plugin.execute(script, context)
