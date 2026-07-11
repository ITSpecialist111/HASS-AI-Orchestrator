"""
Reasoning harness — a proper agentic loop for the orchestrator's
"deep thinking" agent.

Design (2026 provider-neutral deterministic kernel):

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
* **Deterministic execution** — schema validation, ordered mutations,
    read-only parallelism, bounded retries, deduplication, and hard budgets.
* **Provider-native continuity** — GPT-5.6 Responses reasoning state and
    Claude adaptive-thinking/tool blocks are preserved across turns.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import inspect
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Protocol, Union

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - dependency is declared, guard keeps imports fail-soft
    Draft202012Validator = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ReasoningProfile:
    """Immutable model and run policy selected for one reasoning run.

    Profiles tune how much model-side reasoning and runtime budget a goal
    receives. They never relax schema validation, approval gates, tool
    ordering, retries, deduplication, or any other deterministic policy.
    """

    name: str
    label: str
    description: str
    think: bool
    temperature: float
    top_p: float
    top_k: int
    num_predict: int
    max_iterations: int
    max_tool_calls_per_turn: int
    max_total_tool_calls: int
    max_run_seconds: float
    llm_timeout_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "thinking": self.think,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_output_tokens": self.num_predict,
            "max_iterations": self.max_iterations,
            "max_tool_calls_per_turn": self.max_tool_calls_per_turn,
            "max_total_tool_calls": self.max_total_tool_calls,
            "max_run_seconds": self.max_run_seconds,
            "llm_timeout_seconds": self.llm_timeout_seconds,
        }


# Gemma 4's recommended generation sampling is shared by all profiles.
# Speed/depth comes from explicit thinking and bounded output/runtime budgets,
# not from weakening the deterministic action kernel.
REASONING_PROFILES: Dict[str, ReasoningProfile] = {
    "rapid": ReasoningProfile(
        name="rapid",
        label="Rapid",
        description="Fast state checks and simple, low-latency routines.",
        think=False,
        temperature=1.0,
        top_p=0.95,
        top_k=64,
        num_predict=1024,
        max_iterations=6,
        max_tool_calls_per_turn=3,
        max_total_tool_calls=12,
        max_run_seconds=60.0,
        llm_timeout_seconds=45.0,
    ),
    "balanced": ReasoningProfile(
        name="balanced",
        label="Balanced",
        description="Thoughtful everyday planning with bounded latency.",
        think=True,
        temperature=1.0,
        top_p=0.95,
        top_k=64,
        num_predict=3072,
        max_iterations=12,
        max_tool_calls_per_turn=5,
        max_total_tool_calls=30,
        max_run_seconds=180.0,
        llm_timeout_seconds=120.0,
    ),
    "deep": ReasoningProfile(
        name="deep",
        label="Deep",
        description="Extended analysis for complex, multi-system goals.",
        think=True,
        temperature=1.0,
        top_p=0.95,
        top_k=64,
        num_predict=4096,
        max_iterations=40,
        max_tool_calls_per_turn=6,
        max_total_tool_calls=200,
        max_run_seconds=1800.0,
        llm_timeout_seconds=600.0,
    ),
}


def resolve_reasoning_profile(profile: Optional[str]) -> ReasoningProfile:
    """Return a validated profile, defaulting to ``balanced``."""

    name = (profile or "balanced").strip().lower()
    resolved = REASONING_PROFILES.get(name)
    if resolved is None:
        raise ValueError(
            f"profile must be one of {'|'.join(REASONING_PROFILES)}"
        )
    return resolved


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
    # Provider-native assistant content that must be round-tripped unchanged
    # (for example Claude adaptive-thinking signatures).
    provider_payload: Any = None
    # Opaque state used by stateful APIs such as OpenAI Responses.
    continuation: Any = None
    usage: Dict[str, int] = field(default_factory=dict)
    stop_reason: Optional[str] = None

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
    run_id: Optional[str] = None
    profile: Optional[str] = None
    requested_tool_calls: int = 0
    rejected_tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0
    cached_tool_calls: int = 0
    usage: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSemantics:
    """Execution properties used by the deterministic tool scheduler.

    These properties are application policy, not model hints. Remote MCP
    annotations are never trusted automatically.
    """

    read_only: bool = False
    destructive: bool = True
    idempotent: bool = False
    parallel_safe: bool = False
    impact_level: str = "high"
    timeout_seconds: float = 30.0
    max_retries: int = 0


@dataclass(frozen=True)
class ToolExecutionContext:
    """Trusted context supplied by the application, never by the model."""

    run_id: Optional[str] = None
    mode: str = "execute"
    approved: bool = False
    plan_id: Optional[str] = None


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------
class LLMBackend(Protocol):
    name: str

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        *,
        continuation: Any = None,
        profile: Optional[str] = None,
    ) -> LLMResponse: ...


class OllamaToolBackend:
    """Ollama native tool-calling backend, tuned for ``gemma4:e4b``."""

    name = "ollama"

    def __init__(
        self,
        model: str,
        host: Optional[str] = None,
        temperature: float = 1.0,
        top_p: float = 0.95,
        top_k: int = 64,
        num_predict: int = 3072,
        default_profile: str = "balanced",
    ) -> None:
        import ollama  # local import keeps module importable without ollama

        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.num_predict = num_predict
        self.default_profile = resolve_reasoning_profile(default_profile).name
        self._client = ollama.AsyncClient(host=host or os.getenv("OLLAMA_HOST", "http://localhost:11434"))

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        *,
        continuation: Any = None,
        profile: Optional[str] = None,
    ) -> LLMResponse:
        selected = resolve_reasoning_profile(profile or self.default_profile)
        temperature = selected.temperature if profile else self.temperature
        top_p = selected.top_p if profile else self.top_p
        top_k = selected.top_k if profile else self.top_k
        num_predict = selected.num_predict if profile else self.num_predict
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "num_predict": num_predict,
            },
            # Ollama exposes thinking as a top-level chat parameter. Keep it
            # out of ``options`` so the SDK sends the documented wire shape.
            "think": selected.think,
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

        usage = _normalise_usage({
            "input_tokens": _get_value(resp, "prompt_eval_count", 0),
            "output_tokens": _get_value(resp, "eval_count", 0),
        })
        # Ollama returns model reasoning separately as ``message.thinking``.
        # It is intentionally not copied into content/history/traces: the
        # operator sees actions and outcomes, while subsequent turns receive
        # only protocol-required assistant content and tool calls.
        return LLMResponse(
            content=content.strip(),
            tool_calls=calls,
            raw=resp,
            usage=usage,
            stop_reason=_get_value(resp, "done_reason", None),
        )


class AnthropicBackend:
    """Optional Claude backend (uses the public Anthropic SDK).

    Activated when ``ANTHROPIC_API_KEY`` is set or an explicit ``api_key``
    is supplied. Use for the deep-reasoning agent when local models are
    not strong enough.
    """

    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-opus-4-8",
        api_key: Optional[str] = None,
        max_tokens: int = 8192,
        effort: str = "medium",
        adaptive_thinking: bool = True,
        strict_tools: bool = True,
    ) -> None:
        import anthropic  # local import

        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for AnthropicBackend")
        self._client = anthropic.AsyncAnthropic(api_key=key)
        self.model = model
        self.max_tokens = max_tokens
        self.effort = _validate_effort(effort)
        self.adaptive_thinking = adaptive_thinking
        self.strict_tools = strict_tools

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        *,
        continuation: Any = None,
        profile: Optional[str] = None,
    ) -> LLMResponse:
        # Convert OpenAI-style tools → Anthropic tool schema.
        anthropic_tools = []
        for t in tools:
            fn = t.get("function", {})
            input_schema = copy.deepcopy(
                fn.get("parameters") or {"type": "object", "properties": {}}
            )
            if input_schema.get("type") == "object":
                input_schema.setdefault("additionalProperties", False)
            converted = {
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "input_schema": input_schema,
            }
            if self.strict_tools and _strict_schema_eligible(input_schema):
                converted["strict"] = True
            anthropic_tools.append(converted)

        # Pull system prompt out of messages.
        system_msgs = [m["content"] for m in messages if m.get("role") == "system"]
        convo = _to_anthropic_messages(messages)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": convo,
        }
        if system_msgs:
            kwargs["system"] = "\n\n".join(system_msgs)
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
        if _supports_adaptive_thinking(self.model):
            kwargs["output_config"] = {"effort": self.effort}
            if self.adaptive_thinking:
                # Omitted summaries reduce latency while signed thinking blocks
                # are still round-tripped for interleaved tool reasoning.
                kwargs["thinking"] = {"type": "adaptive", "display": "omitted"}

        resp = await self._client.messages.create(
            **kwargs,
        )

        text_chunks: List[str] = []
        calls: List[ToolCall] = []
        provider_payload: List[Dict[str, Any]] = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            provider_payload.append(_model_dump(block))
            if btype == "text":
                text_chunks.append(block.text)
            elif btype == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {})))

        usage_obj = getattr(resp, "usage", None)
        output_details = getattr(usage_obj, "output_tokens_details", None)
        usage = _normalise_usage({
            "input_tokens": _get_value(usage_obj, "input_tokens", 0),
            "output_tokens": _get_value(usage_obj, "output_tokens", 0),
            "cached_input_tokens": (
                _get_value(usage_obj, "cache_read_input_tokens", 0)
            ),
            "cache_write_tokens": (
                _get_value(usage_obj, "cache_creation_input_tokens", 0)
            ),
            "reasoning_tokens": _get_value(output_details, "thinking_tokens", 0),
        })
        return LLMResponse(
            content="\n".join(text_chunks).strip(),
            tool_calls=calls,
            raw=resp,
            provider_payload=provider_payload,
            usage=usage,
            stop_reason=getattr(resp, "stop_reason", None),
        )


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
        *,
        continuation: Any = None,
        profile: Optional[str] = None,
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
        usage_obj = getattr(resp, "usage", None)
        usage = _normalise_usage({
            "input_tokens": _get_value(usage_obj, "prompt_tokens", 0),
            "output_tokens": _get_value(usage_obj, "completion_tokens", 0),
        })
        return LLMResponse(
            content=content,
            tool_calls=calls,
            raw=resp,
            usage=usage,
            stop_reason=getattr(resp.choices[0], "finish_reason", None),
        )


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


class OpenAIResponsesBackend:
    """OpenAI Responses API backend for GPT-5.6-class reasoning models.

    The Responses API preserves model reasoning between tool turns via
    ``previous_response_id``. Only newly-produced tool outputs are sent on
    continuation calls, avoiding duplicated history and retaining reasoning
    items that Chat Completions cannot represent.
    """

    name = "openai"

    def __init__(
        self,
        model: str = "gpt-5.6-terra",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        *,
        effort: str = "medium",
        max_output_tokens: int = 8192,
        store: bool = False,
    ) -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai package is required for OpenAIResponsesBackend") from exc
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("openai: api_key is required")
        self.model = model
        self.effort = _validate_effort(effort)
        self.max_output_tokens = max_output_tokens
        self.store = store
        self._client = AsyncOpenAI(
            api_key=key,
            base_url=base_url or os.getenv("OPENAI_BASE_URL") or None,
        )

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        *,
        continuation: Any = None,
        profile: Optional[str] = None,
    ) -> LLMResponse:
        state = continuation if isinstance(continuation, Mapping) else {}
        consumed = int(state.get("consumed_messages", 0) or 0)
        previous_response_id = state.get("previous_response_id")
        history_items = list(state.get("history_items") or [])
        continuing = bool(previous_response_id or history_items)
        new_messages = messages[consumed:] if continuing else messages

        instructions = "\n\n".join(
            str(m.get("content") or "")
            for m in messages
            if m.get("role") == "system"
        )
        new_items = _to_openai_response_input(new_messages, continuing=continuing)
        input_items = history_items + new_items if history_items else new_items
        response_tools = []
        for tool in tools:
            fn = tool.get("function") or {}
            parameters = copy.deepcopy(
                fn.get("parameters") or {"type": "object", "properties": {}}
            )
            response_tools.append({
                "type": "function",
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "parameters": parameters,
                # Application-side JSON Schema validation remains authoritative.
                # Enable API strict mode only for schemas that meet its stricter
                # all-properties-required contract.
                "strict": _openai_strict_schema_eligible(parameters),
            })

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "input": input_items,
            "tools": response_tools,
            "max_output_tokens": self.max_output_tokens,
            "reasoning": {"effort": self.effort, "context": "all_turns"},
            "store": self.store,
        }
        if instructions and not previous_response_id:
            kwargs["instructions"] = instructions
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        if not self.store:
            kwargs["include"] = ["reasoning.encrypted_content"]

        resp = await self._client.responses.create(**kwargs)
        calls: List[ToolCall] = []
        text_chunks: List[str] = []
        for item in getattr(resp, "output", []) or []:
            item_type = _get_value(item, "type", None)
            if item_type == "function_call":
                args_raw = _get_value(item, "arguments", "{}") or "{}"
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
                except (json.JSONDecodeError, TypeError, ValueError):
                    args = {"_raw": args_raw}
                calls.append(ToolCall(
                    id=str(_get_value(item, "call_id", None) or _get_value(item, "id", None) or uuid.uuid4()),
                    name=str(_get_value(item, "name", "")),
                    arguments=args or {},
                ))
            elif item_type == "message":
                for block in _get_value(item, "content", []) or []:
                    if _get_value(block, "type", None) in ("output_text", "text"):
                        text_chunks.append(str(_get_value(block, "text", "") or ""))

        if not text_chunks:
            output_text = getattr(resp, "output_text", "") or ""
            if output_text:
                text_chunks.append(output_text)

        usage_obj = getattr(resp, "usage", None)
        output_details = _get_value(usage_obj, "output_tokens_details", None)
        input_details = _get_value(usage_obj, "input_tokens_details", None)
        usage = _normalise_usage({
            "input_tokens": _get_value(usage_obj, "input_tokens", 0),
            "output_tokens": _get_value(usage_obj, "output_tokens", 0),
            "cached_input_tokens": _get_value(input_details, "cached_tokens", 0),
            "reasoning_tokens": _get_value(output_details, "reasoning_tokens", 0),
        })
        output_items = [_model_dump(item) for item in (getattr(resp, "output", []) or [])]
        next_continuation: Dict[str, Any] = {"consumed_messages": len(messages)}
        if self.store:
            next_continuation["previous_response_id"] = getattr(resp, "id", None)
        else:
            next_continuation["history_items"] = input_items + output_items
        return LLMResponse(
            content="\n".join(c for c in text_chunks if c).strip(),
            tool_calls=[c for c in calls if c.name],
            raw=resp,
            continuation=next_continuation,
            usage=usage,
            stop_reason=getattr(resp, "status", None),
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
        *,
        continuation: Any = None,
        profile: Optional[str] = None,
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
        usage_data = data.get("usage") or {}
        usage = _normalise_usage({
            "input_tokens": usage_data.get("prompt_tokens", 0),
            "output_tokens": usage_data.get("completion_tokens", 0),
        })
        return LLMResponse(
            content=content,
            tool_calls=calls,
            raw=data,
            usage=usage,
            stop_reason=choices[0].get("finish_reason"),
        )

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
ToolExecutor = Callable[..., Awaitable[Any]]
ToolValidator = Callable[..., Union[Optional[Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]]
SemanticsResolver = Callable[[Dict[str, Any]], ToolSemantics]


@dataclass
class ToolRoute:
    """Maps a tool name to (provider_label, executor)."""

    provider: str
    base_name: str
    schema: Dict[str, Any]
    executor: ToolExecutor
    semantics_resolver: SemanticsResolver
    validator: Optional[ToolValidator] = None


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
        *,
        semantics: Optional[ToolSemantics] = None,
        semantics_resolver: Optional[Callable[[str, Dict[str, Any]], ToolSemantics]] = None,
        validator: Optional[ToolValidator] = None,
        close_schema: bool = False,
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
            parameters = copy.deepcopy(
                fn.get("parameters") or {"type": "object", "properties": {}}
            )
            if close_schema and parameters.get("type") == "object":
                parameters.setdefault("additionalProperties", False)
            # rewrite the schema name so the model sees the routed name
            new_schema = {
                "type": "function",
                "function": {**fn, "name": name, "parameters": parameters},
            }
            if semantics_resolver is not None:
                route_semantics = lambda args, _base=base: semantics_resolver(_base, args)
            else:
                fixed = semantics or ToolSemantics()
                route_semantics = lambda _args, _fixed=fixed: _fixed
            self._routes[name] = ToolRoute(
                provider=provider,
                base_name=base,
                schema=new_schema,
                executor=self._wrap_executor(base, executor),
                semantics_resolver=route_semantics,
                validator=validator,
            )

    @staticmethod
    def _wrap_executor(base_name: str, executor: ToolExecutor) -> ToolExecutor:
        async def _call(
            _name: str,
            args: Dict[str, Any],
            context: Optional[ToolExecutionContext] = None,
        ) -> Any:
            result = _invoke_with_optional_context(executor, base_name, args, context)
            return await result if inspect.isawaitable(result) else result
        return _call

    def schemas(self) -> List[Dict[str, Any]]:
        return [r.schema for r in self._routes.values()]

    def names(self) -> List[str]:
        return list(self._routes.keys())

    def semantics(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolSemantics:
        route = self._routes.get(name)
        if route is None:
            return ToolSemantics()
        try:
            return route.semantics_resolver(arguments or {})
        except Exception:
            logger.exception("Tool semantics resolver failed for %s", name)
            return ToolSemantics()

    async def validate_call(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None,
    ) -> Optional[Dict[str, Any]]:
        route = self._routes.get(name)
        if route is None:
            return _tool_error("unknown_tool", f"Unknown tool: {name}", retryable=False)
        if not isinstance(arguments, dict):
            return _tool_error(
                "invalid_arguments",
                f"Arguments for {name} must be a JSON object.",
                retryable=False,
            )

        parameters = (route.schema.get("function") or {}).get("parameters") or {}
        if Draft202012Validator is not None and parameters:
            try:
                errors = sorted(
                    Draft202012Validator(parameters).iter_errors(arguments),
                    key=lambda e: list(e.absolute_path),
                )
            except Exception as exc:
                logger.warning("Invalid JSON schema for tool %s: %s", name, exc)
                errors = []
            if errors:
                details = []
                for err in errors[:5]:
                    path = ".".join(str(part) for part in err.absolute_path) or "$"
                    details.append({"path": path, "message": err.message})
                return _tool_error(
                    "invalid_arguments",
                    f"Tool arguments failed schema validation for {name}.",
                    retryable=False,
                    details=details,
                )

        if route.validator is not None:
            try:
                validation = _invoke_with_optional_context(
                    route.validator,
                    route.base_name,
                    arguments,
                    context,
                )
                if inspect.isawaitable(validation):
                    validation = await validation
            except Exception as exc:
                logger.exception("Custom validator failed for %s", name)
                return _tool_error(
                    "validator_error",
                    f"Safety validation failed for {name}: {exc}",
                    retryable=False,
                )
            if validation:
                return _normalise_tool_result(validation)
        return None

    async def call(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None,
    ) -> Dict[str, Any]:
        route = self._routes.get(name)
        validation_error = await self.validate_call(name, arguments, context)
        if validation_error is not None:
            return validation_error
        assert route is not None
        semantics = self.semantics(name, arguments)
        try:
            result = await asyncio.wait_for(
                _invoke_executor(route.executor, name, arguments, context),
                timeout=max(0.1, semantics.timeout_seconds),
            )
            return _normalise_tool_result(result)
        except asyncio.TimeoutError:
            return _tool_error(
                "timeout",
                f"Tool {name} timed out after {semantics.timeout_seconds:g}s.",
                retryable=semantics.read_only or semantics.idempotent,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Tool %s raised", name)
            return _tool_error(
                "execution_error",
                f"{type(exc).__name__}: {exc}",
                retryable=semantics.read_only or semantics.idempotent,
            )


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
        max_total_tool_calls: int = 30,
        max_run_seconds: float = 180.0,
        llm_timeout_seconds: float = 120.0,
        max_parallel_tools: int = 5,
        max_repeated_tool_calls: int = 2,
        max_consecutive_tool_error_turns: int = 3,
        max_tool_result_chars: int = 12000,
        max_context_chars: int = 250000,
        on_event: Optional[EventCallback] = None,
        tool_call_interceptor: Optional[Any] = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_iterations = max(1, int(max_iterations))
        self.max_tool_calls_per_turn = max(1, int(max_tool_calls_per_turn))
        self.max_total_tool_calls = max(1, int(max_total_tool_calls))
        self.max_run_seconds = max(1.0, float(max_run_seconds))
        self.llm_timeout_seconds = max(0.01, float(llm_timeout_seconds))
        self.max_parallel_tools = max(1, int(max_parallel_tools))
        self.max_repeated_tool_calls = max(1, int(max_repeated_tool_calls))
        self.max_consecutive_tool_error_turns = max(1, int(max_consecutive_tool_error_turns))
        self.max_tool_result_chars = max(1000, int(max_tool_result_chars))
        self.max_context_chars = max(10000, int(max_context_chars))
        self.on_event = on_event
        # Optional dry-run interceptor with ``async call(name, args)``
        # and ``set_iteration(int)`` (see :mod:`plan_executor`).
        self.tool_call_interceptor = tool_call_interceptor

    async def run(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        *,
        run_id: Optional[str] = None,
        mode: str = "execute",
        profile: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_event: Optional[EventCallback] = None,
        tool_call_interceptor: Optional[Any] = None,
    ) -> HarnessResult:
        started = time.monotonic()
        selected_profile = resolve_reasoning_profile(profile) if profile else None
        effective_max_iterations = min(
            self.max_iterations,
            selected_profile.max_iterations if selected_profile else self.max_iterations,
        )
        effective_max_tool_calls_per_turn = min(
            self.max_tool_calls_per_turn,
            selected_profile.max_tool_calls_per_turn
            if selected_profile else self.max_tool_calls_per_turn,
        )
        effective_max_total_tool_calls = min(
            self.max_total_tool_calls,
            selected_profile.max_total_tool_calls
            if selected_profile else self.max_total_tool_calls,
        )
        effective_max_run_seconds = min(
            self.max_run_seconds,
            selected_profile.max_run_seconds if selected_profile else self.max_run_seconds,
        )
        effective_llm_timeout_seconds = min(
            self.llm_timeout_seconds,
            selected_profile.llm_timeout_seconds
            if selected_profile else self.llm_timeout_seconds,
        )
        run_id = run_id or uuid.uuid4().hex
        event_callback = on_event if on_event is not None else self.on_event
        interceptor = (
            tool_call_interceptor
            if tool_call_interceptor is not None
            else self.tool_call_interceptor
        )
        user_payload = goal.strip()
        if context:
            user_payload += "\n\nContext:\n" + json.dumps(context, indent=2, default=str)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt or self.system_prompt},
            {"role": "user", "content": user_payload},
        ]
        trace: List[HarnessStep] = []
        total_tool_calls = 0
        requested_tool_calls = 0
        rejected_tool_calls = 0
        successful_tool_calls = 0
        failed_tool_calls = 0
        cached_tool_calls = 0
        usage: Dict[str, int] = {}
        continuation: Any = None
        repeated_calls: Dict[str, int] = {}
        successful_results: Dict[str, Dict[str, Any]] = {}
        read_cache: Dict[str, Dict[str, Any]] = {}
        consecutive_tool_error_turns = 0
        schemas = self.tools.schemas()
        execution_context = ToolExecutionContext(run_id=run_id, mode=mode)

        for iteration in range(1, effective_max_iterations + 1):
            step_started = time.monotonic()
            elapsed = time.monotonic() - started
            if elapsed >= effective_max_run_seconds:
                return self._build_result(
                    answer="The reasoning run reached its wall-clock budget before completion.",
                    trace=trace,
                    iterations=iteration - 1,
                    tool_calls=total_tool_calls,
                    stopped_reason="time_budget",
                    started=started,
                    run_id=run_id,
                    requested=requested_tool_calls,
                    rejected=rejected_tool_calls,
                    successful=successful_tool_calls,
                    failed=failed_tool_calls,
                    cached=cached_tool_calls,
                    profile=selected_profile.name if selected_profile else None,
                    usage=usage,
                )
            if _estimate_messages_chars(messages) > self.max_context_chars:
                return self._build_result(
                    answer=(
                        "The reasoning run reached its context budget. Narrow the goal "
                        "or use more selective discovery filters."
                    ),
                    trace=trace,
                    iterations=iteration - 1,
                    tool_calls=total_tool_calls,
                    stopped_reason="context_budget",
                    started=started,
                    run_id=run_id,
                    requested=requested_tool_calls,
                    rejected=rejected_tool_calls,
                    successful=successful_tool_calls,
                    failed=failed_tool_calls,
                    cached=cached_tool_calls,
                    profile=selected_profile.name if selected_profile else None,
                    usage=usage,
                )

            if interceptor is not None and hasattr(interceptor, "set_iteration"):
                try:
                    interceptor.set_iteration(iteration)
                except Exception:
                    pass
            try:
                remaining = max(0.1, effective_max_run_seconds - elapsed)
                response = await asyncio.wait_for(
                    self._call_llm(
                        messages,
                        schemas,
                        continuation,
                        selected_profile.name if selected_profile else None,
                    ),
                    timeout=min(effective_llm_timeout_seconds, remaining),
                )
            except asyncio.TimeoutError:
                logger.error("LLM call timed out at iteration %d", iteration)
                return self._build_result(
                    answer=f"LLM timeout after {min(effective_llm_timeout_seconds, remaining):g}s.",
                    trace=trace,
                    iterations=iteration - 1,
                    tool_calls=total_tool_calls,
                    stopped_reason="llm_timeout",
                    started=started,
                    run_id=run_id,
                    requested=requested_tool_calls,
                    rejected=rejected_tool_calls,
                    successful=successful_tool_calls,
                    failed=failed_tool_calls,
                    cached=cached_tool_calls,
                    profile=selected_profile.name if selected_profile else None,
                    usage=usage,
                )
            except asyncio.CancelledError:
                await self._emit(
                    {"type": "cancelled", "run_id": run_id, "iteration": iteration},
                    event_callback,
                )
                raise
            except Exception as exc:
                logger.exception("LLM call failed at iteration %d", iteration)
                return self._build_result(
                    answer=f"LLM error: {exc}",
                    trace=trace,
                    iterations=iteration - 1,
                    tool_calls=total_tool_calls,
                    stopped_reason="llm_error",
                    started=started,
                    run_id=run_id,
                    requested=requested_tool_calls,
                    rejected=rejected_tool_calls,
                    successful=successful_tool_calls,
                    failed=failed_tool_calls,
                    cached=cached_tool_calls,
                    profile=selected_profile.name if selected_profile else None,
                    usage=usage,
                )

            continuation = response.continuation
            _merge_usage(usage, response.usage)
            await self._emit({
                "type": "thought",
                "run_id": run_id,
                "iteration": iteration,
                "profile": selected_profile.name if selected_profile else None,
                "content": response.content,
                "usage": response.usage,
            }, event_callback)

            if response.is_final:
                trace.append(HarnessStep(
                    iteration=iteration,
                    thought=response.content,
                    duration_ms=int((time.monotonic() - step_started) * 1000),
                ))
                return self._build_result(
                    answer=response.content,
                    trace=trace,
                    iterations=iteration,
                    tool_calls=total_tool_calls,
                    stopped_reason="final",
                    started=started,
                    run_id=run_id,
                    requested=requested_tool_calls,
                    rejected=rejected_tool_calls,
                    successful=successful_tool_calls,
                    failed=failed_tool_calls,
                    cached=cached_tool_calls,
                    profile=selected_profile.name if selected_profile else None,
                    usage=usage,
                )

            all_calls = response.tool_calls
            requested_tool_calls += len(all_calls)
            remaining_tool_budget = max(0, effective_max_total_tool_calls - total_tool_calls)
            accepted_count = min(
                len(all_calls),
                effective_max_tool_calls_per_turn,
                remaining_tool_budget,
            )
            calls = all_calls[:accepted_count]
            rejected = all_calls[accepted_count:]
            total_tool_calls += len(calls)
            rejected_tool_calls += len(rejected)

            # Append every provider-requested call. Calls rejected by a budget
            # still receive a synthetic result so provider protocols never see
            # unresolved tool_use/function_call records.
            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                    }
                    for c in all_calls
                ],
            }
            if response.provider_payload is not None:
                assistant_message["provider_payload"] = response.provider_payload
            messages.append(assistant_message)

            results = await self._execute_batch(
                calls,
                interceptor=interceptor,
                context=execution_context,
                repeated_calls=repeated_calls,
                successful_results=successful_results,
                read_cache=read_cache,
            )
            budget_results = [
                _tool_error(
                    "tool_budget_exceeded",
                    (
                        f"Tool call {call.name} was not executed because this turn or "
                        "run exhausted its configured tool-call budget."
                    ),
                    retryable=False,
                )
                for call in rejected
            ]
            results.extend(budget_results)

            step_calls: List[Dict[str, Any]] = []
            step_results: List[Dict[str, Any]] = []
            for call, result in zip(all_calls, results):
                step_calls.append({"id": call.id, "name": call.name, "arguments": call.arguments})
                step_results.append({"id": call.id, "name": call.name, "result": result})
                if _result_ok(result):
                    successful_tool_calls += 1
                else:
                    failed_tool_calls += 1
                if bool((result.get("_harness") or {}).get("cached")):
                    cached_tool_calls += 1
                # Tool result message back to the model.
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": _serialise_result(result, self.max_tool_result_chars),
                })
                await self._emit({
                    "type": "tool_call",
                    "run_id": run_id,
                    "iteration": iteration,
                    "name": call.name,
                    "arguments": call.arguments,
                    "result": result,
                }, event_callback)

            trace.append(HarnessStep(
                iteration=iteration,
                thought=response.content,
                tool_calls=step_calls,
                tool_results=step_results,
                duration_ms=int((time.monotonic() - step_started) * 1000),
            ))

            if results and all(not _result_ok(r) for r in results):
                consecutive_tool_error_turns += 1
            else:
                consecutive_tool_error_turns = 0
            if consecutive_tool_error_turns >= self.max_consecutive_tool_error_turns:
                return self._build_result(
                    answer=(
                        "The run stopped after repeated tool-error turns. Review the "
                        "trace and correct the tool inputs or connectivity before retrying."
                    ),
                    trace=trace,
                    iterations=iteration,
                    tool_calls=total_tool_calls,
                    stopped_reason="tool_errors",
                    started=started,
                    run_id=run_id,
                    requested=requested_tool_calls,
                    rejected=rejected_tool_calls,
                    successful=successful_tool_calls,
                    failed=failed_tool_calls,
                    cached=cached_tool_calls,
                    profile=selected_profile.name if selected_profile else None,
                    usage=usage,
                )

        # Budget exhausted.
        return self._build_result(
            answer="Maximum reasoning iterations reached without a final answer.",
            trace=trace,
            iterations=effective_max_iterations,
            tool_calls=total_tool_calls,
            stopped_reason="max_iterations",
            started=started,
            run_id=run_id,
            requested=requested_tool_calls,
            rejected=rejected_tool_calls,
            successful=successful_tool_calls,
            failed=failed_tool_calls,
            cached=cached_tool_calls,
            profile=selected_profile.name if selected_profile else None,
            usage=usage,
        )

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        schemas: List[Dict[str, Any]],
        continuation: Any,
        profile: Optional[str],
    ) -> LLMResponse:
        kwargs: Dict[str, Any] = {}
        if _accepts_keyword(self.llm.chat, "continuation"):
            kwargs["continuation"] = continuation
        if profile and _accepts_keyword(self.llm.chat, "profile"):
            kwargs["profile"] = profile
        if kwargs:
            return await self.llm.chat(messages, schemas, **kwargs)
        # Compatibility for small scripted test/custom backends written against
        # the original two-argument protocol.
        return await self.llm.chat(messages, schemas)

    async def _execute_batch(
        self,
        calls: List[ToolCall],
        *,
        interceptor: Optional[Any],
        context: ToolExecutionContext,
        repeated_calls: Dict[str, int],
        successful_results: Dict[str, Dict[str, Any]],
        read_cache: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not calls:
            return []
        semantics = [self.tools.semantics(c.name, c.arguments) for c in calls]
        can_parallelise = all(s.read_only and s.parallel_safe for s in semantics)

        async def execute(call: ToolCall) -> Dict[str, Any]:
            return await self._execute_one(
                call,
                interceptor=interceptor,
                context=context,
                repeated_calls=repeated_calls,
                successful_results=successful_results,
                read_cache=read_cache,
            )

        if not can_parallelise:
            # Any mutation makes the entire batch ordered. This preserves model
            # call order and prevents read/write races against Home Assistant.
            return [await execute(call) for call in calls]

        semaphore = asyncio.Semaphore(self.max_parallel_tools)

        async def limited(call: ToolCall) -> Dict[str, Any]:
            async with semaphore:
                return await execute(call)

        gathered = await asyncio.gather(
            *(limited(call) for call in calls),
            return_exceptions=True,
        )
        out: List[Dict[str, Any]] = []
        for call, result in zip(calls, gathered):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                out.append(_tool_error(
                    "execution_error",
                    f"{type(result).__name__}: {result}",
                    retryable=False,
                ))
            else:
                out.append(_normalise_tool_result(result))
        return out

    async def _execute_one(
        self,
        call: ToolCall,
        *,
        interceptor: Optional[Any],
        context: ToolExecutionContext,
        repeated_calls: Dict[str, int],
        successful_results: Dict[str, Dict[str, Any]],
        read_cache: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        semantics = self.tools.semantics(call.name, call.arguments)
        fingerprint = _tool_call_fingerprint(call.name, call.arguments)
        repeated_calls[fingerprint] = repeated_calls.get(fingerprint, 0) + 1

        if semantics.read_only and fingerprint in read_cache:
            return _with_harness_meta(read_cache[fingerprint], cached=True, attempts=0)
        if fingerprint in successful_results:
            previous = successful_results[fingerprint]
            if semantics.idempotent:
                return _with_harness_meta(previous, cached=True, deduplicated=True, attempts=0)
            return _tool_error(
                "duplicate_non_idempotent_call",
                f"Repeated non-idempotent call blocked: {call.name}",
                retryable=False,
            )
        if repeated_calls[fingerprint] > self.max_repeated_tool_calls:
            return _tool_error(
                "repeated_call_limit",
                f"Repeated identical call limit reached for {call.name}.",
                retryable=False,
            )

        validation = await self.tools.validate_call(call.name, call.arguments, context)
        if validation is not None:
            return validation

        dispatch = interceptor.call if interceptor is not None else self.tools.call
        retries = max(0, semantics.max_retries if semantics.read_only else 0)
        started = time.monotonic()
        result: Dict[str, Any] = _tool_error("not_executed", "Tool was not executed.")
        attempts = 0
        for attempt in range(retries + 1):
            attempts = attempt + 1
            try:
                invoked = _invoke_with_optional_context(
                    dispatch,
                    call.name,
                    call.arguments,
                    context,
                )
                raw_result = await asyncio.wait_for(
                    invoked if inspect.isawaitable(invoked) else _as_awaitable(invoked),
                    timeout=max(0.1, semantics.timeout_seconds),
                )
                result = _normalise_tool_result(raw_result)
            except asyncio.TimeoutError:
                result = _tool_error(
                    "timeout",
                    f"Tool {call.name} timed out after {semantics.timeout_seconds:g}s.",
                    retryable=semantics.read_only,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                result = _tool_error(
                    "execution_error",
                    f"{type(exc).__name__}: {exc}",
                    retryable=semantics.read_only,
                )
            if _result_ok(result) or not _result_retryable(result) or attempt >= retries:
                break
            await asyncio.sleep(min(1.0, 0.1 * (2 ** attempt)))

        result = _with_harness_meta(
            result,
            attempts=attempts,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        if _result_ok(result):
            successful_results[fingerprint] = copy.deepcopy(result)
            if semantics.read_only:
                read_cache[fingerprint] = copy.deepcopy(result)
            else:
                # A mutation may invalidate every state observation made so far.
                read_cache.clear()
        return result

    @staticmethod
    def _build_result(
        *,
        answer: str,
        trace: List[HarnessStep],
        iterations: int,
        tool_calls: int,
        stopped_reason: str,
        started: float,
        run_id: str,
        requested: int,
        rejected: int,
        successful: int,
        failed: int,
        cached: int,
        profile: Optional[str],
        usage: Dict[str, int],
    ) -> HarnessResult:
        return HarnessResult(
            answer=answer,
            trace=trace,
            iterations=iterations,
            tool_calls=tool_calls,
            stopped_reason=stopped_reason,
            duration_ms=int((time.monotonic() - started) * 1000),
            run_id=run_id,
            profile=profile,
            requested_tool_calls=requested,
            rejected_tool_calls=rejected,
            successful_tool_calls=successful,
            failed_tool_calls=failed,
            cached_tool_calls=cached,
            usage=dict(usage),
        )

    async def _emit(
        self,
        event: Dict[str, Any],
        callback: Optional[EventCallback],
    ) -> None:
        if callback is None:
            return
        try:
            await callback(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover
            logger.debug("on_event callback failed: %s", exc)


def _serialise_result(result: Any, max_chars: int = 12000) -> str:
    """Serialize a result as valid JSON, compacting rather than slicing it.

    Raw string slicing can produce invalid JSON and hide that data was lost.
    The compact envelope preserves success/error fields, reports the original
    size, and includes a recursively-trimmed high-signal prefix.
    """
    normalised = _normalise_tool_result(result)
    try:
        raw = json.dumps(normalised, default=str, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        normalised = {"ok": True, "result": str(result)}
        raw = json.dumps(normalised, ensure_ascii=False, separators=(",", ":"))
    if len(raw) <= max_chars:
        return raw

    compacted = _compact_json_value(normalised, max_items=20, max_string=1200, depth=0)
    envelope = {
        "ok": _result_ok(normalised),
        "truncated": True,
        "original_chars": len(raw),
        "note": "Tool result compacted by the harness; narrow the query or paginate for full data.",
        "data": compacted,
    }
    encoded = json.dumps(envelope, default=str, ensure_ascii=False, separators=(",", ":"))
    while len(encoded) > max_chars and envelope["data"]:
        envelope["data"] = _compact_json_value(
            envelope["data"], max_items=8, max_string=400, depth=0
        )
        encoded = json.dumps(envelope, default=str, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) > max_chars:
            envelope["data"] = {"summary": str(envelope["data"])[: max(100, max_chars // 3)]}
            encoded = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))
            break
    return encoded


def _to_anthropic_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert the harness's OpenAI-style history to Claude content blocks."""
    out: List[Dict[str, Any]] = []
    index = 0
    while index < len(messages):
        message = messages[index]
        role = message.get("role")
        if role == "system":
            index += 1
            continue
        if role == "tool":
            results: List[Dict[str, Any]] = []
            while index < len(messages) and messages[index].get("role") == "tool":
                tool_message = messages[index]
                content = str(tool_message.get("content") or "")
                block: Dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": str(tool_message.get("tool_call_id") or ""),
                    "content": content,
                }
                if _serialised_result_is_error(content):
                    block["is_error"] = True
                results.append(block)
                index += 1
            out.append({"role": "user", "content": results})
            continue
        if role == "assistant":
            native_payload = message.get("provider_payload")
            if isinstance(native_payload, list):
                content_blocks = copy.deepcopy(native_payload)
            else:
                content_blocks: List[Dict[str, Any]] = []
                text = str(message.get("content") or "")
                if text:
                    content_blocks.append({"type": "text", "text": text})
                for tool_call in message.get("tool_calls") or []:
                    function = tool_call.get("function") or {}
                    args_raw = function.get("arguments") or "{}"
                    try:
                        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    except (json.JSONDecodeError, TypeError):
                        args = {"_raw": args_raw}
                    content_blocks.append({
                        "type": "tool_use",
                        "id": str(tool_call.get("id") or uuid.uuid4()),
                        "name": str(function.get("name") or ""),
                        "input": args or {},
                    })
            out.append({"role": "assistant", "content": content_blocks})
        else:
            out.append({"role": "user", "content": message.get("content") or ""})
        index += 1
    return out


