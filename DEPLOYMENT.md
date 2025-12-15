# 🚀 AI Orchestrator - Production Deployment Guide (Phase 6)

## ✅ System Status: COMPLETE
This deployment package includes the full **Phase 6** feature set:
- **Universal Agents**: Create agents for *any* integration.
- **Agent Factory**: No-Code "Wizard" to generate agents via chat.
- **RAG Brain**: Long-term memory & PDF manual ingestion (Context Awareness).
- **Space Ops Dashboard**: Real-time analytics, status grid, and knowledge visualization.
- **Orchestrator**: Multi-agent coordination with conflict resolution.

---

## 📦 Installation Options

### Option 1: Home Assistant Add-on (Production)

#### Prerequisites
- Home Assistant OS / Supervised
- SSH Access (to copy files)
- **4GB+ RAM** (Local LLM requirement)

#### 1. Copy Files
Copy this entire repository to your Home Assistant `/addons/ai-orchestrator` folder.

#### 2. Install
1. Go to **Settings > Add-ons > Local Add-ons**.
2. Install **AI Orchestrator**.
3. **DO NOT START YET**.

#### 3. Configuration
Configure the add-on in the "Configuration" tab:

```yaml
ollama_host: "http://localhost:11434" # Or external IP
dry_run_mode: true                    # Keep TRUE for first run!
log_level: "info"
default_model: "mistral:7b-instruct"  # The brain
```

#### 4. Start
Click **Start**. The first run will take 5-10 minutes to:
1. Pull the LLM model (4GB).
2. Build the vector database.

Monitor the **Log** tab:
```
✓ Connect to Home Assistant
✓ Architect Agent initialized
✓ Orchestration loop started
✅ AI Orchestrator (Phase 6) ready!
```

---

## 🎮 Getting Started (Dashboard)

Navigate to: `http://homeassistant.local:8099`

### 1. The Dashboard
- **Live Ops**: See your agents (Heating, Security, etc.) pulsing when they "think".
- **Analytics**: View decision history charts.
- **Knowledge**: Watch the "Brain" icon light up when agents read manuals.

### 2. Creating Your First Agent (No-Code)
1. Click the **(+) New Agent** button (bottom right).
2. Valid "Suggested" agents based on your devices will appear.
3. **Or Chat**: "Make a bot that turns on the porch light at sunset."
4. The **Architect** will draft a plan.
5. Click **Approve & Deploy**.
6. Restart the add-on to activate the new agent.

### 3. Advanced Configuration (YAML)
For power users, edit `agents.yaml` in the `/addon_configs` (or mapped) directory:

```yaml
agents:
  - id: "my_custom_agent"
    name: "Lab Manager"
    entities: [sensor.lab_temp, switch.3d_printer]
    instruction: "Turn off printer if temp > 30C."
```

---

## 🧠 Adding Knowledge (RAG)
To make your agents smarter, drop PDF manuals or Markdown files into:
`/addon_configs/ai-orchestrator/manuals/` (or `/data/manuals` depending on mapping).

The system automatically ingests them on startup. Agents will search these files before making decisions.

---

## 🧪 Verification Checklist

### ✅ Startup
- [ ] Dashboard Loads (Green "Connected" badge).
- [ ] "Architect Agent initialized" in logs.

### ✅ RAG
- [ ] Drop a dummy PDF in `/data/manuals`.
- [ ] Restart. Log should say "Ingesting...".

### ✅ Factory
- [ ] Create a "Test Agent" via the Dashboard Wizard.
- [ ] Verify it appears in `agents.yaml`.

---

## ⚠️ Safety & Production
1. **Dry Run**: Keep `dry_run_mode: true` initially. Agents will *log* actions but not execute them.
2. **Go Live**: Set `dry_run_mode: false` in config when confident.
3. **Approval Queue**: High-impact actions (unlocking doors) require manual approval via the API/Dashboard (Phase 2 feature).

---
**Technical Support**:
Check `/data/logs/orchestrator.log` for detailed debugging.
