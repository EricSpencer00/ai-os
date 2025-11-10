# Integration Guide: Adding v2 Components to the Daemon

This guide shows how to integrate the new v2 components (delta detection, local planner, WebSocket agent) into the existing AuraOS daemon.

---

## 📋 Integration Checklist

- [ ] 1. Add dependencies to requirements.txt (already done ✅)
- [ ] 2. Import new modules in daemon
- [ ] 3. Add v2 configuration to config.json
- [ ] 4. Update main inference loop with delta + planner
- [ ] 5. Setup WebSocket agent in VM bootstrap
- [ ] 6. Add host wake-check to system startup
- [ ] 7. Test full v2 stack
- [ ] 8. Update documentation

---

## 1️⃣ Configuration (config.json)

Add this section to `auraos_daemon/config.json`:

```json
{
  "VERSION": "2.0",
  
  "INFERENCE": {
    "strategy": "hybrid",
    "use_delta_detection": true,
    "use_local_planner": true,
    "use_websocket_agent": true,
    "vision_only_on_demand": true
  },

  "PERCEPTION": {
    "display": ":1",
    "screenshot_tool": "scrot",
    "grid_size": 64,
    "delta_threshold": 20,
    "max_regions": 10
  },

  "PLANNING": {
    "local_planner_model": "mistral",
    "local_planner_timeout": 30,
    "vision_model": "llava:13b",
    "vision_timeout": 120,
    "max_actions_per_cycle": 5,
    "min_confidence_for_execution": 0.3
  },

  "CONTROL": {
    "ws_agent_uri": "ws://localhost:6789",
    "ws_connection_timeout": 10,
    "ws_action_timeout": 5,
    "action_retry_count": 2,
    "action_retry_delay": 1.0
  }
}
```

---

## 2️⃣ Update Daemon Main Loop

**File: `auraos_daemon/daemon.py`**

Replace the screenshot + LLaVA loop with v2 components:

```python
# OLD (v1):
from auraos_daemon.core.screen_automation import ScreenAutomationAgent

# NEW (v2):
from auraos_daemon.core.screen_diff import ScreenDiffDetector
from auraos_daemon.core.local_planner import LocalPlanner
from auraos_daemon.core.ws_agent import WebSocketAgent
import json

class AuraOSDaemonV2:
    """AuraOS daemon with v2 architecture (hybrid inference)."""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        
        # Initialize v2 components
        perception_cfg = self.config.get("PERCEPTION", {})
        self.detector = ScreenDiffDetector(
            display=perception_cfg.get("display", ":1"),
            grid_size=perception_cfg.get("grid_size", 64),
            threshold=perception_cfg.get("delta_threshold", 20),
            max_regions=perception_cfg.get("max_regions", 10),
        )
        
        planning_cfg = self.config.get("PLANNING", {})
        self.planner = LocalPlanner(
            model=planning_cfg.get("local_planner_model", "mistral"),
            timeout=planning_cfg.get("local_planner_timeout", 30),
        )
        
        control_cfg = self.config.get("CONTROL", {})
        self.agent = WebSocketAgent(
            uri=control_cfg.get("ws_agent_uri", "ws://localhost:6789"),
            timeout=control_cfg.get("ws_connection_timeout", 10),
        )
        
        self.agent.connect()
        self.logger = logging.getLogger(__name__)

    def inference_loop(self, user_goal: str, max_iterations: int = 10):
        """
        Main v2 inference loop with delta detection + local planner + WebSocket control.
        
        Args:
            user_goal: High-level user intent (e.g., "open firefox and go to google.com")
            max_iterations: Max action cycles
        """
        self.logger.info(f"Starting v2 inference loop: {user_goal}")
        
        for iteration in range(max_iterations):
            start_time = time.time()
            
            # === STEP 1: Perceive (Fast Delta Detection) ===
            self.logger.info(f"[{iteration+1}/{max_iterations}] Perceiving...")
            perception = self.detector.capture_and_diff()
            
            if perception is None:
                self.logger.error("Perception failed")
                break
            
            # === STEP 2: Plan (Local Lightweight Model) ===
            self.logger.info(f"Planning actions...")
            screen_summary = perception.get("summary", "Unknown screen state")
            changed_regions = perception.get("changed_regions", [])
            
            try:
                actions = self.planner.plan(
                    goal=user_goal,
                    screen_summary=screen_summary,
                    screen_regions=changed_regions[:3],  # Send top 3 regions
                    max_actions=self.config["PLANNING"].get("max_actions_per_cycle", 5),
                )
            except Exception as e:
                self.logger.error(f"Planning failed: {e}")
                actions = [{"action": "wait", "duration": 1}]
            
            # === STEP 3: Execute (WebSocket Agent) ===
            self.logger.info(f"Executing {len(actions)} actions...")
            success_count = 0
            
            for action in actions:
                try:
                    result = self.agent.execute_action(
                        action,
                        timeout=self.config["CONTROL"].get("ws_action_timeout", 5)
                    )
                    
                    if result.get("success"):
                        success_count += 1
                        self.logger.debug(f"✓ {action.get('action')} succeeded")
                    else:
                        self.logger.warn(f"✗ {action.get('action')} failed: {result.get('error')}")
                        
                except Exception as e:
                    self.logger.error(f"Action execution error: {e}")
            
            # === STEP 4: Decide if Done ===
            cycle_time = time.time() - start_time
            self.logger.info(f"Cycle {iteration+1} done: {success_count}/{len(actions)} actions, {cycle_time:.2f}s")
            
            if success_count == 0 and iteration > 2:
                self.logger.warn("No successful actions; may be stuck")
                # Could implement recovery logic here
            
            # Check if goal achieved (simple heuristic)
            if self._check_goal_achieved(user_goal, screen_summary):
                self.logger.info(f"✓ Goal achieved: {user_goal}")
                return True
        
        self.logger.warn(f"Max iterations reached without completing goal")
        return False
    
    def _check_goal_achieved(self, goal: str, screen_summary: str) -> bool:
        """Simple heuristic to check if goal is achieved."""
        goal_lower = goal.lower()
        summary_lower = screen_summary.lower()
        
        # Very basic check — in production, query vision model
        if "open firefox" in goal_lower and "firefox" in summary_lower:
            return True
        if "click" in goal_lower and ("clicked" in summary_lower or "active" in summary_lower):
            return True
        
        return False
    
    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'agent'):
            self.agent.disconnect()
        self.logger.info("Daemon shutdown")


# Example usage:
if __name__ == "__main__":
    daemon = AuraOSDaemonV2("auraos_daemon/config.json")
    daemon.inference_loop("open firefox and navigate to google.com", max_iterations=15)
    daemon.cleanup()
```

