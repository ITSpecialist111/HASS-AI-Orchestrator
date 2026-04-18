"""Smoke tests for Phase 8 / Milestone G (SSE streaming + MCP prompts)."""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

# chromadb fails to import on Python 3.14 + pydantic 2.x (BaseSettings moved).
# Pre-mock it so importing main (which pulls in rag_manager) succeeds.
_mock_chromadb = MagicMock()
_mock_chromadb.PersistentClient = MagicMock
_mock_chromadb.config = MagicMock()
_mock_chromadb.config.Settings = MagicMock
sys.modules.setdefault("chromadb", _mock_chromadb)
sys.modules.setdefault("chromadb.config", _mock_chromadb.config)


# ---------------------------------------------------------------------------
# Streaming via DeepReasoningAgent.run_streaming
# ---------------------------------------------------------------------------
@pytest.fixture
def agent_factory(monkeypatch, tmp_path):
    """Build a DeepReasoningAgent with a fully-scripted LLM."""
    import agents.deep_reasoning_agent as dra
    from reasoning_harness import LLMResponse

    fired: List[Dict[str, Any]] = []

    class _StubLocalMCP:
        tools: Dict[str, Any] = {}
        async def execute_tool(self, **kw):
            fired.append({"name": kw["tool_name"], "args": kw["parameters"]})
            return {"ok": True, "executed": True}

    def _factory(scripted_responses: List[Any], *, default_mode="execute"):
        idx = {"i": 0}

        class _StubLLM:
            name = "stub"
            async def chat(self, messages, tools):
                if idx["i"] >= len(scripted_responses):
                    return LLMResponse(content="(out of script) done")
                r = scripted_responses[idx["i"]]
                idx["i"] += 1
                return r

        monkeypatch.setattr(dra, "OllamaToolBackend", lambda **kw: _StubLLM())

        agent = dra.DeepReasoningAgent(
            local_mcp=_StubLocalMCP(),
            external_mcp=None,
            ollama_model="ignored",
            default_mode=default_mode,
        )
        # Register a few tools so the LLM has something to "call".
        agent.registry._routes.clear()
        agent.registry.register(
            provider="local",
            schemas=[
                {"type": "function", "function": {"name": "turn_on_light", "parameters": {}}},
                {"type": "function", "function": {"name": "list_entities", "parameters": {}}},
            ],
            executor=lambda name, args: agent._local_executor(name, args),
        )
        return agent, fired

    return _factory


@pytest.mark.asyncio
async def test_run_streaming_emits_start_thought_and_final(agent_factory):
    from reasoning_harness import LLMResponse

    agent, _ = agent_factory([
        LLMResponse(content="All clear, nothing to do."),
    ])

    events = []
    async for ev in agent.run_streaming("status check"):
        events.append(ev)

    types = [e["type"] for e in events]
    # Order: start → thought → recall → plan → final
    assert types[0] == "start"
    assert "thought" in types
    assert types[-1] == "final"
    start = events[0]
    assert start["goal"] == "status check"
    assert "run_id" in start
    final = events[-1]["data"]
    assert "All clear" in final["answer"]
    assert final["iterations"] == 1


@pytest.mark.asyncio
async def test_run_streaming_emits_tool_call_event(agent_factory):
    from reasoning_harness import LLMResponse, ToolCall

    agent, fired = agent_factory([
        LLMResponse(
            content="checking",
            tool_calls=[ToolCall(id="c1", name="list_entities", arguments={})],
        ),
        LLMResponse(content="found 12 entities"),
    ])

    events = []
    async for ev in agent.run_streaming("inventory"):
        events.append(ev)

    types = [e["type"] for e in events]
    assert "tool_call" in types
    tc = next(e for e in events if e["type"] == "tool_call")
    assert tc["name"] == "list_entities"
    # In execute mode the tool actually fires.
    assert fired and fired[0]["name"] == "list_entities"


@pytest.mark.asyncio
async def test_run_streaming_restores_original_event_hook(agent_factory):
    from reasoning_harness import LLMResponse

    agent, _ = agent_factory([LLMResponse(content="done")])

    sentinel = object()

    async def original_hook(ev):  # pragma: no cover - never called in this test
        pass

    # Stash a marker hook; run_streaming must restore it after iteration.
    agent.harness.on_event = original_hook

    async for _ in agent.run_streaming("noop"):
        pass

    assert agent.harness.on_event is original_hook


