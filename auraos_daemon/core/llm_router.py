"""
LLM Router for AuraOS Autonomous AI Daemon v8
Intelligently routes requests between local Ollama and cloud Groq API
"""
import logging
import time
import requests
import json
import os

# Load config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    GROQ_API_KEY = config.get("GROQ_API_KEY")
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL = "llama3-70b-8192"
    
    # Ollama configuration
    OLLAMA_CONFIG = config.get("OLLAMA", {})
    OLLAMA_HOST = OLLAMA_CONFIG.get("host", "localhost")
    OLLAMA_PORT = OLLAMA_CONFIG.get("port", 11434)
    OLLAMA_MODEL = OLLAMA_CONFIG.get("model", "gemma:2b")
    OLLAMA_ENABLED = OLLAMA_CONFIG.get("enabled", False)
    
    # Routing configuration
    ROUTING_CONFIG = config.get("LLM_ROUTING", {})
    COMPLEXITY_THRESHOLD = ROUTING_CONFIG.get("complexity_threshold", 50)
    PREFER_LOCAL = ROUTING_CONFIG.get("prefer_local", True)
    FALLBACK_TO_CLOUD = ROUTING_CONFIG.get("fallback_to_cloud", True)
    
except Exception as e:
    logging.warning(f"Error loading config for LLM router: {e}")
    GROQ_API_KEY = None
    GROQ_API_URL = None
    GROQ_MODEL = None
    OLLAMA_HOST = "localhost"
    OLLAMA_PORT = 11434
    OLLAMA_MODEL = "gemma:2b"
    OLLAMA_ENABLED = False
    COMPLEXITY_THRESHOLD = 50
    PREFER_LOCAL = True
    FALLBACK_TO_CLOUD = True


