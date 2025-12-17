# � AI Orchestrator

**The Autonomous AI Automation Engine for Home Assistant.**

AI Orchestrator transforms your smart home from a collection of static "if-this-then-that" scripts into a dynamic, thinking ecosystem. It deploys autonomous AI agents that reason about your home's state, understand your intent, and execute actions intelligently using a built-in Model Context Protocol (MCP) toolset.

**Version**: v0.8.52

## 🌟 Key Features

### 1. Dynamic Agent Reasoning 🧠
Move beyond rigid YAML automations. Create agents with simple natural language job descriptions.
-   **Natural Language Instructions**: "Keep the living room cozy. If it's movie time (dim lights, TV on), ensure the temperature is comfortable."
-   **Smart Context Awareness**: Agents automatically discover relevant devices and services. They know *what* is available in your home.

-   **RAG Knowledge Base**: Feed your agents manuals, documentation, or specific facts so they make informed decisions (e.g., "Don't turn off the heater if the pump is running").

### 2. Internal MCP Tool Engine 🛠️
The system features a purpose-built **Model Context Protocol (MCP) Server** responsible for safely executing agent decisions. This is the bridge between the AI's "brain" and Home Assistant's "hands".
-   It strictly maps AI intent to valid Home Assistant Service calls (`climate.set_temperature`, `light.turn_on`, etc.).
-   It validates parameters to prevent hallucinations or unsafe actions (e.g., preventing extreme temperature settings).
-   It logs every action for transparency.

### 3. Dual-Brain Architecture (v0.8.54) 🧠⚡
The system now supports two distinct AI models to balance intelligence and speed:
-   **Smart Reasoning Model** (e.g., `deepseek-r1:8b`): Used for complex planning, "Orchestrator" duties, and tasks requiring deep thought (e.g. "If I leave for holiday, what should happen?").
-   **Fast Execution Model** (e.g., `mistral:7b-instruct`): Used for "Worker" agents that need to react instantly to motion, door sensors, or simple commands.

### 4. "Minority Report" Dashboard 🖥️
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
3.  **Configure**:
    *   **Ollama Host**: URL of your Ollama instance (default: `http://localhost:11434`).
    *   **Smart Model**: The reasoning model name (default: `deepseek-r1:8b`).
    *   **Fast Model**: The execution model name (default: `mistral:7b-instruct`).
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
  - id: "living_room_manager"
    name: "Living Room Manager"
    model: "mistral:7b-instruct" # Optional: Override default model
    # No entities listed? No problem. The agent will discover them.
    instruction: |
      Keep the living room cozy in the evening. 
      Turn on warm lights if motion is detected after sunset.
      
  - id: "security_guard"
    name: "Security"
    model: "deepseek-r1:8b" # Use Smart model for complex security logic
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
*   **Cause**: The agent is searching for devices that don't match its internal registry.
*   **Fix**:
    1.  Ensure you are on **v0.8.52+** (includes Dynamic Service Discovery and Anti-Hallucination).
    2.  Check the "Decision Stream" log. Does it verify the entity exists?
    3.  Manually assign the entity in `agents.yaml` if auto-discovery is missing it.

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
