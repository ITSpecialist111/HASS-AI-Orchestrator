"""
Tests for the Phase 10A Dashboard Studio.

Everything is mocked: the LLM is stubbed via a fake ``ChatProvider``,
the Home Assistant client is a ``MagicMock``, and the storage layer
writes to ``tmp_path``. No network, no real LLM, no real HA.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from llm_providers import ChatProvider  # noqa: E402
from dashboard_studio import (  # noqa: E402
    DashboardStudio,
    _extract_entity_refs,
    _inject_live_shim,
    _new_id,
    _strip_markdown_fences,
    _title_from_prompt,
)


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------
class _FakeChat(ChatProvider):
    """Returns a deterministic HTML payload, captures every call for asserts."""

    name = "fake"

    def __init__(self, html: str) -> None:
        self._html = html
        self.calls: List[Dict[str, Any]] = []

    def chat(self, model, messages, *, temperature=0.7, max_tokens=1000, extra_options=None):
        self.calls.append({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        return self._html


def _factory(chat: ChatProvider):
    """Wrap a ChatProvider in a factory matching make_chat_provider's signature."""
    return lambda **kwargs: chat


def _make_ha_client(states: Optional[List[Dict[str, Any]]] = None):
    client = MagicMock()
    client.connected = True
    if states is None:
        states = [
            {
                "entity_id": "sensor.kitchen_temperature",
                "state": "21.4",
                "attributes": {"friendly_name": "Kitchen Temp", "unit_of_measurement": "°C", "device_class": "temperature"},
            },
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room"},
            },
            {
                "entity_id": "binary_sensor.front_door",
                "state": "off",
                "attributes": {"friendly_name": "Front Door", "device_class": "door"},
            },
        ]
    client.get_states = AsyncMock(return_value=states)
    return client


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
def test_strip_markdown_fences_removes_html_block():
    assert _strip_markdown_fences("```html\n<!doctype html>x\n```") == "<!doctype html>x"


def test_extract_entity_refs_dedupes_and_sorts():
    html = """
    <span data-entity="sensor.a">x</span>
    <span data-entity='light.b'>y</span>
    <span data-entity="sensor.a">z</span>
    """
    assert _extract_entity_refs(html) == ["light.b", "sensor.a"]


def test_inject_live_shim_before_body_close():
    out = _inject_live_shim("<html><body><h1>hi</h1></body></html>", "abc123")
    # The placeholder token used inside the template must have been substituted.
    assert "%DASHBOARD_ID_JSON%" not in out
    assert '"abc123"' in out
    assert out.count("</body>") == 1
    assert out.index("setInterval") < out.index("</body>")


def test_inject_live_shim_appends_when_no_body_tag():
    out = _inject_live_shim("<div>no body</div>", "z9")
    assert out.endswith("</script>\n") or out.rstrip().endswith("</script>")
    assert '"z9"' in out


def test_title_from_prompt_strips_stopwords():
    assert _title_from_prompt("please make a dashboard for energy and security focus") == "dashboard energy security focus"


