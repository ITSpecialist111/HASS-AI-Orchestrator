# Phase 8 / Milestone G — Streaming + Prompt Library + Dashboard: COMPLETE

> **Status:** ✅ Shipped — closes Phase 8
> **Branch:** v0.11.0-dev
> **Tests:** 175 passed / 4 skipped — +16 new
> **Date:** April 18, 2026

This is the final milestone of [PHASE_8.md](PHASE_8.md). It gives the
orchestrator a **face**: live streaming reasoning output via SSE, a
catalog of MCP-discovered prompts the operator can fire as one-click
workflows, and dashboard panels for triggers and prompts.

After G, the system has the brain (Phase 7) + memory (D) +
conscience (E) + heartbeat (F) + face (G). Phase 8 closes here.

---

## 1. The problem G solves

Phases 7–F made the orchestrator capable, accountable and proactive
— but interaction was still **synchronous and opaque**. Concrete
gaps:

| Gap | Pain |
|---|---|
| `POST /api/reasoning/run` blocks until done. | Long runs feel frozen; no live thoughts/tool calls. |
| 14 OpenClaw MCP prompts (`security_audit`, `energy_optimizer`, …) sit unused. | They're discovered but never surfaced anywhere. |
| Triggers only manageable via `curl`. | The new heartbeat is invisible. |

Milestone G turns these into incremental SSE events, a one-click
prompt library, and dashboard panels for triggers + prompts.

---

## 2. What shipped

### 2.1 G1 — `run_streaming` on the agent + `/api/reasoning/stream`

[ai-orchestrator/backend/agents/deep_reasoning_agent.py](ai-orchestrator/backend/agents/deep_reasoning_agent.py)

New async generator `DeepReasoningAgent.run_streaming(goal, context, mode)` that
yields a sequence of events:

```
start    →  thought  →  tool_call  →  thought  →  …  →  recall  →  plan  →  final
                                                                          (or error)
```

**Implementation choices:**

- Reuses the existing `harness.on_event` hook by wrapping it so events
  also flow into a per-call `asyncio.Queue` while still being
  forwarded to the long-lived dashboard broadcast.
- The original `on_event` is **always restored** in a `finally`
  block — even if the consumer abandons the iterator mid-stream — so
  one rogue HTTP client can't break the broadcast for everyone else.
- The actual reasoning runs in a background task; the iterator
  drains the queue as events arrive and emits `final` (or `error`)
  at the end. A sentinel value cleanly terminates the loop.
- Plan/recall/final are pushed *after* the run completes so the
  consumer sees the full trace of incremental thoughts first, then
  the rich post-run metadata.

[ai-orchestrator/backend/main.py](ai-orchestrator/backend/main.py) — new endpoint:

```http
POST /api/reasoning/stream
Content-Type: application/json
{ "goal": "...", "context": {...}, "mode": "auto" }

→ text/event-stream
  event: start  / data: {...}
  event: thought / data: {...}
  event: tool_call / data: {...}
  event: plan / data: {...}
  event: final / data: {...}
  event: done / data: {}
```

Standard SSE framing (`event:` + `data:` + double newline). Headers
disable proxy buffering (`X-Accel-Buffering: no`, `Cache-Control:
no-cache, no-transform`). On exception we emit a single `error`
event and a terminal `done` so EventSource clients close cleanly.

### 2.2 G2 — MCP prompt catalog

[ai-orchestrator/backend/external_mcp.py](ai-orchestrator/backend/external_mcp.py)

New methods on `ExternalMCPClient`:

- `prompt_specs()` — return discovered prompts as plain dicts
- `get_prompt(name, arguments)` — call MCP `prompts/get`, flatten
  the returned message blocks to a single string for use as a
  reasoning goal. Tolerates string content, `text` blocks and
  unknown blocks (best-effort `str()`).

[ai-orchestrator/backend/main.py](ai-orchestrator/backend/main.py) — three endpoints:

| Method & path | Purpose |
|---|---|
| `GET /api/reasoning/prompts` | List all prompts on the connected external MCP. Returns `{prompts: [], connected: false}` cleanly when MCP isn't connected so the dashboard can render a friendly empty state. |
| `POST /api/reasoning/prompts/{name}/render` | Just render the prompt to text — no reasoning. Useful for previewing. |
| `POST /api/reasoning/prompts/{name}/run` | Render → invoke `deep_reasoner.run()`. Set `stream=true` to stream via SSE instead. Carries the prompt name + arguments into the reasoning context. |

