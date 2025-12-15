"""
Cooling Agent for A/C and fan control.
Maintains cooling comfort (22-25°C) while minimizing energy consumption.
"""
import logging
from typing import Dict, List
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CoolingAgent(BaseAgent):
    """
    Specialist agent for cooling climate control.
    Controls A/C units and fans for optimal comfort and efficiency.
    """
    
    def __init__(
        self,
        mcp_server,
        ha_client,
        cooling_entities: List[str],
        model_name: str = "mistral:7b-instruct",
        decision_interval: int = 120
    ):
        """
        Initialize Cooling Agent.
        
        Args:
            mcp_server: MCP server for tool execution
            ha_client: Home Assistant WebSocket client
            cooling_entities: List of climate entity IDs (A/C units)
            model_name: Ollama model name
            decision_interval: Seconds between decisions
        """
        super().__init__(
            agent_id="cooling",
            name="Cooling Agent",
            skills_path="/app/skills/cooling/SKILLS.md",
            mcp_server=mcp_server,
            ha_client=ha_client,
            model_name=model_name,
            decision_interval=decision_interval
        )
        
        self.cooling_entities = cooling_entities
        logger.info(f"Cooling Agent initialized with {len(cooling_entities)} entities")
    
    async def gather_context(self) -> Dict:
        """
        Gather cooling-specific context.
        
        Returns:
            Dict with climate states, temperature sensors, humidity, outdoor temp
        """
        context = {
            "timestamp": self._get_timestamp(),
            "climate_states": {},
            "sensors": {},
            "time_of_day": self._get_time_of_day()
        }
        
        # Get climate entity states  
        for entity_id in self.cooling_entities:
            try:
                state = await self.ha_client.get_climate_state(entity_id)
                context["climate_states"][entity_id] = state
            except Exception as e:
                logger.error(f"Error getting state for {entity_id}: {e}")
        
        # Get temperature/humidity sensors
        try:
            # These would be configured in SKILLS.md observable entities
            context["sensors"]["outdoor_temp"] = await self._get_sensor_state("sensor.outdoor_temp")
            context["sensors"]["humidity"] = await self._get_sensor_state("sensor.humidity")
        except Exception as e:
            logger.debug(f"Error getting sensors: {e}")
        
        return context
    
    async def decide(self, context: Dict) -> Dict:
        """
        Make cooling decisions based on context.
        
        Args:
            context: Current home state
            
        Returns:
            Dict with reasoning and list of actions
        """
        # Build prompt with SKILLS.md + context
        prompt = self._build_decision_prompt(context)
        
        # Call LLM
        response = await self._call_llm(prompt)
        
        # Parse response for actions
        decision = self._parse_llm_response(response)
        
        return decision
    
    def _build_decision_prompt(self, context: Dict) -> str:
        """Build prompt for LLM decision making"""
        return f"""
You are the Cooling Agent. Your goal is to maintain comfort (22-25°C) while minimizing energy.

SKILLS: {self.skills.get('identity', 'Cooling optimization')}

CURRENT CONTEXT:
{self._format_context(context)}

AVAILABLE TOOLS:
- set_temperature(entity_id, temperature, hvac_mode='cool')
- set_fan_speed(entity_id, speed)  # low/medium/high/auto
- get_climate_state(entity_id)

DECISION CRITERIA:
- Cool occupied spaces to 22-25°C
- Eco mode (27°C) when unoccupied >2h
- Pre-cool before hot periods
- Use fans when temp difference <3°C

Return JSON format:
{{
  "reasoning": "Your analysis",
  "actions": [
    {{"tool": "set_temperature", "parameters": {{"entity_id": "climate.living_room", "temperature": 24.0}}}}
  ]
}}

Return empty actions array if no changes needed.
"""
    
    async def _get_sensor_state(self, entity_id: str) -> float:
        """Get numeric sensor value"""
        try:
            state = await self.ha_client.get_states(entity_id)
            return float(state.get("state", 0))
        except:
            return 0.0
