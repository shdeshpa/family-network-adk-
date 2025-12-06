"""Unified LLM client - Llama3 for best results."""

import json
from typing import Optional
from openai import OpenAI

from src.config import settings


class LLMClient:
    """Unified LLM client - Ollama with Llama3."""
    
    PROVIDERS = {
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "model": "llama3:latest",  # Best for JSON extraction
            "api_key": "ollama"
        },
        "ollama-small": {
            "base_url": "http://localhost:11434/v1",
            "model": "llama3.2:latest",
            "api_key": "ollama"
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "model": "llama-3.1-8b-instant",
            "api_key": None
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "api_key": None
        }
    }
    
    def __init__(self, provider: str = "ollama", model: Optional[str] = None):
        self.provider = provider
        config = self.PROVIDERS.get(provider, self.PROVIDERS["ollama"])
        
        api_key = config["api_key"]
        if provider == "groq" and hasattr(settings, 'groq_api_key'):
            api_key = settings.groq_api_key
        elif provider == "openai":
            api_key = settings.openai_api_key
        
        self.client = OpenAI(
            base_url=config["base_url"],
            api_key=api_key or "not-needed"
        )
        self.model = model or config["model"]
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> dict:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {
                "success": True,
                "text": response.choices[0].message.content,
                "provider": self.provider,
                "model": self.model
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def extract_json(self, prompt: str, system: Optional[str] = None) -> dict:
        json_prompt = f"{prompt}\n\nReturn valid JSON only. No markdown. No explanation."
        
        result = self.generate(json_prompt, system=system)
        
        if not result["success"]:
            return result
        
        try:
            text = result["text"].strip()
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                parts = text.split("```")
                if len(parts) >= 2:
                    text = parts[1]
            
            result["parsed"] = json.loads(text.strip())
            return result
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON parse error: {str(e)}",
                "raw_text": result["text"]
            }