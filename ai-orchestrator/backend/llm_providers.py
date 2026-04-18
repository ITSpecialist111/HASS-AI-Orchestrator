"""
Multi-provider LLM façade.

The orchestrator started life as an Ollama-only project (local, private,
free). Phase 9 widens that to four providers without forcing any of the
existing call sites to change much:

* ``ollama``   — local Ollama daemon (default, unchanged behaviour).
* ``openai``   — OpenAI Chat Completions (api.openai.com or any
                 OpenAI-compatible endpoint via ``OPENAI_BASE_URL``).
* ``github``   — GitHub Models (https://models.github.ai/inference,
                 OpenAI-compatible, auth = ``Bearer $GITHUB_TOKEN``).
* ``foundry``  — Microsoft Foundry hosted agent / model endpoint
                 (Azure AI Inference or Foundry Agents REST). Uses
                 either an API key or a bearer token.

There are two layers:

1. :class:`ChatProvider` — the simple "give me a string back" surface
   used by :class:`BaseAgent._call_llm` and the orchestrator's planning
   loop. It does **not** require tool calling; it just returns text.
2. The tool-calling backends used by :mod:`reasoning_harness` for the
   deep-reasoning agent live in that module so they can share the
   :class:`LLMBackend` Protocol; this module's
   :func:`make_tool_backend` is a thin factory over them.

Selection precedence (per call site, but typically global):
    explicit kwarg > ``LLM_PROVIDER`` env > add-on option > ``ollama``.

All providers degrade gracefully: if their SDK is missing or their
credentials are not configured, ``make_chat_provider`` falls back to
Ollama and logs a warning rather than raising at import time.
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Common types
# ---------------------------------------------------------------------------
PROVIDER_OLLAMA = "ollama"
PROVIDER_OPENAI = "openai"
PROVIDER_GITHUB = "github"
PROVIDER_FOUNDRY = "foundry"

KNOWN_PROVIDERS = {PROVIDER_OLLAMA, PROVIDER_OPENAI, PROVIDER_GITHUB, PROVIDER_FOUNDRY}


def _strip(value: Optional[str]) -> str:
    return (value or "").strip()


def resolve_provider_name(explicit: Optional[str] = None) -> str:
    """Pick the provider name (no instantiation, no I/O)."""
    candidate = _strip(explicit) or _strip(os.getenv("LLM_PROVIDER")) or PROVIDER_OLLAMA
    candidate = candidate.lower()
    if candidate not in KNOWN_PROVIDERS:
        logger.warning("Unknown LLM_PROVIDER=%r, falling back to %s", candidate, PROVIDER_OLLAMA)
        return PROVIDER_OLLAMA
    return candidate


# ---------------------------------------------------------------------------
# ChatProvider — simple text-in/text-out surface
# ---------------------------------------------------------------------------
class ChatProvider(ABC):
    """Minimal sync chat surface.

    Returns the assistant's text content; tool-calling, streaming and
    structured outputs are out of scope here (the deep-reasoning agent
    has its own richer harness).
    """

    name: str = "abstract"

    @abstractmethod
    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        ...


class _OllamaChatProvider(ChatProvider):
    name = PROVIDER_OLLAMA

    def __init__(self, host: Optional[str] = None) -> None:
        import ollama

        self._host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._client = ollama.Client(host=self._host)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        opts: Dict[str, Any] = {
            "temperature": temperature,
            "num_predict": max_tokens,
            "think": False,
        }
        if extra_options:
            opts.update(extra_options)
        resp = self._client.chat(model=model, messages=messages, options=opts, stream=False)
        msg = resp["message"] if isinstance(resp, dict) else getattr(resp, "message", {})
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        return (content or "").strip()


class _OpenAICompatibleChatProvider(ChatProvider):
    """Shared implementation for OpenAI and GitHub Models (both speak the
    OpenAI Chat Completions wire format).
    """

    def __init__(
        self,
        *,
        name: str,
        api_key: str,
        base_url: str,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        if not api_key:
            raise RuntimeError(f"{name}: api_key is required")
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover - surfaced at startup
            raise RuntimeError(
                f"{name}: the 'openai' package is required (pip install openai)"
            ) from exc
        self.name = name
        self._client = OpenAI(api_key=api_key, base_url=base_url, default_headers=default_headers or None)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra_options:
            kwargs.update(extra_options)
        resp = self._client.chat.completions.create(**kwargs)
        if not resp.choices:
            return ""
        return (resp.choices[0].message.content or "").strip()


class _FoundryChatProvider(ChatProvider):
    """Microsoft Foundry / Azure AI Inference chat provider.

    Uses Azure AI Inference's OpenAI-compatible chat completions surface
    (the same shape used by Foundry-deployed models). Auth can be either
    an API key (``api-key`` header) or an Entra bearer token.
    """

    name = PROVIDER_FOUNDRY

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        api_version: Optional[str] = None,
    ) -> None:
        if not endpoint:
            raise RuntimeError("foundry: endpoint URL is required")
        if not api_key and not bearer_token:
            raise RuntimeError("foundry: either api_key or bearer_token is required")
        try:
            import httpx  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("foundry: 'httpx' is required") from exc
        self._endpoint = endpoint.rstrip("/")
        self._api_version = api_version or os.getenv("FOUNDRY_API_VERSION", "2024-08-01-preview")
        self._headers: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["api-key"] = api_key
        if bearer_token:
            self._headers["Authorization"] = f"Bearer {bearer_token}"
        self._httpx = httpx

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        # Foundry "model deployments" embed the deployment name in the
        # path (Azure-OpenAI style); generic Foundry/Inference endpoints
        # accept ``model`` in the body. Support both: if the endpoint
        # already targets a specific deployment, callers can pass an
        # empty model name.
        if "/deployments/" in self._endpoint:
            url = f"{self._endpoint}/chat/completions?api-version={self._api_version}"
        elif model:
            url = f"{self._endpoint}/openai/deployments/{model}/chat/completions?api-version={self._api_version}"
        else:
            url = f"{self._endpoint}/chat/completions?api-version={self._api_version}"

        body: Dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if model and "/deployments/" not in url:
            body["model"] = model
        if extra_options:
            body.update(extra_options)

        with self._httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=self._headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return (message.get("content") or "").strip()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def make_chat_provider(
    provider: Optional[str] = None,
    *,
    ollama_host: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    github_token: Optional[str] = None,
    foundry_endpoint: Optional[str] = None,
    foundry_api_key: Optional[str] = None,
    foundry_bearer_token: Optional[str] = None,
    foundry_api_version: Optional[str] = None,
) -> ChatProvider:
    """Resolve a :class:`ChatProvider`.

    On any configuration / SDK error we fall back to Ollama and log a
    warning so the add-on still boots. This keeps the project's
    "private by default" promise: misconfigured remote credentials never
    silently leak conversations to a cloud provider.
    """
    name = resolve_provider_name(provider)

    try:
        if name == PROVIDER_OPENAI:
            key = _strip(openai_api_key) or _strip(os.getenv("OPENAI_API_KEY"))
            base = _strip(openai_base_url) or _strip(os.getenv("OPENAI_BASE_URL")) or "https://api.openai.com/v1"
            return _OpenAICompatibleChatProvider(name=PROVIDER_OPENAI, api_key=key, base_url=base)

        if name == PROVIDER_GITHUB:
            token = _strip(github_token) or _strip(os.getenv("GITHUB_TOKEN")) or _strip(os.getenv("GITHUB_MODELS_TOKEN"))
            base = _strip(os.getenv("GITHUB_MODELS_BASE_URL")) or "https://models.github.ai/inference"
            return _OpenAICompatibleChatProvider(name=PROVIDER_GITHUB, api_key=token, base_url=base)

        if name == PROVIDER_FOUNDRY:
            endpoint = _strip(foundry_endpoint) or _strip(os.getenv("FOUNDRY_ENDPOINT"))
            key = _strip(foundry_api_key) or _strip(os.getenv("FOUNDRY_API_KEY"))
            bearer = _strip(foundry_bearer_token) or _strip(os.getenv("FOUNDRY_BEARER_TOKEN"))
            return _FoundryChatProvider(
                endpoint=endpoint,
                api_key=key or None,
                bearer_token=bearer or None,
                api_version=foundry_api_version or os.getenv("FOUNDRY_API_VERSION"),
            )
    except Exception as exc:
        logger.warning("LLM provider %s unavailable (%s); falling back to ollama", name, exc)

    return _OllamaChatProvider(host=ollama_host)


# ---------------------------------------------------------------------------
# Tool backend factory (delegates to reasoning_harness)
# ---------------------------------------------------------------------------
def make_tool_backend(
    provider: Optional[str] = None,
    *,
    model: str,
    ollama_host: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    github_token: Optional[str] = None,
    foundry_endpoint: Optional[str] = None,
    foundry_api_key: Optional[str] = None,
    foundry_bearer_token: Optional[str] = None,
    foundry_agent_id: Optional[str] = None,
):
    """Resolve the tool-calling backend for the deep-reasoning harness.

    Returns an instance of :class:`reasoning_harness.LLMBackend`. Falls
    back to Ollama on misconfiguration.
    """
    # Local import — reasoning_harness imports nothing from us, so this
    # avoids a circular import at module load.
    from reasoning_harness import (
        FoundryAgentBackend,
        GitHubModelsBackend,
        OllamaToolBackend,
        OpenAIToolBackend,
    )

    name = resolve_provider_name(provider)

    try:
        if name == PROVIDER_OPENAI:
            key = _strip(openai_api_key) or _strip(os.getenv("OPENAI_API_KEY"))
            base = _strip(openai_base_url) or _strip(os.getenv("OPENAI_BASE_URL")) or "https://api.openai.com/v1"
            return OpenAIToolBackend(model=model, api_key=key, base_url=base, name=PROVIDER_OPENAI)

        if name == PROVIDER_GITHUB:
            token = _strip(github_token) or _strip(os.getenv("GITHUB_TOKEN")) or _strip(os.getenv("GITHUB_MODELS_TOKEN"))
            base = _strip(os.getenv("GITHUB_MODELS_BASE_URL")) or "https://models.github.ai/inference"
            return GitHubModelsBackend(model=model, token=token, base_url=base)

        if name == PROVIDER_FOUNDRY:
            endpoint = _strip(foundry_endpoint) or _strip(os.getenv("FOUNDRY_ENDPOINT"))
            key = _strip(foundry_api_key) or _strip(os.getenv("FOUNDRY_API_KEY"))
            bearer = _strip(foundry_bearer_token) or _strip(os.getenv("FOUNDRY_BEARER_TOKEN"))
            agent_id = _strip(foundry_agent_id) or _strip(os.getenv("FOUNDRY_AGENT_ID"))
            return FoundryAgentBackend(
                endpoint=endpoint,
                api_key=key or None,
                bearer_token=bearer or None,
                model=model,
                agent_id=agent_id or None,
            )
    except Exception as exc:
        logger.warning("Tool backend %s unavailable (%s); falling back to ollama", name, exc)

    return OllamaToolBackend(model=model, host=ollama_host)
