# Graham's AI Orchestrator

![Version](https://img.shields.io/badge/version-v0.12.0-blue) ![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue) ![Kernel](https://img.shields.io/badge/agent%20kernel-deterministic-8b5cf6)

**A local-first AI control plane for Home Assistant.**

AI Orchestrator turns natural-language goals into grounded observations and policy-checked Home Assistant plans. It combines the flexibility of frontier models with deterministic application code for validation, ordering, approvals, replay, budgets, and auditability.

## Why this project is different

- Home Assistant-native entity discovery and state observation.
- Local Ollama by default; OpenAI GPT‑5.6, Anthropic Claude Opus 4.8, GitHub Models, and Microsoft Foundry are opt-in.
- One transparent reasoning loop for chat, dashboard goals, prompt workflows, and proactive triggers.
- Plan → Approve → Execute with exact-argument replay and per-step persistence.
- Read-only parallelism but ordered mutations.
- Schema validation, allowlists, blocked domains, service policy, temperature bounds, timeouts, retry policy, duplicate suppression, and hard budgets.
- Episodic memory, RAG, optional external MCP, no-code agent factory, and generative live dashboards.
- Model-free safety evaluations plus a provider-neutral home-agent scenario dataset.

## 0.12 modernization

The 2026 release removes the dormant no-op LangGraph façade and makes the custom deterministic kernel authoritative. Legacy fixed-cadence autonomous loops are now opt-in because periodic single-shot model actions are less safe and less efficient than event-driven goals and Home Assistant triggers.

It also adds:

- GPT‑5.6 Responses API continuation with private local replay of encrypted reasoning items.
- Claude Opus 4.8 strict tools, adaptive thinking, effort control, and correct signed thinking/tool-result continuity.
- First-class `anthropic` provider selection.
- Atomic plan execution claims and progress checkpoints.
- A single guarded Home Assistant mutation path.
- Current FastAPI, Pydantic, MCP, ChromaDB, Ollama, React 19, and Vite 8 baselines.
- A vulnerability-free frontend dependency audit.

See [MODERNIZATION_2026.md](MODERNIZATION_2026.md) for the review, research, architecture decisions, breaking changes, and roadmap.

## Install

1. Add `https://github.com/ITSpecialist111/HASS-AI-Orchestrator` to the Home Assistant Add-on Store repositories.
2. Install **AI Orchestrator**.
3. Keep dry-run enabled and direct execution disabled initially.
4. Select a provider and configure its model and credentials.
5. Open the ingress dashboard, run read-only audits, and review generated plans before enabling live changes.

Detailed add-on configuration and safety behavior are documented in [ai-orchestrator/README.md](ai-orchestrator/README.md).

## Development verification

The supported backend test runtime is Python 3.11 or 3.12. The suite includes deterministic kernel, API, safety, plan execution, MCP, memory, trigger, provider, streaming, and Home Assistant adapter tests. The dashboard builds with Node 22 and Vite 8.

The root [Dockerfile.test](Dockerfile.test) now runs a clean lockfile-only frontend install/audit/build before assembling the Python test image, so CI also proves that no committed `node_modules` tree is required.

Current verified baseline: **266 backend tests passing, 4 live MCP tests skipped**, plus a clean frontend security audit and production build.

## Project status

The project remains pre-1.0 because live-home evaluations and a native Home Assistant conversation integration still need broader field testing. The safety and execution substrate is now suitable for that next stage; model intelligence is no longer being asked to compensate for missing runtime guarantees.
