"""Contracts for Gemma reasoning profiles and deterministic run budgets."""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from reasoning_harness import (
    LLMResponse,
    OllamaToolBackend,
    REASONING_PROFILES,
    ReasoningHarness,
    ToolCall,
    ToolRegistry,
    ToolSemantics,
    resolve_reasoning_profile,
)


def test_reasoning_profiles_are_stable_and_balanced_by_default():
    assert tuple(REASONING_PROFILES) == ("rapid", "balanced", "deep")
    assert resolve_reasoning_profile(None).name == "balanced"
    assert resolve_reasoning_profile(" DEEP ").name == "deep"
    assert REASONING_PROFILES["rapid"].think is False
    assert REASONING_PROFILES["balanced"].think is True
    assert REASONING_PROFILES["deep"].think is True

    for profile in REASONING_PROFILES.values():
        assert profile.temperature == 1.0
        assert profile.top_p == 0.95
        assert profile.top_k == 64

    with pytest.raises(ValueError, match="rapid\\|balanced\\|deep"):
        resolve_reasoning_profile("unbounded")


@pytest.mark.asyncio
async def test_ollama_profile_uses_documented_think_parameter(monkeypatch):
    calls: List[Dict[str, Any]] = []

    class FakeClient:
        async def chat(self, **kwargs):
            calls.append(kwargs)
            return {
                "message": {
                    "content": "Grounded answer",
                    "thinking": "private model reasoning that must not enter history",
                    "tool_calls": [],
                },
                "prompt_eval_count": 12,
                "eval_count": 8,
                "done_reason": "stop",
            }

    monkeypatch.setattr("ollama.AsyncClient", lambda host: FakeClient())
    backend = OllamaToolBackend(
        model="gemma4:e4b",
        host="http://ollama.test:11434",
    )

    rapid = await backend.chat([{"role": "user", "content": "status"}], [], profile="rapid")
    deep = await backend.chat([{"role": "user", "content": "analyse"}], [], profile="deep")

    assert calls[0]["model"] == "gemma4:e4b"
    assert calls[0]["think"] is False
    assert calls[1]["think"] is True
    assert "think" not in calls[0]["options"]
    assert calls[1]["options"] == {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 64,
        "num_predict": 4096,
    }
    assert rapid.content == "Grounded answer"
    assert deep.content == "Grounded answer"
    assert "private model reasoning" not in deep.content
    assert deep.usage == {"input_tokens": 12, "output_tokens": 8}
    assert deep.stop_reason == "stop"


@pytest.mark.asyncio
async def test_rapid_profile_is_forwarded_and_caps_harness_iterations():
    seen_profiles: List[str] = []

    class ProfileAwareLLM:
        name = "profile-aware"

        def __init__(self):
            self.index = 0

        async def chat(self, messages, tools, *, continuation=None, profile=None):
            seen_profiles.append(profile)
            self.index += 1
            return LLMResponse(
                content=f"step {self.index}",
                tool_calls=[
                    ToolCall(
                        id=str(self.index),
                        name="observe",
                        arguments={"sequence": self.index},
                    )
                ],
            )

    async def observe(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "sequence": arguments["sequence"]}

    registry = ToolRegistry()
    registry.register(
        provider="test",
        schemas=[{
            "type": "function",
            "function": {
                "name": "observe",
                "description": "Read a unique observation",
                "parameters": {
                    "type": "object",
                    "properties": {"sequence": {"type": "integer"}},
                    "required": ["sequence"],
                },
            },
        }],
        executor=observe,
        semantics=ToolSemantics(
            read_only=True,
            destructive=False,
            idempotent=True,
            parallel_safe=True,
            impact_level="read",
        ),
    )
    harness = ReasoningHarness(
        llm=ProfileAwareLLM(),
        tools=registry,
        system_prompt="system",
        max_iterations=20,
        max_tool_calls_per_turn=8,
        max_total_tool_calls=100,
        max_run_seconds=600,
        llm_timeout_seconds=300,
    )

    result = await harness.run("keep observing", profile="rapid")

    assert result.stopped_reason == "max_iterations"
    assert result.profile == "rapid"
    assert result.iterations == 6
    assert result.tool_calls == 6
    assert seen_profiles == ["rapid"] * 6


@pytest.mark.asyncio
async def test_profile_never_changes_deterministic_mutation_order():
    order: List[int] = []

    class OneTurnLLM:
        name = "one-turn"

        def __init__(self):
            self.called = False

        async def chat(self, messages, tools, *, profile=None):
            if self.called:
                return LLMResponse(content="done")
            self.called = True
            return LLMResponse(
                content="apply in order",
                tool_calls=[
                    ToolCall(id="1", name="mutate", arguments={"value": 1}),
                    ToolCall(id="2", name="mutate", arguments={"value": 2}),
                ],
            )

    async def mutate(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        order.append(arguments["value"])
        return {"ok": True, "value": arguments["value"]}

    registry = ToolRegistry()
    registry.register(
        provider="test",
        schemas=[{
            "type": "function",
            "function": {
                "name": "mutate",
                "description": "Ordered mutation",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                    "required": ["value"],
                },
            },
        }],
        executor=mutate,
        semantics=ToolSemantics(
            read_only=False,
            destructive=True,
            idempotent=False,
            parallel_safe=False,
            impact_level="high",
        ),
    )
    harness = ReasoningHarness(
        llm=OneTurnLLM(),
        tools=registry,
        system_prompt="system",
        max_tool_calls_per_turn=5,
    )

    result = await harness.run("ordered change", profile="deep")

    assert result.stopped_reason == "final"
    assert order == [1, 2]
