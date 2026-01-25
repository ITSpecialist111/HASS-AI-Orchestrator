# 🧠 AI Orchestrator

**The Autonomous AI Automation Engine for Home Assistant.**

AI Orchestrator transforms your smart home from a collection of static "if-this-then-that" scripts into a dynamic, thinking ecosystem. It deploys autonomous AI agents that reason about your home's state, understand your intent, and execute actions intelligently using a built-in Model Context Protocol (MCP) toolset.

**Version**: v0.9.47 (Gemini Integration & Connectivity Robustness)

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
-   **Multi-Layer Security (v0.9.5)**:
    -   **Configurable Safety**: All security settings (Allowlists, Blocked Domains, Impact Services, Temp Limits) are now editable via the Add-on Configuration tab in Home Assistant.
    -   **Domain Allowlist**: Only approved domains are allowed for generic service calls.
    -   **Critical Block**: Dangerous domains (`shell_command`, `script`, etc.) are strictly prohibited.
    -   **Approval Queue**: High-impact actions (Entry/Security) require human-in-the-loop approval.
-   It logs every action for transparency.

### 3. Tri-Level Architecture (v0.9.5) 🧠⚡
The system uses three distinct model roles to optimize for cost, speed, and intelligence:
-   **Orchestrator** (e.g., `deepseek-r1:8b`): The "Boss". Plans high-level strategies, delegates tasks to agents, and resolves conflicts (e.g. heating vs cooling).
-   **Smart Agents** (e.g., `deepseek-r1:8b`): Specialist agents that handle complex logic (Security, Energy Management).
-   **Fast Agents** (e.g., `mistral:7b-instruct`): Worker agents that execute simple instructions instantly (Motion Lights).

### 4. "Minority Report" Dashboard 🖥️
-   **Live Decision Stream**: Watch your agents think in real-time. See *why* they made a decision.
-   **Smart Suggestions**: The Architect analyzes your home and suggests new automation opportunities directly in your grid.
-   **No-Code Factory**: Click a suggestion or the "+" button to interview the Architect and build new agents interactively.

### 5. Chat Assistant (v0.9.0) 💬
A floating AI assistant lives in your dashboard, ready to help at any time.
-   **Quick Actions**: Hover over the icon for instant commands (Zap Lights, Arm Security).
-   **Direct Control**: Chat with the Orchestrator directly. "Turn off the kitchen lights and lock the front door."
-   **Context Aware**: It knows the current state of your home and uses your configured Orchestrator model to execute complex requests.
-   **Self-Diagnostic**: If it can't reach your LLM, it will tell you exactly which IP it tried and why it failed.

### 5.1 OpenAI Provider (Optional) ☁️
Enable OpenAI as a first-class AI provider while keeping local mode as the default.
-   **Opt-in**: Requires `openai_api_key` and `use_openai: true`.
-   **Model Overrides**: When enabled, agents/orchestrator use `openai_fast_model` and `openai_smart_model`.
-   **Embeddings**: RAG can use `openai_embedding_model` when OpenAI is active.
-   **Dashboard**: Use `use_openai_for_dashboard: true` to route visual dashboard generation to OpenAI.

### 6. AI Visual Dashboard (v0.9.47) 🎨
The system now features a real-time, LLM-driven visualization engine that builds your entire home interface using natural language.

![AI Visual Dashboard](../AI_Visual_Dashboard.gif)

-   **Dynamic UI Generation**: Use local (Ollama) or state-of-the-art cloud models (**Google Gemini**) to generate bespoke, high-fidelity dashboards.
-   **No YAML, No Coding**: Because the system has deep access to your Home Assistant Entity Registry, it builds the dashboard autonomously. You don't need to manually configure cards or write a single line of YAML.
-   **Dynamic Design**: Just tell the Architect Agent: *"Make a dashboard focused on energy usage with a dark oceanic theme"* or *"Build a 3-column view for my heating and security"* and watch it regenerate in seconds.
-   **Gemini Robotics Model**: Explicitly supports `gemini-robotics-er-1.5-preview` for advanced robotics-grade visualizations.
-   **Mixergy-Style Visuals**: Features skeuomorphic designs like animated vertical water tanks, "Deep Ocean" themes, and glassmorphism.
-   **Integrated Experience**: Access the dashboard directly via the new sidebar button or trigger it from the Chat Assistant quick actions.
-   **Context-Aware**: The dashboard reflects live Home Assistant data and AI decision logic directly in its layout.
-   **Runtime Settings**: Dynamically toggle between Ollama and Gemini, and update API keys directly in the **Settings Modal** without restarting.

---

