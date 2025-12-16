# 🗺️ AI Orchestrator - Product Roadmap

**Current Version**: v0.8.45 (Instant Feedback & Loop Fixes)

This roadmap outlines the strategic direction for the AI Orchestrator. It focuses on evolving from a "text-based automation manager" to a fully multi-modal, voice-interactive home presence.

---

## 🚀 Short Term (v1.0 - The "Polish" Update)

### 1. Voice Integration (HA Assist)
- **Goal**: Talk to your agents via Home Assistant Assist / ESPHome satellites.
- **Feature**: Expose the "Architect" and "Orchestrator" as conversation agents.
- **Use Case**: *"Hey Jarvis, tell the Lighting Agent to set a romantic mood."*

### 2. Mobile Companion App
- **Goal**: A native-feeling mobile view for the Dashboard.
- **Feature**: Responsive design updates for the React dashboard.
- **Use Case**: Checking agent "thoughts" and approving decisions from your phone while away.

### 3. Energy Optimization Agent
- **Goal**: High ROI automation.
- **Feature**: A specialized agent pre-trained on solar production, battery curves, and grid pricing.
- **Use Case**: Automatically pre-cooling the house when solar is high and grid prices are low.

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
