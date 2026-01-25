"""
OpenAI provider (skeleton).
"""
import os
from typing import Any, Dict, List, Optional

from providers.base import AIProvider


class OpenAIProvider(AIProvider):
    """Provider wrapper for OpenAI models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.organization = organization
        self.project = project

        self._client = None
        self._client_style = None
        if not self.api_key:
            raise RuntimeError("OpenAI API key not provided.")
        self._init_client()

    def _init_client(self) -> None:
        try:
            from openai import OpenAI
        except Exception:
            OpenAI = None

        if OpenAI is not None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                organization=self.organization,
                project=self.project,
            )
            self._client_style = "client"
            return

        try:
            import openai
        except Exception as exc:
            raise RuntimeError(
                "OpenAI SDK not installed. Install the 'openai' package to use OpenAIProvider."
            ) from exc

        # Legacy module style
        openai.api_key = self.api_key
        if self.base_url:
            if hasattr(openai, "base_url"):
                openai.base_url = self.base_url
            elif hasattr(openai, "api_base"):
                openai.api_base = self.base_url
        if self.organization and hasattr(openai, "organization"):
            openai.organization = self.organization
        self._client = openai
        self._client_style = "module"

    def chat(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        options = kwargs.pop("options", None)
        if options:
            if "temperature" not in kwargs and "temperature" in options:
                kwargs["temperature"] = options["temperature"]
            if "max_tokens" not in kwargs and "num_predict" in options:
                kwargs["max_tokens"] = options["num_predict"]

        chat_format = kwargs.pop("format", None)
        if chat_format == "json" and self._client_style == "client":
            kwargs.setdefault("response_format", {"type": "json_object"})

        if self._client_style == "client":
            raw = self._client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )
            content = ""
            if getattr(raw, "choices", None):
                content = raw.choices[0].message.content or ""
            return {"message": {"content": content}, "raw": raw}

        raw = self._client.ChatCompletion.create(
            model=model, messages=messages, **kwargs
        )
        content = ""
        try:
            content = raw["choices"][0]["message"]["content"] or ""
        except Exception:
            content = ""
        return {"message": {"content": content}, "raw": raw}

    def embeddings(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        if self._client_style == "client":
            raw = self._client.embeddings.create(
                model=model, input=prompt, **kwargs
            )
            embedding = raw.data[0].embedding if raw.data else []
            return {"embedding": embedding, "raw": raw}

        raw = self._client.Embedding.create(
            model=model, input=prompt, **kwargs
        )
        embedding = []
        try:
            embedding = raw["data"][0]["embedding"]
        except Exception:
            embedding = []
        return {"embedding": embedding, "raw": raw}

    def get_base_url(self) -> str:
        return self.base_url or "https://api.openai.com/v1"
