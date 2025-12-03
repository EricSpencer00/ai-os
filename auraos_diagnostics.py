#!/usr/bin/env python3
"""
AuraOS Vision & Automation Diagnostic Tool
Tests the entire AI automation pipeline from screenshot to action execution.
"""

import os
import sys
import json
import base64
import subprocess
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class AuraOSDiagnostics:
    def __init__(self):
        self.vm_name = "auraos-multipass"
        self.host_ip = "192.168.2.1"
        self.vm_ip = "192.168.2.47"
        self.inference_port = 8081
        self.gui_agent_port = 8765
        
    def run_vm_cmd(self, cmd):
        """Run command inside VM"""
        try:
            result = subprocess.run(
                f'multipass exec {self.vm_name} -- bash -c "{cmd}"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "Timeout", 1
        except Exception as e:
            return "", str(e), 1
    
    def test_inference_server(self):
        """Test inference server connectivity"""
        log.info("=" * 60)
        log.info("TEST 1: Inference Server Connectivity")
        log.info("=" * 60)
        
        # Test from host
        result = subprocess.run(
            f'curl -s http://localhost:{self.inference_port}/health',
            shell=True, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            log.info(f"[OK] Inference server accessible from HOST: {result.stdout}")
        else:
            log.error(f"[X] Cannot reach inference server from host")
            return False
        
        # Test from VM
        stdout, stderr, rc = self.run_vm_cmd(f'curl -s http://{self.host_ip}:{self.inference_port}/health')
        if rc == 0:
            log.info(f"[OK] Inference server accessible from VM at {self.host_ip}:{self.inference_port}")
            log.info(f"  Backend: {stdout}")
        else:
            log.error(f"[X] Cannot reach inference server from VM: {stderr}")
            return False
        
        return True
    
    def test_gui_agent(self):
        """Test GUI Agent connectivity"""
        log.info("")
        log.info("=" * 60)
        log.info("TEST 2: GUI Agent Connectivity")
        log.info("=" * 60)
        
        result = subprocess.run(
            f'curl -s http://{self.vm_ip}:{self.gui_agent_port}/health',
            shell=True, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            log.info(f"[OK] GUI Agent accessible: {result.stdout}")
            return True
        else:
            log.error(f"[X] Cannot reach GUI Agent: {result.stderr}")
            return False
    
    def test_vision_with_image(self):
        """Test vision endpoint with actual screenshot"""
        log.info("")
        log.info("=" * 60)
        log.info("TEST 3: Vision Model with Screenshot")
        log.info("=" * 60)
        
        # Get latest screenshot
        stdout, stderr, rc = self.run_vm_cmd('ls -t /tmp/auraos_screenshots/ | head -1')
        if rc != 0:
            log.error("No screenshots found")
            return False
        
        screenshot_file = stdout
        log.info(f"Using screenshot: {screenshot_file}")
        
        # Get base64 encoded image
        stdout, stderr, rc = self.run_vm_cmd(f'base64 < /tmp/auraos_screenshots/{screenshot_file}')
        if rc != 0 or not stdout:
            log.error(f"Failed to read screenshot: {stderr}")
            return False
        
        image_b64 = stdout[:5000]  # Use first 5000 chars to keep payload manageable
        log.info(f"Image encoded: {len(stdout)} bytes total, using {len(image_b64)} bytes")
        
        # Test inference server /ask endpoint
        payload = {
            "query": "Describe what you see on the desktop in one sentence.",
            "images": [image_b64] if image_b64 else [],
            "parse_json": False
        }
        
        try:
            result = subprocess.run(
                [
                    'curl', '-s', '-X', 'POST',
                    f'http://{self.host_ip}:{self.inference_port}/ask',
                    '-H', 'Content-Type: application/json',
                    '-d', json.dumps(payload)
                ],
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                log.info(f"[OK] Inference server responded")
                log.info(f"  Response: {response.get('response', '')[:200]}...")
                return True
            else:
                log.error(f"[X] Inference server error: {result.stderr}")
                return False
        except Exception as e:
            log.error(f"[X] Exception: {e}")
            return False
    
    def test_action_generation(self):
        """Test vision model can generate action JSON"""
        log.info("")
        log.info("=" * 60)
        log.info("TEST 4: Action Generation (JSON Output)")
        log.info("=" * 60)
        
        # Get latest screenshot  
        stdout, stderr, rc = self.run_vm_cmd('ls -t /tmp/auraos_screenshots/ | head -1')
        if rc != 0:
            log.error("No screenshots found")
            return False
        
        screenshot_file = stdout
        
        # Get base64
        stdout, stderr, rc = self.run_vm_cmd(f'base64 < /tmp/auraos_screenshots/{screenshot_file}')
        if rc != 0 or not stdout:
            log.error(f"Failed to read screenshot")
            return False
        
        image_b64 = stdout[:5000]
        
        # Send action generation request
        prompt = """You are an AI controlling a computer. Based on the screenshot, output a JSON list of actions.
Supported actions:
- {"action": "click", "x": 100, "y": 200}
- {"action": "type", "text": "hello"}
Output ONLY valid JSON list. Example: [{"action": "click", "x": 100, "y": 200}]"""
        
        payload = {
            "query": prompt,
            "images": [image_b64] if image_b64 else [],
            "parse_json": True
        }
        
        try:
            result = subprocess.run(
                [
                    'curl', '-s', '-X', 'POST',
                    f'http://{self.host_ip}:{self.inference_port}/ask',
                    '-H', 'Content-Type: application/json',
                    '-d', json.dumps(payload)
                ],
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                log.info(f"[OK] Server responded")
                
                # Check if actions are present and valid
                if "actions" in response:
                    actions = response["actions"]
                    log.info(f"  Actions returned: {actions}")
                    if isinstance(actions, list) and len(actions) > 0:
                        log.info(f"[OK] Valid action JSON generated!")
                        return True
                    else:
                        log.warning(f"  Actions is empty or not a list")
                else:
                    log.warning(f"  No 'actions' field in response")
                    log.info(f"  Response: {response}")
                
                return False
            else:
                log.error(f"[X] Server error: {result.stderr}")
                return False
        except Exception as e:
            log.error(f"[X] Exception: {e}")
            return False
    
    def test_gui_agent_ask(self):
        """Test GUI Agent /ask endpoint"""
        log.info("")
        log.info("=" * 60)
        log.info("TEST 5: GUI Agent /ask Endpoint")
        log.info("=" * 60)
        
        # Get latest screenshot
        stdout, stderr, rc = self.run_vm_cmd('ls -t /tmp/auraos_screenshots/ | head -1')
        if rc != 0:
            log.error("No screenshots found")
            return False
        
        screenshot_file = stdout
        stdout, stderr, rc = self.run_vm_cmd(f'base64 < /tmp/auraos_screenshots/{screenshot_file}')
        if rc != 0 or not stdout:
            log.error("Failed to read screenshot")
            return False
        
        image_b64 = stdout[:5000]
        
        # Send to GUI Agent
        payload = {
            "query": "Take a screenshot and describe it",
            "recent_screens": [image_b64],
            "num_screens": 1
        }
        
        try:
            result = subprocess.run(
                [
                    'curl', '-s', '-X', 'POST',
                    f'http://{self.vm_ip}:{self.gui_agent_port}/ask',
                    '-H', 'Content-Type: application/json',
                    '-d', json.dumps(payload)
                ],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                log.info(f"[OK] GUI Agent responded")
                if "executed" in response and response.get("status") == "success":
                    log.info(f"  Executed actions: {response.get('executed', [])}")
                    return True
                else:
                    log.warning(f"  Response: {response}")
                    return False
            else:
                log.error(f"[X] GUI Agent error: {result.stderr}")
                return False
        except Exception as e:
            log.error(f"[X] Exception: {e}")
            return False
    
    def run_all_tests(self):
        """Run all diagnostic tests"""
        log.info("\n")
        log.info("╔" + "=" * 58 + "╗")
        log.info("║" + " " * 58 + "║")
        log.info("║" + "AURAOS VISION & AUTOMATION DIAGNOSTICS".center(58) + "║")
        log.info("║" + " " * 58 + "║")
        log.info("╚" + "=" * 58 + "╝")
        
        tests = [
            ("Inference Server", self.test_inference_server),
            ("GUI Agent", self.test_gui_agent),
            ("Vision with Image", self.test_vision_with_image),
            ("Action Generation", self.test_action_generation),
            ("GUI Agent /ask", self.test_gui_agent_ask),
        ]
        
        results = {}
        for name, test_func in tests:
            try:
                results[name] = test_func()
            except Exception as e:
                log.error(f"[X] {name} test failed: {e}")
                results[name] = False
        
        # Summary
        log.info("")
        log.info("=" * 60)
        log.info("SUMMARY")
        log.info("=" * 60)
        for name, result in results.items():
            status = "[OK] PASS" if result else "[X] FAIL"
            log.info(f"{status}: {name}")
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        log.info(f"\nTotal: {passed}/{total} tests passed")
        
        return all(results.values())

if __name__ == "__main__":
    diag = AuraOSDiagnostics()
    success = diag.run_all_tests()
    sys.exit(0 if success else 1)
