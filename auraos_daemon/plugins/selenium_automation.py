"""
Selenium automation plugin for AuraOS Autonomous AI Daemon v8
Browser automation using Selenium WebDriver
"""
import os
import json
import requests
import re
import logging
from flask import jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService

# Load config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    GROQ_API_KEY = config.get("GROQ_API_KEY")
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL = "llama3-70b-8192"
    SELENIUM_CONFIG = config.get("PLUGINS", {}).get("selenium_automation", {})
except Exception:
    GROQ_API_KEY = None
    GROQ_API_URL = None
    GROQ_MODEL = None
    SELENIUM_CONFIG = {}

DOWNLOADS_DIR = os.path.expanduser('~/Downloads')


class Plugin:
    name = "selenium_automation"
    
    def __init__(self):
        self.driver = None
        self.headless = SELENIUM_CONFIG.get("headless", True)
        self.browser = SELENIUM_CONFIG.get("browser", "chrome")
    
    def generate_script(self, intent, context):
        """Generate browser automation script from natural language intent"""
        intent_lower = intent.lower()
        
        # Check for common browser automation patterns
        if any(k in intent_lower for k in ["open", "navigate", "go to", "visit"]):
            return self._generate_navigation_script(intent)
        elif any(k in intent_lower for k in ["click", "press", "tap"]):
            return self._generate_click_script(intent)
        elif any(k in intent_lower for k in ["type", "enter", "fill", "input"]):
            return self._generate_input_script(intent)
        elif any(k in intent_lower for k in ["screenshot", "capture", "snap"]):
            return self._generate_screenshot_script(intent)
        elif any(k in intent_lower for k in ["download", "save"]):
            return self._generate_download_script(intent)
        elif any(k in intent_lower for k in ["search", "find", "look for"]):
            return self._generate_search_script(intent)
        else:
            # Use LLM to generate complex automation script
            return self._generate_llm_script(intent)
    
    def _generate_navigation_script(self, intent):
        """Generate script to navigate to a URL"""
        # Extract URL from intent
        url_match = re.search(r'https?://[^\s]+', intent)
        if url_match:
            url = url_match.group(0)
        else:
            # Try to find domain-like patterns
            words = intent.split()
            url = None
            for word in words:
                if '.' in word and not word.startswith('.'):
                    url = f"https://{word}" if not word.startswith('http') else word
                    break
            if not url:
                url = "https://www.google.com"
        
        script = {
            "action": "navigate",
            "url": url,
            "description": f"Navigate to {url}"
        }
        return jsonify({"script_type": "selenium", "script": json.dumps(script)}), 200
    
    def _generate_click_script(self, intent):
        """Generate script to click an element"""
        # Extract what to click
        element_text = intent.lower().replace("click", "").replace("on", "").replace("the", "").strip()
        
        script = {
            "action": "click",
            "element": element_text,
            "description": f"Click on '{element_text}'"
        }
        return jsonify({"script_type": "selenium", "script": json.dumps(script)}), 200
    
    def _generate_input_script(self, intent):
        """Generate script to input text"""
        # Parse "type <text> into <field>"
        if " into " in intent.lower():
            parts = intent.lower().split(" into ")
            text = parts[0].replace("type", "").replace("enter", "").strip()
            field = parts[1].strip()
        else:
            text = intent.replace("type", "").replace("enter", "").strip()
            field = "search"  # default field
        
        script = {
            "action": "input",
            "text": text,
            "field": field,
            "description": f"Type '{text}' into '{field}'"
        }
        return jsonify({"script_type": "selenium", "script": json.dumps(script)}), 200
    
    def _generate_screenshot_script(self, intent):
        """Generate script to take a screenshot"""
        # Extract filename if provided
        filename_match = re.search(r'as (\w+\.png)', intent)
        filename = filename_match.group(1) if filename_match else "screenshot.png"
        
        script = {
            "action": "screenshot",
            "filename": filename,
            "description": f"Take screenshot and save as {filename}"
        }
        return jsonify({"script_type": "selenium", "script": json.dumps(script)}), 200
    
    def _generate_download_script(self, intent):
        """Generate script to download a file"""
        script = {
            "action": "download",
            "description": "Set up browser for downloading"
        }
        return jsonify({"script_type": "selenium", "script": json.dumps(script)}), 200
    
    def _generate_search_script(self, intent):
        """Generate script to perform a web search"""
        query = intent.lower()
        for word in ["search for", "search", "google", "find", "look for"]:
            query = query.replace(word, "")
        query = query.strip()
        
        script = {
            "action": "search",
            "query": query,
            "description": f"Search Google for '{query}'"
        }
        return jsonify({"script_type": "selenium", "script": json.dumps(script)}), 200
    
    def _generate_llm_script(self, intent):
        """Use LLM to generate complex automation script"""
        if not GROQ_API_KEY:
            return jsonify({"error": "Groq API key not configured"}), 500
        
        system_prompt = """You are a browser automation expert. Generate a JSON script for Selenium automation.
The script should be a JSON object with these fields:
- action: one of [navigate, click, input, screenshot, search, custom]
- Additional fields based on action type
- description: what the script does

For complex tasks, use action="custom" and provide "steps" array with multiple actions.

Example:
{
  "action": "custom",
  "steps": [
    {"action": "navigate", "url": "https://example.com"},
    {"action": "click", "element": "login button"},
    {"action": "input", "field": "username", "text": "user@example.com"}
  ],
  "description": "Login to example.com"
}

Return ONLY the JSON, no explanation."""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": intent}
            ],
            "temperature": 0.1
        }
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            script_json = response.json()["choices"][0]["message"]["content"]
            # Clean up code blocks if present
            script_json = re.sub(r'```json\n?', '', script_json)
            script_json = re.sub(r'```\n?', '', script_json)
            
            return jsonify({"script_type": "selenium", "script": script_json.strip()}), 200
        except Exception as e:
            logging.error(f"Error generating Selenium script: {e}")
            return jsonify({"error": f"Failed to generate script: {e}"}), 500

    def execute(self, script, context):
        """Execute Selenium automation script"""
        try:
            # Parse script JSON
            if isinstance(script, str):
                script_data = json.loads(script)
            else:
                script_data = script
            
            # Initialize browser if not already running
            if not self.driver:
                self._init_browser()
            
            action = script_data.get("action")
            
            if action == "navigate":
                return self._execute_navigate(script_data)
            elif action == "click":
                return self._execute_click(script_data)
            elif action == "input":
                return self._execute_input(script_data)
            elif action == "screenshot":
                return self._execute_screenshot(script_data)
            elif action == "search":
                return self._execute_search(script_data)
            elif action == "custom":
                return self._execute_custom(script_data)
            else:
                return jsonify({"error": f"Unknown action: {action}"}), 400
                
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Invalid JSON script: {e}"}), 400
        except Exception as e:
            logging.error(f"Selenium execution error: {e}")
            return jsonify({"error": str(e)}), 500
    
    def _init_browser(self):
        """Initialize the browser driver"""
        try:
            if self.browser == "chrome":
                chrome_options = ChromeOptions()
                if self.headless:
                    chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                # Set download directory
                prefs = {"download.default_directory": DOWNLOADS_DIR}
                chrome_options.add_experimental_option("prefs", prefs)
                
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                firefox_options = FirefoxOptions()
                if self.headless:
                    firefox_options.add_argument("--headless")
                
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
            
            self.driver.implicitly_wait(10)
            logging.info(f"Browser initialized: {self.browser}")
        except Exception as e:
            logging.error(f"Failed to initialize browser: {e}")
            raise
    
    def _execute_navigate(self, script_data):
        """Navigate to URL"""
        url = script_data.get("url")
        self.driver.get(url)
        return jsonify({"output": f"Navigated to {url}", "current_url": self.driver.current_url}), 200
    
    def _execute_click(self, script_data):
        """Click an element"""
        element_text = script_data.get("element", "")
        
        try:
            # Try multiple strategies to find element
            element = None
            
            # Try by link text
            try:
                element = self.driver.find_element(By.PARTIAL_LINK_TEXT, element_text)
            except NoSuchElementException:
                pass
            
            # Try by button text
            if not element:
                try:
                    element = self.driver.find_element(By.XPATH, f"//button[contains(text(), '{element_text}')]")
                except NoSuchElementException:
                    pass
            
            # Try by input value
            if not element:
                try:
                    element = self.driver.find_element(By.XPATH, f"//input[@value='{element_text}']")
                except NoSuchElementException:
                    pass
            
            if element:
                element.click()
                return jsonify({"output": f"Clicked on '{element_text}'"}), 200
            else:
                return jsonify({"error": f"Could not find element: {element_text}"}), 404
                
        except Exception as e:
            return jsonify({"error": f"Click failed: {str(e)}"}), 500
    
    def _execute_input(self, script_data):
        """Input text into a field"""
        field = script_data.get("field", "")
        text = script_data.get("text", "")
        
        try:
            # Try to find input field
            element = None
            
            # Try by name
            try:
                element = self.driver.find_element(By.NAME, field)
            except NoSuchElementException:
                pass
            
            # Try by ID
            if not element:
                try:
                    element = self.driver.find_element(By.ID, field)
                except NoSuchElementException:
                    pass
            
            # Try by placeholder
            if not element:
                try:
                    element = self.driver.find_element(By.XPATH, f"//input[@placeholder='{field}']")
                except NoSuchElementException:
                    pass
            
            if element:
                element.clear()
                element.send_keys(text)
                element.send_keys(Keys.RETURN)
                return jsonify({"output": f"Entered '{text}' into '{field}'"}), 200
            else:
                return jsonify({"error": f"Could not find field: {field}"}), 404
                
        except Exception as e:
            return jsonify({"error": f"Input failed: {str(e)}"}), 500
    
    def _execute_screenshot(self, script_data):
        """Take a screenshot"""
        filename = script_data.get("filename", "screenshot.png")
        filepath = os.path.join(DOWNLOADS_DIR, filename)
        
        self.driver.save_screenshot(filepath)
        return jsonify({"output": f"Screenshot saved to {filepath}", "file": filepath}), 200
    
    def _execute_search(self, script_data):
        """Perform a Google search"""
        query = script_data.get("query", "")
        
        self.driver.get("https://www.google.com")
        search_box = self.driver.find_element(By.NAME, "q")
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        
        # Wait for results
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "search"))
        )
        
        return jsonify({"output": f"Searched for '{query}'", "current_url": self.driver.current_url}), 200
    
    def _execute_custom(self, script_data):
        """Execute multiple steps"""
        steps = script_data.get("steps", [])
        results = []
        
        for step in steps:
            action = step.get("action")
            if action == "navigate":
                result = self._execute_navigate(step)
            elif action == "click":
                result = self._execute_click(step)
            elif action == "input":
                result = self._execute_input(step)
            elif action == "screenshot":
                result = self._execute_screenshot(step)
            elif action == "search":
                result = self._execute_search(step)
            else:
                result = (jsonify({"error": f"Unknown action: {action}"}), 400)
            
            results.append(result[0].get_json() if hasattr(result[0], 'get_json') else result[0])
            
            # Stop if any step fails
            if result[1] != 200:
                break
        
        return jsonify({"output": "Custom automation completed", "results": results}), 200
    
    def cleanup(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logging.info("Browser closed")
