# Gemma 4 E4B profiles and human control layer

**Release:** 0.13.0
**Scope:** local model selection, per-run depth, deterministic action invariants, and dashboard information architecture

## Why `gemma4:e4b`

The requested target was an 8B-class Gemma model that could support both low-latency checks and deeper tool-based investigation without installing separate rapid and reasoning models.

Ollama's official `gemma4:e4b` artifact is the E4B variant in Gemma 4's roughly 8B-total parameter class. The published Ollama artifact is approximately 9.6 GB and advertises a 128K context window. It supports tools and thinking, so one model can serve all three operator profiles.

The runtime deliberately does not force the advertised maximum context. Context allocation has a direct memory cost and should remain a deployment/hardware decision.

## Official generation contract

Gemma 4 guidance recommends:

- `temperature=1.0`;
- `top_p=0.95`; and
- `top_k=64`.

All profiles keep those values. Rapid is not made faster by degrading sampling. Instead, it explicitly disables thinking and receives smaller output/run budgets.

Ollama's chat API exposes `think` as a top-level request field, not an entry in `options`. Release 0.13 sends this documented shape:

| Profile | `think` | Maximum generated tokens | Run limits before deployment caps |
|---|---:|---:|---|
| Rapid | `false` | 1,024 | 6 iterations, 3 tools/turn, 12 tools, 60 s |
| Balanced | `true` | 3,072 | 12 iterations, 5 tools/turn, 30 tools, 180 s |
| Deep | `true` | 4,096 | 40 iterations, 6 tools/turn, 200 tools, 1,800 s |

The shipped deployment caps Deep at 20 iterations, 5 tools/turn, 48 total tools, 420 seconds, and 240 seconds per model call. Profile limits and deployment limits are combined with `min()`, so a profile can never exceed operator configuration.

There is no unsupported or invented “thinking-token budget” parameter. Balanced and Deep both use Ollama's documented boolean thinking control; their practical depth differs through output and run ceilings.

## Thinking privacy

Ollama returns reasoning separately as `message.thinking`. The backend intentionally does not copy that field into:

- `LLMResponse.content`;
- subsequent conversation messages;
- `HarnessStep` traces;
- persisted decision JSON;
- SSE operator progress; or
- the React dashboard.

The human sees model-authored updates when present, ground-truth observations, guarded tool requests, exact plans, and outcomes. Private scratch reasoning is neither presented as an explanation nor replayed as trusted context.

## Deterministic invariants

Profiles are immutable per-run policy objects. They affect model thinking, output, and resource ceilings only. The following remain identical for Rapid, Balanced, and Deep:

- closed JSON Schema validation;
- deployment domain/service/entity policy;
- trusted execution context;
- read-only parallel scheduling;
- ordered mutation scheduling;
- read-only retry boundaries;
- non-retry of mutations;
- read caching and invalidation after mutation;
- idempotent deduplication;
- non-idempotent duplicate blocking;
- exact plan interception;
- high-impact human approval;
- atomic plan claims;
- step checkpoints; and
- protocol-complete results for rejected tool requests.

A dedicated regression executes two mutation requests under Deep and asserts that their observed order remains `[1, 2]`.

## Public API

The following requests accept optional `profile: rapid|balanced|deep`:

- `POST /api/reasoning/run`;
- `POST /api/reasoning/stream`; and
- `POST /api/reasoning/prompts/{name}/run`.

The selected profile is returned by blocking results, SSE start/final events, diagnostics, and persisted run records. `/api/reasoning/info` publishes the three profiles with their effective deployment-capped limits.

## Human interface rationale

The old dashboard exposed nine implementation-oriented tabs with equal visual weight. Release 0.13 reorganizes the product around operator intent:

1. **Home** — Is the system healthy, and does anything need attention?
2. **Ask & Run** — What outcome should the home accomplish, and how deeply should it reason?
3. **Plans** — What exact physical actions require human authority?
4. **Automation** — Which specialists and proactive triggers are configured?
5. **Insights** — What happened, and how is the system performing?
6. **Studio** — Which purpose-built visual views exist?

Quick Ask remains available from every page but now calls the same authoritative reasoning endpoint directly.

The interface uses the exact Clawpilot light/dark variables, Segoe UI/Aptos, a single rose accent, status-only success/warning/danger colors, semantic focus rings, reduced-motion support, responsive cards, and a mobile drawer. Raw payloads and tool arguments remain available behind explicit disclosure instead of dominating the primary view.

## Deployment migration

- New installs use `gemma4:e4b` for all local model defaults.
- Existing `/config/agents.yaml` is retained and never overwritten.
- The add-on checks exact Ollama model tags and pulls each distinct configured model once.
- `reasoning_default_profile` defaults to `balanced`.
- The local artifact requires substantially more storage than the previous small fast-model default; verify disk and memory before upgrade.
- Keep dry-run enabled while validating the new model on representative entities and plans.

## Sources

- [Google Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- [Google Gemma function calling](https://ai.google.dev/gemma/docs/capabilities/function-calling)
- [Ollama Gemma 4 library](https://ollama.com/library/gemma4)
- [Ollama thinking capability](https://docs.ollama.com/capabilities/thinking)
- [Ollama tool calling capability](https://docs.ollama.com/capabilities/tool-calling)