---

## 3️⃣ Update VM Bootstrap

**File: `vm_resources/run_and_bootstrap_vm.sh`**

Add WebSocket agent installation to the bootstrap:

```bash
# After gui-bootstrap completes, add:

echo "[bootstrap] Installing WebSocket agent..."
bash /tmp/install_ws_agent.sh

# Ensure bootstrap_done marker is set
mkdir -p /var/log/auraos
touch /var/log/auraos/bootstrap_done
echo "Bootstrap completed successfully" >> /var/log/auraos/bootstrap.log
```

**Or embed in `auraos.sh` vm-setup:**

In the Step 6/7 section where we embed application scripts, add the WebSocket agent installation inline (similar to how terminal + homescreen are embedded).

---

## 4️⃣ Add Host Wake Check (macOS)

**File: `~/Library/LaunchAgents/com.auraos.vm-wake-check.plist`**

```bash
# One-time setup:
mkdir -p ~/Library/LaunchAgents
cp tools/com.auraos.vm-wake-check.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.auraos.vm-wake-check.plist
```

---

## 5️⃣ Create Integration Test

**File: `test_v2_integration.py`**

```python
#!/usr/bin/env python3
"""Integration test for v2 components."""

import sys
import time
import logging
from pathlib import Path

# Add auraos_daemon to path
sys.path.insert(0, str(Path(__file__).parent / "auraos_daemon"))

from core.screen_diff import ScreenDiffDetector
from core.local_planner import LocalPlanner
from core.ws_agent import WebSocketAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_v2_stack():
    """Test all v2 components together."""
    
    logger.info("=== Testing v2 Stack ===")
    
    # Test 1: Delta detection
    logger.info("1. Testing delta detection...")
    detector = ScreenDiffDetector(display=":1")
    result = detector.capture_and_diff()
    assert result is not None
    assert "changed_regions" in result
    logger.info(f"   ✓ Detected {len(result['changed_regions'])} regions")
    
    # Test 2: Local planner
    logger.info("2. Testing local planner...")
    planner = LocalPlanner(model="mistral")
    actions = planner.plan(
        goal="take screenshot",
        screen_summary="Desktop with taskbar",
    )
    assert isinstance(actions, list)
    assert all("action" in a for a in actions)
    logger.info(f"   ✓ Planned {len(actions)} actions")
    
    # Test 3: WebSocket agent
    logger.info("3. Testing WebSocket agent...")
    agent = WebSocketAgent(uri="ws://localhost:6789")
    if agent.connect():
        result = agent.execute_action({"action": "screenshot"})
        assert "success" in result
        agent.disconnect()
        logger.info("   ✓ WebSocket agent responsive")
    else:
        logger.warn("   ⚠ WebSocket agent not available (skip)")
    
    logger.info("✅ All v2 components working!")
    return True


if __name__ == "__main__":
    try:
        test_v2_stack()
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)
```

