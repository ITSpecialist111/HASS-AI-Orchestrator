"""Smoke tests for Phase 8 / Milestone E (Plan \u2192 Approve \u2192 Execute)."""
from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List

import pytest

from plan_executor import (
    DryRunInterceptor,
    PlanProposal,
    PlanStore,
    RecordedIntent,
    ToolClassifier,
    replay_plan,
    summarise_risk,
)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------
class TestToolClassifier:
    def setup_method(self) -> None:
        self.c = ToolClassifier()

    @pytest.mark.parametrize("name", [
        "list_entities", "get_state", "search_entities", "history_get",
        "render_template", "find_devices", "describe_area",
        "hass_list_entities", "hass_get_state",
    ])
    def test_read_only_tools_are_not_mutating(self, name):
        cls = self.c.classify(name, {})
        assert cls.is_mutating is False
        assert cls.impact_level == "read"

    @pytest.mark.parametrize("name,expected_level", [
        ("set_temperature", "high"),  # high-impact pattern wins
        ("turn_on_light", "low"),
        ("turn_off_switch", "low"),
        ("toggle_fan", "low"),
        ("hass_call_service", "high"),
        ("automation_create", "high"),
        ("script_delete", "high"),
        ("scene_update", "high"),
        ("lock_front_door", "high"),
        ("unlock_back_door", "high"),
        ("arm_alarm", "high"),
        ("disarm_alarm_panel", "high"),
        ("restart_addon", "high"),
        ("set_thermostat_mode", "high"),  # 'thermostat' + high-impact pattern
    ])
    def test_mutating_tools_are_flagged(self, name, expected_level):
        cls = self.c.classify(name, {})
        assert cls.is_mutating is True
        assert cls.impact_level == expected_level

    def test_unknown_tool_is_treated_as_low_impact_mutating(self):
        cls = self.c.classify("frobnicate_widget", {})
        assert cls.is_mutating is True
        assert cls.impact_level == "low"
        assert "unrecognised" in cls.reason

    def test_overrides_take_precedence(self):
        c = ToolClassifier(
            read_only_overrides=["frobnicate_widget"],
            mutating_overrides=["render_template_dangerous"],
        )
        assert c.classify("frobnicate_widget", {}).is_mutating is False
        assert c.classify("render_template_dangerous", {}).is_mutating is True


# ---------------------------------------------------------------------------
# Interceptor
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_interceptor_passes_read_only_calls_through():
    fired: List[str] = []
    async def underlying(name, args):
        fired.append(name)
        return {"ok": True, "value": "real-data"}

    intercept = DryRunInterceptor(underlying)
    out = await intercept.call("list_entities", {})
    assert out == {"ok": True, "value": "real-data"}
    assert fired == ["list_entities"]
    assert intercept.intents == []


@pytest.mark.asyncio
async def test_interceptor_records_mutating_calls_without_firing():
    fired: List[str] = []
    async def underlying(name, args):
        fired.append(name)
        return {"ok": True}

    intercept = DryRunInterceptor(underlying)
    intercept.set_iteration(3)
    out = await intercept.call("set_temperature", {"entity_id": "climate.lounge", "temp": 21})

    assert out["dry_run"] is True
    assert out["ok"] is True
    assert out["intent_sequence"] == 1
    assert fired == []  # never reached the underlying tool
    assert len(intercept.intents) == 1

    intent = intercept.intents[0]
    assert intent.tool_name == "set_temperature"
    assert intent.arguments == {"entity_id": "climate.lounge", "temp": 21}
    assert intent.impact_level == "high"
    assert intent.iteration == 3


@pytest.mark.asyncio
async def test_interceptor_handles_mixed_sequence():
    async def underlying(name, args):
        return {"ok": True, "data": name}

    intercept = DryRunInterceptor(underlying)
    intercept.set_iteration(1)
    await intercept.call("list_entities", {})
    await intercept.call("turn_on_light", {"entity_id": "light.kitchen"})
    intercept.set_iteration(2)
    await intercept.call("get_state", {"entity_id": "light.kitchen"})
    await intercept.call("set_temperature", {"entity_id": "climate.lounge", "temp": 22})

    assert [i.tool_name for i in intercept.intents] == ["turn_on_light", "set_temperature"]
    assert [i.sequence for i in intercept.intents] == [1, 2]
    assert [i.iteration for i in intercept.intents] == [1, 2]


