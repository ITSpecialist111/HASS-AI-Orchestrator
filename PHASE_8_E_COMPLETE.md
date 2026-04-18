# Phase 8 / Milestone E — Plan → Approve → Execute: COMPLETE

> **Status:** ✅ Shipped
> **Branch:** Phase 8 work-in-progress (v0.11.0-dev)
> **Tests:** 125 passed / 4 skipped — +46 new
> **Date:** April 18, 2026

This document describes Milestone **E** of [PHASE_8.md](PHASE_8.md) —
"the conscience". The deep reasoner can now **plan before it acts**,
**queue high-impact actions** for human approval, and
**deterministically replay** approved plans without re-invoking the
LLM. Together with Milestone D (memory), this is what makes it safe
to flip `dry_run_mode: false` in production.

---

## 1. The problem E solves

Phase 7 + Milestone D made the reasoner powerful and reflective. But
it was still **fait accompli**: a request to "lock the front door
and arm the alarm at night" would do exactly that, immediately, and
only show its work afterwards. Two specific gaps:

| Gap | Why it matters |
|---|---|
| No way to preview a plan | The user can't say "no, I meant the back door" before locks click. |
| Approval gating only at the per-tool layer | High-impact action mid-plan trips the local MCP approval queue, but you've already done the cheap setup steps. |
| Re-running for "execute now" risks LLM drift | If the user approves a plan, then we ask the LLM to "go ahead", the model might choose different actions. |

Milestone E closes all three with a **plan / execute** split powered
by a dry-run interceptor and deterministic replay.

---

## 2. What shipped

### 2.1 New: `plan_executor.py`

[ai-orchestrator/backend/plan_executor.py](ai-orchestrator/backend/plan_executor.py) — ~430 lines.

Self-contained module with four responsibilities. **No dependency on
the LLM, the harness, or the agent.**

#### `ToolClassifier`

Heuristic name-pattern classifier. Conservative-by-default: anything
unrecognised is treated as low-impact mutating (recorded, not silently
fired).

```python
@dataclass
class Classification:
    is_mutating: bool
    impact_level: str  # "read" | "low" | "medium" | "high"
    reason: str        # human-readable
```

Rule order (first match wins):

1. **Read-only / mutating overrides** (per-deployment)
2. **High-impact regex patterns** — `lock`, `unlock`, `arm_*`,
   `disarm*`, `alarm`, `set_temperature/hvac/thermostat`,
   `automation/script/scene_(create|update|delete)`, `call_service`,
   `restart`, `reload`, `thermostat`. Underscores are word
   boundaries so `lock_front_door` matches but
   `unlock_back_door` doesn't accidentally match `lock`'s `unlock`
   pattern.
3. **Read-only prefixes** — `list_/get_/search_/read_/query_/find_/`
   `describe_/info_/history_/fetch_/lookup_/render_template/summary_`
4. **Generic mutating hints** — `set_/turn_/toggle/create/update/`
   `delete/trigger/enable/disable/fire_event/post_/patch_/...`
5. **Unknown** → low-impact mutating with reason
   `"unrecognised — treated as mutating"`

**Provider prefix stripping.** Names are normalised against a small
prefix list (`hass_`, `openclaw_`, `mcp_`) before matching, so
`hass_list_entities` is correctly classified as read-only without
needing to add every external MCP tool to an allow-list.

> **Why high-impact wins over read-only prefix.** It doesn't really —
> the prefixes are mutually exclusive in practice. But the explicit
> ordering makes the rules easier to reason about: "does the name
> *say* it's dangerous?" → if yes, stop. Then "does the name *say*
> it's a read?" → if yes, stop. Then heuristics. The order also
> protects against a future external MCP that ships e.g.
> `get_lock_state` (would correctly classify as read).

#### `DryRunInterceptor`

A stateful wrapper around any `async (name, args) -> dict` callable.
Read-only calls pass straight through. Mutating calls are recorded
and a synthetic `{"ok": true, "dry_run": true, ...}` is returned to
keep the LLM happily reasoning.

```python
intercept = DryRunInterceptor(self.registry.call, classifier)
self.harness.tool_call_interceptor = intercept
# … harness.run() …
intents: List[RecordedIntent] = intercept.intents
```

`set_iteration(i)` is bumped by the harness before every loop turn
so each `RecordedIntent` knows which step produced it (useful for
debugging and for dashboards that want to overlay plan steps on the
trace).