@pytest.mark.asyncio
async def test_run_streaming_in_plan_mode_emits_plan(agent_factory):
    from reasoning_harness import LLMResponse, ToolCall

    agent, fired = agent_factory([
        LLMResponse(
            content="planning",
            tool_calls=[ToolCall(id="c1", name="turn_on_light",
                                 arguments={"entity_id": "light.kitchen"})],
        ),
        LLMResponse(content="plan complete"),
    ], default_mode="plan")

    events = []
    async for ev in agent.run_streaming("plan kitchen light", mode="plan"):
        events.append(ev)

    # In plan mode the real executor must NOT fire.
    assert fired == []
    plan_event = next(e for e in events if e["type"] == "plan")
    assert plan_event["plan"] is not None
    assert plan_event["plan"]["mutating_count"] == 1


@pytest.mark.asyncio
async def test_run_streaming_handles_inner_error(agent_factory, monkeypatch):
    """A blowing-up LLM should surface as an ``error`` event, not a raise."""
    import agents.deep_reasoning_agent as dra

    class _Boom:
        name = "boom"
        async def chat(self, messages, tools):
            raise RuntimeError("kaboom")

    monkeypatch.setattr(dra, "OllamaToolBackend", lambda **kw: _Boom())
    agent, _ = agent_factory([])  # responses ignored, replaced by Boom
    # Replace harness LLM directly because factory already created it.
    agent.harness.llm = _Boom()

    events = []
    async for ev in agent.run_streaming("fail"):
        events.append(ev)

    # The harness catches LLM errors and returns a final answer rather
    # than raising, so we should still see a `final` event with the
    # llm_error stop reason. No `error` event is expected in that path.
    final = events[-1]
    assert final["type"] == "final"
    assert final["data"]["stopped_reason"] == "llm_error"


# ---------------------------------------------------------------------------
# SSE endpoint shape
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sse_endpoint_streams_events(agent_factory):
    """Exercise main.reasoning_stream with a stub agent."""
    from reasoning_harness import LLMResponse
    import main as backend_main

    agent, _ = agent_factory([LLMResponse(content="hi")])
    backend_main.deep_reasoner = agent

    from main import reasoning_stream, ReasoningRequest

    response = await reasoning_stream(ReasoningRequest(goal="ping"))
    body_chunks: List[str] = []
    async for chunk in response.body_iterator:
        body_chunks.append(chunk if isinstance(chunk, str) else chunk.decode())

    body = "".join(body_chunks)
    assert "event: start" in body
    assert "event: final" in body
    assert "event: done" in body
    # Each event is followed by a JSON data line.
    final_line = next(
        line for line in body.splitlines()
        if line.startswith("data:") and '"answer"' in line
    )
    payload = json.loads(final_line[len("data:"):].strip())
    assert payload["data"]["answer"] == "hi"


