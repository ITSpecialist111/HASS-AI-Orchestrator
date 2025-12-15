from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent
from ..mcp_server import MCPServer
from ..ha_client import HAWebSocketClient

class UniversalAgent(BaseAgent):
    """
    A universal agent that operates based on natural language instructions
    and a dynamic list of entities, rather than hardcoded logic.
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        instruction: str,
        mcp_server: MCPServer,
        ha_client: HAWebSocketClient,
        entities: List[str],
        rag_manager: Optional[Any] = None,
        model_name: str = "mistral:7b-instruct",
        decision_interval: int = 120
    ):
        # Universal agents don't use a fixed skills_path
        # We pass a dummy path or None, and override _load_skills
        super().__init__(
            agent_id=agent_id,
            name=name,
            mcp_server=mcp_server,
            ha_client=ha_client,
            skills_path=None, 
            rag_manager=rag_manager,
            model_name=model_name,
            decision_interval=decision_interval
        )
        self.instruction = instruction
        self.entities = entities

    def _load_skills(self) -> str:
        """
        Override: Load skills from the instruction string provided in config
        instead of a markdown file.
        """
        prompt = f"""
# AGENT ROLE: {self.name}
# TARGET ENTITIES: {', '.join(self.entities) if self.entities else 'Dynamic/All'}

# PRIMARY INSTRUCTION
{self.instruction}

# CAPABILITIES
You have access to Home Assistant services via the 'call_ha_service' tool.
You can control ANY entity in your target list.
        """
        return prompt

    async def _get_state_description(self) -> str:
        """
        Get state of assigned entities.
        """
        states = []
        if not self.entities:
            return "No specific entities assigned. Monitor global state if needed."
            
        for entity_id in self.entities:
            state = await self.ha_client.get_state(entity_id)
            if state:
                attrs = state.get("attributes", {})
                friendly_name = attrs.get("friendly_name", entity_id)
                val = state.get("state", "unknown")
                # Format specific attributes for context if needed
                states.append(f"- {friendly_name} ({entity_id}): {val}")
            else:
                states.append(f"- {entity_id}: unknown")
                
        return "\n".join(states)
