"""Deterministic contract tests for the 2026 reasoning kernel.

These are model-free evaluations: a scripted backend requests tools and the
suite verifies that runtime policy, not model compliance, controls execution.
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from mcp_server import MCPServer
from evals.scenario_contract import load_scenarios, score_result
import llm_providers
from plan_executor import PlanStore
from reasoning_harness import (
    HarnessResult,
    LLMResponse,
    OpenAIResponsesBackend,
    ReasoningHarness,
    ToolCall,
    ToolExecutionContext,
    ToolRegistry,
    ToolSemantics,
    _serialise_result,
    _to_anthropic_messages,
)


class ScriptedLLM:
    name = "scripted"

    def __init__(self, responses: List[LLMResponse]):
        self.responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    async def chat(self, messages, tools):
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        return self.responses.pop(0)


def schema(name: str, properties=None, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Test tool {name}",
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


READ = ToolSemantics(
    read_only=True,
    destructive=False,
    idempotent=True,
    parallel_safe=True,
    impact_level="read",
    timeout_seconds=1,
    max_retries=2,
)
MUTATION = ToolSemantics(
    read_only=False,
    destructive=False,
    idempotent=True,
    parallel_safe=False,
    impact_level="low",
    timeout_seconds=1,
)
NON_IDEMPOTENT = ToolSemantics(
    read_only=False,
    destructive=True,
    idempotent=False,
    parallel_safe=False,
    impact_level="high",
    timeout_seconds=1,
)


@pytest.mark.asyncio
async def test_invalid_arguments_never_reach_executor():
    executed = []

    async def executor(name, args):
        executed.append(args)
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        "local",
        [schema("set_level", {"level": {"type": "integer"}}, ["level"])],
        executor,
        semantics=MUTATION,
    )
    llm = ScriptedLLM([
        LLMResponse("bad input", [ToolCall("1", "set_level", {"level": "high"})]),
        LLMResponse("I could not apply the invalid value."),
    ])

    result = await ReasoningHarness(llm, registry, "system").run("set it")

    assert executed == []
    assert result.failed_tool_calls == 1
    tool_result = result.trace[0].tool_results[0]["result"]
    assert tool_result["error_code"] == "invalid_arguments"


@pytest.mark.asyncio
async def test_mixed_read_write_batch_is_strictly_ordered():
    events: List[str] = []

    async def executor(name, args):
        events.append(f"start:{name}")
        await asyncio.sleep(0.01)
        events.append(f"end:{name}")
        return {"ok": True}

    registry = ToolRegistry()
    registry.register("local", [schema("get_state")], executor, semantics=READ)
    registry.register("local", [schema("turn_on")], executor, semantics=MUTATION)
    llm = ScriptedLLM([
        LLMResponse("observe then act", [
            ToolCall("1", "get_state", {}),
            ToolCall("2", "turn_on", {}),
        ]),
        LLMResponse("done"),
    ])

    await ReasoningHarness(llm, registry, "system").run("ordered")

    assert events == ["start:get_state", "end:get_state", "start:turn_on", "end:turn_on"]


@pytest.mark.asyncio
async def test_read_only_transient_failure_retries_but_mutation_does_not():
    attempts = {"read": 0, "write": 0}

    async def executor(name, args):
        attempts[args["kind"]] += 1
        return {"ok": False, "error": "temporary timeout", "retryable": True}

    registry = ToolRegistry()
    registry.register(
        "local",
        [schema("read_tool", {"kind": {"type": "string"}}, ["kind"])],
        executor,
        semantics=READ,
    )
    registry.register(
        "local",
        [schema("write_tool", {"kind": {"type": "string"}}, ["kind"])],
        executor,
        semantics=MUTATION,
    )
    llm = ScriptedLLM([
        LLMResponse("try", [
            ToolCall("1", "read_tool", {"kind": "read"}),
            ToolCall("2", "write_tool", {"kind": "write"}),
        ]),
        LLMResponse("done"),
    ])

    await ReasoningHarness(llm, registry, "system").run("retry policy")

    assert attempts == {"read": 3, "write": 1}


@pytest.mark.asyncio
async def test_successful_idempotent_mutation_is_deduplicated_within_run():
    executions = 0

    async def executor(name, args):
        nonlocal executions
        executions += 1
        return {"ok": True, "state": "on"}

    registry = ToolRegistry()
    registry.register("local", [schema("turn_on")], executor, semantics=MUTATION)
    llm = ScriptedLLM([
        LLMResponse("act", [ToolCall("1", "turn_on", {})]),
        LLMResponse("repeat", [ToolCall("2", "turn_on", {})]),
        LLMResponse("done"),
    ])

    result = await ReasoningHarness(llm, registry, "system").run("dedupe")

    assert executions == 1
    assert result.cached_tool_calls == 1
    assert result.trace[1].tool_results[0]["result"]["_harness"]["deduplicated"] is True


@pytest.mark.asyncio
async def test_repeated_non_idempotent_mutation_is_blocked():
    executions = 0

    async def executor(name, args):
        nonlocal executions
        executions += 1
        return {"ok": True}

    registry = ToolRegistry()
    registry.register("local", [schema("toggle")], executor, semantics=NON_IDEMPOTENT)
    llm = ScriptedLLM([
        LLMResponse("toggle", [ToolCall("1", "toggle", {})]),
        LLMResponse("toggle again", [ToolCall("2", "toggle", {})]),
        LLMResponse("done"),
    ])

    result = await ReasoningHarness(llm, registry, "system").run("do not double toggle")

    assert executions == 1
    assert result.trace[1].tool_results[0]["result"]["error_code"] == "duplicate_non_idempotent_call"


@pytest.mark.asyncio
async def test_rejected_calls_still_receive_protocol_results():
    seen = []

    async def executor(name, args):
        seen.append(args["n"])
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        "local",
        [schema("read", {"n": {"type": "integer"}}, ["n"])],
        executor,
        semantics=READ,
    )
    llm = ScriptedLLM([
        LLMResponse("many", [ToolCall(str(i), "read", {"n": i}) for i in range(5)]),
        LLMResponse("done"),
    ])
    harness = ReasoningHarness(llm, registry, "system", max_tool_calls_per_turn=2)

    result = await harness.run("bounded")

    assert seen == [0, 1]
    assert result.rejected_tool_calls == 3
    second_request_messages = llm.calls[1]["messages"]
    assert len([m for m in second_request_messages if m["role"] == "tool"]) == 5


def test_large_result_compaction_is_valid_json_and_explicit():
    encoded = _serialise_result(
        {"ok": True, "entities": [{"entity_id": f"sensor.{i}", "state": "x" * 200} for i in range(200)]},
        max_chars=2000,
    )
    parsed = json.loads(encoded)

    assert len(encoded) <= 2000
    assert parsed["truncated"] is True
    assert parsed["original_chars"] > len(encoded)


@pytest.mark.asyncio
async def test_llm_timeout_is_a_terminal_bounded_result():
    class SlowLLM:
        name = "slow"

        async def chat(self, messages, tools):
            await asyncio.sleep(0.1)
            return LLMResponse("late")

    result = await ReasoningHarness(
        SlowLLM(), ToolRegistry(), "system", llm_timeout_seconds=0.01
    ).run("timeout")

    assert isinstance(result, HarnessResult)
    assert result.stopped_reason == "llm_timeout"


@pytest.mark.asyncio
async def test_usage_is_aggregated_across_model_turns():
    registry = ToolRegistry()

    async def executor(name, args):
        return {"ok": True}

    registry.register("local", [schema("read")], executor, semantics=READ)
    llm = ScriptedLLM([
        LLMResponse("check", [ToolCall("1", "read", {})], usage={"input_tokens": 10, "output_tokens": 2}),
        LLMResponse("done", usage={"input_tokens": 15, "output_tokens": 3}),
    ])

    result = await ReasoningHarness(llm, registry, "system").run("usage")

    assert result.usage == {"input_tokens": 25, "output_tokens": 5}


def test_plan_store_claim_is_atomic(tmp_path):
    from plan_executor import PlanProposal, RecordedIntent

    store = PlanStore(str(tmp_path / "plans.db"))
    plan = PlanProposal(
        id="p1",
        run_id="r1",
        goal="goal",
        intents=[RecordedIntent(1, "turn_on", {}, "low", "test", {}, 1, "now")],
        answer="",
        iterations=1,
        duration_ms=1,
        backend="test",
        timestamp="2026-01-01T00:00:00Z",
    )
    store.save(plan)

    assert store.claim_for_execution("p1") == "claimed"
    assert store.claim_for_execution("p1") == "already_executing"


@pytest.mark.asyncio
async def test_dry_run_still_rejects_blocked_home_assistant_domain(monkeypatch):
    class HA:
        async def call_service(self, **kwargs):
            raise AssertionError("must never execute")

    server = MCPServer(HA(), dry_run=True)
    result = await server.execute_tool(
        "call_ha_service",
        {"domain": "shell_command", "service": "run", "entity_id": "shell_command.run"},
    )

    assert result["ok"] is False
    assert result["error_code"] == "blocked_domain"


@pytest.mark.asyncio
async def test_malformed_home_assistant_entity_id_is_rejected():
    class HA:
        async def call_service(self, **kwargs):
            raise AssertionError("must never execute")

    server = MCPServer(HA(), dry_run=False)
    result = await server.execute_tool(
        "call_ha_service",
        {"domain": "light", "service": "turn_on", "entity_id": "light.bad/id"},
    )

    assert result["ok"] is False
    assert result["error_code"] == "invalid_entity_id"


@pytest.mark.asyncio
async def test_approved_plan_context_executes_high_impact_service_without_second_queue():
    calls = []

    class HA:
        async def call_service(self, **kwargs):
            calls.append(kwargs)
            return {"done": True}

    class Queue:
        async def add_request(self, **kwargs):
            raise AssertionError("approved replay must not queue a second approval")

    server = MCPServer(HA(), approval_queue=Queue(), dry_run=False)
    result = await server.execute_tool(
        "lock_door",
        {"entity_id": "lock.front_door"},
        context=ToolExecutionContext(approved=True, plan_id="p1", run_id="r1"),
    )

    assert result["ok"] is True
    assert calls[0]["domain"] == "lock"
    assert calls[0]["service"] == "lock"


def test_anthropic_message_conversion_groups_tool_results_and_preserves_payload():
    payload = [
        {"type": "thinking", "thinking": "", "signature": "signed"},
        {"type": "tool_use", "id": "t1", "name": "read", "input": {}},
        {"type": "tool_use", "id": "t2", "name": "read", "input": {}},
    ]
    converted = _to_anthropic_messages([
        {"role": "system", "content": "system"},
        {"role": "user", "content": "inspect"},
        {"role": "assistant", "content": "", "tool_calls": [], "provider_payload": payload},
        {"role": "tool", "tool_call_id": "t1", "content": '{"ok":true}'},
        {"role": "tool", "tool_call_id": "t2", "content": '{"ok":false,"error":"boom"}'},
    ])

    assert converted[1]["content"][0]["signature"] == "signed"
    assert len(converted[2]["content"]) == 2
    assert converted[2]["content"][1]["is_error"] is True


class FakeOutputItem:
    def __init__(self, **values):
        self.__dict__.update(values)

    def model_dump(self, exclude_none=True):
        return dict(self.__dict__)


@pytest.mark.asyncio
async def test_openai_responses_replays_encrypted_reasoning_locally():
    captured = []
    responses = [
        SimpleNamespace(
            id="resp1",
            status="completed",
            output=[
                FakeOutputItem(type="reasoning", encrypted_content="ciphertext"),
                FakeOutputItem(type="function_call", id="fc1", call_id="call1", name="read", arguments="{}"),
            ],
            output_text="",
            usage=SimpleNamespace(input_tokens=5, output_tokens=3, input_tokens_details=None, output_tokens_details=None),
        ),
        SimpleNamespace(
            id="resp2",
            status="completed",
            output=[FakeOutputItem(type="message", content=[FakeOutputItem(type="output_text", text="done")])],
            output_text="done",
            usage=SimpleNamespace(input_tokens=6, output_tokens=2, input_tokens_details=None, output_tokens_details=None),
        ),
    ]

    class Responses:
        async def create(self, **kwargs):
            captured.append(kwargs)
            return responses.pop(0)

    backend = OpenAIResponsesBackend.__new__(OpenAIResponsesBackend)
    backend.model = "gpt-5.6-terra"
    backend.effort = "medium"
    backend.max_output_tokens = 1000
    backend.store = False
    backend._client = SimpleNamespace(responses=Responses())
    tools = [schema("read")]
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "inspect"},
    ]

    first = await backend.chat(messages, tools)
    messages.extend([
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call1", "type": "function", "function": {"name": "read", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "call1", "name": "read", "content": '{"ok":true}'},
    ])
    second = await backend.chat(messages, tools, continuation=first.continuation)

    assert first.tool_calls[0].id == "call1"
    assert second.content == "done"
    assert captured[0]["store"] is False
    assert captured[0]["include"] == ["reasoning.encrypted_content"]
    second_input = captured[1]["input"]
    assert any(item.get("encrypted_content") == "ciphertext" for item in second_input)
    assert any(item.get("type") == "function_call_output" for item in second_input)


def test_home_agent_evaluation_dataset_and_scorer_are_executable():
    scenarios = load_scenarios()
    scenario = next(item for item in scenarios if item["id"] == "security_action_requires_approval")
    score = score_result(scenario, {
        "tool_calls": 2,
        "answer": "The front door unlock requires approval.",
        "trace": [{"tool_calls": [{"name": "unlock_door"}]}],
        "plan": {
            "requires_approval": True,
            "intents": [{"tool_name": "unlock_door"}],
        },
    })

    assert len(scenarios) >= 10
    assert score["passed"] is True


def test_current_cloud_provider_routing(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    chat = llm_providers.make_chat_provider()
    assert chat.name == "anthropic"

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    tool_backend = llm_providers.make_tool_backend(
        model="gpt-5.6-terra",
        fallback_to_ollama=False,
    )
    assert isinstance(tool_backend, OpenAIResponsesBackend)


def test_remote_provider_can_fail_fast_instead_of_silent_ollama_drift(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="openai"):
        llm_providers.make_tool_backend(
            model="gpt-5.6-terra",
            fallback_to_ollama=False,
        )


@pytest.mark.asyncio
async def test_generated_dashboard_response_is_network_isolated(monkeypatch):
    import main as backend_main

    class Studio:
        def get_html(self, dashboard_id):
            return "<!doctype html><html><body><script>/* generated */</script></body></html>"

    monkeypatch.setattr(backend_main, "dashboard_studio", Studio())
    response = await backend_main.studio_get_dashboard("dashboard-1")
    csp = response.headers["content-security-policy"]

    assert "sandbox allow-scripts" in csp
    assert "connect-src 'none'" in csp
    assert "form-action 'none'" in csp
    assert response.headers["referrer-policy"] == "no-referrer"
