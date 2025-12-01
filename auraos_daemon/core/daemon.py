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
from core.dependency_checker import check_and_install_dependencies
from core.logger import init_logger
from core.output_validator import OutputValidator
from core import llm_router

class AuraOSDaemon:
    def __init__(self):
        self.config = load_config()
        
        # Initialize logger first
        self.logger = init_logger(self.config)
        
        # Check for dependencies before initializing
        check_and_install_dependencies()
        
        self.app = Flask(__name__)
        self.plugin_manager = PluginManager(self.config)
        self.decision_engine = DecisionEngine(self.plugin_manager)
        # Initialize a shared LLM router and expose it via the daemon for plugins
        try:
            self.llm_router = llm_router.get_router()
            logging.info(f"LLM Router initialized: {self.llm_router is not None}")
        except Exception as e:
            logging.warning(f"Could not initialize LLM Router: {e}")

        self.self_improvement = SelfImprovement(self)
        self.ability_tree = self.self_improvement.ability_tree
        self.output_validator = OutputValidator(self.config)
        self._setup_routes()
        
        logging.info("AuraOS Daemon initialized successfully")

    def _setup_routes(self):
        @self.app.route("/generate_script", methods=["POST"])
        def generate_script():
            # Use decision engine to select plugin/tool and generate script
            logging.info("Received request to generate script")
            return self.decision_engine.handle_generate_script()

        @self.app.route("/execute_script", methods=["POST"])
        def execute_script():
            # Use plugin manager to safely execute script
            logging.info("Received request to execute script")
            return self.plugin_manager.handle_execute_script()

        @self.app.route("/self_improve", methods=["POST"])
        def self_improve():
            # Trigger self-improvement
            logging.info("Received request to self-improve")
            return self.self_improvement.handle_self_improve()

        @self.app.route("/report_missing_ability", methods=["POST"])
        def report_missing_ability():
            data = request.get_json(force=True)
            ability = data.get("ability")
            if not ability:
                logging.warning("Received report_missing_ability request with no ability specified")
                return jsonify({"error": "No ability specified."}), 400
            logging.info(f"Reporting missing ability: {ability}")
            self.ability_tree.report_missing(ability)
            return jsonify({"status": f"Reported missing ability: {ability}"}), 200
            
        @self.app.route("/self_reflect", methods=["POST"])
        def self_reflect():
            logging.info("Triggered self-reflection")
            # This endpoint can be expanded with more complex self-reflection logic
            return self.self_improvement.handle_self_improve()
            
        @self.app.route("/validate_output", methods=["POST"])
        def validate_output():
            """Validate script output and suggest improvements"""
            data = request.get_json(force=True)
            intent = data.get("intent", "")
            script = data.get("script", "")
            output = data.get("output", "")
            error = data.get("error", "")
            
            logging.info(f"Validating output for intent: {intent[:50]}...")
            
            validation = self.output_validator.validate_output(intent, script, output, error)
            return jsonify(validation), 200

        @self.app.route("/health", methods=["GET"]) 
        def health():
            """Return health status including LLM router status and plugin summary."""
            status = {
                "service": "auraos-daemon",
                "status": "ok",
            }
            try:
                if hasattr(self, 'llm_router') and self.llm_router:
                    status['llm'] = self.llm_router.get_status()
                else:
                    status['llm'] = {"available": False}
            except Exception as e:
                status['llm_error'] = str(e)

            try:
                status['plugins'] = list(self.plugin_manager.plugins.keys())
            except Exception:
                status['plugins'] = []

            return jsonify(status), 200
            
        @self.app.route("/improve_script", methods=["POST"])
        def improve_script():
            """Automatically improve a script based on its output"""
            data = request.get_json(force=True)
            intent = data.get("intent", "")
            script = data.get("script", "")
            output = data.get("output", "")
            error = data.get("error", "")
            
            logging.info(f"Improving script for intent: {intent[:50]}...")
            
            improvement = self.output_validator.auto_improve_script(intent, script, output, error)
            return jsonify(improvement), 200

    def run(self):
        logging.info("Starting AuraOS AI Daemon v8...")
        self.app.run(host="0.0.0.0", port=5050)
