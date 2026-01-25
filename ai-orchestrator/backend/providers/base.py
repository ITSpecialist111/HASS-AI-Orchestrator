"""
Provider abstraction for AI capabilities.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AIProvider(ABC):
    """Abstract interface for AI providers."""

    @abstractmethod
    def chat(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Run a chat completion and return the raw provider response."""
        raise NotImplementedError

    @abstractmethod
    def embeddings(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate embeddings and return the raw provider response."""
        raise NotImplementedError

    def get_base_url(self) -> str:
        """Return provider base URL for diagnostics, if available."""
        return "unknown"

