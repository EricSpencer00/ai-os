"""
Shell plugin for AuraOS Autonomous AI Daemon v8
Executes shell scripts and generates shell scripts from intent.
"""
import subprocess
from flask import jsonify

class Plugin:
    name = "shell"
    def generate_script(self, intent, context):
        # Stub: In production, use LLM or rules to generate shell script
        script = f"echo 'Intent: {intent}'"
        return jsonify({"script_type": "shell", "script": script}), 200

    def execute(self, script, context):
        try:
            result = subprocess.run(script, shell=True, capture_output=True, text=True)
            return jsonify({
                "status": "success" if result.returncode == 0 else "error",
                "return_code": result.returncode,
                "output": result.stdout,
                "error_output": result.stderr
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
