# Create New Agent

## Purpose
Creates a new autonomous AI agent for the Home Assistant AI Orchestrator with proper structure, skills file, and integration.

## Usage
`/create-agent [agent-name] [domain] [description]`

Example: `/create-agent energy-optimizer energy "Manages solar production and battery storage"`

## Instructions for Agent

When this command is invoked:

1. **Validate Input**:
   - Agent name should be kebab-case
   - Domain should be a valid HA domain (light, climate, switch, etc.)
   - Description should be clear and specific

2. **Create Agent Python File** in `ai-orchestrator/backend/agents/`:
   - Inherit from `base_agent.py`
   - Implement `gather_context()` method
   - Implement `decide()` method
   - Include proper error handling
   - Add docstrings and type hints

3. **Create SKILLS.md** in `ai-orchestrator/skills/[agent-name]/`:
   - Define agent purpose and role
   - List available tools and capabilities
   - Provide decision-making guidelines
   - Include example scenarios

4. **Update agents.yaml**:
   - Add new agent entry with proper configuration
   - Set reasonable decision interval
   - Configure relevant entity filters

5. **Create Tests**:
   - Add test file in `ai-orchestrator/backend/tests/`
   - Include smoke tests for initialization
   - Test context gathering
   - Test decision making logic

6. **Update Documentation**:
   - Add entry to README if significant
   - Document any new dependencies

## Expected Outcome
- New agent class file created
- Skills documentation in place
- Agent registered in configuration
- Basic tests created
- Agent ready to be deployed and tested

## Example Structure
```python
# [agent_name]_agent.py
from .base_agent import BaseAgent

class [AgentName]Agent(BaseAgent):
    """
    [Description]
    """
    
    async def gather_context(self) -> dict:
        """Gather relevant state information"""
        pass
    
    async def decide(self) -> list:
        """Make decisions based on context"""
        pass
```
