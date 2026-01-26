# AI Orchestrator - Project Knowledge Base

*Last Updated: 2025-01-26*
*This is a living document. Update it as you discover new patterns and insights.*

## Project Overview

**AI Orchestrator** is a Home Assistant add-on that transforms static automations into a dynamic, AI-driven smart home ecosystem. It uses multi-agent AI to reason about home state and execute actions intelligently.

### Key Features
- **Multi-Agent System**: Specialist agents (Heating, Cooling, Lighting, Security, etc.)
- **Orchestrator**: Central coordinator using LangGraph workflows
- **RAG Knowledge Base**: Context-aware decision making with PDF/manual ingestion
- **MCP Server**: Safe tool execution engine for Home Assistant services
- **Visual Dashboard**: AI-generated dynamic dashboards (supports Ollama, OpenAI, Gemini)
- **Chat Interface**: Natural language control via floating assistant

### Technology Stack
- **Backend**: Python 3.11+, FastAPI, LangGraph
- **Frontend**: React (dashboard), AI-generated HTML (visual dashboard)
- **LLM Providers**: Ollama (local), OpenAI, Google Gemini
- **Integration**: Home Assistant WebSocket API, MCP (Model Context Protocol)

### Current Version
- **Version**: v0.9.47 (Gemini Integration & Connectivity Robustness)
- **Status**: Alpha

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Server                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Orchestrator │  │  MCP Server  │  │  RAG Manager │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
│  ┌──────▼──────────────────▼──────────────────▼──────┐  │
│  │         Specialist Agents (Heating, etc.)         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
  Home Assistant      LLM Providers        Knowledge Base
  (WebSocket)      (Ollama/OpenAI/Gemini)    (Vector DB)
```

### Core Components

#### 1. Orchestrator (`orchestrator.py`)
- **Role**: Central coordinator for multi-agent system
- **Responsibilities**:
  - Plans high-level strategies
  - Distributes tasks to specialist agents
  - Resolves conflicts between agents
  - Manages approval queue for high-impact actions
  - Generates visual dashboards
  - Handles chat requests
- **Workflow**: Uses LangGraph state machine (Plan → Distribute → Wait → Aggregate → Resolve → Approve → Execute)
- **Key Methods**:
  - `run_planning_loop()`: Main orchestration cycle
  - `execute_workflow()`: Single workflow execution
  - `process_chat_request()`: Handle user chat messages
  - `generate_visual_dashboard()`: Create AI-generated dashboards

#### 2. MCP Server (`mcp_server.py`)
- **Role**: Safe tool execution engine
- **Responsibilities**:
  - Validates tool calls from agents
  - Maps AI intent to Home Assistant service calls
  - Enforces security (allowlists, blocked domains, limits)
  - Logs all actions
- **Security Features**:
  - Domain allowlist (only approved domains)
  - Critical domain blocks (shell_command, script, etc.)
  - Approval queue for high-impact actions
  - Temperature and change limits

#### 3. Home Assistant Client (`ha_client.py`)
- **Role**: WebSocket connection to Home Assistant
- **Responsibilities**:
  - Maintains WebSocket connection
  - Fetches entity states
  - Executes service calls
  - Handles reconnection logic

#### 4. RAG Manager (`rag_manager.py`)
- **Role**: Knowledge base management
- **Responsibilities**:
  - Ingests PDF/manual files
  - Creates embeddings
  - Provides context to agents
  - Delta-based updates for efficiency

#### 5. Approval Queue (`approval_queue.py`)
- **Role**: Human-in-the-loop for high-impact actions
- **Responsibilities**:
  - Queues actions requiring approval
  - Tracks approval status
  - Executes approved actions

### Agent Architecture

All agents inherit from `BaseAgent` (`agents/base_agent.py`):

```python
class BaseAgent:
    async def gather_context() -> dict
    async def decide() -> list
    async def execute() -> list
```

#### Agent Types

1. **Heating Agent** (`agents/heating_agent.py`)
   - Domain: `climate`
   - Focus: Heating control and optimization

2. **Cooling Agent** (`agents/cooling_agent.py`)
   - Domain: `climate`
   - Focus: Cooling control and optimization

3. **Lighting Agent** (`agents/lighting_agent.py`)
   - Domain: `light`, `scene`
   - Focus: Light control and scene management

4. **Security Agent** (`agents/security_agent.py`)
   - Domain: `lock`, `alarm_control_panel`, `camera`
   - Focus: Security and access control

5. **Universal Agent** (`agents/universal_agent.py`)
   - Domain: Any
   - Focus: Generic agent for any Home Assistant domain

6. **Architect Agent** (`agents/architect_agent.py`)
   - Role: Agent creation and suggestions
   - Focus: Analyzes home and suggests new automations

### Workflow Graph (`workflow_graph.py`)

LangGraph state machine defining orchestrator workflow:

**States**:
1. **Plan**: Analyze home state, create tasks
2. **Distribute**: Send tasks to agents
3. **Wait**: Collect agent responses
4. **Aggregate**: Combine decisions
5. **Resolve**: Handle conflicts
6. **Check Approval**: Route high-impact to queue
7. **Execute**: Run approved actions

**State Type**: `OrchestratorState` (TypedDict with tasks, decisions, conflicts, etc.)

## Code Patterns

### Async Patterns

All I/O operations use `asyncio`:

```python
# Parallel state gathering
states = await asyncio.gather(
    agent1.get_states(),
    agent2.get_states(),
    agent3.get_states()
)
```

### Agent Decision Making

Standard pattern for agents:

```python
async def decide(self) -> List[Decision]:
    # 1. Gather context
    context = await self.gather_context()
    
    # 2. Query RAG if needed
    knowledge = await self.rag_manager.query(context)
    
    # 3. Call LLM for decision
    decision = await self.llm_client.chat(...)
    
    # 4. Return structured decision
    return [Decision(...)]
