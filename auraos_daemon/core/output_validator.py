"""
Output validator for AuraOS Autonomous AI Daemon v8
Analyzes script outputs and provides feedback for improvement
"""
import logging
import json
import os
import requests
import re
from datetime import datetime

class OutputValidator:
    def __init__(self, config=None):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.validation_log = os.path.join(self.base_dir, "validation.log")
        
        # Load config for API keys
        self.config = config or {}
        self.api_key = self.config.get("GROQ_API_KEY")
        self.api_url = self.config.get("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
        self.model = self.config.get("GROQ_MODEL", "llama3-70b-8192")
        
    def validate_output(self, intent, script, output, error=None):
        """
        Validates the output of a script execution and provides feedback
        
        Args:
            intent: Original user intent
            script: The script that was executed
            output: The stdout from script execution
            error: Any error message (stderr) from execution
            
        Returns:
            dict: Validation results with feedback and improvement suggestions
        """
        # Log the validation request
        self._log_validation_request(intent, script, output, error)
        
        # Check for macOS compatibility issues
        macos_issues = self._check_macos_compatibility(script, error)
        
        # Prepare prompt for validation
        system_prompt = (
            "You are an expert system output validator for AuraOS. Your task is to analyze the output of a shell script "
            "and determine if it correctly fulfilled the user's intent. If there are issues, suggest improvements. "
            "Analyze potential issues like compatibility problems (macOS vs Linux), parsing errors, empty outputs, etc. "
            "Focus on practical solutions that work in macOS. Use standard Unix tools and avoid Linux-specific features."
        )
        
        user_prompt = (
            f"User intent: {intent}\n\n"
            f"Shell script executed:\n```bash\n{script}\n```\n\n"
        )
        
        if output and output.strip():
            user_prompt += f"Script output:\n```\n{output}\n```\n\n"
        else:
            user_prompt += "Script output: [EMPTY OR NULL]\n\n"
            
        if error:
            user_prompt += f"Error message:\n```\n{error}\n```\n\n"
            
        if macos_issues:
            user_prompt += f"Detected macOS compatibility issues:\n- " + "\n- ".join(macos_issues) + "\n\n"
            
        user_prompt += (
            "Please analyze the output and determine:\n"
            "1. Is the output valid and does it fulfill the user's intent? (yes/no)\n"
            "2. What are the specific issues with the script or output, if any?\n"
            "3. How can the script be improved to better fulfill the intent?\n"
            "4. Provide a corrected script if needed.\n"
            "Return your analysis in JSON format with these keys: valid, issues, improvements, corrected_script"
        )
        
        # Call API to validate
        validation_result = self._call_validation_api(system_prompt, user_prompt)
        
        # Parse validation result
        try:
            # Look for JSON in the response
            json_match = re.search(r'```json\s*(.*?)\s*```', validation_result, re.DOTALL)
            if json_match:
                validation_json = json.loads(json_match.group(1))
            else:
                # Try to find any JSON-like structure
                json_match = re.search(r'({.*})', validation_result, re.DOTALL)
                if json_match:
                    validation_json = json.loads(json_match.group(1))
                else:
                    # Fallback to parsing the whole response
                    validation_json = json.loads(validation_result)
        except (json.JSONDecodeError, AttributeError):
            # If we can't parse a JSON structure, create a default one
            validation_json = {
                "valid": False,
                "issues": ["Failed to parse validation response"],
                "improvements": ["The validation system encountered an error"],
                "corrected_script": None
            }
            
        # Log the validation result
        self._log_validation_result(validation_json)
        
        return validation_json
        
    def _call_validation_api(self, system_prompt, user_prompt):
        """Call the AI API to validate the output"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logging.error(f"Validation API call failed: {e}")
            return json.dumps({
                "valid": False,
                "issues": [f"Validation API call failed: {str(e)}"],
                "improvements": ["Check API connection and retry"],
                "corrected_script": None
            })
            
    def _log_validation_request(self, intent, script, output, error):
        """Log validation request details"""
        timestamp = datetime.now().isoformat()
        with open(self.validation_log, "a") as f:
            f.write(f"\n--- VALIDATION REQUEST {timestamp} ---\n")
            f.write(f"Intent: {intent}\n")
            f.write(f"Script:\n{script}\n")
            f.write(f"Output:\n{output}\n")
            if error:
                f.write(f"Error:\n{error}\n")
                
    def _log_validation_result(self, result):
        """Log validation result"""
        with open(self.validation_log, "a") as f:
            f.write(f"Validation Result:\n{json.dumps(result, indent=2)}\n")
            f.write("--- END VALIDATION ---\n")
    
    def auto_improve_script(self, intent, script, output, error=None):
        """
        Automatically improve a script based on its output
        
        Args:
            intent: Original user intent
            script: The script that was executed
            output: The stdout from script execution
            error: Any error message (stderr) from execution
            
        Returns:
            dict: Results containing improved script and explanation
        """
        validation = self.validate_output(intent, script, output, error)
        
        if validation.get("valid", False):
            # Script is valid, no improvements needed
            return {
                "improved": False,
                "script": script,
                "explanation": "The script executed successfully and produced valid output."
            }
            
        # Script needs improvement
        improved_script = validation.get("corrected_script")
        if not improved_script:
            # No corrected script provided, generate one
            improved_script = self._generate_improved_script(intent, script, validation.get("issues", []))
        
        return {
            "improved": True,
            "script": improved_script,
            "explanation": "\n".join(validation.get("improvements", ["Script improved to fix detected issues."]))
        }
        
    def _generate_improved_script(self, intent, original_script, issues):
        """Generate an improved script using the AI"""
        system_prompt = (
            "You are an expert shell script generator for macOS. Your task is to correct a shell script "
            "that had issues. Generate a corrected script that addresses the issues and works properly on macOS. "
            "Use standard Unix tools and avoid Linux-specific features. Focus on reliability and compatibility.\n"
            "1. Always ensure scripts work on macOS\n"
            "2. Do NOT use the -P flag with grep as it's not supported on macOS\n"
            "3. Instead of grep -P, use a combination of grep, sed, and awk\n"
            "4. Prefer simple, reliable approaches over complex ones\n"
            "5. Handle edge cases (empty results, unexpected formats)\n"
            "6. Prefer XMLPath/jq for XML/JSON instead of regex when possible\n"
            "7. Make output clear, structured, and user-friendly\n"
            "8. Return only the fixed script with no explanation\n"
        )
        
        user_prompt = (
            f"User intent: {intent}\n\n"
            f"Original script:\n```bash\n{original_script}\n```\n\n"
            f"Issues to fix:\n- " + "\n- ".join(issues) + "\n\n"
            "Please provide a corrected script that addresses these issues. Return only the script, with no explanation."
        )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            improved_script = response.json()["choices"][0]["message"]["content"]
            # Remove code block markers if present
            improved_script = re.sub(r'```(bash|sh)?', '', improved_script, flags=re.IGNORECASE).replace('```', '').strip()
            
            return improved_script
        except Exception as e:
            logging.error(f"Script improvement failed: {e}")
            return original_script
            
    def _check_macos_compatibility(self, script, error=None):
        """Perform quick checks for common macOS compatibility issues"""
        issues = []
        
        # Check for grep -P usage (not supported in macOS)
        if 'grep -P' in script or 'grep -oP' in script:
            issues.append("Using grep -P or -oP which is not supported in macOS")
            
        # Check for other Linux-specific commands
        if 'apt' in script or 'apt-get' in script:
            issues.append("Using apt/apt-get which is not available in macOS")
            
        # Check for readlink -f (macOS uses greadlink from coreutils)
        if 'readlink -f' in script:
            issues.append("Using readlink -f which is not supported in macOS (use greadlink from coreutils)")
            
        # Check for specific error messages
        if error:
            if 'invalid option -- P' in error:
                issues.append("Error indicates grep -P was used which is not supported in macOS")
                
            if 'command not found' in error:
                # Extract the command that wasn't found
                cmd_match = re.search(r'([a-zA-Z0-9_-]+): command not found', error)
                if cmd_match:
                    cmd = cmd_match.group(1)
                    issues.append(f"Command '{cmd}' not found in macOS")
                    
        return issues