@pytest.mark.asyncio
async def test_sse_endpoint_rejects_bad_mode():
    from fastapi import HTTPException
    from main import reasoning_stream, ReasoningRequest
    import main as backend_main

    # Even without an agent, validation should hit first if mode invalid.
    backend_main.deep_reasoner = object()  # any truthy stub
    with pytest.raises(HTTPException) as exc:
        await reasoning_stream(ReasoningRequest(goal="x", mode="bogus"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_sse_endpoint_503_when_agent_missing():
    from fastapi import HTTPException
    from main import reasoning_stream, ReasoningRequest
    import main as backend_main

    backend_main.deep_reasoner = None
    with pytest.raises(HTTPException) as exc:
        await reasoning_stream(ReasoningRequest(goal="x"))
    assert exc.value.status_code == 503


# ---------------------------------------------------------------------------
# MCP prompt catalog
# ---------------------------------------------------------------------------
class _StubExternalMCP:
    """Just enough surface for the prompt endpoints."""

    def __init__(self, *, prompts=None, get_prompt_result=None, connected=True):
        self.connected = connected
        self.name = "stub_mcp"
        self.tools = {}
        self.resources = []
        self._prompts = prompts or []
        self._get_prompt_result = get_prompt_result

    def prompt_specs(self):
        return list(self._prompts)

    async def get_prompt(self, name, arguments):
        if self._get_prompt_result is None:
            return {"ok": False, "error": f"unknown_prompt:{name}"}
        return self._get_prompt_result


@pytest.mark.asyncio
async def test_prompts_endpoint_returns_empty_when_disconnected():
    import main as backend_main
    from main import reasoning_prompts

    backend_main.external_mcp = None
    backend_main.native_prompts = None
    out = await reasoning_prompts()
    assert out["prompts"] == []
    assert out["connected"] is False
    assert out.get("external_connected") is False
    assert out.get("native_count") == 0


@pytest.mark.asyncio
async def test_prompts_endpoint_lists_discovered_prompts():
    import main as backend_main
    from main import reasoning_prompts

    backend_main.native_prompts = None
    stub = _StubExternalMCP(prompts=[
        {"name": "security_audit", "description": "audit", "arguments": []},
        {"name": "energy_optimizer", "description": "save", "arguments": []},
    ])
    backend_main.external_mcp = stub

    out = await reasoning_prompts()
    assert out["connected"] is True
    assert {p["name"] for p in out["prompts"]} == {"security_audit", "energy_optimizer"}


@pytest.mark.asyncio
async def test_prompt_render_returns_rendered_text():
    import main as backend_main
    from main import reasoning_prompt_render, PromptRunRequest

    backend_main.native_prompts = None
    backend_main.external_mcp = _StubExternalMCP(
        prompts=[{"name": "p1", "description": "", "arguments": []}],
        get_prompt_result={"ok": True, "name": "p1", "description": "",
                           "text": "Rendered goal", "messages": []},
    )
    out = await reasoning_prompt_render("p1", PromptRunRequest())
    assert out["text"] == "Rendered goal"


@pytest.mark.asyncio
async def test_prompt_render_400_on_missing_prompt():
    from fastapi import HTTPException
    import main as backend_main
    from main import reasoning_prompt_render, PromptRunRequest

    backend_main.native_prompts = None
    backend_main.external_mcp = _StubExternalMCP()
    with pytest.raises(HTTPException) as exc:
        await reasoning_prompt_render("nope", PromptRunRequest())
    # Unknown prompt now returns 404 (semantically clearer than 400).
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_prompt_render_404_when_no_sources_have_prompt():
    from fastapi import HTTPException
    import main as backend_main
    from main import reasoning_prompt_render, PromptRunRequest

    backend_main.native_prompts = None
    backend_main.external_mcp = None
    with pytest.raises(HTTPException) as exc:
        await reasoning_prompt_render("x", PromptRunRequest())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_prompt_run_invokes_reasoner_with_rendered_goal(agent_factory):
    from reasoning_harness import LLMResponse
    import main as backend_main
    from main import reasoning_prompt_run, PromptRunRequest

    agent, _ = agent_factory([LLMResponse(content="audit complete")])
    backend_main.deep_reasoner = agent
    backend_main.native_prompts = None
    backend_main.external_mcp = _StubExternalMCP(
        prompts=[{"name": "security_audit", "description": "", "arguments": []}],
        get_prompt_result={"ok": True, "name": "security_audit",
                           "text": "Audit the home security posture.",
                           "messages": []},
    )

    out = await reasoning_prompt_run(
        "security_audit",
        PromptRunRequest(arguments={"depth": "quick"}, mode="execute"),
    )
    assert out["prompt"] == "security_audit"
    assert out["answer"] == "audit complete"
    assert out["iterations"] == 1


@pytest.mark.asyncio
async def test_prompt_run_400_when_rendered_text_empty(agent_factory):
    from fastapi import HTTPException
    import main as backend_main
    from main import reasoning_prompt_run, PromptRunRequest

    agent, _ = agent_factory([])
    backend_main.deep_reasoner = agent
    backend_main.native_prompts = None
    backend_main.external_mcp = _StubExternalMCP(
        prompts=[{"name": "blank", "description": "", "arguments": []}],
        get_prompt_result={"ok": True, "name": "blank", "text": "",
                           "messages": []},
    )
    with pytest.raises(HTTPException) as exc:
        await reasoning_prompt_run("blank", PromptRunRequest())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_prompt_run_streams_when_stream_true(agent_factory):
    from reasoning_harness import LLMResponse
    import main as backend_main
    from main import reasoning_prompt_run, PromptRunRequest

    agent, _ = agent_factory([LLMResponse(content="streaming hello")])
    backend_main.deep_reasoner = agent
    backend_main.native_prompts = None
    backend_main.external_mcp = _StubExternalMCP(
        prompts=[{"name": "p", "description": "", "arguments": []}],
        get_prompt_result={"ok": True, "name": "p",
                           "text": "say hello", "messages": []},
    )

    response = await reasoning_prompt_run("p", PromptRunRequest(stream=True))
    chunks: List[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, str) else chunk.decode())
    body = "".join(chunks)
    assert "event: start" in body
    assert "event: final" in body
    assert "streaming hello" in body
