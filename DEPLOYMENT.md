# AI Orchestrator 0.13 deployment guide

This guide covers the Home Assistant add-on release that uses `gemma4:e4b` as its single local reasoning model, exposes Rapid/Balanced/Deep profiles, and keeps all physical actions inside the deterministic tool and plan kernel.

## Install from the add-on repository

1. Open **Settings → Add-ons → Add-on Store** in Home Assistant.
2. Open **Repositories** from the three-dot menu.
3. Add `https://github.com/ITSpecialist111/HASS-AI-Orchestrator`.
4. Install **AI Orchestrator**.
5. Open **Configuration** before the first start.
6. Keep `dry_run_mode: true` and `reasoning_allow_direct_execute: false`.
7. Start the add-on and open its ingress UI.

The first local-model start can take time. The E4B Ollama artifact is approximately 9.6 GB, in addition to Python, frontend, embedding, decision, and dashboard storage.

## Recommended local configuration

```yaml
ollama_host: http://localhost:11434
llm_provider: ollama

# Usually leave both blank: the add-on uses the Supervisor Core proxy.
# For direct Core access, configure both values instead.
ha_url: ""
ha_access_token: ""

orchestrator_model: gemma4:e4b
smart_model: gemma4:e4b
fast_model: gemma4:e4b
deep_reasoning_model: gemma4:e4b
reasoning_default_profile: balanced

dry_run_mode: true
reasoning_allow_direct_execute: false
deep_reasoning_max_iterations: 20
reasoning_max_tool_calls: 48
reasoning_max_seconds: 420
reasoning_llm_timeout: 240
reasoning_tool_timeout: 30
reasoning_max_concurrent_runs: 1

enable_legacy_autonomous_loops: false
enable_legacy_dashboard_loop: false
enable_rag: true
disable_telemetry: true
```

When `ollama_host` points to localhost, the add-on starts Ollama and pulls each distinct configured model exactly once. Exact model tags are checked, so another Gemma variant does not satisfy `gemma4:e4b` accidentally.

For an external Ollama host, pull the model on that server:

```text
ollama pull gemma4:e4b
```

RAG can also pull its embedding model on first use.

## Reasoning profiles

| Profile | Thinking | Default effective ceiling | Recommended use |
|---|---|---|---|
| Rapid | Off | 6 iterations / 12 tools / 60 seconds | State checks and simple routines |
| Balanced | On | 12 iterations / 30 tools / 180 seconds | Normal multi-step home goals |
| Deep | On | 20 iterations / 48 tools / 420 seconds | Complex diagnosis across systems |

The deployment settings are hard ceilings. Profiles do not alter tool schemas, domain policy, mutation order, approval gates, retries, deduplication, or exact-plan replay.

## Home Assistant authentication

The add-on uses one of two mutually exclusive modes:

1. **Supervisor proxy (recommended):** leave `ha_url` and `ha_access_token` blank. Home Assistant injects `SUPERVISOR_TOKEN`; the add-on connects through `http://supervisor/core`.
2. **Direct Core:** set `ha_access_token` to a Home Assistant Long-Lived Access Token. Optionally set `ha_url` (for example `http://192.168.68.57:8123`); when omitted in add-on mode, the internal `http://homeassistant:8123` hostname is used.

Never place tokens in prompts, agent instructions, entity names, logs, screenshots, or support messages. `/api/health` and `/api/health/home-assistant` deliberately expose connection diagnostics without credentials or entity values.

## First-run verification

1. Confirm the Home page reports a live Home Assistant connection.
2. Open **Ask & Run** and verify `ollama / gemma4:e4b` is shown.
3. Select **Rapid** and run: “Audit the home for unavailable entities. Do not change anything.”
4. Confirm every entity ID came from a discovery/state tool.
5. Select **Balanced**, choose **Plan only**, and request a low-risk light change.
6. Open **Plans** and inspect the exact tool, entity, arguments, and impact classification.
7. Exercise approve/reject while global dry-run remains on.
8. Review allowed/blocked domains, high-impact services, and temperature limits before considering live tools.
9. Test routine lighting before climate, locks, alarms, cameras, or covers.

## Upgrading from 0.12

- The manifest changes local defaults from Qwen/DeepSeek/Mistral to `gemma4:e4b`.
- Existing persistent `/config/agents.yaml` is retained; it is never overwritten on upgrade.
- New installs receive Gemma E4B specialist defaults.
- The dashboard navigation changes to Home, Ask & Run, Plans, Automation, Insights, and Studio.
- The API adds optional `profile: rapid|balanced|deep` to run, stream, and workflow requests.
- Back up `/data/chroma`, plan/trigger databases, and generated dashboards before any major add-on update.

## Safety boundary

- Direct execute mode remains off by default.
- Auto mode executes only plans that local impact policy does not require a human to approve.
- High-impact plans pause in the Plans workspace.
- Approval replays the stored tool calls and arguments; the model is not asked to generate them again.
- Home Assistant accepting a service call is not yet proof of the physical outcome. Post-action state verification remains a pre-1.0 milestone.

## Troubleshooting

- **Model pull is slow:** check free storage, add-on logs, and network access to the Ollama registry.
- **External Ollama cannot connect:** use a host address reachable from the add-on container, not the Home Assistant browser's `localhost`.
- **Dashboard is blank after update:** hard refresh the ingress page and verify the built frontend assets are present in add-on logs.
- **Home Assistant is disconnected:** verify Supervisor access or the Long-Lived Access Token and direct Core URL.
- **Plans endpoint is unavailable:** confirm the plan store initialized and `/data` is writable.
- **A run reaches a budget:** use a narrower goal or deliberately choose a deeper profile; do not raise all ceilings without representative testing.

See [README.md](README.md) for architecture, privacy, provider behavior, evaluation, and the road to 1.0.