```

### Error Handling

Consistent error handling pattern:

```python
try:
    result = await operation()
    logger.info(f"Success: {result}")
except SpecificError as e:
    logger.error(f"Error in operation: {e}", exc_info=True)
    return fallback_value
```

### Testing Patterns

- **Smoke tests**: Quick validation (`@pytest.mark.smoke`)
- **Integration tests**: Full system tests (`@pytest.mark.integration`)
- **Unit tests**: Isolated component tests (`@pytest.mark.unit`)
- **Async tests**: Use `pytest-asyncio` and `@pytest.mark.asyncio`

Test file naming: `test_<component>_<type>.py`

## File Structure

### Backend (`ai-orchestrator/backend/`)
```
backend/
├── main.py                 # FastAPI app entry point
├── orchestrator.py         # Core orchestrator
├── mcp_server.py           # Tool execution engine
├── ha_client.py            # HA WebSocket client
├── rag_manager.py          # RAG knowledge base
├── approval_queue.py       # Approval queue
├── workflow_graph.py       # LangGraph workflow
├── agents/                 # Agent implementations
│   ├── base_agent.py
│   ├── heating_agent.py
│   ├── cooling_agent.py
│   ├── lighting_agent.py
│   ├── security_agent.py
│   ├── universal_agent.py
│   └── architect_agent.py
├── providers/              # LLM providers
│   ├── base.py
│   ├── local_provider.py
│   └── openai_provider.py
└── tests/                  # Test suite
```

### Frontend (`ai-orchestrator/dashboard/`)
- React application
- Real-time WebSocket updates
- Agent status visualization

### Visual Dashboard (`ai-visual-dashboard/`)
- AI-generated HTML dashboards
- Supports Ollama, OpenAI, Gemini
- Dynamic regeneration based on home state

## API Endpoints

### Agent Management
- `GET /api/agents`: List all agents
- `GET /api/agents/{id}`: Get agent details
- `POST /api/agents`: Create new agent
- `PUT /api/agents/{id}`: Update agent
- `DELETE /api/agents/{id}`: Delete agent

### Chat Interface
- `POST /api/chat`: Send chat message to orchestrator

### Configuration
- `GET /api/config`: Get configuration
- `PATCH /api/config`: Update configuration
- `GET /api/config/openai`: Get OpenAI runtime state

### Analytics
- `GET /api/analytics`: Get analytics data
- `GET /api/analytics/decisions`: Get decision history

### Factory
- `POST /api/factory/suggest`: Get agent suggestions
- `POST /api/factory/create`: Create agent via wizard

## Development Workflow

### Adding a New Agent

1. Create agent class in `agents/`:
   ```python
   from .base_agent import BaseAgent
   
   class MyAgent(BaseAgent):
       async def gather_context(self) -> dict:
           # Gather relevant state
           pass
       
       async def decide(self) -> List[Decision]:
           # Make decisions
           pass
   ```

2. Create skills file in `ai-orchestrator/skills/<agent-name>/SKILLS.md`

3. Register in `agents.yaml` or via factory

4. Write tests in `tests/test_<agent>_*.py`

### Testing

Run tests:
```bash
cd ai-orchestrator/backend
pytest -m smoke -v          # Smoke tests
pytest tests/ -v            # All tests
pytest tests/test_file.py   # Specific file
```

### Deployment

1. Update version in `config.json`
2. Run full test suite
3. Build Docker image
4. Update repository
5. Test in Home Assistant

## Known Patterns & Solutions

### Async Context Gathering
Agents gather context in parallel:
```python
contexts = await asyncio.gather(
    self.get_climate_states(),
    self.get_sensor_states(),
    self.get_switch_states()
)
```

### Conflict Resolution
Orchestrator resolves conflicts using rules:
- Heating vs Cooling: Disable both
- Security vs Comfort: Security priority
- Away mode: Override comfort targets

### RAG Integration
Agents query RAG before decisions:
```python
knowledge = await self.rag_manager.query(
    query=context_summary,
    top_k=5
)
```

## Important Notes

### Security
- All tool calls go through MCP server
- Domain allowlist enforced
- Critical domains blocked
- Approval required for high-impact actions

### Performance
- Tri-level architecture: Orchestrator (smart), Smart Agents, Fast Agents
- Parallel context gathering
- Delta-based RAG updates
- Cached entity states

### Error Recovery
- WebSocket reconnection logic
- Graceful fallbacks for LLM failures
- Retry logic for transient errors
- Comprehensive logging

## Discovery Log

*Add new findings here as they're discovered*

### 2025-01-26: Agent Communication Pattern
- Agents communicate through Orchestrator's task ledger
- Tasks created in `orchestrator.py:plan()`
- Distributed via `distribute_tasks()`
- Agents update `progress_ledger` with decisions
- Collected in `aggregate_decisions()`