# ---------------------------------------------------------------------------
# PlanStore
# ---------------------------------------------------------------------------
def _make_intent(seq: int, name: str, level: str = "low") -> RecordedIntent:
    return RecordedIntent(
        sequence=seq,
        tool_name=name,
        arguments={"x": seq},
        impact_level=level,
        classification_reason="test",
        simulated_result={"ok": True, "dry_run": True},
        iteration=1,
        timestamp="2026-04-18T00:00:00+00:00",
    )


def _make_plan(plan_id: str = "p1", intents=None) -> PlanProposal:
    return PlanProposal(
        id=plan_id,
        run_id="r1",
        goal="test goal",
        intents=intents or [_make_intent(1, "turn_on_light")],
        answer="planned",
        iterations=2,
        duration_ms=100,
        backend="stub",
        timestamp="2026-04-18T00:00:00+00:00",
    )


class TestPlanStore:
    def setup_method(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = PlanStore(db_path=self.tmp.name)

    def teardown_method(self) -> None:
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_save_and_get(self):
        plan = _make_plan()
        self.store.save(plan)
        out = self.store.get(plan.id)
        assert out is not None
        assert out.id == plan.id
        assert out.goal == "test goal"
        assert len(out.intents) == 1
        assert out.intents[0].tool_name == "turn_on_light"
        assert out.status == "pending"

    def test_get_missing_returns_none(self):
        assert self.store.get("does-not-exist") is None

    def test_list_filters_by_status_and_orders_recent_first(self):
        p1 = _make_plan("p1")
        p1.timestamp = "2026-04-10T00:00:00+00:00"
        p2 = _make_plan("p2")
        p2.timestamp = "2026-04-15T00:00:00+00:00"
        p2.status = "executed"
        self.store.save(p1)
        self.store.save(p2)

        all_plans = self.store.list()
        assert [p.id for p in all_plans] == ["p2", "p1"]

        executed = self.store.list(status="executed")
        assert [p.id for p in executed] == ["p2"]

    def test_update_status_persists(self):
        plan = _make_plan()
        self.store.save(plan)
        ok = self.store.update_status(
            plan.id,
            "executed",
            execution_results=[{"sequence": 1, "ok": True}],
            executed_at="2026-04-18T01:00:00+00:00",
        )
        assert ok is True
        out = self.store.get(plan.id)
        assert out.status == "executed"
        assert out.executed_at == "2026-04-18T01:00:00+00:00"
        assert out.execution_results == [{"sequence": 1, "ok": True}]

    def test_update_status_returns_false_for_missing(self):
        assert self.store.update_status("nope", "executed") is False


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_replay_executes_intents_in_order_with_real_args():
    fired: List[Dict[str, Any]] = []
    async def underlying(name, args):
        fired.append({"name": name, "args": args})
        return {"ok": True}

    plan = _make_plan(intents=[
        _make_intent(1, "turn_on_light"),
        _make_intent(2, "set_temperature", level="high"),
    ])
    plan.intents[0].arguments = {"entity_id": "light.kitchen"}
    plan.intents[1].arguments = {"entity_id": "climate.lounge", "temp": 21}

    results = await replay_plan(plan, underlying)

    assert [r["sequence"] for r in results] == [1, 2]
    assert all(r["ok"] for r in results)
    assert all(not r["skipped"] for r in results)
    assert fired == [
        {"name": "turn_on_light", "args": {"entity_id": "light.kitchen"}},
        {"name": "set_temperature", "args": {"entity_id": "climate.lounge", "temp": 21}},
    ]


@pytest.mark.asyncio
async def test_replay_aborts_after_failure_and_marks_remainder_skipped():
    call_count = {"n": 0}
    async def underlying(name, args):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {"ok": True}
        return {"ok": False, "error": "boom"}

    plan = _make_plan(intents=[
        _make_intent(1, "turn_on_light"),
        _make_intent(2, "turn_on_switch"),
        _make_intent(3, "turn_off_light"),
    ])

    results = await replay_plan(plan, underlying)
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False
    assert results[2]["skipped"] is True
    assert results[2]["ok"] is False
    # Underlying was called twice (success then failure), then never again.
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_replay_handles_executor_exception_as_failure():
    async def underlying(name, args):
        raise RuntimeError("connection lost")

    plan = _make_plan(intents=[_make_intent(1, "turn_on_light")])
    results = await replay_plan(plan, underlying)
    assert results[0]["ok"] is False
    assert "RuntimeError" in results[0]["result"]["error"]


@pytest.mark.asyncio
async def test_replay_pending_approval_counts_as_ok():
    """Local MCP returns ``{status: pending_approval}`` for high-impact
    actions \u2014 that's still a successful planner outcome."""
    async def underlying(name, args):
        return {"status": "pending_approval"}

    plan = _make_plan(intents=[_make_intent(1, "lock_door", level="high")])
    results = await replay_plan(plan, underlying)
    assert results[0]["ok"] is True


# ---------------------------------------------------------------------------
# Risk summary
# ---------------------------------------------------------------------------
def test_summarise_risk_empty():
    assert "Read-only" in summarise_risk([])


def test_summarise_risk_groups_by_level():
    summary = summarise_risk([
        _make_intent(1, "turn_on_light", level="low"),
        _make_intent(2, "set_temperature", level="medium"),
        _make_intent(3, "lock_door", level="high"),
    ])
    assert "1 high-impact" in summary
    assert "1 medium-impact" in summary
    assert "1 low-impact" in summary


# ---------------------------------------------------------------------------
# Agent integration: plan / auto / execute modes
# ---------------------------------------------------------------------------
@pytest.fixture
def stubbed_agent_factory(monkeypatch, tmp_path):
    """Builds a DeepReasoningAgent whose LLM is fully scriptable.

    The factory accepts a list of ``LLMResponse`` objects \u2014 they are
    returned in order from ``llm.chat``.
    """
    import agents.deep_reasoning_agent as dra
    from reasoning_harness import LLMResponse, ToolCall

    fired: List[Dict[str, Any]] = []

    class _StubLocalMCP:
        tools: Dict[str, Any] = {}
        async def execute_tool(self, **kw):
            fired.append({"name": kw["tool_name"], "args": kw["parameters"]})
            return {"ok": True, "executed": True}

    def _factory(scripted_responses: List[LLMResponse], *, default_mode="auto"):
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

        plan_store = PlanStore(db_path=str(tmp_path / "plans.db"))
        agent = dra.DeepReasoningAgent(
            local_mcp=_StubLocalMCP(),
            external_mcp=None,
            ollama_model="ignored",
            plan_store=plan_store,
            default_mode=default_mode,
        )
        # Manually register a couple of tools so the registry has entries
        # the LLM can "call".
        agent.registry._routes.clear()
        agent.registry.register(
            provider="local",
            schemas=[
                {"type": "function", "function": {"name": "turn_on_light", "parameters": {}}},
                {"type": "function", "function": {"name": "lock_front_door", "parameters": {}}},
                {"type": "function", "function": {"name": "list_entities", "parameters": {}}},
            ],
            executor=lambda name, args: agent._local_executor(name, args),
        )
        return agent, plan_store, fired

    return _factory


@pytest.mark.asyncio
async def test_plan_mode_records_intents_without_firing(stubbed_agent_factory):
    from reasoning_harness import LLMResponse, ToolCall

    agent, plan_store, fired = stubbed_agent_factory([
        # Iteration 1: ask for a tool
        LLMResponse(content="planning", tool_calls=[
            ToolCall(id="c1", name="turn_on_light", arguments={"entity_id": "light.kitchen"}),
        ]),
        # Iteration 2: final answer
        LLMResponse(content="Done"),
    ])

    result = await agent.run("Plan turning on the kitchen light", mode="plan")

    # In plan mode the underlying executor must NOT have been called.
    assert fired == []

    plan = getattr(result, "plan")
    assert plan is not None
    assert plan["mutating_count"] == 1
    assert plan["intents"][0]["tool_name"] == "turn_on_light"
    assert plan["intents"][0]["arguments"] == {"entity_id": "light.kitchen"}
    assert getattr(result, "executed_inline") is False

    # Plan must be persisted.
    saved = plan_store.get(plan["id"])
    assert saved is not None
    assert saved.status == "pending"


@pytest.mark.asyncio
async def test_auto_mode_executes_inline_when_no_high_impact(stubbed_agent_factory):
    from reasoning_harness import LLMResponse, ToolCall

    agent, plan_store, fired = stubbed_agent_factory([
        LLMResponse(content="planning", tool_calls=[
            ToolCall(id="c1", name="turn_on_light", arguments={"entity_id": "light.kitchen"}),
        ]),
        LLMResponse(content="Done"),
    ])

    result = await agent.run("Turn on the kitchen light", mode="auto")

    plan = getattr(result, "plan")
    assert plan is not None
    assert getattr(result, "executed_inline") is True
    # And the underlying tool actually fired during the inline replay.
    assert fired == [{"name": "turn_on_light", "args": {"entity_id": "light.kitchen"}}]
    saved = plan_store.get(plan["id"])
    assert saved.status == "executed"
    assert saved.executed_at is not None


@pytest.mark.asyncio
async def test_auto_mode_queues_when_high_impact_present(stubbed_agent_factory):
    from reasoning_harness import LLMResponse, ToolCall

    agent, plan_store, fired = stubbed_agent_factory([
        LLMResponse(content="planning", tool_calls=[
            ToolCall(id="c1", name="lock_front_door", arguments={"entity_id": "lock.front"}),
            ToolCall(id="c2", name="turn_on_light", arguments={"entity_id": "light.porch"}),
        ]),
        LLMResponse(content="Done"),
    ])

    result = await agent.run("Lock the front door and turn on the porch", mode="auto")

    plan = getattr(result, "plan")
    assert plan is not None
    assert plan["high_impact_count"] >= 1
    assert getattr(result, "executed_inline") is False
    assert fired == []  # nothing fires yet \u2014 awaiting approval
    saved = plan_store.get(plan["id"])
    assert saved.status == "pending"
    assert saved.requires_approval is True


@pytest.mark.asyncio
async def test_execute_plan_replays_against_real_tools(stubbed_agent_factory):
    from reasoning_harness import LLMResponse, ToolCall

    agent, plan_store, fired = stubbed_agent_factory([
        LLMResponse(content="planning", tool_calls=[
            ToolCall(id="c1", name="lock_front_door", arguments={"entity_id": "lock.front"}),
        ]),
        LLMResponse(content="Done"),
    ])

    # Generate a pending plan first.
    result = await agent.run("Lock the front door", mode="auto")
    plan_id = result.plan["id"]
    assert fired == []  # high-impact \u2014 not executed inline

    out = await agent.execute_plan(plan_id)
    assert out is not None
    assert out["status"] == "executed"
    assert len(out["execution_results"]) == 1
    assert fired == [{"name": "lock_front_door", "args": {"entity_id": "lock.front"}}]


@pytest.mark.asyncio
async def test_execute_plan_is_idempotent(stubbed_agent_factory):
    from reasoning_harness import LLMResponse, ToolCall

    agent, plan_store, fired = stubbed_agent_factory([
        LLMResponse(content="planning", tool_calls=[
            ToolCall(id="c1", name="lock_front_door", arguments={"entity_id": "lock.front"}),
        ]),
        LLMResponse(content="Done"),
    ])

    result = await agent.run("Lock the front door", mode="auto")
    plan_id = result.plan["id"]

    first = await agent.execute_plan(plan_id)
    second = await agent.execute_plan(plan_id)
    assert first["status"] == "executed"
    assert second["status"] == "already_executed"
    # Underlying tool fired exactly once across both calls.
    assert len(fired) == 1


@pytest.mark.asyncio
async def test_execute_mode_skips_planning(stubbed_agent_factory):
    """In execute mode the interceptor is off, no plan is recorded,
    and tools fire immediately during the harness run."""
    from reasoning_harness import LLMResponse, ToolCall

    agent, plan_store, fired = stubbed_agent_factory([
        LLMResponse(content="acting", tool_calls=[
            ToolCall(id="c1", name="turn_on_light", arguments={"entity_id": "light.kitchen"}),
        ]),
        LLMResponse(content="Done"),
    ])

    result = await agent.run("Turn on the light", mode="execute")
    assert getattr(result, "plan") is None
    assert getattr(result, "executed_inline") is False
    assert fired == [{"name": "turn_on_light", "args": {"entity_id": "light.kitchen"}}]


@pytest.mark.asyncio
async def test_reject_plan_marks_status(stubbed_agent_factory):
    from reasoning_harness import LLMResponse, ToolCall

    agent, plan_store, fired = stubbed_agent_factory([
        LLMResponse(content="planning", tool_calls=[
            ToolCall(id="c1", name="lock_front_door", arguments={}),
        ]),
        LLMResponse(content="Done"),
    ])
    result = await agent.run("Lock", mode="auto")
    plan_id = result.plan["id"]

    assert await agent.reject_plan(plan_id) is True
    saved = plan_store.get(plan_id)
    assert saved.status == "rejected"