#### `PlanProposal` + `PlanStore`

```python
@dataclass
class PlanProposal:
    id: str
    run_id: Optional[str]
    goal: str
    intents: List[RecordedIntent]
    answer: str                         # the LLM's plain-English plan
    iterations: int
    duration_ms: int
    backend: Optional[str]              # "ollama" | "anthropic"
    timestamp: str
    status: str = "pending"             # pending | approved | executed | executed_with_errors | rejected
    requires_approval: bool = True
    risk_summary: str = ""              # "1 high-impact, 2 low-impact action(s) across 3 step(s)."
    executed_at: Optional[str] = None
    execution_results: List[Dict] = []
```

`PlanStore` is SQLite at `/data/plans.db` (workspace-local fallback
for tests). Single table, indexed on `(status, timestamp)`. Methods:

- `save(plan)` — upsert
- `get(plan_id)` → `PlanProposal | None`
- `list(status=None, limit=50)` — newest first
- `update_status(plan_id, status, *, execution_results, executed_at)`

Why a fresh table rather than reusing `ApprovalQueue`'s
`approvals` table: a plan is N intents grouped under one approval,
not a single action. Trying to model that on top of the per-action
schema would have meant either (a) one approval row per intent (UI
asks the human N times) or (b) JSON-blobbing intents into
`action_data` (loses queryability). A purpose-built `plans` table is
cleaner.

#### `replay_plan(plan, underlying_call)`

The **deterministic replay** core.

```python
results = await replay_plan(plan, agent.registry.call)
```

- Iterates intents in original order
- Calls each tool with the **exact arguments captured during planning**
- Records `{sequence, tool_name, arguments, result, ok, skipped, duration_ms}`
- **Aborts on first failure** — remaining intents marked
  `{ok: False, skipped: True}`
- Treats `{status: "pending_approval"}` as success — the local MCP
  approval queue still gates high-impact actions per its rules; the
  planner's job is to surface *what* will be tried, not to second-
  guess existing per-tool gates

**No second LLM round-trip.** The actions the human approved are
exactly the actions that fire. This is the property the "approve"
button needs to actually mean what it appears to mean.

#### `summarise_risk(intents) -> str`

One-liner for the dashboard / approval card. Groups intents by
impact level and renders e.g. `"1 high-impact, 2 low-impact
action(s) across 3 step(s)."`.

---

### 2.2 Wired: `ReasoningHarness`

[ai-orchestrator/backend/reasoning_harness.py](ai-orchestrator/backend/reasoning_harness.py)

Three small, surgical changes:

```python
def __init__(..., tool_call_interceptor: Optional[Any] = None):
    self.tool_call_interceptor = tool_call_interceptor

# Per iteration:
if self.tool_call_interceptor is not None:
    self.tool_call_interceptor.set_iteration(iteration)

# When dispatching tool calls:
dispatch = (self.tool_call_interceptor.call
            if self.tool_call_interceptor is not None
            else self.tools.call)
results = await asyncio.gather(*[dispatch(c.name, c.arguments) for c in calls])
```

**The harness still doesn't know what a "plan" is** — it only knows
about an optional callable that intercepts tool calls. This keeps the
harness focused on its single responsibility (the agentic loop) and
makes the interceptor swappable (telemetry wrappers, tracing
wrappers, future per-tool-throttling, etc.).

---

### 2.3 Wired: `DeepReasoningAgent`

[ai-orchestrator/backend/agents/deep_reasoning_agent.py](ai-orchestrator/backend/agents/deep_reasoning_agent.py)

#### Constructor additions

```python
DeepReasoningAgent(
    ...,
    plan_store: Optional[PlanStore] = None,
    tool_classifier: Optional[ToolClassifier] = None,
    default_mode: str = "auto",        # "auto" | "plan" | "execute"
)
```

Backward compatible — omit `plan_store` and the agent runs exactly
as in Milestone D (defaults to `execute` semantics for any mode but
`plan`).

#### `run(goal, context, *, mode=None)` semantics

