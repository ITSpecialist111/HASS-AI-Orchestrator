# 🗺️ AI Orchestrator - Product Roadmap

**Current Version**: v0.9.45 (Gemini Intelligence & Multi-Provider Video)

This roadmap outlines the strategic direction for the AI Orchestrator. It focuses on evolving from a "text-based automation manager" to a fully multi-modal, voice-interactive home presence.

---

## 🚀 Short Term (v1.0 - The "Polish" Update)

### 1. Zero-Downtime Agent Reloading
- **Goal**: Add/Update agents without restarting the entire backend (Hot Reload).
- **Feature**: Implement a mechanism for dynamic agent loading and unloading.
- **Use Case**: Rapid iteration on agent logic without service interruption.

-   [x] **Chat Interface**: Floating dashboard assistant for natural language control. (v0.9.0)
-   [x] **RAG Optimization**: Delta-based ingestion for instant startup. (v0.9.1)
-   [x] **Configurable Security**: Domain blocking and hardware limits via UI. (v0.9.5)
-   [x] **Visual Dashboard Integration**: Sidebar access and quick actions. (v0.9.5)
-   [x] **Gemini Intelligence Provider**: Integrated Google Gemini for high-fidelity dashboards. (v0.9.43)
-   [ ] **Voice Interface**: Real-time voice interaction via Home Assistant Assist pipeline. (v1.0)

### 2. Voice Integration (HA Assist)
- **Goal**: Talk to your agents via Home Assistant Assist / ESPHome satellites.
- **Feature**: Expose the "Architect" and "Orchestrator" as conversation agents.
- **Use Case**: *"Hey Jarvis, tell the Lighting Agent to set a romantic mood."*

### 3. Mobile Companion App
- **Goal**: A native-feeling mobile view for the Dashboard.
- **Feature**: Responsive design updates for the React dashboard.
- **Use Case**: Checking agent "thoughts" and approving decisions from your phone while away.

### 4. Chat Assistant (Completed v0.9.0) ✅
- **Goal**: Talk to your house via the Dashboard.
- **Feature**: Floating Action Button with Quick Actions and Chat Interface.
- **Use Case**: *"Turn off the lights"* -> Orchestrator executes immediately.

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
