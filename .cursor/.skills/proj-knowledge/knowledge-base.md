# HASS AI Orchestrator - Project Knowledge Base

> **Last Updated**: 2026-01-26
> 
> This is a living document that evolves as agents explore and understand the project.

## Project Overview

The HASS AI Orchestrator is a Home Assistant add-on that transforms static automations into a dynamic, AI-driven ecosystem. It uses autonomous AI agents that reason about home state and execute actions intelligently through a Model Context Protocol (MCP) server.

**Key Technologies**:
- Python backend (FastAPI)
- React/TypeScript dashboard
- Ollama/OpenAI/Gemini LLM providers
- ChromaDB for RAG knowledge base
- LangGraph for workflow orchestration

## Directory Structure

```
ai-orchestrator/
├── backend/              # Python backend
│   ├── agents/          # Agent implementations
│   ├── providers/      # LLM provider abstractions
│   ├── tests/          # Test suite
│   └── main.py         # FastAPI application entry
├── dashboard/           # React frontend
├── skills/             # Agent skill definitions
└── config.json         # Add-on configuration
```

## Core Components

### Orchestrator (`ai-orchestrator/backend/orchestrator.py`)
- **Purpose**: Central coordinator for multi-agent system using LangGraph workflows
- **Key Functions**:
  - Plans tasks and distributes to agents
  - Resolves conflicts between agents
  - Manages approval queue for high-impact actions
  - Coordinates agent decision cycles
- **Dependencies**: `workflow_graph`, `ha_client`, `mcp_server`, `approval_queue`
- **Used By**: `main.py` (FastAPI app)
- **Patterns**: LangGraph workflow pattern, task ledger pattern

### MCP Server (`ai-orchestrator/backend/mcp_server.py`)
- **Purpose**: Model Context Protocol server for safely executing agent decisions
- **Key Functions**:
  - `_register_tools()`: Registers available MCP tools (15 tools total)
  - `execute_tool()`: Executes tool calls with validation
  - `_set_temperature()`: Sets climate temperature (10-30°C bounds, ±3°C rate limit)
  - `_set_hvac_mode()`: Sets HVAC mode with validation
- **Dependencies**: `ha_client`, `approval_queue`, `rag_manager`
- **Used By**: All agents via orchestrator
- **Patterns**: Tool registration pattern, safety validation pattern
- **Important**: All tool calls validated; dry-run mode logs without executing

### Base Agent (`ai-orchestrator/backend/agents/base_agent.py`)
- **Purpose**: Base class for all autonomous agents
- **Key Methods**:
  - `gather_context()`: Collects relevant Home Assistant state
  - `decide()`: Makes decisions using LLM
  - `execute()`: Executes decisions via MCP server
- **Dependencies**: `ha_client`, `mcp_server`, LLM providers
- **Used By**: All specific agents (heating, cooling, lighting, security, etc.)
- **Patterns**: Template method pattern, context gathering pattern

## Agents

### Heating Agent (`ai-orchestrator/backend/agents/heating_agent.py`)
- **Purpose**: Manages heating systems intelligently
- **Capabilities**: Temperature control, HVAC mode management
- **Tools**: `set_temperature`, `set_hvac_mode`, `get_climate_state`
- **Decision Logic**: Uses LLM to reason about comfort, efficiency, schedules

### Cooling Agent (`ai-orchestrator/backend/agents/cooling_agent.py`)
- **Purpose**: Manages cooling systems
- **Capabilities**: Similar to heating agent but for cooling
- **Tools**: Same as heating agent
- **Decision Logic**: Optimizes cooling for comfort and efficiency

### Architect Agent (`ai-orchestrator/backend/agents/architect_agent.py`)
- **Purpose**: Creates and configures new agents via chat interface
- **Capabilities**: Agent factory, configuration generation
- **Tools**: Agent creation tools, configuration management
- **Decision Logic**: Interviews users and generates agent configs

### Universal Agent (`ai-orchestrator/backend/agents/universal_agent.py`)
- **Purpose**: Generic agent that can work with any Home Assistant domain
- **Capabilities**: Works with any entity type via MCP tools
- **Tools**: All MCP tools (climate, lighting, switch, etc.)
- **Decision Logic**: Domain-agnostic reasoning

## Integration Points

### Home Assistant Integration
- **WebSocket Client**: `ha_client.py` manages WebSocket connection
- **State Updates**: Agents receive real-time state changes
- **Service Calls**: MCP server executes `homeassistant.call_service`
- **Entity Registry**: Agents discover available entities

### LLM Providers
- **Local Provider**: Ollama integration (`local_provider.py`)
- **OpenAI Provider**: Cloud-based OpenAI (`openai_provider.py`)
- **Gemini Provider**: Google Gemini for dashboard generation
- **Provider Pattern**: Abstract base class for provider switching

### RAG Knowledge Base
- **RAG Manager**: `rag_manager.py` handles document ingestion
- **ChromaDB**: Vector database for embeddings
- **Embeddings**: Uses `nomic-embed-text` model
- **Integration**: Agents query knowledge base before decisions

## Patterns & Conventions

### Agent Pattern
- All agents inherit from `BaseAgent`
- Implement `gather_context()` and `decide()` methods
- Use MCP server for all actions
- Follow decision interval configuration

### Safety Pattern
- All tool calls validated before execution
- Temperature bounds: 10-30°C
- Rate limiting: ±3°C max change per call
- Dry-run mode for testing
- Approval queue for high-impact actions

### Configuration Pattern
- YAML-based agent configuration (`agents.yaml`)
- Environment variables for runtime config
- JSON config for add-on settings
- Separate configs for dev/prod

## Important Notes

- **Dry Run Mode**: Default enabled; agents log actions without executing
- **Decision Intervals**: Configurable per agent (default 120s)
- **Safety First**: All actions go through MCP validation
- **Multi-Provider**: Supports Ollama, OpenAI, and Gemini simultaneously
- **Dashboard Port**: 8999 (configurable)
- **Data Directory**: `/data` in add-on, workspace-local for dev

## Testing

- **Test Suite**: `backend/tests/` directory
- **Smoke Tests**: Fast validation tests (`-m smoke`)
- **Integration Tests**: Full system tests
- **Test Fixtures**: Mock HA client, Ollama client in `conftest.py`
- **Run Tests**: `pytest -m smoke -v` from backend directory
