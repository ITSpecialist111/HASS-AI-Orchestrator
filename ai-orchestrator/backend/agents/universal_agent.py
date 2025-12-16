from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from .base_agent import BaseAgent
from mcp_server import MCPServer
from ha_client import HAWebSocketClient

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
            skills_path="UNIVERSAL_AGENT", 
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
            # Dynamic mode: fetch all relevant entities to let LLM decide
            try:
                all_states = await self.ha_client.get_states()
                relevant_domains = ["climate", "light", "switch", "sensor", "binary_sensor", "lock", "cover"]
                
                # Filter and take first 50 to avoid token limit
                filtered = [
                    s for s in all_states 
                    if s['entity_id'].split('.')[0] in relevant_domains
                ][:50]
                
                states.append("Dynamic Entity Discovery (Top 50 relevant):")
                for s in filtered:
                    eid = s['entity_id']
                    friendly = s.get('attributes', {}).get('friendly_name', eid)
                    val = s['state']
                    states.append(f"- {friendly} ({eid}): {val}")
                    
                return "\n".join(states)
            except Exception as e:
                return f"Error discovering entities: {e}"

        for entity_id in self.entities:
            try:
                state = await self.ha_client.get_states(entity_id)
                if state:
                    attrs = state.get("attributes", {})
                    friendly_name = attrs.get("friendly_name", entity_id)
                    val = state.get("state", "unknown")
                    states.append(f"- {friendly_name} ({entity_id}): {val}")
                else:
                    states.append(f"- {entity_id}: unknown")
            except Exception as e:
                states.append(f"- {entity_id}: unavailable ({str(e)})")
                
        return "\n".join(states)

    async def gather_context(self) -> Dict:
        """
        Gather current context for universal agent.
        Uses _get_state_description helper.
        """
        state_desc = await self._get_state_description()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "state_description": state_desc,
            "instruction": self.instruction
        }

    async def decide(self, context: Dict) -> Dict:
        """
        Make decision based on instruction and current state.
        """
        # Build prompt
        state_desc = context.get("state_description", "No state data")
        
        prompt = f"""
{self._load_skills()}

CURRENT SITUATION:
Time: {context['timestamp']}

ENTITY STATES:
{state_desc}

Based on your PRIMARY INSTRUCTION and the CURRENT SITUATION, determine if any action is needed.
Respond with a JSON object containing 'reasoning' and 'actions'.
Each action MUST have a 'tool' field (e.g. "call_ha_service") and 'parameters'.
"""
        # Call LLM
        response = await self._call_llm(prompt)
        
        # Parse response (reuse basic parsing logic if available, or simple json load)
        try:
            # Simple cleanup for markdown
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("\n", 1)[1]
                if clean_response.endswith("```"):
                    clean_response = clean_response.rsplit("\n", 1)[0]
            if clean_response.startswith("json"):
                clean_response = clean_response[4:]
            
            data = json.loads(clean_response)
            
            # Validate actions structure
            valid_actions = []
            if "actions" in data and isinstance(data["actions"], list):
                for action in data["actions"]:
                    if "tool" in action:
                        valid_actions.append(action)
                    elif "service" in action: # Handle common hallucination
                        valid_actions.append({
                            "tool": "call_ha_service",
                            "parameters": action
                        })
            
            data["actions"] = valid_actions
            return data
            
        except Exception as e:
            return {
                "reasoning": f"Failed to parse LLM response: {e}",
                "actions": []
            }

