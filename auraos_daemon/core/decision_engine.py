"""
Decision engine for AuraOS Autonomous AI Daemon v8
Selects the best plugin/tool for a given task.
"""
import logging
from flask import request, jsonify

class DecisionEngine:
    def __init__(self, plugin_manager):
        self.plugin_manager = plugin_manager

    def handle_generate_script(self):
        data = request.get_json(force=True)
        intent = data.get("intent", "")
        context = data.get("context", {})
        # Example: select plugin based on intent keywords
        if any(k in intent.lower() for k in ["window", "app", "gui"]):
            plugin = self.plugin_manager.get_plugin('window_manager')
        elif any(k in intent.lower() for k in ["browser", "selenium", "web"]):
            plugin = self.plugin_manager.get_plugin('selenium_automation')
        else:
            plugin = self.plugin_manager.get_plugin('shell')
        if not plugin:
            return jsonify({"error": "No suitable plugin found."}), 500
        return plugin.generate_script(intent, context)