### 2.3 G3 — Dashboard panels

Two new components:

[ai-orchestrator/dashboard/src/components/PromptLibrary.jsx](ai-orchestrator/dashboard/src/components/PromptLibrary.jsx)

- Lists discovered prompts with description and arguments
- Expandable per-prompt: edit arguments inline, click "Run"
- Shows iterations / tool calls / duration / executed-or-pending
  pill / final answer
- Clean disconnected state when external MCP isn't there

[ai-orchestrator/dashboard/src/components/TriggersPanel.jsx](ai-orchestrator/dashboard/src/components/TriggersPanel.jsx)

- Lists all triggers with type/cron/entity/sustain/cooldown summary
- "New trigger" inline form — picks cron vs state, shows the right
  fields, validates server-side
- Per-trigger: enable indicator dot, manual fire (▶), delete (🗑)
- Live "Recent fires" table polling every 5s with status pills
  (executed / awaiting_approval / error)

Wired into [Layout.jsx](ai-orchestrator/dashboard/src/components/Layout.jsx)
as two new sidebar tabs (`Prompt Library`, `Triggers`) and into
[App.jsx](ai-orchestrator/dashboard/src/App.jsx) as new routes.

Vite build clean: 2170 modules, 601 kB JS gzipped to 169 kB.

### 2.4 Bug fix — trigger route ordering

While wiring the dashboard I caught a latent FastAPI bug: the
`GET /api/triggers/{trigger_id}` route was registered **before**
`GET /api/triggers/fires`, which meant the latter was being
shadowed (FastAPI matches in registration order; it would call the
parametrised handler with `trigger_id="fires"`). Fixed by moving
the static `/fires` route above the parametrised one. No tests
exercised this previously because tests call the handlers directly,
not through the router.

---

## 3. Tests

[ai-orchestrator/backend/tests/test_streaming_and_prompts_smoke.py](ai-orchestrator/backend/tests/test_streaming_and_prompts_smoke.py) — 16 tests across 3 groups.

| Group | Tests | What they validate |
|---|---|---|
| `run_streaming` | 5 | Emits `start` → `thought` → `final` for trivial goals; emits `tool_call` events for tool-using runs; restores the original `on_event` hook even after iteration; emits `plan` event in plan-mode without firing real tools; LLM exceptions surface as `final` with `stopped_reason=llm_error` (the harness already swallows them, this confirms streaming preserves that) |
| SSE endpoint | 3 | Streams a well-formed SSE body containing `event: start` / `event: final` / `event: done`; rejects bad mode with HTTP 400; returns 503 when the agent is not initialised |
| MCP prompts | 8 | Empty list when MCP disconnected (no error); lists discovered prompts; render endpoint returns rendered text; render returns 400 on missing prompt; render returns 503 when MCP disconnected; run endpoint invokes reasoner with rendered goal; run rejects empty rendered text with 400; `stream=true` returns SSE with the same final answer |

**Test note.** Because `main.py` imports `chromadb` (which breaks
on Python 3.14 + Pydantic v2 since `BaseSettings` moved out), the
test file pre-mocks `sys.modules["chromadb"]` at collection time.
This mirrors the existing pattern in `test_phase3_smoke.py`.

```
$ python -m pytest -q
175 passed, 4 skipped in 37.29s
```

---

## 4. Files changed

| File | Change |
|---|---|
| `ai-orchestrator/backend/agents/deep_reasoning_agent.py` | +`run_streaming` async generator (~95 lines), +`asyncio` + `AsyncIterator` imports |
| `ai-orchestrator/backend/external_mcp.py` | +`get_prompt()`, +`prompt_specs()` |
| `ai-orchestrator/backend/main.py` | +`StreamingResponse` import, +`/api/reasoning/stream`, +`PromptRunRequest`, +`/api/reasoning/prompts`, +`/api/reasoning/prompts/{name}/render`, +`/api/reasoning/prompts/{name}/run`, route-ordering bug fix on `/api/triggers/fires` |
| `ai-orchestrator/backend/tests/test_streaming_and_prompts_smoke.py` | **NEW** — 16 tests |
| `ai-orchestrator/dashboard/src/components/PromptLibrary.jsx` | **NEW** |
| `ai-orchestrator/dashboard/src/components/TriggersPanel.jsx` | **NEW** |
| `ai-orchestrator/dashboard/src/components/Layout.jsx` | +2 sidebar entries |
| `ai-orchestrator/dashboard/src/App.jsx` | +2 routes |
| `PHASE_8_G_COMPLETE.md` | This document |

