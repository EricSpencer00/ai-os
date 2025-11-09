#!/usr/bin/env python3
"""MVP Test Suite for AuraOS
Tests all core components and identifies issues
"""
import sys
import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class MVPTester:
    """Test all MVP components"""
    
    def __init__(self):
        self.results = []
        self.issues = []
        
    def log(self, msg: str, color: str = RESET):
        """Print colored log message"""
        print(f"{color}{msg}{RESET}")
    
    def test(self, name: str, func) -> bool:
        """Run a test and record result"""
        self.log(f"\n▶ Testing: {name}", BLUE)
        try:
            result = func()
            if result:
                self.log(f"✓ PASS: {name}", GREEN)
                self.results.append((name, True, None))
                return True
            else:
                self.log(f"✗ FAIL: {name}", RED)
                self.results.append((name, False, "Test returned False"))
                self.issues.append(name)
                return False
        except Exception as e:
            self.log(f"✗ ERROR: {name} - {e}", RED)
            self.results.append((name, False, str(e)))
            self.issues.append(name)
            return False
    
    def run_command(self, cmd: List[str], check: bool = True) -> Tuple[bool, str]:
        """Run shell command and return success, output"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            success = result.returncode == 0 if check else True
            output = result.stdout + result.stderr
            return success, output
        except Exception as e:
            return False, str(e)
    
    # ==================== VM TESTS ====================
    
    def test_vm_running(self) -> bool:
        """Check if VM is running"""
        success, output = self.run_command(["multipass", "list"])
        if not success:
            return False
        return "auraos-multipass" in output and "Running" in output
    
    def test_vm_ssh(self) -> bool:
        """Test SSH access to VM"""
        success, output = self.run_command([
            "multipass", "exec", "auraos-multipass", "--", "echo", "test"
        ])
        return success and "test" in output
    
    def test_xvfb_running(self) -> bool:
        """Check if Xvfb is running in VM"""
        success, output = self.run_command([
            "multipass", "exec", "auraos-multipass", "--",
            "pgrep", "-f", "Xvfb"
        ])
        return success and output.strip()
    
    def test_x11vnc_service(self) -> bool:
        """Check if x11vnc service is active"""
        success, output = self.run_command([
            "multipass", "exec", "auraos-multipass", "--",
            "systemctl", "is-active", "auraos-x11vnc.service"
        ])
        return success and "active" in output
    
    def test_novnc_service(self) -> bool:
        """Check if noVNC service is active"""
        success, output = self.run_command([
            "multipass", "exec", "auraos-multipass", "--",
            "systemctl", "is-active", "auraos-novnc.service"
        ])
        return success and "active" in output
    
    def test_gui_agent_service(self) -> bool:
        """Check if GUI agent service is active"""
        success, output = self.run_command([
            "multipass", "exec", "auraos-multipass", "--",
            "systemctl", "is-active", "auraos-gui-agent.service"
        ])
        return success and "active" in output
    
    # ==================== AGENT API TESTS ====================
    
    def test_agent_health(self) -> bool:
        """Test agent health endpoint"""
        try:
            import requests
            response = requests.get("http://localhost:8765/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("ok") == True
            return False
        except Exception as e:
            self.log(f"  Agent health check failed: {e}", YELLOW)
            return False
    
    def test_agent_screenshot(self) -> bool:
        """Test agent screenshot endpoint"""
        try:
            import requests
            response = requests.get("http://localhost:8765/screenshot", timeout=10)
            if response.status_code == 200 and len(response.content) > 1000:
                # Save for inspection
                with open("/tmp/mvp_test_screenshot.png", "wb") as f:
                    f.write(response.content)
                self.log(f"  Screenshot saved: /tmp/mvp_test_screenshot.png ({len(response.content)} bytes)", YELLOW)
                return True
            return False
        except Exception as e:
            self.log(f"  Screenshot test failed: {e}", YELLOW)
            return False
    
    # ==================== KEY MANAGER TESTS ====================
    
    def test_key_manager_import(self) -> bool:
        """Test if KeyManager can be imported"""
        try:
            sys.path.insert(0, str(Path(__file__).parent / "auraos_daemon"))
            from core.key_manager import KeyManager
            km = KeyManager()
            return True
        except Exception as e:
            self.log(f"  Import failed: {e}", YELLOW)
            return False
    
    def test_key_manager_add_get(self) -> bool:
        """Test adding and retrieving keys"""
        try:
            sys.path.insert(0, str(Path(__file__).parent / "auraos_daemon"))
            from core.key_manager import KeyManager
            km = KeyManager()
            
            # Add test key
            km.add_key("test_provider", "test_key_12345")
            
            # Retrieve it
            key = km.get_key("test_provider")
            
            # Clean up
            km.remove_provider("test_provider")
            
            return key == "test_key_12345"
        except Exception as e:
            self.log(f"  Key operations failed: {e}", YELLOW)
            return False
    
    # ==================== SCREEN AUTOMATION TESTS ====================
    
    def test_screen_automation_import(self) -> bool:
        """Test if ScreenAutomation can be imported"""
        try:
            sys.path.insert(0, str(Path(__file__).parent / "auraos_daemon"))
            from core.screen_automation import ScreenAutomation
            sa = ScreenAutomation()
            return True
        except Exception as e:
            self.log(f"  Import failed: {e}", YELLOW)
            return False
    
    def test_screen_capture(self) -> bool:
        """Test screen capture via ScreenAutomation"""
        try:
            sys.path.insert(0, str(Path(__file__).parent / "auraos_daemon"))
            from core.screen_automation import ScreenAutomation
            sa = ScreenAutomation()
            
            screenshot_path = sa.capture_screen()
            if screenshot_path and os.path.exists(screenshot_path):
                size = os.path.getsize(screenshot_path)
                self.log(f"  Captured screenshot: {screenshot_path} ({size} bytes)", YELLOW)
                return size > 1000
            return False
        except Exception as e:
            self.log(f"  Screen capture failed: {e}", YELLOW)
            return False
    
    # ==================== DAEMON TESTS ====================
    
    def test_daemon_structure(self) -> bool:
        """Check if daemon directory structure exists"""
        daemon_dir = Path(__file__).parent / "auraos_daemon"
        required_dirs = [
            daemon_dir / "core",
            daemon_dir / "plugins",
            daemon_dir / "commands"
        ]
        return all(d.exists() and d.is_dir() for d in required_dirs)
    
    def test_daemon_imports(self) -> bool:
        """Test if core daemon modules can be imported"""
        try:
            sys.path.insert(0, str(Path(__file__).parent / "auraos_daemon"))
            from core.logger import AuraLogger
            from core.config import AuraConfig
            return True
        except Exception as e:
            self.log(f"  Daemon import failed: {e}", YELLOW)
            return False
    
    # ==================== INTEGRATION TESTS ====================
    
    def test_end_to_end_screenshot_flow(self) -> bool:
        """Test complete flow: capture → save → verify"""
        try:
            sys.path.insert(0, str(Path(__file__).parent / "auraos_daemon"))
            from core.screen_automation import ScreenAutomation
            import requests
            
            sa = ScreenAutomation()
            
            # 1. Capture via automation module
            screenshot = sa.capture_screen()
            if not screenshot or not os.path.exists(screenshot):
                return False
            
            # 2. Verify via direct API call
            response = requests.get("http://localhost:8765/health", timeout=5)
            if response.status_code != 200:
                return False
            
            # 3. Check display in response
            data = response.json()
            if data.get("display") != ":1":
                return False
            
            self.log(f"  End-to-end flow verified", YELLOW)
            return True
        except Exception as e:
            self.log(f"  Integration test failed: {e}", YELLOW)
            return False
    
    # ==================== MAIN TEST RUNNER ====================
    
    def run_all_tests(self):
        """Run all MVP tests"""
        self.log("="*60, BLUE)
        self.log("AuraOS MVP Test Suite", BLUE)
        self.log("="*60, BLUE)
        
        # VM Tests
        self.log("\n📦 VM Infrastructure Tests", BLUE)
        self.test("VM is running", self.test_vm_running)
        self.test("SSH access works", self.test_vm_ssh)
        self.test("Xvfb is running", self.test_xvfb_running)
        self.test("x11vnc service active", self.test_x11vnc_service)
        self.test("noVNC service active", self.test_novnc_service)
        self.test("GUI agent service active", self.test_gui_agent_service)
        
        # Agent API Tests
        self.log("\n🌐 Agent API Tests", BLUE)
        self.test("Agent health endpoint", self.test_agent_health)
        self.test("Agent screenshot endpoint", self.test_agent_screenshot)
        
        # Key Manager Tests
        self.log("\n🔐 Key Manager Tests", BLUE)
        self.test("KeyManager import", self.test_key_manager_import)
        self.test("Key add/get operations", self.test_key_manager_add_get)
        
        # Screen Automation Tests
        self.log("\n🤖 Screen Automation Tests", BLUE)
        self.test("ScreenAutomation import", self.test_screen_automation_import)
        self.test("Screen capture", self.test_screen_capture)
        
        # Daemon Tests
        self.log("\n⚙️  Daemon Tests", BLUE)
        self.test("Daemon directory structure", self.test_daemon_structure)
        self.test("Daemon core imports", self.test_daemon_imports)
        
        # Integration Tests
        self.log("\n🔗 Integration Tests", BLUE)
        self.test("End-to-end screenshot flow", self.test_end_to_end_screenshot_flow)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        self.log("\n" + "="*60, BLUE)
        self.log("Test Summary", BLUE)
        self.log("="*60, BLUE)
        
        total = len(self.results)
        passed = sum(1 for _, success, _ in self.results if success)
        failed = total - passed
        
        self.log(f"\nTotal Tests: {total}", BLUE)
        self.log(f"Passed: {passed}", GREEN)
        self.log(f"Failed: {failed}", RED if failed > 0 else GREEN)
        
        if self.issues:
            self.log("\n⚠️  Issues Found:", YELLOW)
            for issue in self.issues:
                self.log(f"  • {issue}", RED)
            
            self.log("\n💡 Recommendations:", YELLOW)
            
            if "VM is running" in self.issues:
                self.log("  1. Start the VM: multipass start auraos-multipass", YELLOW)
            
            if any("service" in i.lower() for i in self.issues):
                self.log("  2. Bootstrap the VM: ./vm_resources/gui-bootstrap.sh", YELLOW)
            
            if any("agent" in i.lower() for i in self.issues):
                self.log("  3. Restart SSH tunnels: ./open_vm_gui.sh", YELLOW)
            
            if any("import" in i.lower() for i in self.issues):
                self.log("  4. Install dependencies: cd auraos_daemon && pip install -r requirements.txt", YELLOW)
        
        else:
            self.log("\n🎉 All tests passed! MVP is working correctly.", GREEN)
        
        self.log("\n" + "="*60, BLUE)


if __name__ == "__main__":
    tester = MVPTester()
    tester.run_all_tests()
    
    # Exit with error code if tests failed
    sys.exit(0 if not tester.issues else 1)
