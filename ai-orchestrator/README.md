# � AI Orchestrator

**The Autonomous AI Automation Engine for Home Assistant.**

AI Orchestrator transforms your smart home from a collection of static "if-this-then-that" scripts into a dynamic, thinking ecosystem. It deploys autonomous AI agents that reason about your home's state, understand your intent, and execute actions intelligently using a built-in Model Context Protocol (MCP) toolset.

**Version**: v0.9.1

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

### 3. Tri-Level Architecture (v0.8.60) 🧠⚡
The system uses three distinct model roles to optimize for cost, speed, and intelligence:
-   **Orchestrator** (e.g., `deepseek-r1:8b`): The "Boss". Plans high-level strategies, delegates tasks to agents, and resolves conflicts (e.g. heating vs cooling).
-   **Smart Agents** (e.g., `deepseek-r1:8b`): Specialist agents that handle complex logic (Security, Energy Management).
-   **Fast Agents** (e.g., `mistral:7b-instruct`): Worker agents that execute simple instructions instantly (Motion Lights).

### 4. "Minority Report" Dashboard 🖥️
-   **Live Decision Stream**: Watch your agents think in real-time. See *why* they made a decision.
-   **Agent Cards**: Check status, last thoughts, and activity heartbeat.
-   **No-Code Factory**: Chat with the "Architect" AI to build new agents interactively.

### 5. Chat Assistant (v0.9.0) 💬
A floating AI assistant lives in your dashboard, ready to help at any time.
-   **Quick Actions**: Hover over the icon for instant commands (Zap Lights, Arm Security).
-   **Direct Control**: Chat with the Orchestrator directly. "Turn off the kitchen lights and lock the front door."
-   **Context Aware**: It knows the current state of your home and uses your configured Orchestrator model to execute complex requests.

---

## 📦 Installation

1.  **Add Repository**: Add this repo URL to your Home Assistant Add-on Store.
2.  **Install**: Find "AI Orchestrator" and click Install.
3.  **Configure**:
    *   **Ollama Host**: URL of your Ollama instance (default: `http://localhost:11434`).
    *   **Orchestrator Model**: The main brain for high-level planning (default: `deepseek-r1:8b`).
    *   **Smart Model**: The reasoning model for complex agents (default: `deepseek-r1:8b`).
    *   **Fast Model**: The execution model for responsive agents (default: `mistral:7b-instruct`).
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
    model: "deepseek-r1:8b" # Use Smart model for complex security logic
    decision_interval: 60
    entities:
      - lock.front_door  # Explicitly assigned entities are prioritized
      - binary_sensor.front_door_motion
    instruction: |
      If the front door is unlocked for > 15 mins, lock it and notify me.
```

## 🧠 Anti-Hallucination & Entity Awareness

The system now includes sophisticated mechanisms to ensure agents only interact with devices that actually exist in your home:

### 🎯 Assigned Entities (Visual)
In the Dashboard Agent Details, you can now see exactly which entities an agent has been assigned. 
- **Green Badges**: Actuators (Lights, Switches, Locks)
- **Blue Badges**: Sensors (Motion, Temperature, Contact)

If an agent has "No assigned entities", it will attempt to discover them dynamically at runtime, but explicitly assigning them (or letting the auto-discovery find them) is safer.

### 🔍 Auto-Discovery on Update
When you change an agent's instruction in the Dashboard (e.g., changing "Manage the kitchen" to "Manage the garage"), the **Architect** immediately scans your Entity Registry.
1.  It extracts keywords from your new instruction.
2.  It finds matching entity IDs in your Home Assistant.
3.  It automatically updates the agent's `entities` list.

This prevents the "Hallucinated Entity ID" errors common in other LLM integrations.

### 🛡️ Dynamic Service Restriction (Approved Methods)
Each agent is strictly limited to the Home Assistant services that match its assigned entities. 
*   **Example**: If an agent controls `light.living_room`, it is injected with approved methods like `light.turn_on` and `light.turn_off`.
*   **Effect**: It CANNOT haphazardly call `switch.turn_on` or hallucinate fake services like `light.explode`. The generic "call_ha_service" tool is contextually bound to these approved methods "behind the scenes" in the system prompt.

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