## 📦 Installation

1.  **Add Repository**: Add this repo URL to your Home Assistant Add-on Store.
2.  **Install**: Find "AI Orchestrator" and click Install.
3.  **Configure**:
    *   **Ollama Models**: Pull the required models on your Ollama server:
        ```bash
        ollama pull deepseek-r1:8b
        ollama pull mistral:7b-instruct
        ollama pull nomic-embed-text
        ```
    *   **Ollama Host**: URL of your Ollama instance (default: `http://localhost:11434`).
    *   **Orchestrator Model**: The main brain for high-level planning (default: `deepseek-r1:8b`).
    *   **Smart Model**: The reasoning model for complex agents (default: `deepseek-r1:8b`).
    *   **Fast Model**: The execution model for responsive agents (default: `mistral:7b-instruct`).
    *   **Cloud AI API Key**: (Optional) Add your Google AI API key for high-fidelity "AI Visual Dashboard" generation.
    *   **OpenAI API Key**: (Optional) Set `openai_api_key` and `use_openai: true` to enable OpenAI.
    *   **OpenAI Models**: Override `openai_fast_model`, `openai_smart_model`, `openai_embedding_model` if desired.
    *   **Access Token**: Create a Long-Lived Access Token in your HA User Profile.
    *   **Direct Access Mode**: Automatically falls back to Direct Core Access (e.g., `http://homeassistant:8123`) if the Supervisor Proxy is unavailable or tokens are mismatched.
    *   **Dry Run**: Set to `true` initially to see what agents *would* do without actually doing it.
4.  **Start**: The first startup determines your available hardware and ingests your entities into the Knowledge Base.
    *   **First Run**: May take ~1 minute to embed all entities.
    *   **Subsequent Runs**: Instant (v0.9.1+ Delta Check enabled).

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
    1.  Ensure you are on **v0.9.9+** (includes Dynamic Service Discovery and Anti-Hallucination).
    2.  Check the "Decision Stream" log. Does it verify the entity exists?
    3.  Manually assign the entity in `agents.yaml` if auto-discovery is missing it.

### "I see 'Dry Run' in the logs?"
*   **Cause**: `dry_run_mode` is enabled in configuration.
*   **Fix**: Go to Add-on Configuration and toggle `Dry Run Mode` to `false` when you trust your agents.

### "Agent is stuck in 'Initializing'?"
*   **Cause**: The agent loop likely crashed or LLM is unreachable.
*   **Fix**: Check the "Logs" tab in the Add-on. Ensure Ollama is running and accessible.

### "Chat Assistant says 'No route to host'?"
*   **Cause**: The Add-on container cannot reach your Ollama IP.
*   **Fix**: 
    1.  If Ollama is on the host, use your LAN IP (e.g., `192.168.1.x`), NOT `localhost`.
    2.  Check the error details in the chat bubble for the exact URL it tried.

---

## 📊 Telemetry & Data Collection

We value your privacy. The AI Orchestrator uses **ChromaDB** for local vector storage (Knowledge Base). 

### What is collected?
ChromaDB collects basic, anonymous usage events:
*   When the client starts.
*   When a collection is created.
*   The version of the library.

### What is NOT collected?
*   **Your Home Data**: Entity names, states, and history stay local.
*   **Agent Instructions**: Your prompts and logic are never shared.
*   **Personal Info**: No names, IPs, or location data.

### How to disable?
Set the following environment variable in your Home Assistant configuration:
`CHROMA_TELEMETRY_EXCEPT_OPT_OUT=True`

---

## ⚡ Agent Speed & "Real-Time" Monitoring

By default, agents operate on a **120-second heartbeat**. This balances intelligence with hardware resources.

### Changing the Interval
You can customize this per-agent in `agents.yaml`:
```yaml
- id: "lighting_agent"
  decision_interval: 10 # Check every 10 seconds
```

### Real-Time Monitoring
For mission-critical monitoring (Greenhouses, Security), you can set the interval to **"Real-Time"** (effectively 1-5 seconds). 
> [!IMPORTANT]
> Real-time monitoring significantly increases CPU/GPU usage as the LLM is constantly processing home state. Use a capable LLM server for the best experience.

---

## 🔬 Advanced Monitoring (MLFlow)
Pro users can wrap the `orchestrator.process_chat_request` or `rag_manager.query` methods in Python to connect their own **MLFlow** tracking server for real-time monitoring of agent reasoning and retrieval accuracy.

## 🗺️ Roadmap

-   **v1.0**: Voice Integration (Talk to your house).
-   **v1.1**: Vision capabilities (Show your house camera feeds to agents).
