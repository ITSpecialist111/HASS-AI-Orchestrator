"""
Plan → Approve → Execute (Phase 8 / Milestone E).

The deep reasoner can run in **plan mode**: every mutating tool call
is intercepted by :class:`DryRunInterceptor`, which records the
intent and returns a synthetic success result so the LLM keeps
reasoning. Read-only tools (state/history/discovery) pass through
unchanged because the model needs ground-truth to plan well.

When a plan finishes, :class:`PlanStore` persists the recorded
intents to ``/data/plans.db``. A separate execute endpoint replays
those intents *deterministically* — no second LLM round-trip — so
the actions the human approved are exactly the actions that fire.

This module is deliberately self-contained: it knows about
:class:`ToolRegistry` from ``reasoning_harness`` but not about the
agent or the LLM.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
#: Verb prefixes that indicate a tool *only reads* state. Names are
#: lower-cased before matching. Underscores in the middle are tolerated.
READ_ONLY_PREFIXES: Tuple[str, ...] = (
    "list_", "get_", "search_", "read_", "query_", "find_",
    "describe_", "info_", "history_", "fetch_", "lookup_",
    "render_template", "summary_",
)

#: Substrings that *always* mean a mutating call regardless of prefix.
#: We keep this conservative — false positives (treating a read as
#: mutating) merely block the model less efficiently; false negatives
#: would let unapproved actions slip through.
MUTATING_HINTS: Tuple[str, ...] = (
    "set_", "turn_", "toggle", "lock", "unlock", "arm_", "disarm_",
    "create", "update", "delete", "remove", "call_service",
    "trigger", "enable", "disable", "restart", "reload",
    "fire_event", "send_", "post_", "patch_", "execute",
)

#: Tools whose mere invocation is high-impact and demand approval
#: even if a plan contains nothing else interesting. Patterns are
#: matched against the lower-cased name with ``_`` treated as a word
#: boundary (so ``lock_front_door`` matches ``lock``).
HIGH_IMPACT_PATTERNS: Tuple[re.Pattern, ...] = tuple(re.compile(p) for p in (
    r"(?:^|_)lock(?:_|$)", r"(?:^|_)unlock(?:_|$)",
    r"(?:^|_)arm_\w+", r"(?:^|_)disarm\w*",
    r"alarm",
    r"set_temperature", r"set_hvac", r"set_thermostat",
    r"thermostat",
    r"automation_(create|update|delete)",
    r"script_(create|update|delete)",
    r"scene_(create|update|delete)",
    r"call_service",  # too broad to know — assume worst case
    r"(?:^|_)restart(?:_|$)", r"(?:^|_)reload(?:_|$)",
))

#: Provider name prefixes that are stripped before classification.
#: Lets us treat ``ha_list_entities`` the same as ``list_entities``.
PROVIDER_PREFIXES: Tuple[str, ...] = ("ha_", "hass_", "ext_", "openclaw_", "mcp_")


@dataclass
class Classification:
    """How a single tool call is treated by the planner."""

    is_mutating: bool
    impact_level: str  # "read" | "low" | "medium" | "high"
    reason: str


class ToolClassifier:
    """Heuristic classifier — tool name + arguments → Classification.

    Override ``read_only_overrides`` / ``mutating_overrides`` to
    customise per-deployment. The defaults err on the side of
    declaring things mutating, which is the safe failure mode.
    """

    def __init__(
        self,
        read_only_overrides: Optional[List[str]] = None,
        mutating_overrides: Optional[List[str]] = None,
        high_impact_overrides: Optional[List[str]] = None,
    ) -> None:
        self.read_only_overrides = set(read_only_overrides or [])
        self.mutating_overrides = set(mutating_overrides or [])
        self.high_impact_overrides = set(high_impact_overrides or [])

    def classify(self, name: str, arguments: Dict[str, Any]) -> Classification:
        original = name.lower()
        # Strip provider prefixes so ``hass_list_entities`` matches
        # the same rules as ``list_entities``.
        n = original
        for prefix in PROVIDER_PREFIXES:
            if n.startswith(prefix):
                n = n[len(prefix):]
                break

        if original in self.read_only_overrides or n in self.read_only_overrides:
            return Classification(False, "read", "explicit read-only override")
        if original in self.mutating_overrides or n in self.mutating_overrides:
            return Classification(True, self._impact(n, arguments), "explicit mutating override")

        # High-impact pattern wins outright.
        if (any(p.search(n) for p in HIGH_IMPACT_PATTERNS)
                or original in self.high_impact_overrides
                or n in self.high_impact_overrides):
            return Classification(True, "high", "matched high-impact pattern")

        # Read-only prefix wins (checked before generic mutating hints
        # so e.g. ``get_state`` isn't dragged in by a stray substring).
        if any(n.startswith(p) for p in READ_ONLY_PREFIXES):
            return Classification(False, "read", "matched read-only prefix")

        # Mutating hint anywhere in the name → mutating.
        if any(h in n for h in MUTATING_HINTS):
            return Classification(True, self._impact(n, arguments), "matched mutating hint")

        # Unknown → conservative: treat as low-impact mutating so we
        # at least record it. Better to have an extra plan step than
        # to silently fire something we didn't recognise.
        return Classification(True, "low", "unrecognised — treated as mutating")

    @staticmethod
    def _impact(name: str, args: Dict[str, Any]) -> str:
        n = name.lower()
        if any(p.search(n) for p in HIGH_IMPACT_PATTERNS):
            return "high"
        # Heating/cooling are typically medium even without explicit hint.
        if "temperature" in n or "thermostat" in n or "hvac" in n:
            return "medium"
        # Default for routine mutations (lights, switches).
        return "low"


# ---------------------------------------------------------------------------
# Recorded intents + plan proposals
# ---------------------------------------------------------------------------
@dataclass
class RecordedIntent:
    """A single tool call the LLM *would have* made in execute mode."""

    sequence: int
    tool_name: str
    arguments: Dict[str, Any]
    impact_level: str
    classification_reason: str
    simulated_result: Dict[str, Any]
    iteration: int  # which harness iteration produced it
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlanProposal:
    """A complete reasoning plan awaiting approval / execution."""

    id: str
    run_id: Optional[str]
    goal: str
    intents: List[RecordedIntent]
    answer: str
    iterations: int
    duration_ms: int
    backend: Optional[str]
    timestamp: str
    status: str = "pending"  # pending | approved | executed | rejected | expired
    requires_approval: bool = True
    risk_summary: str = ""
    executed_at: Optional[str] = None
    execution_results: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def high_impact_count(self) -> int:
        return sum(1 for i in self.intents if i.impact_level == "high")

    @property
    def mutating_count(self) -> int:
        return len(self.intents)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["high_impact_count"] = self.high_impact_count
        d["mutating_count"] = self.mutating_count
        return d


# ---------------------------------------------------------------------------
# Dry-run interceptor
# ---------------------------------------------------------------------------
ToolCallable = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]


class DryRunInterceptor:
    """Wraps a tool-callable so mutating calls are *recorded, not run*.

    The interceptor is stateful — it accumulates :class:`RecordedIntent`
    rows across the lifetime of one reasoning run and then exposes them
    via :pyattr:`intents`. Read-only calls pass straight through to the
    real callable.
    """

    def __init__(
        self,
        underlying_call: ToolCallable,
        classifier: Optional[ToolClassifier] = None,
        *,
        synthetic_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._call = underlying_call
        self.classifier = classifier or ToolClassifier()
        self._synthetic = synthetic_payload or {
            "ok": True,
            "dry_run": True,
            "note": "Plan mode: action recorded for approval, not executed.",
        }
        self.intents: List[RecordedIntent] = []
        self._current_iteration: int = 0

    # ------------------------------------------------------------------
    def set_iteration(self, iteration: int) -> None:
        """Called by the harness before each iteration so recorded
        intents know which step produced them."""
        self._current_iteration = iteration

    async def call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        cls = self.classifier.classify(name, arguments)
        if not cls.is_mutating:
            return await self._call(name, arguments)

        # Mutating: record + synthesise success.
        intent = RecordedIntent(
            sequence=len(self.intents) + 1,
            tool_name=name,
            arguments=dict(arguments),
            impact_level=cls.impact_level,
            classification_reason=cls.reason,
            simulated_result=dict(self._synthetic),
            iteration=self._current_iteration,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.intents.append(intent)
        logger.debug(
            "DryRunInterceptor recorded #%d %s impact=%s",
            intent.sequence, name, cls.impact_level,
        )
        return {**self._synthetic, "intent_sequence": intent.sequence}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
class PlanStore:
    """SQLite-backed store for plan proposals.

    Lives in ``/data/plans.db`` (or a workspace-local fallback when
    ``/data`` doesn't exist, e.g. tests).
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS plans (
        id TEXT PRIMARY KEY,
        run_id TEXT,
        goal TEXT NOT NULL,
        answer TEXT NOT NULL,
        iterations INTEGER NOT NULL,
        duration_ms INTEGER NOT NULL,
        backend TEXT,
        timestamp TEXT NOT NULL,
        status TEXT NOT NULL,
        requires_approval INTEGER NOT NULL,
        risk_summary TEXT,
        intents_json TEXT NOT NULL,
        execution_results_json TEXT,
        executed_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status, timestamp);
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            base = Path("/data") if Path("/data").exists() else Path(__file__).parent.parent / "data"
            base.mkdir(parents=True, exist_ok=True)
            db_path = str(base / "plans.db")
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(self.SCHEMA)
        logger.info("PlanStore initialised at %s", self.db_path)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    def save(self, plan: PlanProposal) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO plans (
                    id, run_id, goal, answer, iterations, duration_ms, backend,
                    timestamp, status, requires_approval, risk_summary,
                    intents_json, execution_results_json, executed_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    plan.id, plan.run_id, plan.goal, plan.answer, plan.iterations,
                    plan.duration_ms, plan.backend, plan.timestamp, plan.status,
                    int(plan.requires_approval), plan.risk_summary,
                    json.dumps([i.to_dict() for i in plan.intents]),
                    json.dumps(plan.execution_results) if plan.execution_results else None,
                    plan.executed_at,
                ),
            )

    def get(self, plan_id: str) -> Optional[PlanProposal]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        return _row_to_plan(row) if row else None

    def list(self, *, status: Optional[str] = None, limit: int = 50) -> List[PlanProposal]:
        q = "SELECT * FROM plans"
        args: Tuple[Any, ...] = ()
        if status:
            q += " WHERE status = ?"
            args = (status,)
        q += " ORDER BY timestamp DESC LIMIT ?"
        args = args + (int(limit),)
        with self._conn() as c:
            rows = c.execute(q, args).fetchall()
        return [_row_to_plan(r) for r in rows]

    def update_status(
        self,
        plan_id: str,
        status: str,
        *,
        execution_results: Optional[List[Dict[str, Any]]] = None,
        executed_at: Optional[str] = None,
    ) -> bool:
        with self._conn() as c:
            cur = c.execute(
                """UPDATE plans
                   SET status = ?,
                       execution_results_json = COALESCE(?, execution_results_json),
                       executed_at = COALESCE(?, executed_at)
                   WHERE id = ?""",
                (
                    status,
                    json.dumps(execution_results) if execution_results is not None else None,
                    executed_at,
                    plan_id,
                ),
            )
        return cur.rowcount > 0


