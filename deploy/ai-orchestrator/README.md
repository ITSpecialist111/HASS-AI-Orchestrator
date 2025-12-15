# Home Assistant AI Orchestrator

Production-grade autonomous multi-agent orchestration system for Home Assistant 2025.12.3+.

## Overview

Move from static "if X then Y" automations to reasoning-based, proactive home management driven by multiple collaborating AI agents. The system uses specialist agents (Heating, Cooling, Lighting, Security) plus a deep reasoning orchestration agent that coordinates them, avoids conflicts, and optimizes comfort, energy use, and safety.

### Current Status: Phase 1 - Foundation & MVP

**Implemented:**
- ✅ Single Heating Agent end-to-end pipeline
- ✅ Home Assistant WebSocket integration
- ✅ MCP (Model Context Protocol) server for tool execution
- ✅ Ollama integration for local LLM inference
- ✅ React dashboard for agent monitoring
- ✅ Decision logging and dry-run mode

**Coming in Phase 2:**
- Multi-agent orchestration (Cooling, Lighting, Security)
- LangGraph workflow graphs
- Human-in-the-loop approval queues

## Architecture

```
┌─────────────────────┐      ┌──────────────────────────┐      ┌─────────────┐
│  Home Assistant     │◄────►│  AI Orchestrator Add-on  │◄────►│   Ollama    │
│  - Climate entities │ WS   │  - FastAPI Backend       │ HTTP │  - Mistral  │
│  - Sensors          │      │  - MCP Server            │      │  - Phi 3.5  │
│  - Services API     │      │  - Heating Agent         │      │  - DeepSeek │
└─────────────────────┘      │  - React Dashboard       │      └─────────────┘
                             └──────────────────────────┘
```

## Requirements

### Hardware
- **Minimum**: 8GB RAM (CPU-only with Phi 3.5-mini)
- **Recommended**: 16GB RAM + GPU with 6GB+ VRAM (for Mistral 7B)

### Software
- Home Assistant 2025.12.3+ (OS or Supervised installation)
- Docker 25.0+ (included with HA OS)
- Climate entities configured in Home Assistant

## Installation

### Method 1: Local Add-on (Development)

1. Clone this repository to your Home Assistant add-ons directory:
   ```bash
   cd /addons
   git clone https://github.com/ITSpecialist111/HASS-AI-Orchestrator.git ai-orchestrator
   ```

2. Restart Home Assistant Supervisor

3. Navigate to **Settings → Add-ons → Local Add-ons → AI Orchestrator**

4. Click **Install** (this will build the Docker image)

5. Configure the add-on:
   - Set `heating_entities` to your climate entity IDs
   - Choose model: `mistral:7b-instruct` (GPU) or `phi3.5:3.8b` (CPU)
   - Enable `dry_run_mode` for safe testing

6. Start the add-on and check logs for successful startup

### Method 2: Add-on Store (Coming Soon)

Installation via Home Assistant Community Add-ons store will be available after Phase 4 completion.

## Configuration

### Add-on Configuration Options

```yaml
ollama_host: "http://localhost:11434"  # Ollama server URL
dry_run_mode: true                      # Safe mode: log decisions without executing
log_level: "info"                       # debug | info | warning | error
heating_model: "mistral:7b-instruct"   # LLM model for Heating Agent
heating_entities:                       # Climate entities to control
  - climate.living_room
  - climate.bedroom
decision_interval: 120                  # Seconds between agent decisions
enable_gpu: false                       # Enable GPU acceleration for Ollama
```

### Heating Agent Configuration

The Heating Agent is configured via `skills/heating/SKILLS.md`:
- **Comfort range**: 19-22°C (occupied), 16°C (away mode)
- **Safety limits**: 10-30°C absolute, ±3°C per decision
- **Decision interval**: 120 seconds (configurable)

## Usage

### Accessing the Dashboard

Navigate to `http://<ha-host>:8099` to view:
- Agent status (connected, idle, deciding)
- Real-time decision log
- Current climate states
- Action history

### Dry-Run Mode (Recommended for First Use)

