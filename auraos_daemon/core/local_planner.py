"""
Local lightweight planner for action inference.

Instead of always sending full screenshots + reasoning to LLaVA, this module:
1. Takes screen state summaries (text) + user goal
2. Uses a fast local LLM (Mistral, Phi-3) to plan next actions
3. Only calls vision model (LLaVA) when visual perception is needed

This drastically reduces inference latency and model load.

Usage:
  planner = LocalPlanner(model="mistral")
  actions = planner.plan(goal="open firefox", screen_summary="desktop with taskbar")
  # actions: [{"action": "click", "target": "firefox icon"}, ...]
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


class LocalPlanner:
    """
    Uses a fast local LLM to plan actions without requiring visual inference.
    Falls back to vision model only when needed.
    """

    def __init__(
        self,
        model: str = "mistral",
        ollama_url: str = "http://localhost:11434",
        timeout: int = 30,
        vision_model: str = "llava:13b",
    ):
        """
        Args:
            model: Ollama model for planning (mistral, neural-chat, phi, etc.)
            ollama_url: Ollama API endpoint
            timeout: inference timeout in seconds
            vision_model: Ollama model for visual reasoning (fallback)
        """
        self.model = model
        self.ollama_url = ollama_url
        self.timeout = timeout
        self.vision_model = vision_model
        self.action_history: List[Dict[str, Any]] = []

    def plan(
        self,
        goal: str,
        screen_summary: str,
        screen_regions: Optional[List[tuple]] = None,
        max_actions: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Plan actions to achieve the goal based on screen summary.

        Args:
            goal: User's goal (e.g., "open firefox")
            screen_summary: Text description of current screen state
            screen_regions: List of changed regions [(x, y, w, h), ...]
            max_actions: max number of actions to plan

        Returns:
            List of action dicts: [{"action": "click", "x": 100, "y": 200}, ...]
        """
        prompt = self._build_prompt(goal, screen_summary, screen_regions, max_actions)

        try:
            response = self._query_ollama(self.model, prompt)
            actions = self._parse_actions(response)
            self.action_history.extend(actions)
            return actions
        except Exception as e:
            logger.error(f"Planner error: {e}")
            return [{"action": "wait", "duration": 1}]

    def _build_prompt(
        self,
        goal: str,
        screen_summary: str,
        screen_regions: Optional[List[tuple]],
        max_actions: int,
    ) -> str:
        """Build a prompt for the planner."""
        regions_text = ""
        if screen_regions:
            regions_text = (
                f"\nChanged regions (x, y, w, h): {screen_regions}"
            )

        history_text = ""
        if self.action_history[-3:]:
            history_text = (
                "\nLast actions taken:\n"
                + "\n".join(
                    f"  - {a.get('action', 'unknown')}"
                    for a in self.action_history[-3:]
                )
            )

        prompt = f"""You are a UI automation agent. Your task is to plan the next actions to achieve the goal.

Current screen state:
{screen_summary}
{regions_text}

User goal: {goal}
{history_text}

Plan the next {max_actions} actions to achieve the goal. Each action should be simple and deterministic.

Valid actions:
- click at (x, y)
- type "text"
- key press: enter, backspace, tab, escape, arrow_up, arrow_down, arrow_left, arrow_right
- wait N seconds
- screenshot (for visual confirmation)

Return a JSON array of actions:
[
  {{"action": "click", "x": 100, "y": 200}},
  {{"action": "type", "text": "hello"}},
  {{"action": "key", "key": "enter"}},
  ...
]

Think step-by-step about what UI elements to interact with. Be concise."""

        return prompt

    def _query_ollama(self, model: str, prompt: str) -> str:
        """Query Ollama with the prompt."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    def _parse_actions(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract JSON actions from LLM response."""
        actions = []
        try:
            # Try to find JSON array in response
            match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                actions = json.loads(json_str)
                # Validate and clean actions
                for action in actions:
                    if not isinstance(action, dict) or "action" not in action:
                        logger.warning(f"Invalid action format: {action}")
                        continue
                    actions.append(self._normalize_action(action))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse actions from: {response_text[:200]}")

        if not actions:
            # Fallback: safe do-nothing action
            actions = [{"action": "wait", "duration": 1}]

        return actions

    def _normalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize action dict to standard format."""
        normalized = {"action": action.get("action", "wait")}

        action_type = normalized["action"].lower()

        if action_type == "click":
            normalized["x"] = action.get("x", 640)
            normalized["y"] = action.get("y", 360)
        elif action_type == "type":
            normalized["text"] = action.get("text", "")
        elif action_type == "key":
            normalized["key"] = action.get("key", "enter")
        elif action_type == "wait":
            normalized["duration"] = action.get("duration", 1)

        return normalized

    def decide_if_vision_needed(
        self, goal: str, action_sequence: List[Dict[str, Any]], confidence: float = 0.5
    ) -> bool:
        """
        Decide if visual understanding is needed before executing actions.
        Use heuristics: if planner confidence is low or goal involves visual tasks.

        Args:
            goal: User goal
            action_sequence: Planned actions
            confidence: Internal confidence (0-1)

        Returns:
            True if vision model should be queried
        """
        visual_keywords = [
            "find",
            "locate",
            "identify",
            "recognize",
            "see",
            "visible",
            "button",
            "icon",
            "text",
        ]

        if any(kw in goal.lower() for kw in visual_keywords):
            return True

        if confidence < 0.5:
            return True

        if not action_sequence:
            return True

        return False