def test_new_id_is_sortable_over_time():
    a = _new_id()
    time.sleep(0.005)
    b = _new_id()
    # Timestamp prefix (first 10 chars) must be monotonic when separated.
    assert a[:10] <= b[:10]
    assert len(a) == 16 and len(b) == 16


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_persists_html_and_meta(tmp_path):
    fake_html = (
        "<!doctype html><html><body>"
        "<span data-entity=\"sensor.kitchen_temperature\" data-attr=\"state\">--</span>"
        "<span data-entity='light.living_room'>off</span>"
        "</body></html>"
    )
    chat = _FakeChat(fake_html)
    studio = DashboardStudio(
        ha_client_provider=lambda: _make_ha_client(),
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    meta = await studio.generate("Show kitchen temp and living room light", provider="ollama")

    # File side-effects
    assert (tmp_path / f"{meta.id}.html").exists()
    assert (tmp_path / f"{meta.id}.meta.json").exists()

    # Metadata
    assert meta.title  # non-empty
    assert meta.provider == "ollama"
    assert meta.entity_count == 2
    assert meta.size_bytes > len(fake_html)  # shim was injected
    assert meta.parent_id is None

    # Live shim was injected and references the dashboard id
    saved_html = (tmp_path / f"{meta.id}.html").read_text(encoding="utf-8")
    assert f'"{meta.id}"' in saved_html
    assert "setInterval" in saved_html

    # Chat factory was called with provider routing
    assert chat.calls, "chat provider was not invoked"
    msgs = chat.calls[0]["messages"]
    assert msgs[0]["role"] == "system"
    assert "data-entity" in msgs[0]["content"]
    assert "Show kitchen temp" in msgs[1]["content"]


@pytest.mark.asyncio
async def test_generate_falls_back_when_llm_returns_non_html(tmp_path):
    chat = _FakeChat("Sorry, I can't help with that.")
    studio = DashboardStudio(
        ha_client_provider=lambda: _make_ha_client(),
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    meta = await studio.generate("anything")
    saved = (tmp_path / f"{meta.id}.html").read_text(encoding="utf-8")
    assert saved.lower().startswith("<!doctype")
    assert "Sorry, I can&#39;t help" in saved  # text was escaped


@pytest.mark.asyncio
async def test_iterate_links_parent_and_uses_existing_html_in_prompt(tmp_path):
    base_html = "<!doctype html><html><body><h1>v1</h1></body></html>"
    refined_html = "<!doctype html><html><body><h1>v2 red</h1></body></html>"
    chat = _FakeChat(base_html)
    studio = DashboardStudio(
        ha_client_provider=lambda: _make_ha_client(),
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    parent = await studio.generate("first", provider="ollama")
    chat._html = refined_html  # next call returns the refined version
    child = await studio.iterate(parent.id, "make it red", provider="ollama")
    assert child is not None
    assert child.parent_id == parent.id
    assert child.instruction == "make it red"

    # The second LLM call must include the existing HTML in the user message.
    assert len(chat.calls) == 2
    user_msg = chat.calls[-1]["messages"][1]["content"]
    assert "Existing dashboard to refine" in user_msg
    assert "<h1>v1</h1>" in user_msg


@pytest.mark.asyncio
async def test_iterate_returns_none_for_unknown_base(tmp_path):
    chat = _FakeChat("<!doctype html><html><body>x</body></html>")
    studio = DashboardStudio(
        ha_client_provider=lambda: _make_ha_client(),
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    out = await studio.iterate("does-not-exist", "tweak")
    assert out is None


@pytest.mark.asyncio
async def test_variations_creates_n_dashboards_with_shared_anchor(tmp_path):
    chat = _FakeChat("<!doctype html><html><body>v</body></html>")
    studio = DashboardStudio(
        ha_client_provider=lambda: _make_ha_client(),
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    metas = await studio.variations("solar focused dashboard", n=3)
    assert len(metas) == 3
    anchor = metas[0].variation_of
    assert anchor == metas[0].id  # first one anchors itself
    for m in metas[1:]:
        assert m.variation_of == anchor


# ---------------------------------------------------------------------------
# Gallery / lifecycle
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_dashboards_returns_pinned_first_then_newest(tmp_path):
    chat = _FakeChat("<!doctype html><html><body>x</body></html>")
    studio = DashboardStudio(
        ha_client_provider=lambda: _make_ha_client(),
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    a = await studio.generate("a")
    b = await studio.generate("b")
    c = await studio.generate("c")
    studio.set_pinned(a.id, True)
    listed = studio.list_dashboards()
    assert listed[0].id == a.id  # pinned first
    # The remaining two should be in newest-first order.
    rest_ids = [m.id for m in listed[1:]]
    assert rest_ids == [c.id, b.id]


@pytest.mark.asyncio
async def test_pinned_dashboards_cannot_be_deleted(tmp_path):
    chat = _FakeChat("<!doctype html><html><body>x</body></html>")
    studio = DashboardStudio(
        ha_client_provider=lambda: _make_ha_client(),
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    m = await studio.generate("safe")
    studio.set_pinned(m.id, True)
    assert studio.delete_dashboard(m.id) is False
    assert (tmp_path / f"{m.id}.html").exists()


@pytest.mark.asyncio
async def test_delete_unpinned_dashboard_removes_files(tmp_path):
    chat = _FakeChat("<!doctype html><html><body>x</body></html>")
    studio = DashboardStudio(
        ha_client_provider=lambda: _make_ha_client(),
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    m = await studio.generate("expendable")
    assert studio.delete_dashboard(m.id) is True
    assert not (tmp_path / f"{m.id}.html").exists()
    assert not (tmp_path / f"{m.id}.meta.json").exists()


# ---------------------------------------------------------------------------
# Live state binding
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_live_state_for_returns_only_referenced_entities(tmp_path):
    fake_html = (
        "<!doctype html><html><body>"
        "<span data-entity=\"sensor.kitchen_temperature\">--</span>"
        "</body></html>"
    )
    chat = _FakeChat(fake_html)

    # Custom HA client that records which entity_ids were asked for.
    asked: List[str] = []

    async def fake_get_states(entity_id=None):
        if entity_id is None:
            return [
                {"entity_id": "sensor.kitchen_temperature", "state": "21.4",
                 "attributes": {"unit_of_measurement": "°C"}},
                {"entity_id": "light.unused", "state": "off", "attributes": {}},
            ]
        asked.append(entity_id)
        return {"entity_id": entity_id, "state": "21.4",
                "attributes": {"unit_of_measurement": "°C"},
                "last_updated": "2026-04-19T00:00:00Z"}

    client = MagicMock()
    client.connected = True
    client.get_states = fake_get_states

    studio = DashboardStudio(
        ha_client_provider=lambda: client,
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    meta = await studio.generate("temp")
    state_map = await studio.live_state_for(meta.id)

    assert "sensor.kitchen_temperature" in state_map
    assert state_map["sensor.kitchen_temperature"]["state"] == "21.4"
    assert state_map["sensor.kitchen_temperature"]["attributes"]["unit_of_measurement"] == "°C"
    # We must NOT have queried entities that aren't in the dashboard.
    assert asked == ["sensor.kitchen_temperature"]


@pytest.mark.asyncio
async def test_live_state_for_returns_empty_when_ha_disconnected(tmp_path):
    chat = _FakeChat("<!doctype html><html><body>"
                     "<span data-entity=\"sensor.x\">--</span></body></html>")
    client = MagicMock()
    client.connected = False
    client.get_states = AsyncMock(return_value=[])
    studio = DashboardStudio(
        ha_client_provider=lambda: client,
        store_dir=tmp_path,
        chat_provider_factory=_factory(chat),
    )
    # We need to bypass the disconnected check at generation time so the
    # studio still produces a dashboard for the test.
    client.connected = True
    meta = await studio.generate("x")
    client.connected = False

    assert await studio.live_state_for(meta.id) == {}


# ---------------------------------------------------------------------------
# Provider routing
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_provider_kwarg_overrides_default_and_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    seen: Dict[str, Any] = {}

    def factory(provider=None, **_):
        seen["provider"] = provider
        return _FakeChat("<!doctype html><html><body>x</body></html>")

    studio = DashboardStudio(
        ha_client_provider=lambda: _make_ha_client(),
        store_dir=tmp_path,
        chat_provider_factory=factory,
        default_provider="openai",
    )
    await studio.generate("hi", provider="github")
    assert seen["provider"] == "github"
