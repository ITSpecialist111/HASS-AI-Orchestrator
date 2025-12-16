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

### Option 1: Repository Install (Recommended)

This is the easiest way to install and get automatic updates.

#### 1. Add Repository
1. Open Home Assistant.
2. Go to **Settings > Add-ons > Add-on Store**.
3. Click **⋮** (three dots) > **Repositories**.
4. Add URL: `https://github.com/ITSpecialist111/HASS-AI-Orchestrator`
5. Click **Add**.

#### 2. Install Add-on
1. Reload the page (important!).
2. Find **AI Orchestrator** in the list.
3. Click **Install**.
4. Build time: **5-15 minutes** (it builds locally on your device).
5. **Verify Version**: Ensure it is **v0.8.22** before installing.

#### 3. Configuration
Configure the add-on in the "Configuration" tab:

```yaml
ollama_host: "http://localhost:11434" # Or external IP
dry_run_mode: true                    # Keep TRUE for first run!
log_level: "info"
   ollama_host: "http://192.168.1.x:11434"
   heating_model: "mistral:7b-instruct"
   ha_access_token: "YOUR_LONG_LIVED_TOKEN_HERE" # Required for Direct Core Access
   ```

#### 4. Start
Click **Start**. Monitor the **Log** tab.

---

### Option 2: Manual Install (Legacy)
1. Copy the `ai-orchestrator` folder to `/addons/` on your HA host.
2. Restart Supervisor.
3. Install via Local Add-ons list.

---

## 🎮 Getting Started (Dashboard)

Navigate to: `http://homeassistant.local:8999`

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

### Ingress / Blank Dashboard Issues
If you see a blank dashboard:
1.  **Check Logs**: Look for `DEBUG REQUEST`. If you see `/hassio/ingress/...`, the path fix is working.
2.  **Hard Refresh**: `Ctrl+F5` to clear browser cache of old JS files.
3.  **MIME Types**: Ensure your HA host isn't blocking `.js` files (rare, but possible).
