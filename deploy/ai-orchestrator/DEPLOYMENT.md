# 🚀 Phase 1 Deployment Guide

## ✅ Setup Complete

The following setup steps have been completed:
- ✅ Dashboard dependencies installed (110 packages)
- ✅ Dashboard production bundle built (`dashboard/dist/`)
- ✅ All source files created (22 files total)

---

## 📦 Deployment Options

### Option 1: Home Assistant Add-on (Recommended)

This is the primary deployment method for production use.

#### Prerequisites
- Home Assistant 2025.12.3+ (OS or Supervised installation)
- Climate entities configured in Home Assistant
- SSH access to Home Assistant host (for local add-on)

#### Steps

**1. Copy Repository to HA Add-ons Directory**

```bash
# SSH into your Home Assistant host
ssh root@homeassistant.local

# Navigate to add-ons directory
cd /addons

# Clone or copy the repository
# Option A: If you have git access
git clone <your-repo-url> ai-orchestrator

# Option B: Manual copy (from your Windows machine)
# Use SFTP or SCP to copy the entire HASS-AI-Orchestrator folder
```

**2. Restart Home Assistant Supervisor**

```bash
ha supervisor restart
```

**3. Install Add-on via UI**

1. Open Home Assistant web UI
2. Navigate to **Settings → Add-ons**
3. Click **⋮** (three dots) → **Check for updates**
4. Under **Local add-ons**, find **AI Orchestrator**
5. Click on it and press **Install**
6. Wait for Docker build to complete (~5-10 minutes)

**4. Configure Add-on**

Before starting, configure these settings:

```yaml
ollama_host: "http://localhost:11434"
dry_run_mode: true  # ⚠️ IMPORTANT: Keep enabled for first run
log_level: "info"
heating_model: "mistral:7b-instruct"  # or "phi3.5:3.8b" for lower RAM
heating_entities:
  - climate.living_room  # Replace with your actual entity IDs
  - climate.bedroom
decision_interval: 120  # Seconds between decisions
enable_gpu: false  # Set true if you have GPU available
```

> **⚠️ IMPORTANT**: Replace `climate.living_room` and `climate.bedroom` with your actual climate entity IDs. Find them in **Developer Tools → States**.

**5. Start Add-on**

1. Click **START** in the add-on UI
2. Monitor the **Log** tab for startup progress

Expected log output:
```
🚀 Starting AI Orchestrator backend...
✓ Connected to Home Assistant at http://supervisor/core
✓ MCP Server initialized (dry_run=True)
✓ Heating Agent initialized with 2 entities
✓ Agent decision loop started
✅ AI Orchestrator ready!
```

**6. Access Dashboard**

Navigate to: `http://homeassistant.local:8099`

You should see:
- 🟢 **Connected** indicator (top right)
- **Heating Agent** status card (left)
- **Decision Log** (right, will populate after first decision cycle)

---

### Option 2: Docker Container (Development/Testing)

For testing outside of Home Assistant.

#### Prerequisites
- Docker Desktop installed
- Ollama running locally (optional, or use external server)

#### Steps

**1. Build Docker Image**

```powershell
# From project root
cd c:\Users\graham\Documents\GitHub\HASS-AI-Orchestrator

# Build for your platform
docker build -t ai-orchestrator:dev .
```

**2. Create Environment File**

Create `.env` file in project root:

```env
# Home Assistant connection (use your HA instance)
HA_URL=http://homeassistant.local:8123
HA_TOKEN=your_long_lived_access_token_here

# Ollama configuration
OLLAMA_HOST=http://host.docker.internal:11434

# Agent configuration
DRY_RUN_MODE=true
LOG_LEVEL=INFO
HEATING_MODEL=mistral:7b-instruct
HEATING_ENTITIES=climate.living_room,climate.bedroom
DECISION_INTERVAL=120
```

> **Getting a Long-Lived Access Token**:
> 1. In Home Assistant: Profile → Long-Lived Access Tokens
> 2. Click **Create Token**
> 3. Copy the token immediately (it will only be shown once)

**3. Run Container**

```powershell
docker run -d `
  --name ai-orchestrator `
  -p 8099:8099 `
  --env-file .env `
  -v ${PWD}/data:/data `
  ai-orchestrator:dev
```

**4. View Logs**

```powershell
docker logs -f ai-orchestrator
```

**5. Access Dashboard**

Navigate to: `http://localhost:8099`

---

### Option 3: Local Development (Backend + Frontend Separate)

For development and testing individual components.

#### Backend (Python)

> **Note**: Requires Python 3.11+ to be installed on your system.

```powershell
# Install Python dependencies
cd backend
python -m pip install -r requirements.txt

# Create .env file
# (same as Option 2)

# Run backend
uvicorn main:app --reload --host 0.0.0.0 --port 8099
```

#### Frontend (React)

```powershell
# From dashboard directory (already done)
cd dashboard
npm install  # Already completed
npm run dev  # Development server with hot reload
```

Dashboard will run on `http://localhost:3000` with API proxy to backend.

---

## 🔍 Verification Checklist

After deployment, verify the following:

