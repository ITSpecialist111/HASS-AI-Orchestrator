"""Smoke tests for the native HA tool surface (Phase 8.5).

These tests verify the orchestrator's self-contained tool surface
works without any external MCP dependency.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, NonCallableMagicMock

import pytest

from native_ha_tools import NativeHATools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
SAMPLE_STATES = [
    {"entity_id": "light.kitchen_main", "state": "on", "attributes": {"friendly_name": "Kitchen Main"}},
    {"entity_id": "light.kitchen_island", "state": "off", "attributes": {"friendly_name": "Kitchen Island"}},
    {"entity_id": "climate.living_room", "state": "heat", "attributes": {"friendly_name": "Living Room"}},
    {"entity_id": "binary_sensor.front_door", "state": "off", "attributes": {"friendly_name": "Front Door"}},
    {"entity_id": "lock.front_door", "state": "locked", "attributes": {"friendly_name": "Front Door Lock"}},
]


@pytest.fixture
def fake_client():
    client = NonCallableMagicMock()
    client.connected = True
    client.get_states = AsyncMock(return_value=list(SAMPLE_STATES))
    client.get_services = AsyncMock(return_value={
        "light": {"turn_on": {}, "turn_off": {}, "toggle": {}},
        "climate": {"set_temperature": {}, "set_hvac_mode": {}},
    })
    client.call_service = AsyncMock(return_value={"context": {"id": "abc"}})
    return client


@pytest.fixture
def tools(fake_client):
    async def safe_service_executor(arguments):
        try:
            result = await fake_client.call_service(
                domain=arguments["domain"],
                service=arguments["service"],
                entity_id=arguments.get("entity_id"),
                **(arguments.get("service_data") or {}),
            )
            return {"ok": True, "result": result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    return NativeHATools(fake_client, service_executor=safe_service_executor)


# ---------------------------------------------------------------------------
# Schema / dispatch
# ---------------------------------------------------------------------------
def test_tool_schemas_shape(tools):
    schemas = tools.tool_schemas()
    assert len(schemas) == 7
    names = {s["function"]["name"] for s in schemas}
    assert names == {
        "ha_list_entities",
        "ha_get_state",
        "ha_search_entities",
        "ha_list_domains",
        "ha_list_services",
        "ha_call_service",
        "ha_summarise_area",
    }
    # All names are pre-namespaced with ``ha_``.
    assert all(n.startswith("ha_") for n in names)
    assert NativeHATools.PREFIX == ""


@pytest.mark.asyncio
async def test_unknown_tool_returns_error(tools):
    out = await tools.call("ha_does_not_exist", {})
    assert out["ok"] is False
    assert "unknown_tool" in out["error"]


# ---------------------------------------------------------------------------
# ha_list_entities
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_entities_no_filter(tools):
    out = await tools.call("ha_list_entities", {})
    assert out["ok"] is True
    assert out["count"] == 5
    assert out["entities"][0]["entity_id"] == "light.kitchen_main"


@pytest.mark.asyncio
async def test_list_entities_domain_filter(tools):
    out = await tools.call("ha_list_entities", {"domain": "light"})
    assert out["ok"] is True
    assert out["count"] == 2
    assert {e["entity_id"] for e in out["entities"]} == {
        "light.kitchen_main",
        "light.kitchen_island",
    }


@pytest.mark.asyncio
async def test_list_entities_query_filter(tools):
    out = await tools.call("ha_list_entities", {"query": "front"})
    assert out["ok"] is True
    assert out["count"] == 2  # binary_sensor.front_door + lock.front_door


@pytest.mark.asyncio
async def test_list_entities_limit(tools):
    out = await tools.call("ha_list_entities", {"limit": 2})
    assert out["count"] == 2


# ---------------------------------------------------------------------------
# ha_get_state
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_state_success(tools, fake_client):
    fake_client.get_states = AsyncMock(return_value=SAMPLE_STATES[0])
    out = await tools.call("ha_get_state", {"entity_id": "light.kitchen_main"})
    assert out["ok"] is True
    assert out["state"]["entity_id"] == "light.kitchen_main"


@pytest.mark.asyncio
async def test_get_state_missing_entity_id(tools):
    out = await tools.call("ha_get_state", {})
    assert out["ok"] is False
    assert "required" in out["error"]


@pytest.mark.asyncio
async def test_get_state_not_found(tools, fake_client):
    fake_client.get_states = AsyncMock(side_effect=ValueError("nope"))
    out = await tools.call("ha_get_state", {"entity_id": "light.ghost"})
    assert out["ok"] is False
    assert "entity_not_found" in out["error"]


# ---------------------------------------------------------------------------
# ha_search_entities
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_entities(tools):
    out = await tools.call("ha_search_entities", {"query": "kitchen"})
    assert out["ok"] is True
    assert out["count"] == 2


@pytest.mark.asyncio
async def test_search_entities_requires_query(tools):
    out = await tools.call("ha_search_entities", {})
    assert out["ok"] is False


# ---------------------------------------------------------------------------
# ha_list_domains
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_domains_counts(tools):
    out = await tools.call("ha_list_domains", {})
    assert out["ok"] is True
    counts = {d["domain"]: d["count"] for d in out["domains"]}
    assert counts == {"light": 2, "climate": 1, "binary_sensor": 1, "lock": 1}
    # Sorted by count desc.
    assert out["domains"][0]["domain"] == "light"


# ---------------------------------------------------------------------------
# ha_list_services
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_services_all(tools):
    out = await tools.call("ha_list_services", {})
    assert out["ok"] is True
    assert "light" in out["services"]
    assert "turn_on" in out["services"]["light"]


@pytest.mark.asyncio
async def test_list_services_domain_filter(tools):
    out = await tools.call("ha_list_services", {"domain": "light"})
    assert set(out["services"].keys()) == {"light"}


# ---------------------------------------------------------------------------
# ha_call_service
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_call_service_success(tools, fake_client):
    out = await tools.call(
        "ha_call_service",
        {"domain": "light", "service": "turn_on", "entity_id": "light.kitchen_main"},
    )
    assert out["ok"] is True
    fake_client.call_service.assert_awaited_once()


@pytest.mark.asyncio
async def test_call_service_validation(tools):
    out = await tools.call("ha_call_service", {"domain": "light"})
    assert out["ok"] is False
    assert "required" in out["error"]


@pytest.mark.asyncio
async def test_call_service_propagates_error(tools, fake_client):
    fake_client.call_service = AsyncMock(side_effect=RuntimeError("boom"))
    out = await tools.call(
        "ha_call_service", {"domain": "light", "service": "turn_on"}
    )
    assert out["ok"] is False
    assert out["error"] == "boom"


# ---------------------------------------------------------------------------
# ha_summarise_area
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_summarise_area_groups_by_domain(tools):
    out = await tools.call("ha_summarise_area", {"area": "kitchen"})
    assert out["ok"] is True
    assert out["count"] == 2
    assert "light" in out["by_domain"]
    assert len(out["by_domain"]["light"]) == 2


@pytest.mark.asyncio
async def test_summarise_area_with_domain_restriction(tools):
    out = await tools.call(
        "ha_summarise_area", {"area": "front", "domains": ["lock"]}
    )
    assert out["count"] == 1
    assert "lock" in out["by_domain"]


@pytest.mark.asyncio
async def test_summarise_area_requires_area(tools):
    out = await tools.call("ha_summarise_area", {})
    assert out["ok"] is False
