"""
DeepReasoningAgent — the orchestrator's "brain".

Unlike the fast specialist :class:`UniversalAgent` instances (which run
on a fixed cadence and emit a single batch of actions), this agent is
**goal-driven** and **recursive**:

* It is invoked on demand (chat, orchestrator escalation, REST endpoint).
* It uses :class:`ReasoningHarness` to reason in a loop, calling tools
  from both the legacy in-process :class:`MCPServer` and any external
  MCP servers (no external server is required — the orchestrator ships
  with its own native HA tool surface; an external MCP, if present,
  is purely additive).
* High-impact actions still flow through the existing approval queue
  via the local MCP layer.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from external_mcp import ExternalMCPClient
from llm_providers import (
    PROVIDER_OLLAMA,
    make_tool_backend,
    resolve_provider_name,
)
from memory_store import MemoryStore, RecalledEpisode, ReasoningEpisode
from native_ha_tools import NativeHATools
from plan_executor import (
    DryRunInterceptor,
    PlanProposal,
    PlanStore,
    RecordedIntent,
    ToolClassifier,
    replay_plan,
    summarise_risk,
)
from reasoning_harness import (
    AnthropicBackend,
    HarnessResult,
    LLMBackend,
    OllamaToolBackend,
    ReasoningHarness,
    ToolRegistry,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the deep reasoning agent for a Home Assistant
orchestrator. You coordinate observation and action across the entire
smart home.

How you work
------------
1. You receive a goal from the user or the orchestrator.
2. You have access to three kinds of tools:
   * **Local safety-checked tools** — climate, lights, locks, alarms.
     These are validated and rate-limited; high-impact ones are queued
     for human approval automatically.
   * **Native HA tools** (prefix ``ha_``) — entity discovery, state
     queries, services, area summaries. Always available; built
     directly on the Home Assistant WebSocket API.
   * **External MCP tools** (prefix ``ext_``) — optional, only present
     when an external MCP server is configured. Use them when they
     offer capabilities the native tools don't.
3. Reason step-by-step. Prefer **discovery before action**: query state,
   inspect areas/devices, read history, then propose changes.
4. When you need to combine dissimilar capabilities, call multiple
   tools in parallel in a single turn.
5. Stop and return a final answer as soon as the goal is satisfied or
   you need clarification. Do not call tools unnecessarily.
6. Your final answer must summarise what you observed, what you
   changed (if anything), and any follow-up recommendations.

Safety
------
* Never bypass the approval queue. If a tool returns
  ``{"status": "pending_approval"}`` treat it as success and inform the
  user that approval is required.
* Do not invent entity IDs. Discover them with ``ha_list_entities``,
  ``ha_search_entities`` or ``ha_summarise_area`` before acting.
* If a tool fails, try a different approach rather than retrying the
  same call with the same arguments.
"""


_PLAN_MODE_NOTE = """## Plan mode

You are running in **plan mode**. Mutating tools (anything that
changes state — set/turn/lock/unlock/arm/disarm/create/update/delete/
call_service/…) will be intercepted: they return a synthetic
``{"dry_run": true}`` success without actually firing. Use them
freely to design the plan; the human will review and approve before
any action runs for real.

Read-only tools (list/get/search/history/render_template/…) execute
normally so you can ground your plan in real state.

Your final answer should describe the plan in plain English so the
human can decide whether to approve it.
"""