| `mode` | Interceptor installed? | LLM prompt | Outcome |
|---|---|---|---|
| `execute` | No | base | All tools fire immediately. Phase 7 behaviour. |
| `plan` | Yes | base + `_PLAN_MODE_NOTE` | Mutating tools recorded only. Plan persisted, **never auto-executed**. |
| `auto` (default) | Yes | base + `_PLAN_MODE_NOTE` | Plan first. **No high-impact intents** → execute inline (replay), mark `executed`. **Has high-impact** → leave `pending`, return plan, await approval. |

When the interceptor is installed, the agent appends a `## Plan
mode` block to the system prompt explaining to the model that
mutating tools will return synthetic success and that its final
answer should describe the plan in plain English for the human.

#### Plan lifecycle methods

```python
await agent.execute_plan(plan_id)   # idempotent replay; second call returns "already_executed"
await agent.reject_plan(plan_id)    # marks status = "rejected"
```

Both fail soft when `plan_store is None`.

#### Recall + plan compose cleanly

The D recall block is appended *after* the `_PLAN_MODE_NOTE` so the
model sees, in order:

1. Base system prompt (role, tools, safety)
2. Plan mode note (if planning)
3. Relevant past experience (if memory has hits)

This means recalled episodes can carry context about whether *prior*
similar plans were approved or rejected, which the model can use to
shape its proposal.

---

### 2.4 New: HTTP endpoints

[ai-orchestrator/backend/main.py](ai-orchestrator/backend/main.py)

#### `POST /api/reasoning/run` — additive request + response fields

Request:
```json
{ "goal": "...", "context": {...}, "mode": "auto" }   // mode is new
```

Response (additive, all nullable):
```json
{
  "mode": "auto",
  "plan": {
    "id": "ab12…",
    "run_id": "…",
    "goal": "…",
    "intents": [
      {
        "sequence": 1,
        "tool_name": "lock_front_door",
        "arguments": {"entity_id": "lock.front"},
        "impact_level": "high",
        "classification_reason": "matched high-impact pattern",
        "simulated_result": {"ok": true, "dry_run": true, "note": "…"},
        "iteration": 2,
        "timestamp": "2026-04-18T19:33:00+00:00"
      }
    ],
    "status": "pending",
    "requires_approval": true,
    "risk_summary": "1 high-impact action(s) across 1 step(s).",
    "high_impact_count": 1,
    "mutating_count": 1
  },
  "executed_inline": false,
  "execution_results": null,
  // …existing D + Phase 7 fields
}
```

#### `GET /api/reasoning/plans?status=&limit=`
Lists plans newest-first. Filter by `status`
(`pending|approved|executed|executed_with_errors|rejected`). `limit`
is clamped to `[1, 200]`.

#### `GET /api/reasoning/plans/{plan_id}`
Single plan as a dict.

#### `POST /api/reasoning/plans/{plan_id}/execute`
Replays the recorded intents against the real tools. **Idempotent**
— if already executed, returns the previously-recorded results
without firing anything.

#### `POST /api/reasoning/plans/{plan_id}/reject`
Marks the plan rejected; subsequent execute attempts will see
`status="rejected"` (currently treated as a no-op success in
`execute_plan`; this is the only place the API is slightly
asymmetric — covered in §6 future work).

---

### 2.5 New: tests

[ai-orchestrator/backend/tests/test_plan_executor_smoke.py](ai-orchestrator/backend/tests/test_plan_executor_smoke.py) — 46 tests across 6 groups.

| Group | Tests | What they validate |
|---|---|---|
| `TestToolClassifier` | 25 | Read-only prefixes, all high-impact patterns (incl. `unlock_back_door`, `set_thermostat_mode`), unknown → safe-fail mutating, override precedence, provider-prefix stripping |
| Interceptor | 3 | Read-only pass-through, mutating recorded without firing, mixed sequence + iteration tracking |
| `TestPlanStore` | 5 | Save/get round-trip, missing-id, status filter ordering, `update_status` persistence + missing-id soft-fail |
| Replay | 4 | In-order with real args, abort-and-skip on failure, executor exception → failed result, `pending_approval` counted as success |
| Risk summary | 2 | Empty case, group-by-level wording |
| Agent integration | 7 | All three modes end-to-end + execute_plan idempotency + reject_plan |

**Test infrastructure.** A `stubbed_agent_factory` fixture builds a
fully scriptable `DeepReasoningAgent` whose LLM returns a queue of
`LLMResponse` objects, with a stub local-MCP that records calls into
a shared `fired` list. No Ollama, no Chroma, no network. The fixture
also gives each test its own SQLite plan-store in `tmp_path`.

