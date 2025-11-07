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
        
        # Log the intent
        logging.info(f"Processing intent: {intent[:100]}{'...' if len(intent) > 100 else ''}")
        
        # Enhanced plugin routing with priority order
        intent_lower = intent.lower()
        
        # VM-related intents (highest priority for isolation)
        if any(k in intent_lower for k in [
            "vm", "virtual machine", "create vm", "start vm", "stop vm",
            "execute in vm", "run in vm", "qemu"
        ]):
            plugin = self.plugin_manager.get_plugin('vm_manager')
            if plugin:
                logging.info("Routing to vm_manager plugin")
                return plugin.generate_script(intent, context)
        
        # Browser automation intents
        if any(k in intent_lower for k in [
            "browser", "selenium", "web", "navigate", "open website",
            "click on", "screenshot", "download from", "search google",
            "fill form", "submit", "scrape"
        ]):
            plugin = self.plugin_manager.get_plugin('selenium_automation')
            if plugin:
                logging.info("Routing to selenium_automation plugin")
                return plugin.generate_script(intent, context)
        
        # Window/app management intents
        if any(k in intent_lower for k in [
            "window", "app", "application", "gui", "launch", "open app",
            "close app", "activate", "focus", "move window", "resize window",
            "click at", "type into", "list apps"
        ]):
            plugin = self.plugin_manager.get_plugin('window_manager')
            if plugin:
                logging.info("Routing to window_manager plugin")
                return plugin.generate_script(intent, context)
        
        # Default to shell plugin for everything else
        plugin = self.plugin_manager.get_plugin('shell')
        if not plugin:
            logging.error("Shell plugin not found")
            return jsonify({"error": "No suitable plugin found."}), 500
        
        logging.info("Routing to shell plugin (default)")
        return plugin.generate_script(intent, context)

