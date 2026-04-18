"""Regression tests for previously open GitHub issues.

Covers:
  * #2  — RagManager auto-pulls a missing embedding model.
  * #6  — UniversalAgent uses HAWebSocketClient.get_states (singular
          ``get_state`` did not exist, so every entity reported
          "unavailable").
  * #11 — Orchestrator dashboard refresh loop no longer spams the LLM
          when Home Assistant is disconnected.
  * #17 — Dashboard error path no longer raises
          ``Client.get() takes 2 positional arguments but 3 were given``.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, NonCallableMagicMock, patch

import pytest

# chromadb may fail to import on Python 3.14 + Pydantic v2 (BaseSettings moved).
_mock_chromadb = MagicMock()
_mock_chromadb.PersistentClient = MagicMock
_mock_chromadb.config = MagicMock()
_mock_chromadb.config.Settings = MagicMock
sys.modules.setdefault("chromadb", _mock_chromadb)
sys.modules.setdefault("chromadb.config", _mock_chromadb.config)


# ---------------------------------------------------------------------------
# Issue #2 — RagManager auto-pulls missing embedding model
# ---------------------------------------------------------------------------
def test_issue_2_auto_pulls_missing_embedding_model(tmp_path, monkeypatch):
    import rag_manager

    rm = rag_manager.RagManager(
        persist_dir=str(tmp_path / "chroma"),
        embedding_model="nomic-embed-text",
    )

    call_count = {"n": 0}

    def fake_embeddings(model, prompt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError(
                'model "nomic-embed-text" not found, try pulling it first'
            )
        return {"embedding": [0.1, 0.2, 0.3]}

    fake_pull = MagicMock()
    monkeypatch.setattr(rag_manager.ollama, "embeddings", fake_embeddings)
    monkeypatch.setattr(rag_manager.ollama, "pull", fake_pull)

    out = rm._generate_embedding("hello")
    assert out == [0.1, 0.2, 0.3]
    fake_pull.assert_called_once_with("nomic-embed-text")
    assert rm._embedding_model_ready is True


def test_issue_2_pull_only_attempted_once(tmp_path, monkeypatch):
    import rag_manager

    rm = rag_manager.RagManager(
        persist_dir=str(tmp_path / "chroma"),
        embedding_model="nomic-embed-text",
    )

    def always_missing(model, prompt):
        raise RuntimeError('model "nomic-embed-text" not found, try pulling it first')

    fake_pull = MagicMock(side_effect=RuntimeError("ollama unreachable"))
    monkeypatch.setattr(rag_manager.ollama, "embeddings", always_missing)
    monkeypatch.setattr(rag_manager.ollama, "pull", fake_pull)

    with pytest.raises(RuntimeError):
        rm._generate_embedding("a")
    # Second call must not retry the pull.
    with pytest.raises(RuntimeError):
        rm._generate_embedding("b")
    fake_pull.assert_called_once()


# ---------------------------------------------------------------------------
# Issue #6 — UniversalAgent fetches state via the correct method
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_issue_6_universal_agent_uses_get_states(monkeypatch):
    from agents.universal_agent import UniversalAgent

    ha = NonCallableMagicMock()
    ha.connected = True
    ha.get_states = AsyncMock(return_value={
        "entity_id": "sensor.humidity",
        "state": "62",
        "attributes": {"friendly_name": "Greenhouse Humidity"},
    })
    # Crucially — the bug was calling .get_state(...) which does not
    # exist. Make sure that attribute is absent so any regression
    # raises AttributeError instead of silently passing.
    if hasattr(ha, "get_state"):
        del ha.get_state

    mcp = MagicMock()
    mcp.execute_tool = AsyncMock(return_value={"ok": True})

    agent = UniversalAgent(
        agent_id="greenhouse",
        name="Greenhouse",
        instruction="report humidity",
        mcp_server=mcp,
        ha_client=ha,
        entities=["sensor.humidity"],
        decision_interval=120,
        model_name="test-model",
    )
    desc = await agent._get_state_description()
    assert "Greenhouse Humidity" in desc
    assert "62" in desc
    ha.get_states.assert_awaited_once_with(entity_id="sensor.humidity")


@pytest.mark.asyncio
async def test_issue_6_unavailable_entity_does_not_raise(monkeypatch):
    from agents.universal_agent import UniversalAgent

    ha = NonCallableMagicMock()
    ha.connected = True
    ha.get_states = AsyncMock(side_effect=ValueError("unknown entity"))
    mcp = MagicMock()

    agent = UniversalAgent(
        agent_id="g",
        name="g",
        instruction="x",
        mcp_server=mcp,
        ha_client=ha,
        entities=["sensor.ghost"],
        decision_interval=120,
        model_name="test-model",
    )
    desc = await agent._get_state_description()
    assert "unavailable" in desc.lower()


# ---------------------------------------------------------------------------
# Issue #11 — dashboard refresh loop pauses when HA is disconnected
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_issue_11_dashboard_loop_skips_when_disconnected(monkeypatch):
    from orchestrator import Orchestrator

    inst = Orchestrator.__new__(Orchestrator)
    inst._ha_provider = SimpleNamespace(connected=False)
    inst.dashboard_refresh_interval = 0.01
    inst.last_dashboard_instruction = "x"
    inst.generate_visual_dashboard = AsyncMock(return_value="<html/>")

    # asyncio.sleep stub so we can run the loop briefly then cancel.
    real_sleep = asyncio.sleep
    sleep_calls: list[float] = []

    async def fast_sleep(d):
        sleep_calls.append(d)
        await real_sleep(0)

    monkeypatch.setattr("orchestrator.asyncio.sleep", fast_sleep)

    task = asyncio.create_task(inst.run_dashboard_refresh_loop())
    await real_sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Generation must NOT have been called while disconnected.
    inst.generate_visual_dashboard.assert_not_called()
    # And we should have hit the disconnected sleep path at least once.
    assert any(d >= 30 for d in sleep_calls)


@pytest.mark.asyncio
async def test_issue_11_dashboard_loop_resumes_when_connected(monkeypatch):
    from orchestrator import Orchestrator

    inst = Orchestrator.__new__(Orchestrator)
    state = SimpleNamespace(connected=True)
    inst._ha_provider = state
    inst.dashboard_refresh_interval = 0.01
    inst.last_dashboard_instruction = "x"
    inst.generate_visual_dashboard = AsyncMock(return_value="<html/>")

    real_sleep = asyncio.sleep

    async def fast_sleep(d):
        await real_sleep(0)

    monkeypatch.setattr("orchestrator.asyncio.sleep", fast_sleep)

    task = asyncio.create_task(inst.run_dashboard_refresh_loop())
    await real_sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert inst.generate_visual_dashboard.await_count >= 1


# ---------------------------------------------------------------------------
# Issue #17 — dashboard error path does not raise on host_info lookup
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_issue_17_dashboard_error_path_uses_recorded_host(monkeypatch, tmp_path):
    from orchestrator import Orchestrator

    inst = Orchestrator.__new__(Orchestrator)
    inst._ha_provider = SimpleNamespace(connected=True, get_states=AsyncMock(return_value=[
        {"entity_id": "light.x", "state": "on", "attributes": {}},
    ]))
    inst.ollama_host_used = "http://test-host:11434"
    inst.ollama_client = SimpleNamespace()  # no ._client attr; old code blew up here
    inst.llm_client = MagicMock()
    inst.llm_client.chat.side_effect = RuntimeError("LLM exploded")
    inst._genai_client = None
    inst.use_gemini_for_dashboard = False
    inst.gemini_model_name = "gemini-1.5-pro"
    inst.model_name = "test-model"
    inst.dashboard_dir = tmp_path

    # Should NOT raise — the bug was an unhandled TypeError inside the
    # except block while building the diagnostic message.
    out = await inst.generate_visual_dashboard(user_instruction="x")
    assert "Dashboard Generation Failed" in out
    assert "test-host" in out  # host info now correctly recorded