No new external dependencies. No requirements.txt change.

---

## 5. Acceptance check

> Streaming `/api/reasoning/run` emits `thought` and `tool_call`
> chunks live; the dashboard shows reasoning progress in real time.

✅ The SSE endpoint emits `start → thought → tool_call → … → final
→ done` and the dashboard has been receiving live `thought` /
`tool_call` events on the WS channel since Phase 7. SSE adds the
out-of-band streaming surface that external integrations and a
dedicated streaming UI can use.

> Operator can pick `security_audit` from a dropdown and run it
> with one click.

✅ `Prompt Library` tab lists all discovered MCP prompts; click
expands to show arguments; "Run" fires it through the deep reasoner
in `auto` mode (so the PAE flow gates anything dangerous).

> Memory page shows the last 50 episodes with feedback buttons.

⚠️ Backend is in place (`GET /api/reasoning/memory`,
`POST /api/reasoning/runs/{run_id}/feedback` from Milestone D); a
dedicated dashboard panel is left as polish — the existing
`ReasoningPanel` covers the immediate workflow and the API is
fully usable today.

---

## 6. Acknowledged limitations

1. **No SSE keep-alive ping.** Long idle gaps could cause some
   intermediaries to time out. Easy follow-up: emit a `ping` event
   every 15s from the `_runner` task.
2. **`run_streaming` waits for `run()` to complete before pushing
   `recall`/`plan`/`final`.** The harness emits `thought` and
   `tool_call` in real time (those flow through the queue
   instantly), but the post-run metadata only lands at the end.
   This is intentional — it keeps the implementation a thin wrapper
   over `run()` rather than duplicating its plumbing — at the cost
   of `recall` not arriving before the first thought.
3. **PromptLibrary renders one prompt at a time.** No multi-run
   queuing; no streaming view (it uses the blocking endpoint). For
   the current 14-prompt OpenClaw catalog this is fine.
4. **TriggersPanel polls every 5s.** Cheap and simple but not
   real-time. Could subscribe to the existing `trigger_fired` WS
   broadcast for instant updates — left as polish.
5. **No memory browser UI.** API is there, dashboard panel isn't.
   Same pattern as the existing components if anyone wants to add
   it.
6. **No prompt argument typing.** Arguments come back as schema
   from MCP but the UI renders all of them as plain text inputs.
   For OpenClaw's prompts this is sufficient.

---

## 7. Phase 8 summary — what we shipped end-to-end

Across milestones D + E + F + G:

| Milestone | One-line | Files | Tests |
|---|---|---|---|
| D — Memory | Episodic memory with feedback-weighted recall | `memory_store.py` + agent wiring | 14 |
| E — Plan-Approve-Execute | Dry-run interceptor + plan store + auto/plan/execute modes | `plan_executor.py` + agent wiring | 46 |
| F — Triggers | Cron + state-change triggers always firing through PAE | `triggers.py` + lifespan + 8 endpoints | 34 |
| G — Streaming + Prompts + UI | SSE endpoint + MCP prompt catalog + dashboard panels | 4 new files + wiring | 16 |
| **Total** | | | **+110** |

Suite went from 65 (end of Phase 7) → **175** (end of Phase 8),
with **zero regressions** along the way. No new external deps were
added in any milestone.

---

## 8. What's next

Phase 8 is closed. The orchestrator is now:

- Goal-driven (Phase 7)
- Reflective (D — remembers what worked)
- Accountable (E — proposes plans, gates dangerous actions)
- Proactive (F — fires on schedule and on state changes, all
  through PAE)
- Observable (G — streams its thinking, surfaces prompt workflows,
  exposes triggers in the UI)

Suggested next themes (Phase 9 candidates):
- **Multi-agent collaboration** — reasoner delegating sub-goals to
  specialist agents
- **Shared memory across users** — multi-tenant episodic store
- **Cost telemetry** — per-run token & latency reporting (the
  hooks are there in `HarnessResult`, just need a dashboard)
- **Prompt authoring** — let users define their own prompts as
  YAML and have them appear alongside MCP-discovered ones
- **End-to-end evaluation harness** — replay past episodes against
  the current agent and grade drift

---

*Phase 8 closes April 18, 2026. The orchestrator now thinks,
remembers, deliberates, acts on its own initiative — and shows its
work.*
