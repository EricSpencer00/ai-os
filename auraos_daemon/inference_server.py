#!/usr/bin/env python3
"""
AuraOS Unified Inference Server
Serves both llava:13b (via Ollama) and microsoft/Fara-7B (via Hugging Face Transformers)
Exposes REST API on localhost:8081 compatible with GUI Agent expectations.
"""

import os
import sys
import json
import logging
import requests
import base64
import threading
import time
from pathlib import Path
from flask import Flask, request, jsonify
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/auraos_inference_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
HF_MODEL = os.environ.get("AURAOS_HF_MODEL", "microsoft/Fara-7B")
INFERENCE_BACKEND = os.environ.get("AURAOS_INFERENCE_BACKEND", "auto")  # auto, ollama, or transformers
DEVICE = os.environ.get("AURAOS_DEVICE", "auto")  # auto, cuda, cpu

# State
inference_backend = None
vision_model = None
text_model = None
model_loaded = False


class OllamaBackend:
    """Inference via local Ollama service"""
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llava:13b"):
        self.ollama_url = ollama_url
        self.model = model
        self.name = f"Ollama({model})"
        
    def is_available(self) -> bool:
        """Check if Ollama is reachable"""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                tags = resp.json().get("models", [])
                return any(m.get("name", "").startswith(self.model.split(":")[0]) for m in tags)
        except Exception as e:
            logger.warning(f"Ollama check failed: {e}")
        return False
    
    def generate(self, prompt: str, images: Optional[list] = None, **kwargs) -> str:
        """Generate text from prompt and optional images"""
        try:
            if images:
                # Vision task
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "images": images,
                    "format": "json"
                }
                url = f"{self.ollama_url}/api/generate"
            else:
                # Text-only
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
                url = f"{self.ollama_url}/api/generate"
            
            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("response", "")
            else:
                logger.error(f"Ollama error: {resp.status_code} {resp.text}")
                return ""
        except Exception as e:
            logger.error(f"Ollama generate failed: {e}")
            return ""


class TransformersBackend:
    """Inference via Hugging Face Transformers"""
    def __init__(self, model_name: str = "microsoft/Fara-7B", device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self.name = f"Transformers({model_name})"
        self.pipeline = None
        self.vision_pipeline = None
        
    def load(self):
        """Load model pipelines"""
        try:
            from transformers import pipeline
            logger.info(f"Loading text-generation pipeline for {self.model_name}...")
            self.pipeline = pipeline(
                "text-generation",
                model=self.model_name,
                device_map=self.device if self.device != "auto" else "auto",
                trust_remote_code=True,
                torch_dtype="auto",
                model_kwargs={"load_in_8bit": True} if self.device == "cuda" else {}
            )
            logger.info(f"Text model loaded: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load Transformers model: {e}")
            self.pipeline = None
    
    def is_available(self) -> bool:
        """Check if model is available"""
        return self.pipeline is not None
    
    def generate(self, prompt: str, images: Optional[list] = None, **kwargs) -> str:
        """Generate text from prompt"""
        if not self.pipeline:
            logger.warning("Pipeline not loaded")
            return ""
        
        try:
            max_new_tokens = kwargs.get("max_new_tokens", 256)
            outputs = self.pipeline(
                prompt,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9
            )
            return outputs[0]["generated_text"] if outputs else ""
        except Exception as e:
            logger.error(f"Transformers generate failed: {e}")
            return ""


def select_backend() -> Optional[Any]:
    """Auto-select or manually configure backend"""
    global inference_backend, model_loaded
    
    backend = os.environ.get("AURAOS_INFERENCE_BACKEND", "auto")
    
    if backend == "auto":
        # Try Ollama first (simpler, often already running)
        logger.info("Attempting auto-detection: trying Ollama first...")
        ollama_backend = OllamaBackend(OLLAMA_URL, "llava:13b")
        if ollama_backend.is_available():
            logger.info(f"✓ Using Ollama backend: llava:13b")
            inference_backend = ollama_backend
            model_loaded = True
            return ollama_backend
        
        # Fall back to Transformers
        logger.info("Ollama not available; trying Transformers backend...")
        tf_backend = TransformersBackend(HF_MODEL, DEVICE)
        tf_backend.load()
        if tf_backend.is_available():
            logger.info(f"✓ Using Transformers backend: {HF_MODEL}")
            inference_backend = tf_backend
            model_loaded = True
            return tf_backend
        
        logger.error("No backend available!")
        return None
    
    elif backend == "ollama":
        logger.info(f"Forcing Ollama backend...")
        ollama_backend = OllamaBackend(OLLAMA_URL, "llava:13b")
        if ollama_backend.is_available():
            inference_backend = ollama_backend
            model_loaded = True
            return ollama_backend
        logger.error("Ollama not available")
        return None
    
    elif backend == "transformers":
        logger.info(f"Forcing Transformers backend: {HF_MODEL}")
        tf_backend = TransformersBackend(HF_MODEL, DEVICE)
        tf_backend.load()
        if tf_backend.is_available():
            inference_backend = tf_backend
            model_loaded = True
            return tf_backend
        logger.error(f"Failed to load Transformers model: {HF_MODEL}")
        return None
    
    return None


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok" if model_loaded else "loading",
        "backend": inference_backend.name if inference_backend else "none",
        "model_loaded": model_loaded
    })


