---
name: proj-knowledge
description: Builds and maintains an evolving knowledge base of the AI Orchestrator project architecture, components, functions, patterns, and conventions. Use when agents need to understand the project structure, learn how components interact, discover coding patterns, or when adding new information about the codebase.
---

# Project Knowledge Base

This skill helps agents build and maintain a comprehensive understanding of the AI Orchestrator project. It's a living document that evolves as the project grows.

## Purpose

The project knowledge base serves as:
- **Onboarding resource**: New agents can quickly understand the system
- **Reference guide**: Quick lookup for architecture and patterns
- **Discovery log**: Document findings and insights
- **Coordination tool**: Shared understanding across agent team

## How to Use This Skill

### When to Read
- Before starting work on any feature
- When encountering unfamiliar code
- When troubleshooting issues
- When planning new features

### When to Update
- After discovering new architecture patterns
- When understanding how components interact
- After solving complex problems
- When documenting new features
- When finding important conventions

## Knowledge Base Structure

The knowledge base is maintained in `.cursor/skills/proj-knowledge/proj-knowledge.md`. It should contain:

### 1. Project Overview
- High-level purpose and goals
- Key features and capabilities
- Technology stack
- Current version and status

### 2. Architecture
- System components and their roles
- Data flow and communication patterns
- Key design decisions
- Integration points

### 3. Component Details
- Core modules and their responsibilities
- Agent types and their behaviors
- API structure
- Database/storage patterns

### 4. Code Patterns
- Common coding conventions
- Testing patterns
- Error handling approaches
- Async/await patterns

### 5. Development Workflow
- How to add new agents
- How to extend functionality
- Testing procedures
- Deployment process

### 6. Known Issues & Solutions
- Common problems and fixes
- Workarounds for limitations
- Performance considerations

## Updating the Knowledge Base

### Adding New Information

When you discover something important:

1. **Read the current knowledge base**:
   ```bash
   Read: .cursor/skills/proj-knowledge/proj-knowledge.md
   ```

2. **Identify the appropriate section** or create a new one

3. **Add your findings** with:
   - Clear, concise descriptions
   - Code examples if relevant
   - Context about why it matters
   - References to relevant files

4. **Maintain structure**: Keep sections organized and easy to navigate

### Example Update Format

```markdown
## New Finding: Agent Communication Pattern

**Discovered**: 2025-01-26
**Context**: Working on multi-agent coordination

Agents communicate through the Orchestrator's task ledger:
- Tasks are created in `orchestrator.py:plan()`
- Distributed via `distribute_tasks()`
- Agents update `progress_ledger` with decisions
- See `orchestrator.py:aggregate_decisions()` for collection

**Files**: `ai-orchestrator/backend/orchestrator.py` (lines 296-331)
```

## Key Project Components

### Core System
- **Orchestrator** (`orchestrator.py`): Central coordinator using LangGraph
- **MCP Server** (`mcp_server.py`): Safe tool execution engine
- **HA Client** (`ha_client.py`): Home Assistant WebSocket connection
- **RAG Manager** (`rag_manager.py`): Knowledge base management
- **Approval Queue** (`approval_queue.py`): Human-in-the-loop approvals

### Agents
- **Base Agent** (`agents/base_agent.py`): Foundation for all agents
- **Heating Agent**: Climate control for heating
- **Cooling Agent**: Climate control for cooling
- **Lighting Agent**: Light and scene management
- **Security Agent**: Locks, alarms, cameras
- **Universal Agent**: Generic agent for any domain
- **Architect Agent**: Agent creation and suggestions

### Providers
- **Local Provider** (`providers/local_provider.py`): Ollama integration
- **OpenAI Provider** (`providers/openai_provider.py`): OpenAI API
- **Base Provider** (`providers/base.py`): Provider interface

### Workflow
- **Workflow Graph** (`workflow_graph.py`): LangGraph state machine
- States: Plan → Distribute → Wait → Aggregate → Resolve → Approve → Execute

## Important Patterns

### Agent Structure
All agents inherit from `BaseAgent` and implement:
- `gather_context()`: Collect relevant state
- `decide()`: Make decisions based on context
- `execute()`: Perform actions via MCP

### Async Patterns
- Use `asyncio` for all I/O operations
- Agents run in async loops
- Use `asyncio.gather()` for parallel operations

### Error Handling
- Log errors with context
- Use try/except with specific exceptions
- Return graceful fallbacks

### Testing
- Smoke tests in `tests/test_*_smoke.py`
- Integration tests require mocks
- Use pytest markers: `@pytest.mark.smoke`, `@pytest.mark.integration`

## Quick Reference

### Key Directories
- `ai-orchestrator/backend/`: Main Python backend
- `ai-orchestrator/backend/agents/`: Agent implementations
- `ai-orchestrator/backend/tests/`: Test suite
- `ai-orchestrator/dashboard/`: React frontend
- `ai-visual-dashboard/`: AI-generated dashboard

### Key Files
- `main.py`: FastAPI application entry point
- `orchestrator.py`: Core orchestration logic
- `mcp_server.py`: Tool execution engine
- `workflow_graph.py`: LangGraph workflow definition
- `config.json`: Add-on configuration

### Important Endpoints
- `/api/agents`: Agent management
- `/api/chat`: Chat interface
- `/api/config`: Configuration
- `/api/analytics`: Analytics data
- `/api/factory`: Agent factory

## Maintenance Guidelines

1. **Keep it current**: Update when architecture changes
2. **Be specific**: Include file paths and line numbers
3. **Add examples**: Code snippets help understanding
4. **Cross-reference**: Link related concepts
5. **Date discoveries**: Track when information was added

## Related Skills

- **The-plan**: Current tasks and priorities
- **task-marking**: Marking completed work
- **architecture-understanding**: Deep architecture dives
