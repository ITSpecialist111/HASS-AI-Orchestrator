# 🤖 AI Orchestrator (Phase 6)

**The "Jarvis" for your Home Assistant.**

AI Orchestrator is a local, privacy-focused autonomous system that intelligently manages your smart home using multiple specialized AI agents. It moves beyond simple "if-this-then-that" automation to intent-based AI decision making.

**Version**: v0.8.35

## 🌟 Key Features

### 1. Universal Agents (v2) 🧠
Creating an agent is as simple as writing a job description. You don't need to code python scripts or complex YAML automations.

-   **Natural Language Instructions**: "Monitor the baby's room. If it gets too cold, turn on the heater."
-   **Dynamic Entity Discovery**: You don't even need to tell the agent *which* heater. It will scan your Home Assistant, find relevant devices (prioritizing Climate, Lights, Switches, and Locks), and choose the correct one automatically.
-   **Anti-Hallucination**: The system strictly prevents agents from inventing non-existent devices.

### 2. Model Context Protocol (MCP) Server 🛠️
Agents interact with your home safely through a standardized tool layer.
Available tools include:
-   `set_temperature` / `set_hvac_mode`: Advanced climate control (with safeguards).
-   `turn_on_light` / `set_brightness`: Smart lighting management.
-   `lock_door`: Secure access control.
-   `log`: Agents keep a "diary" of their observations and decisions.
-   `call_ha_service`: Generic fallback for any other Home Assistant service.

### 3. "Minority Report" Dashboard 🖥️
-   **Live Decision Stream**: Watch your agents think in real-time. See *why* they made a decision.
-   **Agent Cards**: Check status, last thoughts, and activity heartbeat.
-   **No-Code Factory**: Chat with the "Architect" AI to build new agents interactively.

---

## 📦 Installation

1.  **Add Repository**: Add this repo URL to your Home Assistant Add-on Store.
2.  **Install**: Find "AI Orchestrator" and click Install.
3.  **Configure**:
    *   **Ollama Host**: URL of your Ollama instance (default: `http://localhost:11434`).
    *   **Access Token**: Create a Long-Lived Access Token in your HA User Profile.
    *   **Dry Run**: Set to `true` initially to see what agents *would* do without actually doing it.
4.  **Start**: The first startup determines your available hardware and may take a few minutes.

## ⚙️ Configuration (`agents.yaml`)

This file lives in `/addon_configs/ai-orchestrator/agents.yaml`. You can edit it manually or use the Dashboard Factory.

```yaml
agents:
  - id: "living_room_manager"
    name: "Living Room Manager"
    model: "mistral:7b-instruct"
    # No entities listed? No problem. The agent will discover them.
    instruction: |
      Keep the living room cozy in the evening. 
      Turn on warm lights if motion is detected after sunset.
      
  - id: "security_guard"
    name: "Security"
    model: "llama3:8b"
    decision_interval: 60
    entities:
      - lock.front_door  # Explicitly assigned entities are prioritized
      - binary_sensor.front_door_motion
    instruction: |
      If the front door is unlocked for > 15 mins, lock it and notify me.
```

---

## 🔧 Troubleshooting

### "Agent is hallucinating entity IDs?"
*   **Cause**: The agent is trying to guess entity names.
*   **Fix**:
    1.  Ensure you are on **v0.8.35+** (includes strict Anti-Hallucination rules).
    2.  Check the "Decision Stream" log. Does it verify the entity exists?
    3.  Manually assign the entity in `agents.yaml` to force it to be visible.

### "I see 'Dry Run' in the logs?"
*   **Cause**: `dry_run_mode` is enabled in configuration.
*   **Fix**: Go to Add-on Configuration and toggle `Dry Run Mode` to `false` when you trust your agents.

### "Agent is stuck in 'Initializing'?"
*   **Cause**: The agent loop likely crashed or LLM is unreachable.
*   **Fix**: Check the "Logs" tab in the Add-on. Ensure Ollama is running and accessible.

---

## 🗺️ Roadmap

-   **v1.0**: Voice Integration (Talk to your house).
-   **v1.1**: Vision capabilities (Show your house camera feeds to agents).
