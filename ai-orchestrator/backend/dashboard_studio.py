"""
Dashboard Studio — generative dashboards for AI Orchestrator.

The original :meth:`Orchestrator.generate_visual_dashboard` is a great
one-shot prompt-to-HTML pipeline, but it has the same limitation as
"text-to-image v0" tools used to: every refresh throws away the previous
output, you can't iterate, you can't compare, and you can't pin a
favourite.

Phase 10A turns dashboard generation into something closer to
modern image generators:

* **Gallery / persistence** — every generation is saved with full
  metadata (prompt, provider, model, timestamp, parent if iterated).
* **Iteration** — "make it more red", "add a solar chart" runs a
  refinement pass with the previous HTML as context, producing a new
  child entry in the gallery (the parent is preserved so you can
  always go back).
* **Variations** — generate N alternates from the same prompt in
  parallel so you can pick a favourite.
* **Live data binding** — the LLM is asked to wrap every dynamic value
  in ``<span data-entity="…" data-attr="…">…</span>`` placeholders.
  The studio injects a tiny polling shim into every saved dashboard so
  values stay fresh *without* re-running the LLM.
* **Multi-provider** — uses :func:`llm_providers.make_chat_provider`,
  so it works with Ollama, OpenAI, GitHub Models, and Microsoft
  Foundry out of the box (Phase 9).
* **Better grounding** — Home Assistant context is grouped by area +
  domain and summarised, not dumped as raw JSON, so the model sees the
  shape of the home rather than 30 random rows.

The studio writes to ``<store_dir>/<id>.html`` and a sidecar
``<id>.meta.json``. ``id`` is a short ULID-ish string derived from the
creation timestamp + a random suffix so directory listings sort
chronologically.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from llm_providers import ChatProvider, make_chat_provider, resolve_provider_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------
@dataclass
class DashboardMeta:
    """Sidecar metadata persisted next to each generated HTML file."""

    id: str
    title: str
    prompt: str
    instruction: Optional[str]   # the iterate/variation hint, if any
    parent_id: Optional[str]     # set when this dashboard is an iteration
    variation_of: Optional[str]  # set when produced by variations()
    created_at: str
    provider: str
    model: str
    pinned: bool = False
    size_bytes: int = 0
    entity_count: int = 0
    sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_ID_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"  # crockford-ish, no i/l/o/u


def _new_id() -> str:
    """Sortable timestamp prefix + random suffix, 16 chars total."""
    ts = int(time.time() * 1000)
    head = ""
    for _ in range(10):
        head = _ID_ALPHABET[ts % len(_ID_ALPHABET)] + head
        ts //= len(_ID_ALPHABET)
    tail = "".join(secrets.choice(_ID_ALPHABET) for _ in range(6))
    return head + tail


_TITLE_STOPWORDS = {
    "a", "an", "the", "with", "for", "of", "and", "or", "to", "in",
    "on", "at", "from", "by", "make", "create", "generate", "build",
    "show", "display", "design", "please",
}


def _title_from_prompt(prompt: str, max_words: int = 6) -> str:
    words = [w.strip(",.!?;:'\"") for w in prompt.split() if w.strip()]
    keep = [w for w in words if w.lower() not in _TITLE_STOPWORDS][:max_words]
    if not keep:
        keep = words[:max_words]
    title = " ".join(keep).strip()
    if len(title) > 60:
        title = title[:57].rstrip() + "…"
    return title or "Untitled dashboard"


_HTML_FENCE_RE = re.compile(r"```(?:html)?\s*", re.IGNORECASE)
_BACKTICK_FENCE_RE = re.compile(r"```\s*$", re.MULTILINE)


def _strip_markdown_fences(text: str) -> str:
    text = _HTML_FENCE_RE.sub("", text)
    text = _BACKTICK_FENCE_RE.sub("", text)
    return text.strip()


# Matches ``data-entity="domain.entity"`` (single or double quotes).
_ENTITY_REF_RE = re.compile(r"""data-entity\s*=\s*['"]([a-z_][a-z0-9_]*\.[a-zA-Z0-9_]+)['"]""")


