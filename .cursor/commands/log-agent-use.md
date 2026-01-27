# Log Agent Use

## Purpose

Record use of Cursor agents/subagents in `.cursor/agent-usage-log.md`. Keeps a **tally** (most used → least used) at the top and a **chronological log** (newest at bottom) for easy viewing of which agents are used most.

## Usage

`/log-agent-use [agent-name] [context]`

- **agent-name** (optional): Agent that was used (e.g. `plan-critic`, `session-ending`). If omitted, infer from recent conversation (e.g. user said "use the plan-critic").
- **context** (optional): Brief reason or trigger (e.g. "User asked to review The-plan").

When an agent or subagent is invoked (e.g. "Use the plan-critic to…"), log that use via this command or by updating the log directly.

## Instructions for Agent

When this command is invoked (or when you have used an agent and need to log it):

1. **Identify the agent**: Use the provided `agent-name` or infer from context (e.g. which agent was just run).

2. **Read** `.cursor/agent-usage-log.md`.

3. **Append a log entry** at the end of the **Log** section (above the `---` and "How to update" block):
   - Format: `YYYY-MM-DD HH:MM | agent-name | context`
   - Use current date/time. Example: `2025-01-26 15:30 | plan-critic | User asked to review The-plan`

4. **Update the Tally** at the top:
   - If the agent is **new**: add a row `| agent-name | 1 |`.
   - If the agent **exists**: add 1 to its Count.
   - **Re-sort** the table by Count **descending** (most used → least used).
   - Remove the *none yet* placeholder row once at least one agent has been logged.

5. **Save** `.cursor/agent-usage-log.md`. Preserve the "How to update" section at the bottom.

## Expected Outcome

- One new log entry at the bottom of the Log section.
- Tally at top updated and sorted most used → least used.
- File remains valid markdown; "How to update" unchanged.

## Example

After using `plan-critic`:

**Tally (excerpt):**
| Agent | Count |
|-------|-------|
| plan-critic | 1 |

**Log (excerpt):**
```
2025-01-26 15:30 | plan-critic | User asked to review The-plan
```