The end-to-end tests are the high-value ones:

- `test_plan_mode_records_intents_without_firing` — proves the
  interceptor really blocks mutating calls
- `test_auto_mode_executes_inline_when_no_high_impact` — proves the
  inline-execute path actually fires the tools
- `test_auto_mode_queues_when_high_impact_present` — proves the
  approval-gate path doesn't fire anything yet
- `test_execute_plan_replays_against_real_tools` — proves
  `/plans/{id}/execute` does fire what was approved
- `test_execute_plan_is_idempotent` — proves double-clicking
  "Approve" doesn't fire actions twice

---

## 3. Acceptance check

> With `dry_run_mode: false`, a goal like "lock all external doors
> and arm the alarm" returns a plan, not a fait accompli; user
> clicks Approve; the *recorded* lock/arm calls fire, not an
> LLM-regenerated set.

✅ Demonstrated end-to-end by
`test_auto_mode_queues_when_high_impact_present` →
`test_execute_plan_replays_against_real_tools`. The lock arguments
captured at plan time are exactly the arguments fired at execute
time. Verified by inspecting the `fired` list in the stub MCP.

---

## 4. Files changed

| File | Change |
|---|---|
| `ai-orchestrator/backend/plan_executor.py` | **NEW** — ~430 lines |
| `ai-orchestrator/backend/reasoning_harness.py` | +3-line interceptor hook (constructor, per-iter bump, dispatch swap) |
| `ai-orchestrator/backend/agents/deep_reasoning_agent.py` | +`mode` parameter, +interceptor wiring, +`_build_plan` / `execute_plan` / `reject_plan`, +`_PLAN_MODE_NOTE`, +`info()` fields |
| `ai-orchestrator/backend/main.py` | +`PlanStore` wiring, +4 endpoints, +`mode` on `/run`, +plan fields in response |
| `ai-orchestrator/backend/tests/test_plan_executor_smoke.py` | **NEW** — 46 tests |
| `PHASE_8_E_COMPLETE.md` | This document |

---

## 5. Test results

```
$ python -m pytest -q
125 passed, 4 skipped in 44.45s
```

The 4 skipped are `test_external_mcp_live.py` (require a running
OpenClaw HASS_MCP server). Everything else green, including all
prior Phase 1–7 + Milestone D tests.

---

## 6. Acknowledged limitations / future work

Not bugs — design decisions called out so future-you can tell what's
intentional.

1. **No state-drift validation at execute time.** If the entity
   state changed between plan and execute (e.g. door is now open),
   we replay anyway. The local MCP layer may still refuse the action
   per its own validation. Future: add an optional pre-execute
   re-check loop that compares current state to the state observed
   during planning.
2. **Plan TTL not enforced.** A plan approved 3 days late will still
   replay. Future: configurable expiry (default 24 h) that auto-marks
   plans `expired`.
3. **`reject_plan` doesn't block subsequent `execute_plan` strongly.**
   `execute_plan` returns `{"status": "rejected"}` early but doesn't
   raise. Today this is fine because the API caller handles it; if
   we ever support agent-driven re-execution we'd need a hard guard.
4. **Risk summary is a single string.** Dashboard work in Milestone G
   will likely want structured risk output. Easy swap when it does
   — `summarise_risk` is one function.
5. **Per-deployment classifier overrides aren't yet user-configurable.**
   They're constructor parameters. Once `triggers.yaml` exists in
   Milestone F, the same yaml could carry classifier overrides.

---

## 7. What's next

**Milestone F — Proactive triggers.** The reasoner fires on its own.

- `TriggerRegistry` + `triggers.yaml` (cron + state-change types)
- `apscheduler` for cron triggers (e.g. nightly energy audit at 22:00)
- State-change triggers via `HAWebSocketClient.subscribe_entities`
  with debouncing
- Triggers always run in `auto` mode so anything dangerous goes
  through the PAE flow we just built
- `/api/triggers` CRUD endpoints

PAE was the prerequisite: triggers running in `execute` mode would
be terrifying. With Milestone E in place, "trigger fired → plan
generated → high-impact → queued for approval" is now a sane default.

---

*Milestone E shipped April 18, 2026. The orchestrator no longer acts
without thinking, and no longer thinks without showing its work.*