def _to_openai_response_input(
    messages: List[Dict[str, Any]],
    *,
    continuing: bool,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        if role == "system":
            continue
        if role == "tool":
            items.append({
                "type": "function_call_output",
                "call_id": str(message.get("tool_call_id") or ""),
                "output": str(message.get("content") or ""),
            })
            continue
        # The assistant function calls are already part of the response named by
        # previous_response_id and must not be submitted twice.
        if continuing and role == "assistant" and message.get("tool_calls"):
            continue
        content = message.get("content")
        if content not in (None, ""):
            items.append({"role": role or "user", "content": content})
    return items


def _strict_schema_eligible(schema: Dict[str, Any]) -> bool:
    return isinstance(schema, dict) and schema.get("type") == "object"


def _openai_strict_schema_eligible(schema: Dict[str, Any]) -> bool:
    if not _strict_schema_eligible(schema):
        return False
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    return schema.get("additionalProperties") is False and required == set(properties)


def _supports_adaptive_thinking(model: str) -> bool:
    lowered = (model or "").lower()
    return any(token in lowered for token in (
        "claude-opus-4-6",
        "claude-opus-4-7",
        "claude-opus-4-8",
        "claude-sonnet-4-6",
        "claude-sonnet-5",
        "claude-fable-5",
        "claude-mythos",
    ))


def _validate_effort(effort: str) -> str:
    value = (effort or "medium").strip().lower()
    if value not in {"none", "low", "medium", "high", "xhigh", "max"}:
        raise ValueError("effort must be one of none|low|medium|high|xhigh|max")
    return value


def _model_dump(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    if isinstance(value, dict):
        return copy.deepcopy(value)
    return {"type": _get_value(value, "type", "unknown"), "value": str(value)}


def _get_value(value: Any, key: str, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _normalise_usage(usage: Mapping[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for key, value in usage.items():
        try:
            number = int(value or 0)
        except (TypeError, ValueError):
            continue
        if number:
            out[key] = number
    return out


def _merge_usage(total: Dict[str, int], update: Optional[Mapping[str, Any]]) -> None:
    for key, value in (update or {}).items():
        try:
            total[key] = total.get(key, 0) + int(value or 0)
        except (TypeError, ValueError):
            continue


def _tool_error(
    code: str,
    message: str,
    *,
    retryable: bool = False,
    details: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "ok": False,
        "error": message,
        "error_code": code,
        "retryable": bool(retryable),
    }
    if details:
        result["details"] = details
    return result


def _normalise_tool_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        out = copy.deepcopy(result)
    else:
        out = {"result": result}
    if "ok" not in out:
        is_error = bool(out.get("is_error") or out.get("isError"))
        if out.get("error") not in (None, ""):
            is_error = True
        out["ok"] = not is_error
    if not out.get("ok") and "error" not in out:
        out["error"] = "Tool execution failed."
    return out


def _result_ok(result: Any) -> bool:
    return bool(_normalise_tool_result(result).get("ok"))


def _result_retryable(result: Any) -> bool:
    normalised = _normalise_tool_result(result)
    if "retryable" in normalised:
        return bool(normalised.get("retryable"))
    text = f"{normalised.get('error_code', '')} {normalised.get('error', '')}".lower()
    return any(token in text for token in (
        "timeout", "temporar", "connection", "unavailable", "rate limit", "429", "503"
    ))


def _with_harness_meta(result: Dict[str, Any], **metadata: Any) -> Dict[str, Any]:
    out = _normalise_tool_result(result)
    current = dict(out.get("_harness") or {})
    current.update({key: value for key, value in metadata.items() if value is not None})
    out["_harness"] = current
    return out


def _serialised_result_is_error(content: str) -> bool:
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False
    return not _result_ok(parsed)


def _tool_call_fingerprint(name: str, arguments: Dict[str, Any]) -> str:
    canonical = json.dumps(
        {"name": name, "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _estimate_messages_chars(messages: List[Dict[str, Any]]) -> int:
    try:
        return len(json.dumps(messages, default=str, ensure_ascii=False))
    except (TypeError, ValueError):
        return sum(len(str(message)) for message in messages)


def _compact_json_value(
    value: Any,
    *,
    max_items: int,
    max_string: int,
    depth: int,
) -> Any:
    if depth >= 5:
        return str(value)[:max_string]
    if isinstance(value, dict):
        items = list(value.items())
        compacted = {
            str(key): _compact_json_value(
                item,
                max_items=max_items,
                max_string=max_string,
                depth=depth + 1,
            )
            for key, item in items[:max_items]
        }
        if len(items) > max_items:
            compacted["_omitted_keys"] = len(items) - max_items
        return compacted
    if isinstance(value, (list, tuple)):
        compacted_list = [
            _compact_json_value(
                item,
                max_items=max_items,
                max_string=max_string,
                depth=depth + 1,
            )
            for item in list(value)[:max_items]
        ]
        if len(value) > max_items:
            compacted_list.append({"_omitted_items": len(value) - max_items})
        return compacted_list
    if isinstance(value, str) and len(value) > max_string:
        return value[:max_string] + f"…[+{len(value) - max_string} chars]"
    return value


def _accepts_keyword(callable_obj: Callable[..., Any], keyword: str) -> bool:
    try:
        parameters = inspect.signature(callable_obj).parameters
    except (TypeError, ValueError):
        return False
    return keyword in parameters or any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )


def _invoke_with_optional_context(
    callable_obj: Callable[..., Any],
    name: str,
    arguments: Dict[str, Any],
    context: Optional[ToolExecutionContext],
) -> Any:
    if _accepts_keyword(callable_obj, "context"):
        return callable_obj(name, arguments, context=context)
    try:
        parameters = list(inspect.signature(callable_obj).parameters.values())
        positional = [
            parameter
            for parameter in parameters
            if parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        if len(positional) >= 3:
            return callable_obj(name, arguments, context)
    except (TypeError, ValueError):
        pass
    return callable_obj(name, arguments)


async def _invoke_executor(
    executor: ToolExecutor,
    name: str,
    arguments: Dict[str, Any],
    context: Optional[ToolExecutionContext],
) -> Any:
    result = _invoke_with_optional_context(executor, name, arguments, context)
    return await result if inspect.isawaitable(result) else result


async def _as_awaitable(value: Any) -> Any:
    return value