def _extract_entity_refs(html: str) -> List[str]:
    """Return the unique ``data-entity`` ids referenced in *html*."""
    return sorted(set(_ENTITY_REF_RE.findall(html)))


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
_SYSTEM_BASE = """You are a senior smart-home data-visualisation designer.
You generate **complete, standalone HTML documents** that visualise live
Home Assistant state. The viewer renders your output directly inside an
``<iframe>``; nothing else wraps it.

Hard rules
----------
1. Output ONLY the HTML document. No prose, no markdown fences, no
   commentary. Start with ``<!doctype html>`` and end with ``</html>``.
2. Use Tailwind CSS via CDN
   (``<script src="https://cdn.tailwindcss.com"></script>``).
3. You may use Lucide icons via
   ``<script src="https://unpkg.com/lucide@latest"></script>`` and call
   ``lucide.createIcons()`` after DOM ready.
4. Every dynamic value MUST be wrapped in a placeholder so the host
   page can refresh it without re-running you:

       <span data-entity="sensor.kitchen_temperature" data-attr="state">
         …current value…
       </span>

   * ``data-entity`` is the Home Assistant entity id.
   * ``data-attr`` is either ``state`` (default if omitted) or
     ``attributes.<name>`` for an attribute (e.g.
     ``attributes.unit_of_measurement``).
   * The placeholder text content is what the viewer sees on first
     paint; the host JS will overwrite it once live state is fetched.
5. NEVER hard-code values that you saw in the context if a live
   placeholder would do — you only see a snapshot, the viewer wants
   live data.
6. Do NOT include ``<script>`` tags that fetch from the network
   yourself. The studio injects a polling shim automatically; adding
   your own fetch loops will cause double refreshes.
7. Background: prefer dark themes (``bg-slate-900``/``bg-zinc-950``)
   unless the user explicitly asks otherwise.
"""

_SYSTEM_ITERATE = """You are refining an existing dashboard. The
previous full HTML is supplied below. Apply the user's change request
**minimally** — keep the structure, layout, theme, and entity bindings
unless the request explicitly asks to change them. Output the FULL
updated HTML document (not a diff). All hard rules from the base
prompt still apply, including the ``data-entity`` placeholder
convention.
"""


# ---------------------------------------------------------------------------
# Live-data shim injected into every saved dashboard
# ---------------------------------------------------------------------------
_LIVE_SHIM_TEMPLATE = """
<script>
(function () {
  var DASHBOARD_ID = %DASHBOARD_ID_JSON%;
  var REFRESH_MS = 15000;
  function applyState(map) {
    document.querySelectorAll('[data-entity]').forEach(function (el) {
      var eid = el.getAttribute('data-entity');
      if (!eid || !map[eid]) return;
      var attr = el.getAttribute('data-attr') || 'state';
      var entity = map[eid];
      var value;
      if (attr === 'state') {
        value = entity.state;
      } else if (attr.indexOf('attributes.') === 0) {
        var key = attr.substring('attributes.'.length);
        value = (entity.attributes || {})[key];
      } else {
        value = entity[attr];
      }
      if (value === undefined || value === null) return;
      el.textContent = String(value);
    });
  }
  function tick() {
    fetch('api/studio/dashboards/' + DASHBOARD_ID + '/state', { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (j) applyState(j); })
      .catch(function () { /* silent */ });
  }
  tick();
  setInterval(tick, REFRESH_MS);
})();
</script>
"""


def _inject_live_shim(html: str, dashboard_id: str) -> str:
    """Append the polling shim before ``</body>`` (or at end if missing)."""
    shim = _LIVE_SHIM_TEMPLATE.replace("%DASHBOARD_ID_JSON%", json.dumps(dashboard_id))
    if "</body>" in html:
        return html.replace("</body>", shim + "\n</body>", 1)
    return html + shim


