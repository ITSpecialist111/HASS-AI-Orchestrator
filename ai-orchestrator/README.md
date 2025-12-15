# 🤖 AI Orchestrator (Phase 6)

**The "Jarvis" for your Home Assistant.**

AI Orchestrator is a local, privacy-focused autonomous system that intelligently manages your smart home using multiple specialized AI agents.

## 🌟 Features

- **Universal Agents**: Create agents for ANY integration (Pool, Solar, Garage, etc.) using natural language.
- **RAG Memory**: Ingests PDF manuals and learns from your entity registry.
- **Agent Factory**: Chat with the "Architect" to build new bots in seconds.
- **Space Ops Dashboard**: Real-time "Minority Report" style visualization.
- **Privacy Focus**: Runs 100% locally using Ollama.

## 📦 Installation

1. Add this repository to your Home Assistant Add-on Store.
2. Install **AI Orchestrator**.
3. **Configuration**:
   ```yaml
   ollama_host: "http://localhost:11434" # or external IP
   ha_access_token: "eyJ0eX..."          # Create under User Profile > Long-Lived Access Tokens
   dry_run_mode: true                    # Recommended for first run
   log_level: "info"
   ```
4. Start the add-on. Initial startup may take 5-10 minutes (model download).

## 🎮 Dashboard

Once running, access the dashboard at:
`http://homeassistant.local:8999`

## 🧠 Brain Training

- Drop PDF manuals into `/addon_configs/ai-orchestrator/manuals/` to teach your agents about your devices.
- Edit `agents.yaml` for advanced configuration.

## ⚠️ Requirements

- **4GB+ RAM** (for local LLM inference)
- Home Assistant OS / Supervised
