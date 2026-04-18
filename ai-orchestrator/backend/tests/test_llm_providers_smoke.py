"""
Tests for the Phase 9 multi-provider LLM façade.

These are isolated, dependency-free tests: we never hit a real OpenAI,
GitHub, Foundry, or Ollama endpoint. Instead we monkeypatch the imports
inside the provider classes so we exercise the routing/credential logic.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import llm_providers  # noqa: E402


# ---------------------------------------------------------------------------
# resolve_provider_name
# ---------------------------------------------------------------------------
def test_resolve_provider_name_defaults_to_ollama(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert llm_providers.resolve_provider_name() == "ollama"


def test_resolve_provider_name_reads_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert llm_providers.resolve_provider_name() == "openai"


def test_resolve_provider_name_explicit_wins(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert llm_providers.resolve_provider_name("github") == "github"


def test_resolve_provider_name_unknown_falls_back(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert llm_providers.resolve_provider_name("not-a-provider") == "ollama"


# ---------------------------------------------------------------------------
# make_chat_provider — fall-back behaviour
# ---------------------------------------------------------------------------
def test_make_chat_provider_default_returns_ollama(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    provider = llm_providers.make_chat_provider()
    assert provider.name == "ollama"


def test_make_chat_provider_openai_without_key_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = llm_providers.make_chat_provider()
    # Missing credentials should not crash; we must fall back to ollama.
    assert provider.name == "ollama"


def test_make_chat_provider_github_without_token_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "github")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    provider = llm_providers.make_chat_provider()
    assert provider.name == "ollama"


def test_make_chat_provider_foundry_without_endpoint_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "foundry")
    monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)
    monkeypatch.delenv("FOUNDRY_API_KEY", raising=False)
    monkeypatch.delenv("FOUNDRY_BEARER_TOKEN", raising=False)
    provider = llm_providers.make_chat_provider()
    assert provider.name == "ollama"


# ---------------------------------------------------------------------------
# make_chat_provider — successful instantiation with stubbed SDKs
# ---------------------------------------------------------------------------
def _install_fake_openai_module(monkeypatch, captured: dict) -> None:
    """Install a fake ``openai`` module so we don't need the real SDK."""
    fake_module = types.ModuleType("openai")

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    captured["create_kwargs"] = kwargs
                    msg = MagicMock()
                    msg.content = "hello from openai"
                    choice = MagicMock()
                    choice.message = msg
                    resp = MagicMock()
                    resp.choices = [choice]
                    return resp

    fake_module.OpenAI = _FakeOpenAI
    fake_module.AsyncOpenAI = _FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_module)


def test_openai_provider_chat_uses_sdk(monkeypatch):
    captured: dict = {}
    _install_fake_openai_module(monkeypatch, captured)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    provider = llm_providers.make_chat_provider()
    assert provider.name == "openai"
    out = provider.chat("gpt-4o-mini", [{"role": "user", "content": "ping"}], max_tokens=42)
    assert out == "hello from openai"
    # Verify the SDK was constructed with our key + the default base_url.
    assert captured["kwargs"]["api_key"] == "sk-test-123"
    assert captured["kwargs"]["base_url"] == "https://api.openai.com/v1"
    # Verify the chat call propagated model + max_tokens.
    assert captured["create_kwargs"]["model"] == "gpt-4o-mini"
    assert captured["create_kwargs"]["max_tokens"] == 42


def test_github_provider_uses_models_base_url(monkeypatch):
    captured: dict = {}
    _install_fake_openai_module(monkeypatch, captured)
    monkeypatch.setenv("LLM_PROVIDER", "github")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test-456")
    monkeypatch.delenv("GITHUB_MODELS_BASE_URL", raising=False)

    provider = llm_providers.make_chat_provider()
    assert provider.name == "github"
    provider.chat("gpt-4o-mini", [{"role": "user", "content": "hi"}])
    assert captured["kwargs"]["api_key"] == "ghp_test-456"
    assert captured["kwargs"]["base_url"] == "https://models.github.ai/inference"


def test_foundry_provider_uses_api_key_header(monkeypatch):
    captured: dict = {}

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "hello from foundry"}}]}

    class _FakeClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return _FakeResponse()

    fake_httpx = types.ModuleType("httpx")
    fake_httpx.Client = _FakeClient
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    monkeypatch.setenv("LLM_PROVIDER", "foundry")
    monkeypatch.setenv("FOUNDRY_ENDPOINT", "https://my-project.cognitiveservices.azure.com")
    monkeypatch.setenv("FOUNDRY_API_KEY", "foundry-key-789")
    monkeypatch.delenv("FOUNDRY_BEARER_TOKEN", raising=False)

    provider = llm_providers.make_chat_provider()
    assert provider.name == "foundry"
    out = provider.chat("gpt-4o", [{"role": "user", "content": "hi"}])
    assert out == "hello from foundry"
    assert captured["headers"]["api-key"] == "foundry-key-789"
    # Model name is folded into the URL for the deployment-style path.
    assert "/openai/deployments/gpt-4o/chat/completions" in captured["url"]


# ---------------------------------------------------------------------------
# make_tool_backend — also falls back gracefully
# ---------------------------------------------------------------------------
def test_make_tool_backend_default_is_ollama(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    backend = llm_providers.make_tool_backend(model="qwen2.5:7b-instruct")
    assert backend.name == "ollama"


def test_make_tool_backend_openai_without_key_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    backend = llm_providers.make_tool_backend(model="gpt-4o-mini")
    assert backend.name == "ollama"


def test_make_tool_backend_github_without_token_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "github")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    backend = llm_providers.make_tool_backend(model="gpt-4o-mini")
    assert backend.name == "ollama"


def test_make_tool_backend_foundry_without_endpoint_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "foundry")
    monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)
    monkeypatch.delenv("FOUNDRY_API_KEY", raising=False)
    monkeypatch.delenv("FOUNDRY_BEARER_TOKEN", raising=False)
    backend = llm_providers.make_tool_backend(model="gpt-4o-mini")
    assert backend.name == "ollama"