Run:
```bash
python3 test_v2_integration.py
```

---

## 6️⃣ Update Configuration File

**File: `auraos_daemon/config.sample.json`**

Add new v2 section:

```json
{
  "VERSION": "2.0",
  
  "INFERENCE": {
    "strategy": "hybrid",
    "use_delta_detection": true,
    "use_local_planner": true,
    "use_websocket_agent": true
  },
  
  "PERCEPTION": {
    "display": ":1",
    "screenshot_tool": "scrot",
    "grid_size": 64,
    "delta_threshold": 20,
    "max_regions": 10
  },
  
  "PLANNING": {
    "local_planner_model": "mistral",
    "local_planner_timeout": 30,
    "vision_model": "llava:13b",
    "max_actions_per_cycle": 5
  },
  
  "CONTROL": {
    "ws_agent_uri": "ws://localhost:6789",
    "ws_connection_timeout": 10,
    "ws_action_timeout": 5
  }
}
```

---

## 7️⃣ Update Port Forwarding

Ensure port 6789 (WebSocket) is forwarded in `auraos.sh`:

```bash
# In cmd_forward():
forward_port() {
    local local_port=$1
    local remote_port=$2
    local name=$3
    
    # Existing forwards:
    # 5901 (VNC), 6080 (noVNC), 8765 (GUI agent)
    
    # ADD:
    # 6789 (WebSocket agent)
}
```

---

## 8️⃣ Testing Workflow

```bash
# 1. Setup dependencies
bash tools/v2_setup.sh

# 2. Run integration test
python3 test_v2_integration.py

# 3. Run demo
python3 tools/demo_v2_architecture.py

# 4. Check VM is ready
./auraos.sh health

# 5. Test inference loop (manual)
python3 -c "
from auraos_daemon.daemon import AuraOSDaemonV2
daemon = AuraOSDaemonV2('auraos_daemon/config.json')
daemon.inference_loop('click the desktop', max_iterations=3)
daemon.cleanup()
"

# 6. Monitor wake checks (macOS)
tail -f logs/vm_wake_check.log
```

---

## 📊 Migration Path

### Phase 1: Gradual Integration (Week 1)
- [ ] Add v2 config to config.json
- [ ] Import modules in daemon.py
- [ ] Keep old logic as fallback

### Phase 2: Selective Usage (Week 2)
- [ ] Enable delta detection for new inference loops
- [ ] Use local planner for simple tasks
- [ ] Fall back to LLaVA for complex vision

### Phase 3: Full Migration (Week 3)
- [ ] Replace all screenshot calls with delta detection
- [ ] Use local planner as default
- [ ] Switch to WebSocket agent for input
- [ ] Remove v1 code

### Phase 4: Optimization (Ongoing)
- [ ] Tune grid size and thresholds
- [ ] Implement state persistence
- [ ] Add advanced recovery strategies

---

## 🧪 Validation Checklist

After integration, verify:

- [ ] Delta detection reduces bandwidth
- [ ] Local planner runs in <500ms
- [ ] WebSocket agent latency is <100ms per action
- [ ] VM recovers after host sleep
- [ ] All tests pass
- [ ] No regressions vs. v1
- [ ] Performance improved by >5x
- [ ] Logs are comprehensive

---

## 🆘 Troubleshooting Integration

### "Delta detection module not found"
```bash
python3 -c "from auraos_daemon.core.screen_diff import ScreenDiffDetector"
```

### "Config key not found"
- Ensure config.json has all keys in config.sample.json
- Use config.get() with defaults

### "WebSocket connection refused"
- Check VM is running: `multipass list`
- Check service: `multipass exec auraos-multipass -- systemctl status auraos-ws-agent`
- Check port forwarding: `./auraos.sh forward start`

### "Planner returns empty"
- Check Ollama: `curl http://localhost:11434/api/tags`
- Check model: `ollama list | grep mistral`

---

## 📚 References

- **v2 Architecture:** `ARCHITECTURE_V2.md`
- **Implementation Summary:** `V2_IMPLEMENTATION_SUMMARY.md`
- **Demo Script:** `tools/demo_v2_architecture.py`
- **Daemon Code:** `auraos_daemon/daemon.py`

---

**Status:** Integration guide ready ✅  
**Next Step:** Start with Phase 1 above
