"""
Local AI provider backed by Ollama.
"""
import os
from typing import Any, Dict, List, Optional

from providers.base import AIProvider


class LocalProvider(AIProvider):
    """Provider wrapper for Ollama local models."""

    def __init__(self, ollama_host: Optional[str] = None):
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        try:
            import ollama
        except Exception as exc:
            raise RuntimeError("Ollama SDK not installed. Install the 'ollama' package to use LocalProvider.") from exc
        self._ollama = ollama
        self.client = ollama.Client(host=self.ollama_host)

    def chat(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        return self.client.chat(model=model, messages=messages, **kwargs)

    def embeddings(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        if hasattr(self.client, "embeddings"):
            return self.client.embeddings(model=model, prompt=prompt, **kwargs)
        return self._ollama.embeddings(model=model, prompt=prompt, **kwargs)

    def get_base_url(self) -> str:
        if hasattr(self.client, "_client"):
            return getattr(self.client._client, "base_url", self.ollama_host)
        return self.ollama_host