# ---------------------------------------------------------------------------
# DashboardStudio
# ---------------------------------------------------------------------------
class DashboardStudio:
    """Multi-provider generative dashboard engine with persistent gallery."""

    META_SUFFIX = ".meta.json"
    HTML_SUFFIX = ".html"

    def __init__(
        self,
        ha_client_provider: Callable[[], Any],
        store_dir: Path | str,
        *,
        chat_provider_factory: Callable[..., ChatProvider] = make_chat_provider,
        default_provider: Optional[str] = None,
        default_model: Optional[str] = None,
    ) -> None:
        self._ha_provider = ha_client_provider
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._chat_provider_factory = chat_provider_factory
        self._default_provider = default_provider
        self._default_model = default_model

    # ------------------------------------------------------------------
    # Provider/model resolution
    # ------------------------------------------------------------------
    def _resolve_model(self, provider_name: str, override: Optional[str]) -> str:
        if override:
            return override
        if self._default_model:
            return self._default_model
        return {
            "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "github": os.getenv("GITHUB_MODEL", "gpt-4o-mini"),
            "foundry": os.getenv("FOUNDRY_MODEL", "gpt-4o"),
            "ollama": os.getenv("ORCHESTRATOR_MODEL", "deepseek-r1:8b"),
        }.get(provider_name, "deepseek-r1:8b")

    # ------------------------------------------------------------------
    # Home Assistant context
    # ------------------------------------------------------------------
    @property
    def ha_client(self) -> Any:
        if callable(self._ha_provider):
            return self._ha_provider()
        return self._ha_provider

    async def gather_context(self, max_entities_per_domain: int = 12) -> Dict[str, Any]:
        """Build a structured snapshot of the home for the LLM.

        Unlike the legacy generator, this groups entities by domain and
        keeps a small per-domain sample so the model can see the *shape*
        of the home (e.g. "8 lights, 14 temperature sensors, 2 locks")
        instead of being drowned in raw JSON.
        """
        client = self.ha_client
        if not client or not getattr(client, "connected", False):
            return {"connected": False, "domains": {}, "summary": {}, "totals": {}}

        try:
            states = await client.get_states()
        except Exception as exc:
            logger.warning("dashboard_studio: failed to fetch states (%s)", exc)
            return {"connected": False, "domains": {}, "summary": {}, "totals": {}}

        if not isinstance(states, list):
            states = [states] if states else []

        by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for s in states:
            entity_id = s.get("entity_id") if isinstance(s, dict) else None
            if not entity_id:
                continue
            domain = entity_id.split(".", 1)[0]
            by_domain.setdefault(domain, []).append(s)

        domains_summary: Dict[str, Any] = {}
        sampled: Dict[str, List[Dict[str, Any]]] = {}
        for domain in sorted(by_domain.keys()):
            rows = by_domain[domain]
            domains_summary[domain] = len(rows)
            sample = []
            for row in rows[:max_entities_per_domain]:
                sample.append({
                    "entity_id": row.get("entity_id"),
                    "state": row.get("state"),
                    "name": (row.get("attributes") or {}).get("friendly_name"),
                    "unit": (row.get("attributes") or {}).get("unit_of_measurement"),
                    "device_class": (row.get("attributes") or {}).get("device_class"),
                })
            sampled[domain] = sample

        return {
            "connected": True,
            "totals": {"entities": sum(domains_summary.values()), "domains": len(domains_summary)},
            "summary": domains_summary,
            "domains": sampled,
        }

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    def _meta_path(self, dashboard_id: str) -> Path:
        return self.store_dir / f"{dashboard_id}{self.META_SUFFIX}"

    def _html_path(self, dashboard_id: str) -> Path:
        return self.store_dir / f"{dashboard_id}{self.HTML_SUFFIX}"

    def _save(self, meta: DashboardMeta, html: str) -> None:
        self._html_path(meta.id).write_text(html, encoding="utf-8")
        self._meta_path(meta.id).write_text(
            json.dumps(meta.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def get_meta(self, dashboard_id: str) -> Optional[DashboardMeta]:
        path = self._meta_path(dashboard_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return DashboardMeta(**data)
        except Exception as exc:
            logger.warning("dashboard_studio: bad meta file %s (%s)", path, exc)
            return None

    def get_html(self, dashboard_id: str) -> Optional[str]:
        path = self._html_path(dashboard_id)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def list_dashboards(self) -> List[DashboardMeta]:
        out: List[DashboardMeta] = []
        for meta_file in sorted(self.store_dir.glob(f"*{self.META_SUFFIX}"), reverse=True):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                out.append(DashboardMeta(**data))
            except Exception as exc:
                logger.warning("dashboard_studio: skipping bad meta %s (%s)", meta_file, exc)
        # Pinned first, then newest.
        out.sort(key=lambda m: (not m.pinned, -_id_to_int(m.id)))
        return out

    def delete_dashboard(self, dashboard_id: str) -> bool:
        meta = self.get_meta(dashboard_id)
        if meta is None:
            return False
        if meta.pinned:
            # Pinned dashboards are protected from accidental delete.
            return False
        for path in (self._meta_path(dashboard_id), self._html_path(dashboard_id)):
            try:
                path.unlink(missing_ok=True)
            except Exception as exc:  # pragma: no cover - filesystem races
                logger.warning("dashboard_studio: failed to delete %s (%s)", path, exc)
        return True

    def set_pinned(self, dashboard_id: str, pinned: bool) -> Optional[DashboardMeta]:
        meta = self.get_meta(dashboard_id)
        if meta is None:
            return None
        if meta.pinned == pinned:
            return meta
        meta.pinned = pinned
        self._meta_path(dashboard_id).write_text(
            json.dumps(meta.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return meta

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    async def generate(
        self,
        prompt: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        instruction: Optional[str] = None,
        parent_id: Optional[str] = None,
        variation_of: Optional[str] = None,
    ) -> DashboardMeta:
        """Run a single generation and persist it."""
        provider_name = resolve_provider_name(provider or self._default_provider)
        chat = self._chat_provider_factory(provider=provider_name)
        model_name = self._resolve_model(provider_name, model)

        context = await self.gather_context()
        base_html: Optional[str] = None
        if parent_id:
            base_html = self.get_html(parent_id)

        messages = self._build_messages(prompt, context, instruction, base_html)

        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(
            None,
            lambda: chat.chat(model_name, messages, temperature=0.4, max_tokens=4096),
        )
        html = _strip_markdown_fences(raw)
        if not html.lower().startswith("<!doctype") and not html.lower().startswith("<html"):
            # Pad with a minimal frame so iframes still render *something*.
            html = (
                "<!doctype html><html><body class=\"bg-slate-900 text-slate-200 p-6 font-sans\">"
                f"<pre class=\"whitespace-pre-wrap text-sm\">{_html_escape(html)}</pre>"
                "</body></html>"
            )

        dashboard_id = _new_id()
        html = _inject_live_shim(html, dashboard_id)

        meta = DashboardMeta(
            id=dashboard_id,
            title=_title_from_prompt(instruction or prompt),
            prompt=prompt,
            instruction=instruction,
            parent_id=parent_id,
            variation_of=variation_of,
            created_at=datetime.now(timezone.utc).isoformat(),
            provider=provider_name,
            model=model_name,
            pinned=False,
            size_bytes=len(html.encode("utf-8")),
            entity_count=len(_extract_entity_refs(html)),
            sha256=hashlib.sha256(html.encode("utf-8")).hexdigest(),
        )
        self._save(meta, html)
        logger.info(
            "dashboard_studio: generated %s (%s/%s, %d bytes, %d entities)",
            meta.id, meta.provider, meta.model, meta.size_bytes, meta.entity_count,
        )
        return meta

    async def iterate(
        self,
        base_id: str,
        instruction: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[DashboardMeta]:
        """Refine an existing dashboard with a new instruction."""
        base = self.get_meta(base_id)
        if base is None:
            return None
        return await self.generate(
            prompt=base.prompt,
            provider=provider,
            model=model,
            instruction=instruction,
            parent_id=base_id,
        )

    async def variations(
        self,
        prompt: str,
        n: int = 3,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[DashboardMeta]:
        """Generate ``n`` independent variations from the same prompt."""
        n = max(1, min(int(n), 6))
        # Tag each variation with a unique seed hint so the model is
        # nudged to produce different layouts/themes.
        seeds = ["bold and dense", "minimal and airy", "data-rich with sparklines",
                 "playful and colourful", "monochrome editorial", "neon cyberpunk"]
        first = await self.generate(
            prompt=prompt,
            provider=provider,
            model=model,
            instruction=f"Variation 1 of {n}: {seeds[0]}",
            variation_of="root",
        )
        # The first dashboard becomes the variation_of anchor for the rest.
        anchor = first.id
        # Update the first to point at itself for clarity.
        first = self.set_pinned(first.id, False) or first  # no-op write to ensure persisted
        first.variation_of = anchor
        self._meta_path(first.id).write_text(
            json.dumps(first.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

        rest = await asyncio.gather(*[
            self.generate(
                prompt=prompt,
                provider=provider,
                model=model,
                instruction=f"Variation {i + 1} of {n}: {seeds[i % len(seeds)]}",
                variation_of=anchor,
            )
            for i in range(1, n)
        ])
        return [first, *rest]

    # ------------------------------------------------------------------
    # Live state
    # ------------------------------------------------------------------
    async def live_state_for(self, dashboard_id: str) -> Dict[str, Any]:
        """Return ``{entity_id: state_object}`` for entities used in the dashboard."""
        html = self.get_html(dashboard_id)
        if html is None:
            return {}
        ids = _extract_entity_refs(html)
        if not ids:
            return {}

        client = self.ha_client
        if not client or not getattr(client, "connected", False):
            return {}

        results: Dict[str, Any] = {}

        async def _one(eid: str) -> None:
            try:
                state = await client.get_states(entity_id=eid)
            except Exception:
                return
            if not state:
                return
            # ``get_states(entity_id=...)`` returns a single dict; some
            # mocks may still wrap in a list — handle both.
            if isinstance(state, list):
                state = state[0] if state else None
            if isinstance(state, dict):
                results[eid] = {
                    "state": state.get("state"),
                    "attributes": state.get("attributes") or {},
                    "last_updated": state.get("last_updated"),
                }

        await asyncio.gather(*[_one(eid) for eid in ids])
        return results

    # ------------------------------------------------------------------
    # Prompt assembly
    # ------------------------------------------------------------------
    def _build_messages(
        self,
        prompt: str,
        context: Dict[str, Any],
        instruction: Optional[str],
        base_html: Optional[str],
    ) -> List[Dict[str, Any]]:
        system = _SYSTEM_BASE
        if base_html:
            system = system + "\n\n" + _SYSTEM_ITERATE

        # Keep the context compact: summary first, then per-domain sample.
        ctx_lines: List[str] = []
        ctx_lines.append("# Home Assistant context")
        if not context.get("connected"):
            ctx_lines.append("(Home Assistant is not currently connected; design with placeholders only.)")
        else:
            totals = context.get("totals", {})
            ctx_lines.append(
                f"{totals.get('entities', 0)} entities across {totals.get('domains', 0)} domains:"
            )
            summary = context.get("summary", {})
            for domain, count in sorted(summary.items(), key=lambda x: -x[1])[:20]:
                ctx_lines.append(f"  * {domain}: {count}")
            ctx_lines.append("")
            ctx_lines.append("## Sample entities (per domain)")
            for domain, rows in (context.get("domains") or {}).items():
                if not rows:
                    continue
                ctx_lines.append(f"### {domain}")
                for row in rows:
                    name = row.get("name") or row.get("entity_id")
                    unit = row.get("unit") or ""
                    dc = row.get("device_class") or ""
                    extras = " ".join(filter(None, [unit, f"({dc})" if dc else ""]))
                    ctx_lines.append(
                        f"- `{row.get('entity_id')}` — {name} = {row.get('state')} {extras}".rstrip()
                    )
        ctx_block = "\n".join(ctx_lines)

        user_parts: List[str] = []
        user_parts.append(f"User prompt: {prompt}")
        if instruction:
            user_parts.append(f"Refinement: {instruction}")
        user_parts.append("")
        user_parts.append(ctx_block)
        if base_html:
            # Truncate base HTML to keep within token budget; the model
            # only needs the structural skeleton to refine.
            trimmed = base_html
            if len(trimmed) > 12_000:
                trimmed = trimmed[:12_000] + "\n<!-- …truncated for context… -->"
            user_parts.append("")
            user_parts.append("# Existing dashboard to refine")
            user_parts.append("```html")
            user_parts.append(trimmed)
            user_parts.append("```")

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n".join(user_parts)},
        ]


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------
def _id_to_int(dashboard_id: str) -> int:
    """Decode the timestamp prefix back to an int for sorting."""
    if len(dashboard_id) < 10:
        return 0
    head = dashboard_id[:10]
    n = 0
    for ch in head:
        idx = _ID_ALPHABET.find(ch)
        if idx < 0:
            return 0
        n = n * len(_ID_ALPHABET) + idx
    return n


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&#39;")
    )
