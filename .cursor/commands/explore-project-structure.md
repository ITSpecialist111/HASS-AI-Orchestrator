# Explore Project Structure

## Purpose
Helps agents navigate and understand the AI Orchestrator project architecture, file organization, and component relationships.

## Usage
`/explore-project-structure [component|all]`

Options:
- `component` - Explore specific component (orchestrator, agents, mcp, etc.)
- `all` - Full project structure overview
- No argument - Interactive exploration

## Instructions for Agent

When this command is invoked:

1. **Determine Scope**:
   - If component specified: Focus on that component
   - If "all": Provide comprehensive overview
   - If no argument: Start with high-level, then drill down

2. **Read Key Files**:
   - Start with `README.md` for project overview
   - Check `DEPLOYMENT.md` for deployment structure
   - Review `ROADMAP.md` for project direction
   - Read `ai-orchestrator/README.md` for component details

3. **Explore Directory Structure**:
   ```bash
   # Backend structure
   List: ai-orchestrator/backend/
   
   # Agent implementations
   List: ai-orchestrator/backend/agents/
   
   # Test suite
   List: ai-orchestrator/backend/tests/
   
   # Frontend
   List: ai-orchestrator/dashboard/
   ```

4. **For Specific Components**:

   **Orchestrator**:
   - Read: `ai-orchestrator/backend/orchestrator.py`
   - Understand: Workflow graph, planning loop, task distribution
   - Related: `workflow_graph.py`, `main.py`

   **Agents**:
   - Read: `ai-orchestrator/backend/agents/base_agent.py`
   - List: All agent implementations
   - Understand: Agent interface and patterns

   **MCP Server**:
   - Read: `ai-orchestrator/backend/mcp_server.py`
   - Understand: Tool execution, security, validation

   **RAG Manager**:
   - Read: `ai-orchestrator/backend/rag_manager.py`
   - Understand: Knowledge base, embeddings, querying

5. **Map Dependencies**:
   - Identify imports and relationships
   - Note external dependencies (FastAPI, LangGraph, etc.)
   - Document internal component dependencies

6. **Document Findings**:
   - Update `proj-knowledge.md` with new insights
   - Note important patterns discovered
   - Document component relationships

## Expected Outcome

- Clear understanding of project structure
- Component relationships mapped
- Key files and their purposes identified
- Architecture patterns documented
- Findings added to knowledge base

## Component Quick Reference

### Core Backend
- `main.py`: FastAPI application, routes, initialization
- `orchestrator.py`: Central coordinator, workflow execution
- `mcp_server.py`: Tool execution engine, security
- `ha_client.py`: Home Assistant WebSocket client
- `rag_manager.py`: RAG knowledge base management
- `approval_queue.py`: Human-in-the-loop approvals
- `workflow_graph.py`: LangGraph state machine

### Agents
- `base_agent.py`: Base class for all agents
- `heating_agent.py`: Climate heating control
- `cooling_agent.py`: Climate cooling control
- `lighting_agent.py`: Light and scene control
- `security_agent.py`: Security and access control
- `universal_agent.py`: Generic domain agent
- `architect_agent.py`: Agent creation and suggestions

### Providers
- `base.py`: Provider interface
- `local_provider.py`: Ollama integration
- `openai_provider.py`: OpenAI API integration

### Frontend
- `dashboard/`: React application
- `ai-visual-dashboard/`: AI-generated HTML dashboards

## Common Exploration Patterns

### Understanding a Feature
1. Find entry point (API endpoint or agent method)
2. Trace execution flow
3. Identify dependencies
4. Check tests for usage examples

### Finding Related Code
1. Search for imports/exports
2. Check test files for usage
3. Look for similar patterns
4. Review documentation

### Understanding Data Flow
1. Start at entry point (API/agent)
2. Follow function calls
3. Note state changes
4. Identify output destinations
