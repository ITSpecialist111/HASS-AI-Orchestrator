"""
Reasoning harness — a proper agentic loop for the orchestrator's
"deep thinking" agent.

Design (Anthropic "Building effective agents", April 2026):

    while not done and budget_remaining:
        response = LLM.chat(messages, tools=tool_schemas)
        if response.tool_calls:
            results = await parallel_execute(response.tool_calls)
            append assistant + tool_result messages
        else:
            return final_answer

Key properties
--------------
* **Provider-agnostic** — pluggable :class:`LLMBackend`. Ships with
  :class:`OllamaToolBackend` (Ollama 0.4+ native tool calling) and
  :class:`AnthropicBackend` (optional, used when an API key is set).
* **Multiple tool providers** — combines a local :class:`MCPServer`
  (legacy in-process tools with safety checks + approval gating) with
  any number of optional :class:`ExternalMCPClient` instances
  (the orchestrator does not require any external MCP server
  — it ships with its own native HA tool surface).
* **Budget caps** — ``max_iterations`` and ``max_tool_calls_per_turn``
  bound runtime cost; exceeded budgets terminate gracefully with a
  partial answer.
* **Observation-driven** — every tool result is fed back into the
  conversation so the model can reason over ground truth.
* **Transparent traces** — every step is recorded for the dashboard /
  decision log.
* **Approval gating** — high-impact tools route through the existing
  :class:`ApprovalQueue` rather than executing directly.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """Normalised LLM output."""

    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw: Any = None

    @property
    def is_final(self) -> bool:
        return not self.tool_calls


@dataclass
class HarnessStep:
    iteration: int
    thought: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class HarnessResult:
    answer: str
    trace: List[HarnessStep] = field(default_factory=list)
    iterations: int = 0
    tool_calls: int = 0
    stopped_reason: str = "final"
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------
class LLMBackend(Protocol):
    name: str

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse: ...


class OllamaToolBackend:
    """Ollama 0.4+ native tool-calling backend.

    Models known to handle tool calling well: ``qwen2.5:14b-instruct``,
    ``qwen2.5:7b-instruct``, ``llama3.1:8b-instruct``, ``mistral-nemo``.
    """

    name = "ollama"

    def __init__(
        self,
        model: str,
        host: Optional[str] = None,
        temperature: float = 0.2,
        num_predict: int = 1500,
    ) -> None:
        import ollama  # local import keeps module importable without ollama

        self.model = model
        self.temperature = temperature
        self.num_predict = num_predict
        self._client = ollama.AsyncClient(host=host or os.getenv("OLLAMA_HOST", "http://localhost:11434"))

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "options": {"temperature": self.temperature, "num_predict": self.num_predict},
            "stream": False,
        }
        if tools:
            kwargs["tools"] = tools
        resp = await self._client.chat(**kwargs)
        msg = resp.get("message", {}) if isinstance(resp, dict) else getattr(resp, "message", {})
        content = (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")) or ""
        raw_calls = (msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)) or []

        calls: List[ToolCall] = []
        for rc in raw_calls:
            fn = rc.get("function", {}) if isinstance(rc, dict) else getattr(rc, "function", {})
            name = fn.get("name") if isinstance(fn, dict) else getattr(fn, "name", None)
            args = fn.get("arguments") if isinstance(fn, dict) else getattr(fn, "arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}
            if not name:
                continue
            calls.append(ToolCall(id=str(uuid.uuid4()), name=name, arguments=args or {}))

        return LLMResponse(content=content.strip(), tool_calls=calls, raw=resp)


class AnthropicBackend:
    """Optional Claude backend (uses the public Anthropic SDK).

    Activated when ``ANTHROPIC_API_KEY`` is set or an explicit ``api_key``
    is supplied. Use for the deep-reasoning agent when local models are
    not strong enough.
    """

    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-opus-4-7",
        api_key: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> None:
        import anthropic  # local import

        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for AnthropicBackend")
        self._client = anthropic.AsyncAnthropic(api_key=key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        # Convert OpenAI-style tools → Anthropic tool schema.
        anthropic_tools = []
        for t in tools:
            fn = t.get("function", {})
            anthropic_tools.append({
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
            })

        # Pull system prompt out of messages.
        system_msgs = [m["content"] for m in messages if m.get("role") == "system"]
        convo = [m for m in messages if m.get("role") != "system"]

        resp = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system="\n\n".join(system_msgs) if system_msgs else None,
            messages=convo,
            tools=anthropic_tools or None,
        )

        text_chunks: List[str] = []
        calls: List[ToolCall] = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_chunks.append(block.text)
            elif btype == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {})))

        return LLMResponse(content="\n".join(text_chunks).strip(), tool_calls=calls, raw=resp)


class OpenAIToolBackend:
    """OpenAI Chat Completions tool-calling backend.

    Speaks the OpenAI ``tools=[{type: "function", function: {...}}]``
    schema. This backend is also reused for GitHub Models (which exposes
    the same wire format at ``https://models.github.ai/inference``);
    :class:`GitHubModelsBackend` is a thin subclass.
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        *,
        name: str = "openai",
        temperature: float = 0.2,
        max_tokens: int = 1500,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai package is required for OpenAIToolBackend") from exc

        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(f"{name}: api_key is required")
        self.name = name
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = AsyncOpenAI(
            api_key=key,
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            default_headers=default_headers or None,
        )

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        resp = await self._client.chat.completions.create(**kwargs)
        if not resp.choices:
            return LLMResponse(content="", tool_calls=[], raw=resp)
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        calls: List[ToolCall] = []
        for tc in (msg.tool_calls or []):
            fn = getattr(tc, "function", None)
            if fn is None:
                continue
            args_raw = getattr(fn, "arguments", "") or "{}"
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
            except json.JSONDecodeError:
                args = {"_raw": args_raw}
            calls.append(ToolCall(id=tc.id, name=fn.name, arguments=args or {}))
        return LLMResponse(content=content, tool_calls=calls, raw=resp)


class GitHubModelsBackend(OpenAIToolBackend):
    """GitHub Models tool-calling backend.

    GitHub Models exposes an OpenAI-compatible API at
    ``https://models.github.ai/inference``. Authentication uses a GitHub
    PAT or fine-grained token with the ``models:read`` scope, sent as
    ``Authorization: Bearer <token>``.
    """

    def __init__(
        self,
        model: str,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        gh_token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_MODELS_TOKEN")
        if not gh_token:
            raise RuntimeError("github: GITHUB_TOKEN (or GITHUB_MODELS_TOKEN) is required")
        super().__init__(
            model=model,
            api_key=gh_token,
            base_url=base_url or "https://models.github.ai/inference",
            name="github",
            **kwargs,
        )


class FoundryAgentBackend:
    """Microsoft Foundry backend (chat-completions or hosted agent).

    Two modes:

    * **Model-deployment mode** (default): treats ``endpoint`` as an
      Azure AI Inference / Foundry chat-completions endpoint and posts
      tool calls in the OpenAI schema. Use this when you have deployed
      a model (e.g. ``gpt-4o``) into a Foundry project.
    * **Hosted-agent mode** (when ``agent_id`` is set): posts to the
      Foundry Agents REST API. Hosted agents manage their own tool
      calls server-side, so the local tool registry is informational
      only — the backend returns the agent's text reply with no
      ``tool_calls`` and the harness terminates after one turn.
    """

    name = "foundry"

    def __init__(
        self,
        endpoint: str,
        *,
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        model: Optional[str] = None,
        agent_id: Optional[str] = None,
        api_version: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> None:
        if not endpoint:
            raise RuntimeError("foundry: endpoint URL is required")
        if not api_key and not bearer_token:
            raise RuntimeError("foundry: either api_key or bearer_token is required")
        try:
            import httpx  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("foundry: 'httpx' is required") from exc
        self._httpx = httpx
        self._endpoint = endpoint.rstrip("/")
        self._model = model or ""
        self._agent_id = agent_id or ""
        self._api_version = api_version or os.getenv("FOUNDRY_API_VERSION", "2024-08-01-preview")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._headers: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["api-key"] = api_key
        if bearer_token:
            self._headers["Authorization"] = f"Bearer {bearer_token}"

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        if self._agent_id:
            return await self._chat_hosted_agent(messages)
        return await self._chat_model_deployment(messages, tools)

    async def _chat_model_deployment(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        if "/deployments/" in self._endpoint:
            url = f"{self._endpoint}/chat/completions?api-version={self._api_version}"
        elif self._model:
            url = f"{self._endpoint}/openai/deployments/{self._model}/chat/completions?api-version={self._api_version}"
        else:
            url = f"{self._endpoint}/chat/completions?api-version={self._api_version}"

        body: Dict[str, Any] = {
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self._model and "/deployments/" not in url:
            body["model"] = self._model
        if tools:
            body["tools"] = tools

        async with self._httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=self._headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices") or []
        if not choices:
            return LLMResponse(content="", tool_calls=[], raw=data)
        msg = choices[0].get("message") or {}
        content = (msg.get("content") or "").strip()
        calls: List[ToolCall] = []
        for tc in (msg.get("tool_calls") or []):
            fn = tc.get("function") or {}
            args_raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
            except json.JSONDecodeError:
                args = {"_raw": args_raw}
            name = fn.get("name")
            if not name:
                continue
            calls.append(ToolCall(id=tc.get("id") or str(uuid.uuid4()), name=name, arguments=args or {}))
        return LLMResponse(content=content, tool_calls=calls, raw=data)

    async def _chat_hosted_agent(self, messages: List[Dict[str, Any]]) -> LLMResponse:
        # Hosted Foundry agents own their tool/runtime stack. We send the
        # latest user message as a thread message and read the agent's
        # text reply. Tool execution happens server-side.
        last_user = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        url = f"{self._endpoint}/agents/{self._agent_id}/runs?api-version={self._api_version}"
        body = {"messages": [{"role": "user", "content": last_user}]}

        async with self._httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=self._headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        # Foundry response shapes vary by API version; handle the common
        # cases pragmatically.
        text = ""
        if isinstance(data, dict):
            if isinstance(data.get("output"), str):
                text = data["output"]
            elif isinstance(data.get("messages"), list) and data["messages"]:
                last = data["messages"][-1]
                if isinstance(last, dict):
                    text = (last.get("content") or last.get("text") or "") if isinstance(last.get("content"), str) else ""
                    if not text and isinstance(last.get("content"), list):
                        text = "\n".join(
                            blk.get("text", "")
                            for blk in last["content"]
                            if isinstance(blk, dict) and blk.get("type") in ("text", "output_text")
                        )
            elif isinstance(data.get("choices"), list) and data["choices"]:
                msg = (data["choices"][0] or {}).get("message") or {}
                text = msg.get("content") or ""
        return LLMResponse(content=(text or "").strip(), tool_calls=[], raw=data)


# ---------------------------------------------------------------------------
# Tool routing
# ---------------------------------------------------------------------------
ToolExecutor = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]


@dataclass
class ToolRoute:
    """Maps a tool name to (provider_label, executor)."""

    provider: str
    schema: Dict[str, Any]
    executor: ToolExecutor


class ToolRegistry:
    """Aggregates tools from multiple providers and routes calls.

    External MCP tools are namespaced when their names collide with local
    tools. Agents call tools by their public name; the registry handles
    dispatch.
    """

    def __init__(self) -> None:
        self._routes: Dict[str, ToolRoute] = {}

    def register(
        self,
        provider: str,
        schemas: List[Dict[str, Any]],
        executor: ToolExecutor,
        prefix: Optional[str] = None,
    ) -> None:
        for schema in schemas:
            fn = schema.get("function") or {}
            base = fn.get("name")
            if not base:
                continue
            name = f"{prefix}{base}" if prefix else base
            if name in self._routes:
                # avoid collisions: prefix the new one
                name = f"{provider}__{base}"
            # rewrite the schema name so the model sees the routed name
            new_schema = {
                "type": "function",
                "function": {**fn, "name": name},
            }
            self._routes[name] = ToolRoute(provider=provider, schema=new_schema, executor=executor)
            # Stash the underlying name so the executor can recover it.
            self._routes[name].executor = self._wrap_executor(base, executor)

    @staticmethod
    def _wrap_executor(base_name: str, executor: ToolExecutor) -> ToolExecutor:
        async def _call(_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
            return await executor(base_name, args)
        return _call

    def schemas(self) -> List[Dict[str, Any]]:
        return [r.schema for r in self._routes.values()]

    def names(self) -> List[str]:
        return list(self._routes.keys())

    async def call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        route = self._routes.get(name)
        if route is None:
            return {"ok": False, "error": f"unknown_tool:{name}"}
        try:
            return await route.executor(name, arguments)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Tool %s raised", name)
            return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------
EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class ReasoningHarness:
    """Recursive tool-use loop ("brain") for the deep reasoning agent."""

    def __init__(
        self,
        llm: LLMBackend,
        tools: ToolRegistry,
        system_prompt: str,
        *,
        max_iterations: int = 12,
        max_tool_calls_per_turn: int = 5,
        on_event: Optional[EventCallback] = None,
        tool_call_interceptor: Optional[Any] = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.max_tool_calls_per_turn = max_tool_calls_per_turn
        self.on_event = on_event
        # Optional dry-run interceptor with ``async call(name, args)``
        # and ``set_iteration(int)`` (see :mod:`plan_executor`).
        self.tool_call_interceptor = tool_call_interceptor

    async def run(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> HarnessResult:
        started = time.monotonic()
        user_payload = goal.strip()
        if context:
            user_payload += "\n\nContext:\n" + json.dumps(context, indent=2, default=str)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_payload},
        ]
        trace: List[HarnessStep] = []
        total_tool_calls = 0
        schemas = self.tools.schemas()

        for iteration in range(1, self.max_iterations + 1):
            step_started = time.monotonic()
            if self.tool_call_interceptor is not None and hasattr(self.tool_call_interceptor, "set_iteration"):
                try:
                    self.tool_call_interceptor.set_iteration(iteration)
                except Exception:
                    pass
            try:
                response = await self.llm.chat(messages, schemas)
            except Exception as exc:
                logger.exception("LLM call failed at iteration %d", iteration)
                return HarnessResult(
                    answer=f"LLM error: {exc}",
                    trace=trace,
                    iterations=iteration - 1,
                    tool_calls=total_tool_calls,
                    stopped_reason="llm_error",
                    duration_ms=int((time.monotonic() - started) * 1000),
                )

            await self._emit({"type": "thought", "iteration": iteration, "content": response.content})

            if response.is_final:
                trace.append(HarnessStep(
                    iteration=iteration,
                    thought=response.content,
                    duration_ms=int((time.monotonic() - step_started) * 1000),
                ))
                return HarnessResult(
                    answer=response.content,
                    trace=trace,
                    iterations=iteration,
                    tool_calls=total_tool_calls,
                    stopped_reason="final",
                    duration_ms=int((time.monotonic() - started) * 1000),
                )

            # Cap tool calls per turn to bound cost.
            calls = response.tool_calls[: self.max_tool_calls_per_turn]
            total_tool_calls += len(calls)

            # Append assistant turn (with tool calls) to history.
            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                    }
                    for c in calls
                ],
            })

            # Execute in parallel, preserving order.
            dispatch = (
                self.tool_call_interceptor.call
                if self.tool_call_interceptor is not None
                else self.tools.call
            )
            results = await asyncio.gather(
                *[dispatch(c.name, c.arguments) for c in calls],
                return_exceptions=False,
            )

            step_calls: List[Dict[str, Any]] = []
            step_results: List[Dict[str, Any]] = []
            for call, result in zip(calls, results):
                step_calls.append({"id": call.id, "name": call.name, "arguments": call.arguments})
                step_results.append({"id": call.id, "name": call.name, "result": result})
                # Tool result message back to the model.
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": _serialise_result(result),
                })
                await self._emit({
                    "type": "tool_call",
                    "iteration": iteration,
                    "name": call.name,
                    "arguments": call.arguments,
                    "result": result,
                })

            trace.append(HarnessStep(
                iteration=iteration,
                thought=response.content,
                tool_calls=step_calls,
                tool_results=step_results,
                duration_ms=int((time.monotonic() - step_started) * 1000),
            ))

        # Budget exhausted.
        return HarnessResult(
            answer="Maximum reasoning iterations reached without a final answer.",
            trace=trace,
            iterations=self.max_iterations,
            tool_calls=total_tool_calls,
            stopped_reason="max_iterations",
            duration_ms=int((time.monotonic() - started) * 1000),
        )

    async def _emit(self, event: Dict[str, Any]) -> None:
        if self.on_event is None:
            return
        try:
            await self.on_event(event)
        except Exception as exc:  # pragma: no cover
            logger.debug("on_event callback failed: %s", exc)


def _serialise_result(result: Any) -> str:
    """Best-effort JSON serialisation of a tool result for the LLM."""
    try:
        return json.dumps(result, default=str)[:8000]
    except (TypeError, ValueError):
        return str(result)[:8000]
