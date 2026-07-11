"""Smoke tests for the new reasoning harness.

These tests stub the LLM and the tool registry so they run without
Ollama, Anthropic or any MCP server.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest

from reasoning_harness import (
    HarnessResult,
    LLMResponse,
    ReasoningHarness,
    ToolCall,
    ToolRegistry,
    ToolSemantics,
)


class ScriptedLLM:
    """Returns a pre-baked sequence of LLMResponses, one per chat() call."""

    name = "scripted"

    def __init__(self, responses: List[LLMResponse]):
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    async def chat(self, messages, tools):
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        if not self._responses:
            return LLMResponse(content="(no more scripted responses)")
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_harness_returns_final_answer_without_tool_calls():
    llm = ScriptedLLM([LLMResponse(content="All good. Nothing to do.")])
    harness = ReasoningHarness(llm=llm, tools=ToolRegistry(), system_prompt="sys")

    result = await harness.run("Check the kitchen lights")

    assert isinstance(result, HarnessResult)
    assert result.stopped_reason == "final"
    assert result.iterations == 1
    assert result.tool_calls == 0
    assert "All good" in result.answer


@pytest.mark.asyncio
async def test_harness_executes_tool_then_finalises():
    executed: List[Dict[str, Any]] = []

    async def fake_executor(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        executed.append({"name": name, "args": args})
        return {"ok": True, "state": "on", "entity_id": args.get("entity_id")}

    registry = ToolRegistry()
    registry.register(
        provider="local",
        schemas=[{
            "type": "function",
            "function": {
                "name": "get_state",
                "description": "Get an entity state",
                "parameters": {"type": "object", "properties": {"entity_id": {"type": "string"}}},
            },
        }],
        executor=fake_executor,
    )

    llm = ScriptedLLM([
        LLMResponse(
            content="Let me check the entity.",
            tool_calls=[ToolCall(id="c1", name="get_state", arguments={"entity_id": "light.kitchen"})],
        ),
        LLMResponse(content="Kitchen light is on."),
    ])
    harness = ReasoningHarness(llm=llm, tools=registry, system_prompt="sys", max_iterations=5)

    result = await harness.run("What's the state of the kitchen light?")

    assert result.stopped_reason == "final"
    assert result.iterations == 2
    assert result.tool_calls == 1
    assert executed == [{"name": "get_state", "args": {"entity_id": "light.kitchen"}}]
    assert "kitchen light is on" in result.answer.lower()
    # Trace should record the tool call and its result.
    assert len(result.trace) == 2
    assert result.trace[0].tool_calls[0]["name"] == "get_state"
    assert result.trace[0].tool_results[0]["result"]["ok"] is True


@pytest.mark.asyncio
async def test_harness_runs_parallel_tool_calls():
    call_order: List[str] = []

    async def slow_executor(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        call_order.append(f"start:{args['n']}")
        await asyncio.sleep(0.05)
        call_order.append(f"end:{args['n']}")
        return {"ok": True, "n": args["n"]}

    registry = ToolRegistry()
    registry.register(
        provider="local",
        schemas=[{
            "type": "function",
            "function": {
                "name": "noop",
                "description": "noop",
                "parameters": {"type": "object", "properties": {"n": {"type": "integer"}}},
            },
        }],
        executor=slow_executor,
        semantics=ToolSemantics(
            read_only=True,
            destructive=False,
            idempotent=True,
            parallel_safe=True,
            impact_level="read",
        ),
    )

    llm = ScriptedLLM([
        LLMResponse(
            content="Calling three in parallel.",
            tool_calls=[
                ToolCall(id="a", name="noop", arguments={"n": 1}),
                ToolCall(id="b", name="noop", arguments={"n": 2}),
                ToolCall(id="c", name="noop", arguments={"n": 3}),
            ],
        ),
        LLMResponse(content="Done."),
    ])
    harness = ReasoningHarness(llm=llm, tools=registry, system_prompt="sys")

    result = await harness.run("parallel")

    assert result.tool_calls == 3
    # All three should start before any of them ends → interleaved order.
    starts = [s for s in call_order if s.startswith("start")]
    ends = [s for s in call_order if s.startswith("end")]
    assert call_order.index(starts[-1]) < call_order.index(ends[0])


@pytest.mark.asyncio
async def test_harness_respects_max_iterations():
    async def fake_executor(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        provider="local",
        schemas=[{
            "type": "function",
            "function": {
                "name": "loop_tool",
                "description": "always called",
                "parameters": {"type": "object", "properties": {}},
            },
        }],
        executor=fake_executor,
    )

    # Always emit a tool call → harness must terminate at max_iterations.
    looping = [
        LLMResponse(
            content=f"step {i}",
            tool_calls=[ToolCall(id=str(i), name="loop_tool", arguments={})],
        )
        for i in range(20)
    ]
    llm = ScriptedLLM(looping)
    harness = ReasoningHarness(
        llm=llm, tools=registry, system_prompt="sys", max_iterations=3
    )

    result = await harness.run("loop forever")

    assert result.stopped_reason == "max_iterations"
    assert result.iterations == 3
    assert result.tool_calls == 3


@pytest.mark.asyncio
async def test_harness_caps_tool_calls_per_turn():
    seen: List[str] = []

    async def fake_executor(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        seen.append(args["i"])
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        provider="local",
        schemas=[{
            "type": "function",
            "function": {
                "name": "many",
                "description": "many",
                "parameters": {"type": "object", "properties": {"i": {"type": "string"}}},
            },
        }],
        executor=fake_executor,
    )

    llm = ScriptedLLM([
        LLMResponse(
            content="too many",
            tool_calls=[
                ToolCall(id=str(i), name="many", arguments={"i": str(i)})
                for i in range(10)
            ],
        ),
        LLMResponse(content="done"),
    ])
    harness = ReasoningHarness(
        llm=llm, tools=registry, system_prompt="sys", max_tool_calls_per_turn=3
    )

    result = await harness.run("cap me")

    assert result.tool_calls == 3
    assert seen == ["0", "1", "2"]
    assert result.stopped_reason == "final"


@pytest.mark.asyncio
async def test_harness_emits_events():
    events: List[Dict[str, Any]] = []

    async def on_event(ev: Dict[str, Any]) -> None:
        events.append(ev)

    async def fake_executor(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        provider="local",
        schemas=[{
            "type": "function",
            "function": {
                "name": "ping",
                "description": "ping",
                "parameters": {"type": "object", "properties": {}},
            },
        }],
        executor=fake_executor,
    )

    llm = ScriptedLLM([
        LLMResponse(content="thinking", tool_calls=[ToolCall(id="x", name="ping", arguments={})]),
        LLMResponse(content="done"),
    ])
    harness = ReasoningHarness(
        llm=llm, tools=registry, system_prompt="sys", on_event=on_event
    )

    await harness.run("trace please")

    types = [e["type"] for e in events]
    assert "thought" in types
    assert "tool_call" in types
