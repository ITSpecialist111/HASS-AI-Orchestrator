"""
Lighting Agent for smart lighting control.
Optimizes lighting for comfort, security, and energy efficiency.
"""
import logging
from typing import Dict, List
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class LightingAgent(BaseAgent):
    """
    Specialist agent for lighting automation.
    Controls lights with circadian rhythm, occupancy detection, and security patterns.
    """
    
    def __init__(
        self,
        mcp_server,
        ha_client,
        lighting_entities: List[str],
        model_name: str = "phi3.5:3.8b",
        decision_interval: int = 60
    ):
        """
        Initialize Lighting Agent.
        
        Args:
            mcp_server: MCP server for tool execution
            ha_client: Home Assistant WebSocket client
            lighting_entities: List of light entity IDs
            model_name: Ollama model (phi3.5 for fast decisions)
            decision_interval: Seconds between decisions (60s for lighting)
        """
        super().__init__(
            agent_id="lighting",
            name="Lighting Agent",
            skills_path="/app/skills/lighting/SKILLS.md",
            mcp_server=mcp_server,
            ha_client=ha_client,
            model_name=model_name,
            decision_interval=decision_interval
        )
        
        self.lighting_entities = lighting_entities
        logger.info(f"Lighting Agent initialized with {len(lighting_entities)} entities")
    
    async def gather_context(self) -> Dict:
        """Gather lighting-specific context"""
        context = {
            "timestamp": self._get_timestamp(),
            "lights": {},
            "sensors": {},
            "time_of_day": self._get_time_of_day(),
            "circadian_phase": self._get_circadian_phase()
        }
        
        # Get light states
        for entity_id in self.lighting_entities:
            try:
                state = await self.ha_client.get_states(entity_id)
                context["lights"][entity_id] = state
            except Exception as e:
                logger.error(f"Error getting {entity_id}: {e}")
        
        # Get occupancy and ambient light
        try:
            context["sensors"]["occupancy"] = await self._get_sensor_state("binary_sensor.home_occupied")
            context["sensors"]["ambient_light"] = await self._get_sensor_state("sensor.ambient_light_lux")
        except:
            pass
        
        return context
    
    async def decide(self, context: Dict) -> Dict:
        """Make lighting decisions based on context"""
        prompt = self._build_decision_prompt(context)
        response = await self._call_llm(prompt)
        decision = self._parse_llm_response(response)
        return decision
    
    def _get_circadian_phase(self) -> str:
        """Get circadian rhythm phase (warm/neutral/cool)"""
        hour = datetime.now().hour
        if 6 <= hour < 10:
            return "cool"  # Morning: 5000-6500K
        elif 10 <= hour < 17:
            return "neutral"  # Day: 4000-5000K
        else:
            return "warm"  # Evening/Night: 2700-3500K
    
    def _build_decision_prompt(self, context: Dict) -> str:
        """Build prompt for lighting decisions"""
        return f"""
You are the Lighting Agent. Optimize lighting for comfort, security, and energy.

CURRENT CONTEXT:
{self._format_context(context)}

AVAILABLE TOOLS:
- turn_on_light(entity_id, brightness=100, color_temp=None)
- turn_off_light(entity_id)
- set_brightness(entity_id, brightness)
- set_color_temp(entity_id, kelvin)

DECISION CRITERIA:
- Auto-on when occupied + dark (<50 lux)
- Circadian rhythm: warm (2700K) evening, cool (6500K) morning
- Security lighting when away
- Gradual dimming before bedtime

Return JSON with reasoning and actions. Empty actions if no changes needed.
"""
    
    async def _get_sensor_state(self, entity_id: str):
        """Get sensor state"""
        try:
            state = await self.ha_client.get_states(entity_id)
            return state.get("state")
        except:
            return None
