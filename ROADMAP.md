# 🗺️ AI Orchestrator - Product Roadmap

**Current Version**: v0.13.6 (RAG Startup Compatibility)

This roadmap outlines the strategic direction for the AI Orchestrator. It focuses on evolving from a "text-based automation manager" to a fully multi-modal, voice-interactive home presence.

---

## 🚀 Short Term (v1.0 - The "Polish" Update)

### 0.12 foundation completed

-   [x] **Single Authoritative Kernel**: Chat, prompts, triggers, and goals share one bounded loop.
-   [x] **Deterministic Tools**: Schema validation, ordered mutations, read-only concurrency, retries, deduplication, and hard budgets.
-   [x] **Durable Plans**: Atomic execution claims, exact replay, trusted approval context, and per-step checkpoints.
-   [x] **Frontier Provider Semantics**: GPT-5.6 Responses and Claude Opus 4.8 adaptive/strict tool support.
-   [x] **Executable Evaluations**: Model-free safety contracts and a provider-neutral home scenario dataset.

### 0.13 human control layer completed

-   [x] **One Local Gemma Engine**: `gemma4:e4b` is the default local model across the runtime.
-   [x] **Rapid / Balanced / Deep**: Explicit thinking and bounded run profiles without changing deterministic tool policy.
-   [x] **Human Operations IA**: Home, Ask & Run, Plans, Automation, Insights, and Studio replace nine fragmented technical tabs.
-   [x] **Responsive & Accessible UI**: Mobile drawer, 44 px controls, keyboard focus, ARIA semantics, light/dark Clawpilot tokens, and reduced motion.
-   [x] **Thinking Privacy**: Private model thinking is separated from assistant output, history, traces, persistence, and operator views.

### Highest-priority path to 1.0

1. **Native Home Assistant conversation integration** using `ConversationEntity`, `ChatLog`, `LLMContext`, exposed entities, conversation IDs, and Assist voice pipelines.
2. **Outcome verification** that re-observes affected entities after replay and marks each intent verified, failed, or uncertain.
3. **Temporal world model** built from HA recorder/statistics for occupancy, comfort, energy, and anomaly baselines.
4. **Real-provider evaluation CI** comparing model profiles on task success, safety, calls, tokens, latency, and cost.
5. **Run trace export** using the existing run IDs/checkpoints with an OpenTelemetry-compatible sink.

### 1. Zero-Downtime Agent Reloading
- **Goal**: Add/Update agents without restarting the entire backend (Hot Reload).
- **Feature**: Implement a mechanism for dynamic agent loading and unloading.
- **Use Case**: Rapid iteration on agent logic without service interruption.

-   [x] **Chat Interface**: Floating dashboard assistant for natural language control. (v0.9.0)
-   [x] **RAG Optimization**: Delta-based ingestion for instant startup. (v0.9.1)
-   [x] **Configurable Security**: Domain blocking and hardware limits via UI. (v0.9.5)
-   [x] **Visual Dashboard Integration**: Sidebar access and quick actions. (v0.9.5)
-   [x] **Gemini Intelligence Provider**: Integrated Google Gemini for high-fidelity dashboards. (v0.9.43)
-   [x] **Deep Reasoning Agent**: Goal-driven agentic loop with native HA tool surface, optional external MCP, Anthropic Claude backend. (v0.10.0 / Phase 7)
-   [x] **Triggers & Prompt Library**: Proactive triggers + reusable workflow prompts surfaced in the dashboard. (v0.10.0 / Phase 8 + 8.5)
-   [x] **Multi-Provider LLM**: Ollama, OpenAI, Anthropic, GitHub Models, and Microsoft Foundry selectable per install. Remote deep-reasoner configuration now fails explicitly instead of silently drifting providers. (v0.12.0)
-   [ ] **Voice Interface**: Real-time voice interaction via Home Assistant Assist pipeline. (v1.0)

### 2. Voice Integration (HA Assist)
- **Goal**: Talk to your agents via Home Assistant Assist / ESPHome satellites.
- **Feature**: Expose the "Architect" and "Orchestrator" as conversation agents.
- **Use Case**: *"Hey Jarvis, tell the Lighting Agent to set a romantic mood."*

### 3. Mobile Companion App
- **Goal**: A native-feeling mobile view for the Dashboard.
- **Feature**: Responsive web control is complete in 0.13; native notifications/offline packaging remain future work.
- **Use Case**: Checking grounded run activity and approving exact plans from your phone while away.

### 4. Chat Assistant (Completed v0.9.0) ✅
- **Goal**: Talk to your house via the Dashboard.
- **Feature**: Floating Action Button with Quick Actions and Chat Interface.
- **Use Case**: *"Turn off the lights"* → the authoritative kernel observes, validates, and executes or pauses according to policy.

### 5. Energy Optimization Agent
- **Goal**: High ROI automation.
- **Feature**: A specialized agent pre-trained on solar production, battery curves, and grid pricing.
- **Use Case**: Automatically pre-cooling the house when solar is high and grid prices are low.

### 6. MLFlow Integration (Advanced Diagnostics)
- **Goal**: Allow pro users to monitor agent performance.
- **Feature**: Add `MLFLOW_TRACKING_URI` support to the Add-on configuration.
- **Use Case**: Track agent decisions, retrieval accuracy (RAG), and model latency in real-time.

---

## 🔭 Medium Term (v2.0 - The "Vision" Update)

### 4. Vision Capabilities (LLaVA Integration)
- **Goal**: Give the agents "eyes".
- **Feature**: Integrate vision-language models (like LLaVA or BakLLaVA).
- **Use Case**:
    - **Security Agent**: Analyzes camera frames. *"I see a delivery driver at the door, unlocking for 2 minutes."*
    - **Lighting Agent**: Checks if the room is *actually* dark or if someone is reading.

### 5. Reinforcement Learning (RLHF)
- **Goal**: Agents learn from *your* corrections.
- **Feature**: "Thumbs up/down" on decisions in the dashboard feeds back into the vector memory.
- **Use Case**: If you override the heating every night at 8 PM, the agent learns this preference automatically without new instructions.

### 6. Multi-Node Deployment
- **Goal**: Scale beyond a single Pi/NUC.
- **Feature**: Run the "Brain" (LLM) on a gaming PC or server, while Home Assistant runs on a Pi.
- **Use Case**: High-speed inference using a dedicated GPU server while keeping HA low-power.

---

## 🔮 Long Term (v3.0 - The "Sentience" Update)

### 7. Proactive Maintenance
- **Goal**: Predict failures before they happen.
- **Feature**: Analyze long-term sensor trends (vibration, power usage).
- **Use Case**: *"The fridge compressor is cycling 20% more frequently. It may fail soon."*

### 8. Personality Engine
- **Goal**: Make the AI feel like a family member.
- **Feature**: Configurable personalities (e.g., "Formal Butler", "Sarcastic Droid", "Caring Grandmother").
- **Use Case**: Agents communicate in a style that fits your home's vibe.

### 9. Matter & Thread Mesh Awareness
- **Goal**: Spatial awareness of the network.
- **Feature**: Agents understand the physical location of devices based on mesh topology.
- **Use Case**: *"I can't reach the bedroom light, but the hallway Repeater is offline. I'll restart it."*

---

## 💡 Community & Ecosystem

- **Agent Marketplace**: A "Store" where users can share their best `agents.yaml` configs (e.g., "Complex Aquarium Manager").
- **Cloud Backup**: Encrypted backup of your RAG vector database (Knowledge Base).
