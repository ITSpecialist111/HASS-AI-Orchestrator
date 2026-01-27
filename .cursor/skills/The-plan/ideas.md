# Ideas – LCARS HA, Critics, Cursor vs Add-on

*Collated from brainstorming, The-plan, and critic design. Update as we decide.*

---

## 1. Cursor on HA Server vs Add-on Approach

**Question:** Would it be better to port Cursor to the Home Assistant server than to use the add-on approach?

**Short answer: No. Keep the add-on approach.** Use Cursor on your dev machine; run the AI Orchestrator as an HA add-on on the HA server.

### Add-on approach (current)

- **Dev:** Cursor on your PC (or dev machine). Edit code, run critics, git, terminals.
- **Runtime:** AI Orchestrator add-on runs on the HA host (Pi, NUC, etc.). Connects to HA via WebSocket/API.
- **Deploy:** Build add-on → install via HACS or manual → add-on talks to HA.

**Pros:**

- Clear split: dev environment vs production. HA stays focused on automation.
- Cursor, Node, Electron, and dev tooling stay off the HA host (often resource-limited).
- Critics, session-ending, and other subagents run where you already work.
- Git, backups, and iteration stay on your machine; no mixing dev and production on the HA box.

### “Port Cursor” to HA server

- **Idea:** Run Cursor (or a Cursor-like dev environment) on the same machine as Home Assistant.

**Cons:**

- Cursor is a desktop/Electron app. It’s heavy and not meant for headless/server use.
- HA often runs on Pi/NUC. Cursor + Node + frontend tooling would stress the device.
- Putting dev and production on the same host increases risk (accidental breaks, updates, etc.).
- You’d still need to build and run the add-on *on* that host; Cursor there doesn’t simplify add-on deployment.

**When “dev on HA host” might make sense:**

- **Devcontainer on a beefy HA host:** e.g. x86 NUC with lots of RAM. Run a devcontainer (VS Code + backend tools) on that host, develop there, deploy add-on there. Still use the **add-on** for the Orchestrator; you’re only moving the *dev environment* to the same hardware.
- **Remote dev:** SSH + “Remote - SSH” or “Remote - Containers” into a dev box (same network as HA). Code runs on dev box; add-on runs on HA. Again, add-on approach unchanged.

### MCP and Cursor ↔ HA

- **HA MCP server:** Exposes HA as tools (entities, services) to MCP clients.
- **Cursor ↔ HA:** Configure Cursor to use HA’s MCP server (e.g. `mcp-proxy` → `https://<ha>/api/mcp`). You then *control* HA from Cursor (lights, etc.); you’re not “porting” Cursor to HA.
- This is **complementary** to the add-on: add-on = Orchestrator runtime; MCP = Cursor (on your PC) talking to HA.

### Recommendation

- **Keep the add-on approach** for the AI Orchestrator.
- **Keep Cursor on your dev machine** for code, critics, session-ending, and git.
- **Use HA’s MCP** when you want Cursor to control HA. Don’t run Cursor itself on the HA server.
- If you want “dev on HA hardware,” use a devcontainer on a capable host and still deploy the add-on there; that’s an environment choice, not a replacement for the add-on.

---

## 2. Critic Usage Notes

Critics are subagents that roast plans, code, config, and use cases. Use them for **fresh, unbiased feedback** – especially when the main chat has gotten long or agreeable.

### List of critics

| Critic | What it roasts | When to use |
|--------|----------------|-------------|
| **plan-critic** | The-plan, task structure, priorities, dependencies, coordination | After updating The-plan, adding tasks, or reviewing sprint |
| **roadmap-critic** | ROADMAP.md, versioning, features, HA/Assist alignment | When changing roadmap or planning releases |
| **environment-critic** | Docker, config.json, run.sh, requirements, add-on config | When changing Dockerfile, config, or run scripts |
| **python-critic** | Backend Python (FastAPI, agents, MCP, RAG) | After editing `ai-orchestrator/backend/` |
| **javascript-critic** | Dashboard React/Vite/JSX | After editing `ai-orchestrator/dashboard/` |
| **yaml-critic** | agents.yaml, translations, YAML config | After editing YAML |
| **lcars-ha-use-case-critic** | LCARS HA plan, Assist pipeline, multi-agents, HACS, use cases | When planning LCARS theme, Assist, or HACS workflow |

### How to use

- **Invoke by name:** e.g. “Use the plan-critic to review The-plan” or “Run the python-critic on the last change.”
- **Delegate early:** Before you’ve invested too much in one direction. Critics work best with clear scope (e.g. “this file” or “this section of The-plan”).
- **Fresh context:** Like the video’s “brutal critic,” they’re meant to give unbiased feedback. Use them instead of asking the same chat “is this good?” after a long thread.
- **Session-ending:** When wrapping up, use **session-ending** to summarize, update The-plan/session-summary, and commit. Use critics *during* the session; use session-ending *at the end*.

### Workflow idea

1. **Plan:** Update The-plan → run **plan-critic**.
2. **Implement:** Edit code (Python/JS/YAML) → run the right **language critic**.
3. **Config / deploy:** Change Docker or add-on config → run **environment-critic**.
4. **Roadmap / LCARS:** Change roadmap or LCARS/Assist plan → run **roadmap-critic** or **lcars-ha-use-case-critic**.
5. **Wrap up:** Run **session-ending** to summarize, sync, and commit.

### Files

- Critics live in `.cursor/agents/` (e.g. `plan-critic.md`, `python-critic.md`).
- Session-ending: `session-ending.md`.
- This doc: `.cursor/skills/The-plan/ideas.md`.

---

## 3. Agent usage log

A simple log tracks **which agents/subagents are used** and **how often**.

- **File:** `.cursor/agent-usage-log.md`
- **Top:** Tally table (most used → least used).
- **Bottom:** Chronological log; new entries appended at the end.

**To log a use:** Run `/log-agent-use [agent-name] [context]` or update the file manually (see "How to update" in the log). After using a critic or any agent, log it so the tally stays current.

**Command:** `.cursor/commands/log-agent-use.md`

---

*Last updated: 2025-01-26*