### ✅ Add-on Health
- [ ] Add-on status shows "Running" (green)
- [ ] No errors in add-on logs
- [ ] Ollama model successfully pulled (check logs)
- [ ] FastAPI backend started on port 8099

### ✅ Home Assistant Connection
- [ ] Log shows "✓ Connected to Home Assistant"
- [ ] No WebSocket authentication errors
- [ ] Climate entities recognized (check logs for entity count)

### ✅ Dashboard
- [ ] Dashboard loads at `http://<ha-host>:8099`
- [ ] Connection indicator shows "Connected" (green)
- [ ] Agent status card displays correct information
- [ ] Decision log is visible (may be empty initially)

### ✅ Decision Loop
- [ ] Wait 2-3 minutes (120s interval)
- [ ] First decision appears in dashboard log
- [ ] Decision shows `DRY RUN` badge
- [ ] No actual temperature changes occur (dry-run mode active)
- [ ] Decision log file created in `/data/decisions/heating/`

---

## 🛠️ Troubleshooting

### Issue: Ollama Model Won't Load

**Symptoms**: Error in logs about model not found or OOM

**Solutions**:
```bash
# Check available RAM
docker exec -it addon_ai-orchestrator free -h

# Try smaller model
# Edit add-on config: heating_model: "phi3.5:3.8b"

# Manual model pull
docker exec -it addon_ai-orchestrator ollama pull phi3.5:3.8b
```

### Issue: WebSocket Connection Failed

**Symptoms**: "❌ Failed to connect to Home Assistant WebSocket"

**Solutions**:
- Verify `hassio_api: true` in `config.yaml`
- Check HA core is running: `ha core info`
- Restart add-on
- Check supervisor token is available: `echo $SUPERVISOR_TOKEN` (inside container)

### Issue: Dashboard Shows "Disconnected"

**Symptoms**: Red indicator, no WebSocket updates

**Solutions**:
```powershell
# Check backend is running
curl http://homeassistant.local:8099/api/health

# Check logs for WebSocket errors
docker logs addon_ai-orchestrator | Select-String "WebSocket"

# Restart add-on
```

### Issue: No Climate Entities Found

**Symptoms**: "Heating Agent initialized with 0 entities"

**Solutions**:
- Verify entity IDs in add-on config
- Check entities exist: **Developer Tools → States** → filter "climate"
- Entity IDs are case-sensitive: `climate.living_room` not `Climate.Living_Room`

---

## 🧪 Testing in Dry-Run Mode

Before enabling live control, thoroughly test the agent's decisions:

1. **Monitor Initial Decisions** (1-2 hours)
   - Watch dashboard for decision patterns
   - Check decision logs in `/data/decisions/heating/`
   - Verify temperature targets are reasonable

2. **Review Decision Reasoning**
   - Each decision includes reasoning text
   - Should align with SKILLS.md criteria
   - Should respect comfort ranges (19-22°C occupied, 16°C away)

3. **Test Different Scenarios**
   - Manually adjust temperature in HA UI
   - Leave home (trigger occupancy sensor)
   - Return home
   - Change time of day

4. **Validate Safety Checks**
   - No temperature should exceed 30°C or drop below 10°C
   - Changes should be gradual (≤3°C per decision)
   - Agent should respect manual overrides

---

## ⚠️ Enabling Production Mode

Once you're confident in the agent's behavior:

1. **Stop Add-on**
2. **Edit Configuration**:
   ```yaml
   dry_run_mode: false  # ⚠️ CRITICAL: This enables real control
   ```
3. **Start Add-on**
4. **Monitor Closely** for first 24 hours:
   - Watch actual temperature changes
   - Keep manual override ready
   - Review decision logs daily

> **Safety Net**: Manual temperature changes in HA UI will temporarily pause agent automation. The agent will resume control after the manual override period expires.

---

## 📊 Next Steps

### Phase 1 Complete ✅
- Single Heating Agent fully functional
- Dry-run testing validated
- Production mode optional

### Phase 2 Preview (Coming Soon)
- **Cooling Agent**: A/C optimization
- **Lighting Agent**: Adaptive lighting
- **Security Agent**: Automated security responses
- **Orchestration**: Multi-agent coordination via LangGraph
- **Human-in-the-Loop**: Approval queue for high-impact decisions

---

## 📝 Quick Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| Add-on Config | HA UI → Settings → Add-ons → AI Orchestrator | User settings |
| Dashboard | `http://<ha-host>:8099` | Real-time monitoring |
| Logs | Add-on UI → Log tab | Troubleshooting |
| Decision Logs | `/data/decisions/heating/` | Historical decisions |
| SKILLS.md | `/app/skills/heating/SKILLS.md` | Agent specification |

---

## 🆘 Support

If you encounter issues:

1. Check logs: Add-on UI → Log tab
2. Review this troubleshooting guide
3. Verify all prerequisites met
4. Check [README.md](file:///c:/Users/graham/Documents/GitHub/HASS-AI-Orchestrator/README.md) for additional details
5. Consult [walkthrough.md](file:///C:/Users/graham/.gemini/antigravity/brain/7ad4cdc8-592b-4f90-9d1a-a820385d4696/walkthrough.md) for architecture details

---

**✨ You're ready to deploy Phase 1!**
