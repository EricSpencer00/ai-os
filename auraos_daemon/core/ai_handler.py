"""
Enhanced AI Task Handler
Integrates with daemon, screen capture context, and removes confirmation barriers.
"""
import logging
import subprocess
import json
import requests
import os
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from core.screen_context import ScreenCaptureManager, ScreenContextDB

logger = logging.getLogger(__name__)


class EnhancedAIHandler:
    """Handles AI task generation, execution, and result reporting"""
    
    def __init__(self, daemon_config: Dict, daemon_host: str = "localhost", daemon_port: int = 5000):
        self.config = daemon_config
        self.daemon_host = daemon_host
        self.daemon_port = daemon_port
        self.base_url = f"http://{daemon_host}:{daemon_port}"
        self.screen_manager = ScreenCaptureManager()
        self.execution_log = []
    
    def process_ai_request(self, user_input: str, auto_execute: bool = True) -> Dict:
        """
        Process user request through full AI pipeline without confirmation
        
        Flow:
        1. Capture current screen context
        2. Parse user intent with daemon
        3. Generate script via decision engine
        4. Validate output
        5. Auto-execute (no confirmation) if safe
        6. Report results
        """
        logger.info(f"Processing AI request: {user_input[:100]}")
        
        result = {
            'status': 'processing',
            'user_input': user_input,
            'timestamp': datetime.now().isoformat(),
            'steps': []
        }
        
        # Step 1: Capture screen context
        try:
            screen_context = self._capture_context("AI task initiated")
            result['steps'].append({
                'name': 'Screen Capture',
                'status': 'success',
                'context_summary': f"Captured {len(screen_context['screenshots'])} recent screenshots"
            })
        except Exception as e:
            logger.error(f"Failed to capture screen context: {e}")
            screen_context = {}
            result['steps'].append({
                'name': 'Screen Capture',
                'status': 'warning',
                'error': str(e)
            })
        
        # Step 2: Generate script from user input
        try:
            script_response = self._generate_script(user_input, screen_context)
            generated_script = script_response.get('script', '')
            reasoning = script_response.get('reasoning', '')
            
            result['steps'].append({
                'name': 'Script Generation',
                'status': 'success',
                'script_preview': generated_script[:200] if generated_script else 'No script generated'
            })
            result['generated_script'] = generated_script
            result['reasoning'] = reasoning
        except Exception as e:
            logger.error(f"Failed to generate script: {e}")
            result['steps'].append({
                'name': 'Script Generation',
                'status': 'error',
                'error': str(e)
            })
            result['status'] = 'failed'
            return result
        
        # Step 3: Validate script safety
        try:
            validation = self._validate_script(generated_script, user_input)
            is_safe = validation.get('is_safe', False)
            safety_notes = validation.get('notes', [])
            
            result['steps'].append({
                'name': 'Safety Validation',
                'status': 'success',
                'is_safe': is_safe,
                'safety_notes': safety_notes
            })
            
            if not is_safe:
                logger.warning(f"Script failed safety validation: {safety_notes}")
                result['status'] = 'blocked'
                result['reason'] = 'Script did not pass safety validation'
                return result
        except Exception as e:
            logger.error(f"Failed to validate script: {e}")
            result['steps'].append({
                'name': 'Safety Validation',
                'status': 'error',
                'error': str(e)
            })
            result['status'] = 'failed'
            return result
        
        # Step 4: Execute script (no confirmation needed)
        if auto_execute and is_safe:
            try:
                execution_result = self._execute_script(generated_script)
                
                result['steps'].append({
                    'name': 'Script Execution',
                    'status': 'success' if execution_result['exit_code'] == 0 else 'error',
                    'exit_code': execution_result['exit_code'],
                    'output_lines': len(execution_result['stdout'].split('\n'))
                })
                
                result['execution'] = {
                    'exit_code': execution_result['exit_code'],
                    'stdout': execution_result['stdout'],
                    'stderr': execution_result['stderr'],
                    'duration_seconds': execution_result['duration']
                }
                
                # Step 5: Post-execution validation
                try:
                    post_validation = self._validate_output(
                        user_input,
                        generated_script,
                        execution_result['stdout'],
                        execution_result['stderr']
                    )
                    
                    result['steps'].append({
                        'name': 'Post-Execution Validation',
                        'status': 'success',
                        'output_valid': post_validation.get('is_valid', False),
                        'suggestions': post_validation.get('suggestions', [])
                    })
                except Exception as e:
                    logger.error(f"Post-execution validation failed: {e}")
                    result['steps'].append({
                        'name': 'Post-Execution Validation',
                        'status': 'warning',
                        'error': str(e)
                    })
                
                result['status'] = 'completed'
            except Exception as e:
                logger.error(f"Script execution failed: {e}")
                result['steps'].append({
                    'name': 'Script Execution',
                    'status': 'error',
                    'error': str(e)
                })
                result['status'] = 'failed'
        else:
            result['status'] = 'pending_approval' if not auto_execute else 'blocked_safety'
        
        return result
    
    def _capture_context(self, description: str = "") -> Dict:
        """Capture current screen context"""
        self.screen_manager.capture_screenshot(description)
        context = self.screen_manager.get_context_for_ai(minutes=5)
        return context
    
    def _generate_script(self, intent: str, screen_context: Dict = None) -> Dict:
        """Call daemon to generate script"""
        payload = {
            'intent': intent,
            'context': screen_context or {}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/generate_script",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to daemon at {self.base_url}")
            # Fallback to simple heuristic
            return self._fallback_plan(intent)
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            raise
    
    def _validate_script(self, script: str, intent: str) -> Dict:
        """Validate script safety"""
        # Basic safety checks
        dangerous_patterns = [
            'rm -rf /',
            'dd if=/dev/zero',
            'mkfs',
            ':(){:|:&};:',  # Fork bomb
            'chmod 000 /',
        ]
        
        notes = []
        is_safe = True
        
        for pattern in dangerous_patterns:
            if pattern in script:
                is_safe = False
                notes.append(f"Dangerous pattern detected: {pattern}")
        
        # Check for common risky operations without safeguards
        if 'sudo' in script and '--preserve-env' in script:
            notes.append("Sudo with --preserve-env detected (potential privilege escalation)")
        
        if 'eval' in script or '$((' in script:
            notes.append("Dynamic code execution detected (eval/arithmetic expansion)")
        
        return {
            'is_safe': is_safe,
            'notes': notes
        }
    
    def _execute_script(self, script: str) -> Dict:
        """Execute script and capture output"""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                script,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5-minute timeout
                cwd=os.path.expanduser('~')
            )
            
            duration = time.time() - start_time
            
            return {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': duration
            }
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                'exit_code': 124,
                'stdout': '',
                'stderr': 'Command execution timed out after 5 minutes',
                'duration': duration
            }
        except Exception as e:
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': time.time() - start_time
            }
    
    def _validate_output(self, intent: str, script: str, stdout: str, stderr: str) -> Dict:
        """Post-execution validation via daemon"""
        payload = {
            'intent': intent,
            'script': script,
            'output': stdout,
            'error': stderr
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/validate_output",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Output validation failed: {e}")
            return {
                'is_valid': stderr == '',
                'suggestions': []
            }
    
    def _fallback_plan(self, text: str) -> Dict:
        """Fallback heuristic if daemon is unavailable"""
        text_l = text.lower()
        script = ""
        reasoning = ""
        
        if 'install' in text_l and ('pip' in text_l or 'python' in text_l):
            script = 'pip install -r requirements.txt'
            reasoning = 'Detected pip installation request, will install from requirements.txt'
        elif 'install' in text_l:
            # Extract package name
            parts = text.split()
            pkg = None
            for p in reversed(parts):
                if p.isalpha() and len(p) > 2:
                    pkg = p
                    break
            if pkg:
                script = f'apt-get update && apt-get install -y {pkg}'
                reasoning = f'Detected package installation, will apt-install {pkg}'
        elif 'restart' in text_l and 'service' in text_l:
            script = 'systemctl restart auraos'
            reasoning = 'Detected service restart request'
        else:
            script = f'echo "Task recognized but not actionable without daemon: {text}"'
            reasoning = 'No pattern match; would require daemon for proper handling'
        
        return {
            'script': script,
            'reasoning': reasoning
        }
    
    def get_execution_summary(self) -> Dict:
        """Get summary of all executions in this session"""
        return {
            'total_requests': len(self.execution_log),
            'successful': sum(1 for e in self.execution_log if e.get('status') == 'completed'),
            'failed': sum(1 for e in self.execution_log if e.get('status') == 'failed'),
            'blocked': sum(1 for e in self.execution_log if e.get('status') == 'blocked'),
            'executions': self.execution_log
        }
    
    def close(self):
        """Clean up resources"""
        self.screen_manager.close()