@app.route('/models', methods=['GET'])
def list_models():
    """List available models"""
    return jsonify({
        "backends": {
            "ollama": {
                "available": True,
                "model": "llava:13b",
                "type": "vision"
            },
            "transformers": {
                "available": True,
                "model": HF_MODEL,
                "type": "text"
            }
        },
        "current": inference_backend.name if inference_backend else "none"
    })


@app.route('/generate', methods=['POST'])
def generate():
    """
    Generate endpoint compatible with gui_agent.py expectations.
    
    POST body:
    {
        "model": "llava:13b" or "fara-7b",
        "prompt": "...",
        "images": ["base64_encoded_image_1", "base64_encoded_image_2"],
        "max_new_tokens": 256,
        "format": "json" (optional)
    }
    
    Returns:
    {
        "response": "generated text",
        "status": "success" | "error"
    }
    """
    if not inference_backend:
        return jsonify({"status": "error", "error": "No backend initialized"}), 503
    
    if not model_loaded:
        return jsonify({"status": "error", "error": "Model still loading"}), 503
    
    try:
        data = request.json or {}
        prompt = data.get("prompt", "")
        images = data.get("images", [])
        max_new_tokens = data.get("max_new_tokens", 256)
        
        if not prompt:
            return jsonify({"status": "error", "error": "Missing prompt"}), 400
        
        logger.info(f"Generate request: backend={inference_backend.name}, prompt_len={len(prompt)}, images={len(images)}")
        
        response = inference_backend.generate(
            prompt,
            images=images if images else None,
            max_new_tokens=max_new_tokens
        )
        
        return jsonify({
            "status": "success",
            "response": response
        })
    
    except Exception as e:
        logger.error(f"Generate error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/ask', methods=['POST'])
def ask():
    """
    Ask endpoint for GUI agent (mimics gui_agent.py interface).
    
    POST body:
    {
        "query": "describe what you see in the image",
        "images": ["base64_encoded_screenshot"],
        "parse_json": True/False
    }
    
    Returns:
    {
        "status": "success",
        "response": "...",
        "actions": [...] if parse_json
    }
    """
    if not inference_backend:
        return jsonify({"status": "error", "error": "No backend initialized"}), 503
    
    if not model_loaded:
        return jsonify({"status": "error", "error": "Model still loading"}), 503
    
    try:
        data = request.json or {}
        query = data.get("query", "")
        images = data.get("images", [])
        parse_json = data.get("parse_json", False)
        
        if not query:
            return jsonify({"status": "error", "error": "Missing query"}), 400
        
        logger.info(f"Ask request: query_len={len(query)}, images={len(images)}")
        
        response = inference_backend.generate(query, images=images if images else None)
        
        result = {
            "status": "success",
            "response": response
        }
        
        # Try to parse as JSON if requested
        if parse_json:
            try:
                result["actions"] = json.loads(response)
            except json.JSONDecodeError:
                result["actions"] = []
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Ask error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def startup_check():
    """Run startup checks"""
    global inference_backend, model_loaded
    
    logger.info("Starting AuraOS Inference Server...")
    logger.info(f"  OLLAMA_URL={OLLAMA_URL}")
    logger.info(f"  HF_MODEL={HF_MODEL}")
    logger.info(f"  DEVICE={DEVICE}")
    logger.info(f"  BACKEND={INFERENCE_BACKEND}")
    
    # Attempt to load backend
    backend = select_backend()
    if not backend:
        logger.warning("No inference backend available at startup. Server will attempt to serve requests but may fail.")
    else:
        logger.info(f"✓ Inference backend ready: {backend.name}")


if __name__ == '__main__':
    startup_check()
    
    logger.info("Starting Flask app on 0.0.0.0:8081...")
    try:
        app.run(host='0.0.0.0', port=8081, debug=False, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        sys.exit(0)
