"""
External MCP client.

Connects to an **optional** remote Model Context Protocol server
(any MCP-compliant server such as the OpenClaw HASS_MCP add-on at
``http://<ha>:8080/mcp``) over Streamable HTTP, discovers
tools / resources / prompts, and exposes them as a tool-provider that
the reasoning harness can call.

This is intentionally separate from the legacy in-process ``MCPServer``
in ``mcp_server.py`` — that module is a local tool registry and is
*not* MCP-protocol. This module speaks real MCP.

Designed to fail soft: if the SDK is not installed or the server is
unreachable the client surfaces an empty tool list and logs the
reason, so the rest of the orchestrator keeps running.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import-time guard
    from mcp import ClientSession  # type: ignore
    from mcp.client.streamable_http import streamablehttp_client  # type: ignore
    _MCP_AVAILABLE = True
except Exception as _imp_err:  # pragma: no cover
    ClientSession = None  # type: ignore
    streamablehttp_client = None  # type: ignore
    _MCP_AVAILABLE = False
    _MCP_IMPORT_ERROR = _imp_err


@dataclass
class MCPToolSpec:
    """Lightweight description of a remote MCP tool."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    annotations: Dict[str, Any] = field(default_factory=dict)
    server: str = "external"

    def to_openai_schema(self) -> Dict[str, Any]:
        """Render in the OpenAI/Ollama-compatible function-call schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description or self.name,
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            },
        }


@dataclass
class MCPResourceSpec:
    uri: str
    name: str
    description: str = ""
    mime_type: Optional[str] = None


@dataclass
class MCPPromptSpec:
    name: str
    description: str = ""
    arguments: List[Dict[str, Any]] = field(default_factory=list)


class ExternalMCPClient:
    """Long-lived MCP client over Streamable HTTP.

    Parameters
    ----------
    url:
        Full URL to the MCP endpoint, e.g. ``http://homeassistant.local:8080/mcp``.
    token:
        Optional bearer token. Sent as ``Authorization: Bearer <token>``.
    name:
        Logical name used in logs / tool namespacing.
    request_timeout:
        Per-tool-call timeout in seconds.
    """

    def __init__(
        self,
        url: str,
        token: Optional[str] = None,
        name: str = "hass-mcp",
        request_timeout: float = 30.0,
    ) -> None:
        self.url = url
        self.token = token
        self.name = name
        self.request_timeout = request_timeout

        self._stack: Optional[AsyncExitStack] = None
        self._session: Optional[ClientSession] = None  # type: ignore[assignment]
        self._lock = asyncio.Lock()
        self._connected = False

        self.tools: Dict[str, MCPToolSpec] = {}
        self.resources: List[MCPResourceSpec] = []
        self.prompts: List[MCPPromptSpec] = []

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    @property
    def available(self) -> bool:
        return _MCP_AVAILABLE

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Establish the MCP session and discover the tool surface.

        Returns ``True`` on success, ``False`` if the SDK is missing or the
        server is unreachable. Never raises.
        """
        if not _MCP_AVAILABLE:
            logger.warning(
                "External MCP disabled: 'mcp' package not installed (%s)",
                _MCP_IMPORT_ERROR,
            )
            return False

        async with self._lock:
            if self._connected:
                return True
            try:
                headers = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"

                self._stack = AsyncExitStack()
                read, write, _ = await self._stack.enter_async_context(
                    streamablehttp_client(self.url, headers=headers or None)
                )
                self._session = await self._stack.enter_async_context(
                    ClientSession(read, write)
                )
                await self._session.initialize()
                await self._discover()
                self._connected = True
                logger.info(
                    "External MCP connected to %s — %d tools, %d resources, %d prompts",
                    self.url,
                    len(self.tools),
                    len(self.resources),
                    len(self.prompts),
                )
                return True
            except Exception as exc:
                logger.error("External MCP connect failed (%s): %s", self.url, exc)
                await self._safe_close()
                return False

    async def aclose(self) -> None:
        await self._safe_close()

    async def _safe_close(self) -> None:
        self._connected = False
        self._session = None
        stack, self._stack = self._stack, None
        if stack is not None:
            try:
                await stack.aclose()
            except Exception as exc:  # pragma: no cover
                logger.debug("MCP stack close error: %s", exc)

    # ------------------------------------------------------------------
    # discovery
    # ------------------------------------------------------------------
    async def _discover(self) -> None:
        assert self._session is not None
        # Tools
        try:
            tools_resp = await self._session.list_tools()
            self.tools = {
                t.name: MCPToolSpec(
                    name=t.name,
                    description=getattr(t, "description", "") or "",
                    input_schema=getattr(t, "inputSchema", None) or {"type": "object", "properties": {}},
                    output_schema=getattr(t, "outputSchema", None),
                    annotations=(
                        t.annotations.model_dump(exclude_none=True)
                        if getattr(t, "annotations", None) is not None
                        and hasattr(t.annotations, "model_dump")
                        else dict(getattr(t, "annotations", None) or {})
                    ),
                    server=self.name,
                )
                for t in tools_resp.tools
            }
        except Exception as exc:
            logger.warning("MCP list_tools failed: %s", exc)

        # Resources
        try:
            res_resp = await self._session.list_resources()
            self.resources = [
                MCPResourceSpec(
                    uri=str(r.uri),
                    name=getattr(r, "name", "") or "",
                    description=getattr(r, "description", "") or "",
                    mime_type=getattr(r, "mimeType", None),
                )
                for r in res_resp.resources
            ]
        except Exception as exc:
            logger.debug("MCP list_resources failed: %s", exc)

        # Prompts
        try:
            pr_resp = await self._session.list_prompts()
            self.prompts = [
                MCPPromptSpec(
                    name=p.name,
                    description=getattr(p, "description", "") or "",
                    arguments=[a.model_dump() if hasattr(a, "model_dump") else dict(a)
                               for a in (getattr(p, "arguments", None) or [])],
                )
                for p in pr_resp.prompts
            ]
        except Exception as exc:
            logger.debug("MCP list_prompts failed: %s", exc)

    # ------------------------------------------------------------------
    # invocation
    # ------------------------------------------------------------------
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a remote MCP tool. Returns a normalised dict result."""
        if not self._connected or self._session is None:
            return {"ok": False, "error": "mcp_not_connected"}
        if name not in self.tools:
            return {"ok": False, "error": f"unknown_tool:{name}"}

        try:
            res = await asyncio.wait_for(
                self._session.call_tool(name, arguments or {}),
                timeout=self.request_timeout,
            )
        except asyncio.TimeoutError:
            return {"ok": False, "error": "timeout", "timeout": self.request_timeout}
        except Exception as exc:
            logger.exception("MCP call_tool %s failed", name)
            return {"ok": False, "error": str(exc)}

        # Flatten content blocks to text where possible.
        text_chunks: List[str] = []
        structured: Optional[Any] = getattr(res, "structuredContent", None)
        for block in getattr(res, "content", []) or []:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_chunks.append(getattr(block, "text", "") or "")
            elif btype == "json" and structured is None:
                structured = getattr(block, "data", None)
            else:
                # image / resource / unknown — render a stub
                text_chunks.append(f"[{btype} content omitted]")

        return {
            "ok": not getattr(res, "isError", False),
            "is_error": bool(getattr(res, "isError", False)),
            "text": "\n".join(c for c in text_chunks if c).strip(),
            "structured": structured,
        }

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        if not self._connected or self._session is None:
            return {"ok": False, "error": "mcp_not_connected"}
        try:
            res = await asyncio.wait_for(
                self._session.read_resource(uri), timeout=self.request_timeout
            )
        except Exception as exc:
            logger.exception("MCP read_resource %s failed", uri)
            return {"ok": False, "error": str(exc)}
        chunks: List[str] = []
        for c in getattr(res, "contents", []) or []:
            text = getattr(c, "text", None)
            if text:
                chunks.append(text)
        return {"ok": True, "text": "\n".join(chunks).strip()}

    async def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Render an MCP prompt to text.

        The MCP ``prompts/get`` call returns a list of messages; we
        flatten them to a single string the deep reasoner can use as
        a goal. Returns ``{"ok": bool, "text": str, "messages": [...]}``.
        """
        if not self._connected or self._session is None:
            return {"ok": False, "error": "mcp_not_connected"}
        if not any(p.name == name for p in self.prompts):
            return {"ok": False, "error": f"unknown_prompt:{name}"}
        try:
            res = await asyncio.wait_for(
                self._session.get_prompt(name, arguments or {}),
                timeout=self.request_timeout,
            )
        except asyncio.TimeoutError:
            return {"ok": False, "error": "timeout", "timeout": self.request_timeout}
        except Exception as exc:
            logger.exception("MCP get_prompt %s failed", name)
            return {"ok": False, "error": str(exc)}

        messages: List[Dict[str, Any]] = []
        text_parts: List[str] = []
        for m in getattr(res, "messages", []) or []:
            role = getattr(m, "role", "user")
            content = getattr(m, "content", None)
            text = ""
            if content is None:
                pass
            elif isinstance(content, str):
                text = content
            elif getattr(content, "type", None) == "text":
                text = getattr(content, "text", "") or ""
            else:
                # Best-effort string coercion for unknown content blocks.
                text = str(content)
            messages.append({"role": role, "content": text})
            if text:
                text_parts.append(text)

        description = getattr(res, "description", None) or ""
        return {
            "ok": True,
            "name": name,
            "description": description,
            "text": "\n\n".join(text_parts).strip(),
            "messages": messages,
        }

    def prompt_specs(self) -> List[Dict[str, Any]]:
        """Return discovered prompts as plain dicts for API surfaces."""
        return [
            {
                "name": p.name,
                "description": p.description,
                "arguments": list(p.arguments or []),
            }
            for p in self.prompts
        ]

    # ------------------------------------------------------------------
    # introspection helpers used by the harness
    # ------------------------------------------------------------------
    def tool_schemas(self) -> List[Dict[str, Any]]:
        return [t.to_openai_schema() for t in self.tools.values()]

    def tool_summary(self, max_tools: int = 20) -> str:
        lines = [f"External MCP `{self.name}` — {len(self.tools)} tools available."]
        for t in list(self.tools.values())[:max_tools]:
            desc = (t.description or "").strip().splitlines()[0] if t.description else ""
            lines.append(f"  - {t.name}: {desc[:120]}")
        if len(self.tools) > max_tools:
            lines.append(f"  …(+{len(self.tools) - max_tools} more)")
        return "\n".join(lines)
