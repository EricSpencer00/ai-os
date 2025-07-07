"""
Core daemon logic for AuraOS Autonomous AI Daemon v8
"""
import logging
from flask import Flask, request, jsonify
from core.plugin_manager import PluginManager
from core.decision_engine import DecisionEngine
from core.self_improvement import SelfImprovement
from core.config import load_config
from core.ability_tree import AbilityTree

class AuraOSDaemon:
    def __init__(self):
        self.config = load_config()
        self.app = Flask(__name__)
        self.plugin_manager = PluginManager(self.config)
        self.decision_engine = DecisionEngine(self.plugin_manager)
        self.self_improvement = SelfImprovement(self)
        self.ability_tree = self.self_improvement.ability_tree
        self._setup_routes()
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def _setup_routes(self):
        @self.app.route("/generate_script", methods=["POST"])
        def generate_script():
            # Use decision engine to select plugin/tool and generate script
            return self.decision_engine.handle_generate_script()

        @self.app.route("/execute_script", methods=["POST"])
        def execute_script():
            # Use plugin manager to safely execute script
            return self.plugin_manager.handle_execute_script()

        @self.app.route("/self_improve", methods=["POST"])
        def self_improve():
            # Trigger self-improvement
            return self.self_improvement.handle_self_improve()

        @self.app.route("/report_missing_ability", methods=["POST"])
        def report_missing_ability():
            data = request.get_json(force=True)
            ability = data.get("ability")
            if not ability:
                return jsonify({"error": "No ability specified."}), 400
            self.ability_tree.report_missing(ability)
            return jsonify({"status": f"Reported missing ability: {ability}"}), 200

    def run(self):
        logging.info("Starting AuraOS AI Daemon v8...")
        self.app.run(host="0.0.0.0", port=5050)