With `dry_run_mode: true`, the agent will:
- ✅ Make decisions and log them
- ✅ Broadcast updates to dashboard
- ❌ NOT execute actual climate changes

Review decision logs in `/data/decisions/heating/` before disabling dry-run mode.

### Enabling Production Mode

1. Review decision logs to verify agent behavior
2. Set `dry_run_mode: false` in add-on configuration
3. Restart the add-on
4. Monitor first few decisions closely
5. Use Home Assistant UI to override if needed

## Safety Features

- **Temperature Bounds**: Hard limits 10-30°C
- **Change Limits**: Maximum ±3°C per decision
- **Dry-Run Mode**: Test decisions without execution
- **Manual Override**: HA UI changes pause agent for 30 minutes
- **Decision Logging**: All actions logged to `/data/decisions/`

## Technology Stack

### Core Runtime
- **Python 3.11+**: Backend services
- **Docker 25.0+**: Multi-arch containerization
- **Node.js 20 LTS**: Dashboard build toolchain

### AI/ML
- **Microsoft Agent Framework 0.2+**: Orchestration patterns
- **LangGraph 0.2+**: Workflow graphs (Phase 2)
- **Ollama 0.5+**: Local LLM serving
- **Supported Models**: Mistral 7B, DeepSeek-R1 8B, Phi 3.5-mini

### Web Framework
- **FastAPI**: Backend API
- **React 18.2+**: Dashboard UI
- **Vite 5+**: Frontend build tool

### Storage & Observability
- **Chroma 0.5+**: RAG vector database (Phase 3)
- **OpenTelemetry 1.21+**: Metrics and tracing (Phase 4)
- **Prometheus**: Monitoring (Phase 4)

## Project Structure

```
HASS-AI-Orchestrator/
├── config.yaml              # HA add-on manifest
├── Dockerfile               # Multi-arch build
├── run.sh                   # Entrypoint script
├── README.md                # This file
│
├── backend/
│   ├── requirements.txt
│   ├── main.py              # FastAPI app
│   ├── ha_client.py         # HA WebSocket client
│   ├── mcp_server.py        # MCP tool server
│   └── agents/
│       ├── base_agent.py    # Abstract base
│       └── heating_agent.py # Phase 1 implementation
│
├── dashboard/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       └── index.css
│
└── skills/
    └── heating/
        └── SKILLS.md        # Heating agent specification
```

## Development

### Local Development Setup

1. **Backend**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   export HA_TOKEN="your_token"
   export HA_URL="http://homeassistant.local:8123"
   uvicorn main:app --reload
   ```

2. **Frontend**:
   ```bash
   cd dashboard
   npm install
   npm run dev  # Runs on http://localhost:3000
   ```

3. **Ollama** (separate terminal):
   ```bash
   ollama serve
   ollama pull mistral:7b-instruct
   ```

### Running Tests

```bash
cd backend
pytest tests/ -v
```

## Phased Roadmap

- **Phase 1** (Current): Foundation & MVP - Single Heating Agent
- **Phase 2** (Weeks 5-8): Multi-Agent Orchestration
- **Phase 3** (Weeks 9-12): RAG Knowledge + Hardware Optimization
- **Phase 4** (Weeks 13-20): Production Hardening & HA Store Release

## Troubleshooting

### Ollama Model Won't Load
- Check available RAM: `free -h`
- Try smaller model: `phi3.5:3.8b` instead of `mistral:7b-instruct`
- Enable swap if RAM < 8GB

### Agent Not Making Decisions
- Check logs: `docker logs addon_ai-orchestrator`
- Verify `heating_entities` are valid climate entities
- Ensure entities have `temperature` and `hvac_mode` attributes

### Dashboard Not Loading
- Verify port 8099 is accessible
- Check browser console for errors
- Ensure backend is running: `curl http://localhost:8099/api/health`

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Acknowledgments

Built with:
- [Home Assistant](https://www.home-assistant.io/)
- [Ollama](https://ollama.com/)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [LangGraph](https://github.com/langchain-ai/langgraph)