class DeepReasoningAgent:
    """Goal-driven reasoning agent built on :class:`ReasoningHarness`."""

    def __init__(
        self,
        agent_id: str = "deep_reasoner",
        name: str = "Deep Reasoning Agent",
        *,
        local_mcp: Any,
        external_mcp: Optional[ExternalMCPClient] = None,
        ha_client: Optional[Any] = None,
        ollama_model: str = "qwen2.5:14b-instruct",
        ollama_host: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        anthropic_model: str = "claude-opus-4-7",
        provider: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        openai_model: Optional[str] = None,
        github_token: Optional[str] = None,
        github_model: Optional[str] = None,
        foundry_endpoint: Optional[str] = None,
        foundry_api_key: Optional[str] = None,
        foundry_bearer_token: Optional[str] = None,
        foundry_model: Optional[str] = None,
        foundry_agent_id: Optional[str] = None,
        max_iterations: int = 12,
        max_tool_calls_per_turn: int = 5,
        broadcast_func: Optional[Any] = None,
        memory_store: Optional[MemoryStore] = None,
        recall_k: int = 3,
        recall_max_age_days: float = 180.0,
        plan_store: Optional[PlanStore] = None,
        tool_classifier: Optional[ToolClassifier] = None,
        default_mode: str = "auto",
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.local_mcp = local_mcp
        self.external_mcp = external_mcp
        self.ha_client = ha_client
        self.native_tools: Optional[NativeHATools] = (
            NativeHATools(ha_client) if ha_client is not None else None
        )
        self.ha_client = ha_client
        self.native_tools: Optional[NativeHATools] = (
            NativeHATools(ha_client) if ha_client is not None else None
        )
        self.broadcast_func = broadcast_func
        self.memory_store = memory_store
        self.recall_k = max(0, recall_k)
        self.recall_max_age_days = recall_max_age_days
        self.plan_store = plan_store
        self.tool_classifier = tool_classifier or ToolClassifier()
        if default_mode not in ("auto", "plan", "execute"):
            raise ValueError("default_mode must be one of auto|plan|execute")
        self.default_mode = default_mode
        self.status = "idle"
        self.last_run_at: Optional[datetime] = None
        self.last_result: Optional[HarnessResult] = None
        # Map of run_id -> episode_id so /feedback can target the
        # right episode without exposing internal ids.
        self._run_to_episode: Dict[str, str] = {}

        # Decision log directory
        base = Path("/data/decisions") if os.path.exists("/data") else Path(__file__).parent.parent.parent / "data" / "decisions"
        self.log_dir = base / "deep_reasoner"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Provider precedence:
        #   1. explicit anthropic_api_key (legacy fast-path)
        #   2. provider arg / LLM_PROVIDER env (new, multi-provider)
        #   3. Ollama default
        self.llm: LLMBackend
        if anthropic_api_key:
            try:
                self.llm = AnthropicBackend(model=anthropic_model, api_key=anthropic_api_key)
                logger.info("DeepReasoningAgent using Anthropic backend (%s)", anthropic_model)
            except Exception as exc:
                logger.warning("Anthropic backend unavailable, falling back to Ollama: %s", exc)
                self.llm = OllamaToolBackend(model=ollama_model, host=ollama_host)
        else:
            resolved = resolve_provider_name(provider)
            if resolved == PROVIDER_OLLAMA:
                self.llm = OllamaToolBackend(model=ollama_model, host=ollama_host)
                logger.info("DeepReasoningAgent using Ollama backend (%s)", ollama_model)
            else:
                # Pick the per-provider model; fall back to ollama_model
                # as a last-resort string (some providers will reject it,
                # but we surface that as a runtime error rather than a
                # silent default that hides misconfiguration).
                model_for_provider = (
                    openai_model if resolved == "openai"
                    else github_model if resolved == "github"
                    else foundry_model if resolved == "foundry"
                    else ollama_model
                ) or ollama_model
                self.llm = make_tool_backend(
                    resolved,
                    model=model_for_provider,
                    ollama_host=ollama_host,
                    openai_api_key=openai_api_key,
                    openai_base_url=openai_base_url,
                    github_token=github_token,
                    foundry_endpoint=foundry_endpoint,
                    foundry_api_key=foundry_api_key,
                    foundry_bearer_token=foundry_bearer_token,
                    foundry_agent_id=foundry_agent_id,
                )
                logger.info(
                    "DeepReasoningAgent using %s backend (%s)",
                    getattr(self.llm, "name", resolved),
                    model_for_provider,
                )

        self.registry = ToolRegistry()
        self._register_tools()
        self.harness = ReasoningHarness(
            llm=self.llm,
            tools=self.registry,
            system_prompt=SYSTEM_PROMPT,
            max_iterations=max_iterations,
            max_tool_calls_per_turn=max_tool_calls_per_turn,
            on_event=self._on_event,
        )

    # ------------------------------------------------------------------
    def _register_tools(self) -> None:
        # Local safety-checked tools.
        local_schemas = _local_tool_schemas(self.local_mcp)
        if local_schemas:
            self.registry.register(
                provider="local",
                schemas=local_schemas,
                executor=self._local_executor,
            )

        # Native HA discovery + control tools (no external dependency).
        if self.native_tools is not None:
            self.registry.register(
                provider="native_ha",
                schemas=self.native_tools.tool_schemas(),
                executor=self._native_executor,
            )

        # Optional external MCP server (additive, e.g. OpenClaw HASS_MCP).
        if self.external_mcp is not None and self.external_mcp.connected:
            ext_schemas = self.external_mcp.tool_schemas()
            if ext_schemas:
                self.registry.register(
                    provider="external_mcp",
                    schemas=ext_schemas,
                    executor=self._external_executor,
                    prefix="ext_",
                )

        logger.info(
            "DeepReasoningAgent tool surface: %d tools registered (%s)",
            len(self.registry.names()),
            ", ".join(self.registry.names()[:10]) + ("…" if len(self.registry.names()) > 10 else ""),
        )

    async def _local_executor(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self.local_mcp.execute_tool(
            tool_name=name, parameters=arguments, agent_id=self.agent_id
        )

    async def _native_executor(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        assert self.native_tools is not None
        return await self.native_tools.call(name, arguments)

    async def _external_executor(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        assert self.external_mcp is not None
        return await self.external_mcp.call_tool(name, arguments)

    async def _on_event(self, event: Dict[str, Any]) -> None:
        if self.broadcast_func is None:
            return
        await self.broadcast_func({
            "type": "reasoning_event",
            "data": {
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                **event,
            },
        })

    # ------------------------------------------------------------------
    async def run(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        *,
        mode: Optional[str] = None,
    ) -> HarnessResult:
        """Run a reasoning goal.

        ``mode``:
          * ``"execute"``  — Phase 7 behaviour, all tools fire for real.
          * ``"plan"``     — mutating tools recorded only; returns a
            :class:`PlanProposal` stamped on the result.
          * ``"auto"``     — plan first; auto-execute if no high-impact
            actions, else queue plan for approval.
        """
        effective_mode = (mode or self.default_mode).lower()
        if effective_mode not in ("auto", "plan", "execute"):
            raise ValueError(f"unknown mode {mode!r}")

        self.status = "thinking"
        self.last_run_at = datetime.now()
        run_id = uuid.uuid4().hex

        # ---- D2: pre-flight memory recall --------------------------------
        recalled = await self._recall(goal)
        recall_block = _format_recall(recalled)
        base_prompt = SYSTEM_PROMPT
        if effective_mode in ("plan", "auto"):
            base_prompt = base_prompt + "\n\n" + _PLAN_MODE_NOTE
        if recall_block:
            self.harness.system_prompt = base_prompt + "\n\n" + recall_block
        else:
            self.harness.system_prompt = base_prompt

        # ---- E1+E2: install dry-run interceptor for plan/auto -----------
        interceptor: Optional[DryRunInterceptor] = None
        if effective_mode in ("plan", "auto"):
            interceptor = DryRunInterceptor(
                underlying_call=self.registry.call,
                classifier=self.tool_classifier,
            )
            self.harness.tool_call_interceptor = interceptor
        else:
            self.harness.tool_call_interceptor = None

        try:
            result = await self.harness.run(goal=goal, context=context)
            self.last_result = result
            self._persist(goal, result, run_id=run_id)
            episode_id = await self._remember_episode(goal, result)
            if episode_id:
                self._run_to_episode[run_id] = episode_id

            plan: Optional[PlanProposal] = None
            execution_results: Optional[List[Dict[str, Any]]] = None
            executed_inline = False
            if interceptor is not None:
                plan = self._build_plan(run_id, goal, result, interceptor.intents)
                # E5: auto mode — execute inline when nothing dangerous.
                if effective_mode == "auto" and plan.high_impact_count == 0 and plan.intents:
                    plan.requires_approval = False
                    plan.status = "executed"
                    plan.executed_at = datetime.now(timezone.utc).isoformat()
                    execution_results = await replay_plan(plan, self.registry.call)
                    plan.execution_results = execution_results
                    executed_inline = True
                elif effective_mode == "auto" and not plan.intents:
                    # Read-only plan — nothing to execute, mark complete.
                    plan.requires_approval = False
                    plan.status = "executed"
                    plan.executed_at = datetime.now(timezone.utc).isoformat()
                if self.plan_store is not None:
                    self.plan_store.save(plan)

            try:
                setattr(result, "run_id", run_id)
                setattr(result, "episode_id", self._run_to_episode.get(run_id))
                setattr(result, "recalled", [_recall_to_dict(r) for r in recalled])
                setattr(result, "mode", effective_mode)
                setattr(result, "plan", plan.to_dict() if plan else None)
                setattr(result, "executed_inline", executed_inline)
                setattr(result, "execution_results", execution_results)
            except Exception:
                pass
            return result
        finally:
            self.status = "idle"
            self.harness.tool_call_interceptor = None

    # ------------------------------------------------------------------
    async def run_streaming(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        *,
        mode: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Run a reasoning goal and yield incremental events.

        Yields dicts shaped as ``{"type": ..., "data": {...}}``. Event
        types are:

        * ``start`` — once, with ``{"goal", "mode", "run_id"}``
        * ``recall`` — once after memory recall, with ``{"recalled": [...]}``
        * ``thought`` — per harness iteration, with the LLM thinking
        * ``tool_call`` — for each executed tool call
        * ``plan`` — once after the run, with the proposed plan dict
          (``None`` in execute mode)
        * ``final`` — once at the end, with the full result payload
        * ``error`` — on exception (terminal)
        """
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()

        async def _push(event: Dict[str, Any]) -> None:
            await queue.put(event)

        # Hook the harness's per-step events into our queue while
        # also forwarding to the original broadcast (so the WS UI
        # still sees them).
        original_on_event = self.harness.on_event

        async def _on_event(ev: Dict[str, Any]) -> None:
            await _push(dict(ev))
            if original_on_event is not None:
                try:
                    await original_on_event(ev)
                except Exception as exc:
                    logger.debug("broadcast event failed: %s", exc)

        self.harness.on_event = _on_event
        run_id = uuid.uuid4().hex
        await _push({"type": "start", "goal": goal,
                     "mode": (mode or self.default_mode), "run_id": run_id})

        async def _runner() -> None:
            try:
                # Match the body of run() but reuse the recall/plan
                # plumbing. Easiest: monkey-patch run_id by capturing
                # the result and re-emitting it.
                result = await self.run(goal, context, mode=mode)
                # Recall block already happened inside run(); surface it.
                await _push({
                    "type": "recall",
                    "recalled": list(getattr(result, "recalled", []) or []),
                })
                plan = getattr(result, "plan", None)
                await _push({"type": "plan", "plan": plan})
                await _push({
                    "type": "final",
                    "data": {
                        "run_id": getattr(result, "run_id", run_id),
                        "episode_id": getattr(result, "episode_id", None),
                        "mode": getattr(result, "mode", "execute"),
                        "answer": result.answer,
                        "iterations": result.iterations,
                        "tool_calls": result.tool_calls,
                        "stopped_reason": result.stopped_reason,
                        "duration_ms": result.duration_ms,
                        "executed_inline": getattr(result, "executed_inline", False),
                        "execution_results": getattr(result, "execution_results", None),
                        "plan": plan,
                    },
                })
            except Exception as exc:
                logger.exception("run_streaming inner failure")
                await _push({"type": "error", "error": str(exc)})
            finally:
                await queue.put(SENTINEL)

        task = asyncio.create_task(_runner())
        try:
            while True:
                ev = await queue.get()
                if ev is SENTINEL:
                    break
                yield ev
            await task
        finally:
            # Always restore the original event hook even if the
            # consumer abandons the iterator.
            self.harness.on_event = original_on_event
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

    # ------------------------------------------------------------------
    async def _recall(self, goal: str) -> List[RecalledEpisode]:
        if not self.memory_store or not self.memory_store.enabled or self.recall_k <= 0:
            return []
        try:
            return await self.memory_store.recall(
                goal,
                k=self.recall_k,
                max_age_days=self.recall_max_age_days,
            )
        except Exception as exc:
            logger.warning("DeepReasoningAgent recall failed: %s", exc)
            return []

    async def _remember_episode(self, goal: str, result: HarnessResult) -> Optional[str]:
        if not self.memory_store or not self.memory_store.enabled:
            return None
        try:
            episode = self._build_episode(goal, result)
            return await self.memory_store.remember(episode)
        except Exception as exc:
            logger.warning("DeepReasoningAgent remember failed: %s", exc)
            return None

    def _build_episode(self, goal: str, result: HarnessResult) -> ReasoningEpisode:
        tools_used: List[str] = []
        seen: set = set()
        for step in result.trace:
            for tc in step.tool_calls or []:
                name = tc.get("name") if isinstance(tc, dict) else None
                if name and name not in seen:
                    tools_used.append(name)
                    seen.add(name)

        # The summary is the answer itself, truncated. We deliberately
        # don't ask the LLM to re-summarise here to keep this code
        # path free of extra LLM round-trips; a richer summariser is
        # an easy follow-up (use self.llm.chat with a small prompt).
        summary = (result.answer or "").strip()
        if len(summary) > 1500:
            summary = summary[:1500].rstrip() + "…"

        return ReasoningEpisode(
            id=uuid.uuid4().hex,
            goal=goal,
            summary=summary,
            answer=result.answer or "",
            iterations=int(result.iterations or 0),
            tool_calls=int(result.tool_calls or 0),
            tools_used=tools_used,
            stopped_reason=result.stopped_reason or "",
            duration_ms=int(result.duration_ms or 0),
            timestamp=datetime.now(timezone.utc).isoformat(),
            score=0.0,
            backend=getattr(self.llm, "name", None),
        )

    # ------------------------------------------------------------------
    async def submit_feedback(
        self,
        run_id: str,
        rating: int,
        note: Optional[str] = None,
    ) -> bool:
        """Record human feedback on a past run by ``run_id``."""
        episode_id = self._run_to_episode.get(run_id)
        if not episode_id:
            return False
        if not self.memory_store:
            return False
        return await self.memory_store.update_feedback(episode_id, rating, note)

    # ------------------------------------------------------------------
    # Plan/execute helpers (Milestone E)
    # ------------------------------------------------------------------
    def _build_plan(
        self,
        run_id: str,
        goal: str,
        result: HarnessResult,
        intents: List[RecordedIntent],
    ) -> PlanProposal:
        return PlanProposal(
            id=uuid.uuid4().hex,
            run_id=run_id,
            goal=goal,
            intents=list(intents),
            answer=result.answer or "",
            iterations=int(result.iterations or 0),
            duration_ms=int(result.duration_ms or 0),
            backend=getattr(self.llm, "name", None),
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="pending",
            requires_approval=any(i.impact_level == "high" for i in intents),
            risk_summary=summarise_risk(intents),
        )

    async def execute_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Replay a stored plan against the real tools.

        Returns ``None`` if the plan cannot be found, otherwise a dict
        with the per-step execution results.
        """
        if self.plan_store is None:
            return None
        plan = self.plan_store.get(plan_id)
        if plan is None:
            return None
        if plan.status == "executed":
            return {
                "plan_id": plan.id,
                "status": "already_executed",
                "execution_results": plan.execution_results,
                "executed_at": plan.executed_at,
            }
        if plan.status == "rejected":
            return {"plan_id": plan.id, "status": "rejected"}

        results = await replay_plan(plan, self.registry.call)
        executed_at = datetime.now(timezone.utc).isoformat()
        all_ok = all(r.get("ok") for r in results)
        new_status = "executed" if all_ok else "executed_with_errors"
        self.plan_store.update_status(
            plan.id,
            new_status,
            execution_results=results,
            executed_at=executed_at,
        )
        return {
            "plan_id": plan.id,
            "status": new_status,
            "execution_results": results,
            "executed_at": executed_at,
        }

    async def reject_plan(self, plan_id: str) -> bool:
        if self.plan_store is None:
            return False
        return self.plan_store.update_status(plan_id, "rejected")

    def _persist(self, goal: str, result: HarnessResult, run_id: Optional[str] = None) -> None:
        """Save reasoning run to /data/decisions/deep_reasoner/ for the dashboard."""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            entry = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.agent_id,
                "run_id": run_id,
                "goal": goal,
                "answer": result.answer,
                "iterations": result.iterations,
                "tool_calls": result.tool_calls,
                "stopped_reason": result.stopped_reason,
                "duration_ms": result.duration_ms,
                "trace": [
                    {
                        "iteration": s.iteration,
                        "thought": s.thought,
                        "tool_calls": s.tool_calls,
                        "tool_results": s.tool_results,
                        "duration_ms": s.duration_ms,
                    }
                    for s in result.trace
                ],
            }
            path = self.log_dir / f"{ts}.json"
            with open(path, "w") as f:
                json.dump(entry, f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Failed to persist reasoning run: %s", exc)

    # ------------------------------------------------------------------
    def info(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "backend": self.llm.name,
            "tool_count": len(self.registry.names()),
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "native_tools_enabled": self.native_tools is not None,
            "external_mcp_connected": bool(self.external_mcp and self.external_mcp.connected),
            "external_mcp_tools": len(self.external_mcp.tools) if self.external_mcp else 0,
            "memory_enabled": bool(self.memory_store and self.memory_store.enabled),
            "recall_k": self.recall_k,
            "plan_store_enabled": self.plan_store is not None,
            "default_mode": self.default_mode,
        }


def _local_tool_schemas(local_mcp: Any) -> List[Dict[str, Any]]:
    """Adapt the legacy :class:`MCPServer` registry to OpenAI tool schema."""
    schemas: List[Dict[str, Any]] = []
    tools = getattr(local_mcp, "tools", {}) or {}
    for tool_name, tool_def in tools.items():
        params = tool_def.get("parameters") if isinstance(tool_def, dict) else None
        if not isinstance(params, dict):
            params = {"type": "object", "properties": {}}
        schemas.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": (tool_def.get("description") if isinstance(tool_def, dict) else "") or tool_name,
                "parameters": params,
            },
        })
    return schemas


def _format_recall(recalled: List[RecalledEpisode]) -> str:
    """Render recalled episodes as a system-prompt addendum."""
    if not recalled:
        return ""
    lines = [
        "## Relevant past experience",
        "",
        "Before reasoning, consider these prior runs on similar goals.",
        "Cite them when they meaningfully change your plan; ignore them",
        "if they are not actually relevant.",
        "",
    ]
    for i, r in enumerate(recalled, 1):
        ep = r.episode
        score_tag = ""
        if ep.score > 0:
            score_tag = " [user marked this run helpful]"
        elif ep.score < 0:
            score_tag = " [user marked this run unhelpful — avoid repeating its mistakes]"
        tools = ", ".join(ep.tools_used[:5]) if ep.tools_used else "(none)"
        lines.append(
            f"{i}. **Goal:** {ep.goal}{score_tag}\n"
            f"   **When:** {ep.timestamp}  **Iter/Tools:** {ep.iterations}/{ep.tool_calls}\n"
            f"   **Tools used:** {tools}\n"
            f"   **What happened:** {ep.summary}\n"
        )
    return "\n".join(lines)


def _recall_to_dict(r: RecalledEpisode) -> Dict[str, Any]:
    ep = r.episode
    return {
        "episode_id": ep.id,
        "goal": ep.goal,
        "summary": ep.summary,
        "timestamp": ep.timestamp,
        "score": ep.score,
        "similarity": round(r.similarity, 4),
        "recency_weight": round(r.recency_weight, 4),
        "feedback_weight": round(r.feedback_weight, 4),
        "final_score": round(r.final_score, 4),
    }