def _row_to_plan(row: sqlite3.Row) -> PlanProposal:
    intents_raw = json.loads(row["intents_json"] or "[]")
    intents = [RecordedIntent(**i) for i in intents_raw]
    exec_raw = row["execution_results_json"]
    return PlanProposal(
        id=row["id"],
        run_id=row["run_id"],
        goal=row["goal"],
        intents=intents,
        answer=row["answer"],
        iterations=row["iterations"],
        duration_ms=row["duration_ms"],
        backend=row["backend"],
        timestamp=row["timestamp"],
        status=row["status"],
        requires_approval=bool(row["requires_approval"]),
        risk_summary=row["risk_summary"] or "",
        executed_at=row["executed_at"],
        execution_results=json.loads(exec_raw) if exec_raw else [],
    )


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------
async def replay_plan(
    plan: PlanProposal,
    underlying_call: ToolCallable,
) -> List[Dict[str, Any]]:
    """Execute the recorded intents in order against the real tools.

    Returns a list of ``{sequence, tool_name, arguments, result,
    duration_ms, ok}`` dicts in the same order as ``plan.intents``.
    Stops on the first failure and marks remaining intents skipped.

    Determinism: we use the *exact* arguments captured during planning,
    so the executed actions match what the human approved. We do not
    consult the LLM during replay.
    """
    out: List[Dict[str, Any]] = []
    aborted = False
    for intent in plan.intents:
        if aborted:
            out.append({
                "sequence": intent.sequence,
                "tool_name": intent.tool_name,
                "arguments": intent.arguments,
                "result": None,
                "ok": False,
                "skipped": True,
                "duration_ms": 0,
            })
            continue
        t0 = time.monotonic()
        try:
            result = await underlying_call(intent.tool_name, intent.arguments)
            ok = _result_ok(result)
        except Exception as exc:
            result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            ok = False
        out.append({
            "sequence": intent.sequence,
            "tool_name": intent.tool_name,
            "arguments": intent.arguments,
            "result": result,
            "ok": ok,
            "skipped": False,
            "duration_ms": int((time.monotonic() - t0) * 1000),
        })
        if not ok:
            aborted = True
            logger.warning(
                "replay_plan: aborting after failed step #%d (%s)",
                intent.sequence, intent.tool_name,
            )
    return out


def _result_ok(result: Any) -> bool:
    if not isinstance(result, dict):
        return True  # unknown shape, assume success
    if "ok" in result:
        return bool(result.get("ok"))
    if "error" in result:
        return False
    if result.get("status") == "pending_approval":
        # The local MCP layer queues high-impact actions itself; that's
        # still a "successful" outcome from the planner's point of view.
        return True
    return True


# ---------------------------------------------------------------------------
# Risk summary
# ---------------------------------------------------------------------------
def summarise_risk(intents: List[RecordedIntent]) -> str:
    """Human-readable one-liner for the dashboard / approval card."""
    if not intents:
        return "Read-only plan (no actions to execute)."
    by_level: Dict[str, int] = {}
    for i in intents:
        by_level[i.impact_level] = by_level.get(i.impact_level, 0) + 1
    parts = []
    for level in ("high", "medium", "low"):
        n = by_level.get(level, 0)
        if n:
            parts.append(f"{n} {level}-impact")
    head = ", ".join(parts) if parts else f"{len(intents)} actions"
    return f"{head} action(s) across {len(intents)} step(s)."
