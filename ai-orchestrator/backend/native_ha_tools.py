"""Self-contained Home Assistant tool surface.

Phase 8.5: removes the OpenClaw HASS_MCP add-on as a prerequisite by
exposing a native discovery + control toolset built directly on top
of the existing :class:`HAWebSocketClient`. The deep reasoner can now
operate fully without any external MCP server connected; an external
MCP, if present, is purely additive.

Every tool returns a normalised ``{"ok": bool, ...}`` dict shaped
the same way :class:`ExternalMCPClient.call_tool` does, so the
reasoning harness sees a uniform tool result shape.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool schemas (OpenAI / function-calling format)
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "ha_list_entities",
            "description": (
                "List Home Assistant entities. Optional filter by domain "
                "(e.g. 'light', 'climate', 'binary_sensor') and/or by a "
                "case-insensitive substring of the entity_id or friendly "
                "name. Returns entity_id, state, friendly_name, domain."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain filter, optional."},
                    "query": {"type": "string", "description": "Substring filter, optional."},
                    "limit": {"type": "integer", "description": "Max results (default 100)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ha_get_state",
            "description": (
                "Get the full state and attributes of a single entity by "
                "entity_id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string"},
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ha_search_entities",
            "description": (
                "Free-text search across entity_ids and friendly names. "
                "Use this when you don't know the exact entity_id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ha_list_domains",
            "description": "List all entity domains currently present in Home Assistant.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ha_list_services",
            "description": (
                "List Home Assistant services. Optional domain filter "
                "(e.g. 'light' returns turn_on/turn_off/toggle/…)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ha_call_service",
            "description": (
                "Call any Home Assistant service. This is a mutating tool "
                "and will be intercepted by the plan/auto modes for "
                "approval. Prefer the safety-checked specialist tools "
                "(turn_on_light, set_temperature, …) when they fit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "service": {"type": "string"},
                    "entity_id": {"type": "string", "description": "Target entity, optional."},
                    "data": {"type": "object", "description": "Extra service data, optional."},
                },
                "required": ["domain", "service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ha_summarise_area",
            "description": (
                "Summarise the state of a logical room/area by matching "
                "entity_ids whose names contain the area substring. "
                "Useful when there's no first-class area registry call."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {"type": "string", "description": "Area name fragment, e.g. 'kitchen'."},
                    "domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Restrict to these domains (optional).",
                    },
                },
                "required": ["area"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------
class NativeHATools:
    """Adapter exposing :class:`HAWebSocketClient` as a tool registry."""

    PROVIDER = "native_ha"
    PREFIX = ""  # tools already namespaced with ``ha_`` in their schemas

    def __init__(
        self,
        ha_client: Any,
        service_executor: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
    ) -> None:
        self.ha_client = ha_client
        self.service_executor = service_executor

    # ---- registry interface -----------------------------------------------
    def tool_schemas(self) -> List[Dict[str, Any]]:
        return [dict(s) for s in TOOL_SCHEMAS]

    def tool_names(self) -> List[str]:
        return [s["function"]["name"] for s in TOOL_SCHEMAS]

    async def call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        handler: Optional[Callable[..., Awaitable[Dict[str, Any]]]] = getattr(
            self, f"_t_{name}", None
        )
        if handler is None:
            return {"ok": False, "error": f"unknown_tool:{name}"}
        try:
            return await handler(arguments or {})
        except Exception as exc:
            logger.exception("Native HA tool %s failed", name)
            return {"ok": False, "error": str(exc)}

    # ---- helpers ----------------------------------------------------------
    async def _all_states(self) -> List[Dict[str, Any]]:
        client = self.ha_client
        if client is None:
            raise RuntimeError("ha_client not available")
        states = await client.get_states()
        if isinstance(states, dict):
            return [states]
        return list(states or [])

    @staticmethod
    def _domain(entity_id: str) -> str:
        return entity_id.split(".", 1)[0] if "." in entity_id else ""

    @staticmethod
    def _slim(state: Dict[str, Any]) -> Dict[str, Any]:
        attrs = state.get("attributes") or {}
        return {
            "entity_id": state.get("entity_id"),
            "state": state.get("state"),
            "friendly_name": attrs.get("friendly_name"),
            "domain": NativeHATools._domain(state.get("entity_id", "")),
        }

    # ---- tools ------------------------------------------------------------
    async def _t_ha_list_entities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        domain = (args.get("domain") or "").strip().lower() or None
        query = (args.get("query") or "").strip().lower() or None
        limit = int(args.get("limit") or 100)
        states = await self._all_states()
        out: List[Dict[str, Any]] = []
        for s in states:
            eid = s.get("entity_id") or ""
            if domain and self._domain(eid) != domain:
                continue
            if query:
                fn = ((s.get("attributes") or {}).get("friendly_name") or "").lower()
                if query not in eid.lower() and query not in fn:
                    continue
            out.append(self._slim(s))
            if len(out) >= limit:
                break
        return {"ok": True, "count": len(out), "entities": out}

    async def _t_ha_get_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = (args.get("entity_id") or "").strip()
        if not entity_id:
            return {"ok": False, "error": "entity_id required"}
        try:
            state = await self.ha_client.get_states(entity_id=entity_id)
        except ValueError:
            return {"ok": False, "error": f"entity_not_found:{entity_id}"}
        return {"ok": True, "state": state}

    async def _t_ha_search_entities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = (args.get("query") or "").strip().lower()
        if not query:
            return {"ok": False, "error": "query required"}
        limit = int(args.get("limit") or 25)
        states = await self._all_states()
        hits: List[Dict[str, Any]] = []
        for s in states:
            eid = s.get("entity_id") or ""
            fn = ((s.get("attributes") or {}).get("friendly_name") or "").lower()
            if query in eid.lower() or query in fn:
                hits.append(self._slim(s))
                if len(hits) >= limit:
                    break
        return {"ok": True, "count": len(hits), "matches": hits}

    async def _t_ha_list_domains(self, args: Dict[str, Any]) -> Dict[str, Any]:
        states = await self._all_states()
        counts: Dict[str, int] = {}
        for s in states:
            d = self._domain(s.get("entity_id") or "")
            if d:
                counts[d] = counts.get(d, 0) + 1
        return {
            "ok": True,
            "domains": sorted(
                ({"domain": k, "count": v} for k, v in counts.items()),
                key=lambda x: (-x["count"], x["domain"]),
            ),
        }

    async def _t_ha_list_services(self, args: Dict[str, Any]) -> Dict[str, Any]:
        domain = (args.get("domain") or "").strip().lower() or None
        try:
            services = await self.ha_client.get_services()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        if domain:
            services = {domain: services.get(domain, {})}
        # Trim each service's payload to just the keys (descriptions can be huge).
        trimmed = {
            d: sorted(list((svcs or {}).keys()))
            for d, svcs in (services or {}).items()
        }
        return {"ok": True, "services": trimmed}

    async def _t_ha_call_service(self, args: Dict[str, Any]) -> Dict[str, Any]:
        domain = (args.get("domain") or "").strip()
        service = (args.get("service") or "").strip()
        if not domain or not service:
            return {"ok": False, "error": "domain and service required"}
        entity_id = args.get("entity_id")
        extra = args.get("data") or {}
        if self.service_executor is None:
            return {
                "ok": False,
                "error": "safe_service_executor_unavailable",
                "error_code": "safety_guard_unavailable",
            }
        try:
            return await self.service_executor({
                "domain": domain,
                "service": service,
                "entity_id": entity_id,
                "service_data": extra,
            })
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def _t_ha_summarise_area(self, args: Dict[str, Any]) -> Dict[str, Any]:
        area = (args.get("area") or "").strip().lower()
        if not area:
            return {"ok": False, "error": "area required"}
        domains = {d.lower() for d in (args.get("domains") or [])}
        states = await self._all_states()
        matches: List[Dict[str, Any]] = []
        for s in states:
            eid = (s.get("entity_id") or "").lower()
            fn = ((s.get("attributes") or {}).get("friendly_name") or "").lower()
            if area not in eid and area not in fn:
                continue
            if domains and self._domain(eid) not in domains:
                continue
            matches.append(self._slim(s))
        # Group by domain for a quick mental picture.
        by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for m in matches:
            by_domain.setdefault(m["domain"], []).append(m)
        return {
            "ok": True,
            "area": area,
            "count": len(matches),
            "by_domain": by_domain,
        }