class LLMRouter:
    """Routes LLM requests to the most appropriate model"""
    
    def __init__(self):
        self.ollama_available = self._check_ollama_availability()
        self.groq_available = bool(GROQ_API_KEY)
        
        logging.info(f"LLM Router initialized:")
        logging.info(f"  - Ollama: {'Available' if self.ollama_available else 'Not available'}")
        logging.info(f"  - Groq: {'Available' if self.groq_available else 'Not available'}")
    
    def _check_ollama_availability(self):
        """Check if Ollama is running and accessible"""
        if not OLLAMA_ENABLED:
            return False
        
        try:
            response = requests.get(
                f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags",
                timeout=2
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                # Check if our configured model is available
                model_names = [m.get('name') for m in models]
                if OLLAMA_MODEL in model_names:
                    logging.info(f"Ollama model '{OLLAMA_MODEL}' is available")
                    return True
                else:
                    logging.warning(f"Ollama is running but model '{OLLAMA_MODEL}' not found. Available: {model_names}")
                    return False
            return False
        except requests.exceptions.RequestException as e:
            logging.debug(f"Ollama not available: {e}")
            return False
    
    def calculate_complexity(self, prompt, context=None):
        """
        Calculate the complexity score of a request
        Returns: int (0-100)
        
        Factors:
        - Prompt length
        - Number of steps required
        - Presence of complex keywords
        - Context size
        """
        score = 0
        
        # Length factor (longer prompts = more complex)
        word_count = len(prompt.split())
        if word_count > 100:
            score += 30
        elif word_count > 50:
            score += 20
        elif word_count > 20:
            score += 10
        
        # Complex keywords
        complex_keywords = [
            'analyze', 'compare', 'evaluate', 'complex', 'comprehensive',
            'detailed', 'explain in detail', 'multi-step', 'algorithm',
            'optimize', 'architecture', 'design pattern', 'refactor'
        ]
        
        prompt_lower = prompt.lower()
        keyword_matches = sum(1 for kw in complex_keywords if kw in prompt_lower)
        score += keyword_matches * 10
        
        # Simple keywords (reduce complexity)
        simple_keywords = [
            'list', 'show', 'what is', 'hello', 'hi', 'help',
            'simple', 'quick', 'basic', 'open', 'close'
        ]
        
        simple_matches = sum(1 for kw in simple_keywords if kw in prompt_lower)
        score -= simple_matches * 5
        
        # Context size
        if context and isinstance(context, dict):
            context_size = len(str(context))
            if context_size > 1000:
                score += 15
            elif context_size > 500:
                score += 10
        
        # Code generation tasks (more complex)
        if any(kw in prompt_lower for kw in ['script', 'code', 'function', 'class', 'generate']):
            score += 15
        
        # Normalize to 0-100
        return max(0, min(100, score))
    
    def route(self, prompt, context=None, force_model=None):
        """
        Route a request to the appropriate LLM
        
        Args:
            prompt: The user's prompt
            context: Additional context (dict)
            force_model: Force a specific model ("ollama" or "groq")
        
        Returns:
            dict with 'model', 'response', 'tokens', 'latency_ms'
        """
        # Check forced routing
        if force_model == "ollama" and self.ollama_available:
            return self._call_ollama(prompt, context)
        elif force_model == "groq" and self.groq_available:
            return self._call_groq(prompt, context)
        
        # Calculate complexity
        complexity = self.calculate_complexity(prompt, context)
        logging.info(f"Request complexity score: {complexity}/100")
        
        # Routing logic
        if PREFER_LOCAL and self.ollama_available:
            # Try local first for everything if preferred
            if complexity < COMPLEXITY_THRESHOLD:
                logging.info(f"Routing to Ollama (complexity {complexity} < {COMPLEXITY_THRESHOLD})")
                result = self._call_ollama(prompt, context)
                if result.get('success'):
                    return result
                elif FALLBACK_TO_CLOUD and self.groq_available:
                    logging.warning("Ollama failed, falling back to Groq")
                    return self._call_groq(prompt, context)
                else:
                    return result
            else:
                # High complexity - use cloud
                logging.info(f"Routing to Groq (complexity {complexity} >= {COMPLEXITY_THRESHOLD})")
                if self.groq_available:
                    return self._call_groq(prompt, context)
                elif self.ollama_available:
                    logging.warning("Groq not available, falling back to Ollama")
                    return self._call_ollama(prompt, context)
                else:
                    return {
                        'success': False,
                        'error': 'No LLM available',
                        'model': None
                    }
        else:
            # Prefer cloud, fallback to local
            if self.groq_available:
                logging.info("Routing to Groq (cloud preferred)")
                return self._call_groq(prompt, context)
            elif self.ollama_available:
                logging.info("Groq not available, using Ollama")
                return self._call_ollama(prompt, context)
            else:
                return {
                    'success': False,
                    'error': 'No LLM available',
                    'model': None
                }
    
    def _call_ollama(self, prompt, context=None):
        """Call local Ollama model"""
        start_time = time.time()
        
        try:
            # Build messages
            messages = []
            if context and context.get('system_prompt'):
                messages.append({"role": "system", "content": context['system_prompt']})
            messages.append({"role": "user", "content": prompt})
            
            # Call Ollama API
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False
            }
            
            response = requests.post(
                f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/chat",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': True,
                'model': f"ollama/{OLLAMA_MODEL}",
                'response': data['message']['content'],
                'tokens': data.get('eval_count', 0),
                'latency_ms': latency_ms
            }
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Ollama API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': f"ollama/{OLLAMA_MODEL}",
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        except Exception as e:
            logging.error(f"Unexpected error calling Ollama: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': f"ollama/{OLLAMA_MODEL}"
            }
    
    def _call_groq(self, prompt, context=None):
        """Call cloud Groq API"""
        start_time = time.time()
        
        try:
            # Build messages
            messages = []
            if context and context.get('system_prompt'):
                messages.append({"role": "system", "content": context['system_prompt']})
            messages.append({"role": "user", "content": prompt})
            
            # Call Groq API
            payload = {
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.1
            }
            
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': True,
                'model': f"groq/{GROQ_MODEL}",
                'response': data['choices'][0]['message']['content'],
                'tokens': data.get('usage', {}).get('total_tokens', 0),
                'latency_ms': latency_ms
            }
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Groq API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': f"groq/{GROQ_MODEL}",
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        except Exception as e:
            logging.error(f"Unexpected error calling Groq: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': f"groq/{GROQ_MODEL}"
            }
    
    def get_status(self):
        """Get status of available LLMs"""
        return {
            'ollama': {
                'available': self.ollama_available,
                'host': OLLAMA_HOST,
                'port': OLLAMA_PORT,
                'model': OLLAMA_MODEL
            },
            'groq': {
                'available': self.groq_available,
                'model': GROQ_MODEL
            },
            'routing': {
                'prefer_local': PREFER_LOCAL,
                'complexity_threshold': COMPLEXITY_THRESHOLD,
                'fallback_to_cloud': FALLBACK_TO_CLOUD
            }
        }


# Module-level singleton for convenience across the codebase
_GLOBAL_LLM_ROUTER = None

def get_router():
    """Return a shared LLMRouter instance (lazy init)."""
    global _GLOBAL_LLM_ROUTER
    if _GLOBAL_LLM_ROUTER is None:
        try:
            _GLOBAL_LLM_ROUTER = LLMRouter()
        except Exception as e:
            logging.error(f"Failed to initialize global LLMRouter: {e}")
            _GLOBAL_LLM_ROUTER = None
    return _GLOBAL_LLM_ROUTER
