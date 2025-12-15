"""
Security Agent for alarm, lock, and camera control.
Maintains security while minimizing false alarms.
"""
import logging
from typing import Dict, List
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """
    Specialist agent for security automation.
    Manages alarms, locks, and cameras with high-impact approval requirements.
    """
    
    def __init__(
        self,
        mcp_server,
        ha_client,
        security_entities: List[str],
        model_name: str = "mistral:7b-instruct",
        decision_interval: int = 180
    ):
        """
        Initialize Security Agent.
        
        Args:
            mcp_server: MCP server for tool execution
            ha_client: Home Assistant WebSocket client
            security_entities: List of alarm/lock entity IDs
            model_name: Ollama model (Mistral for reasoning)
            decision_interval: Seconds between checks (180s)
        """
        super().__init__(
            agent_id="security",
            name="Security Agent",
            skills_path="/app/skills/security/SKILLS.md",
            mcp_server=mcp_server,
            ha_client=ha_client,
            model_name=model_name,
            decision_interval=decision_interval
        )
        
        self.security_entities = security_entities
        logger.info(f"Security Agent initialized with {len(security_entities)} entities")
    
    async def gather_context(self) -> Dict:
        """Gather security context"""
        context = {
            "timestamp": self._get_timestamp(),
            "security_devices": {},
            "sensors": {},
            "time_of_day": self._get_time_of_day()
        }
        
        # Get security device states
        for entity_id in self.security_entities:
            try:
                state = await self.ha_client.get_states(entity_id)
                context["security_devices"][entity_id] = state
            except Exception as e:
                logger.error(f"Error getting {entity_id}: {e}")
        
        # Get sensors
        try:
            context["sensors"]["occupancy"] = await self._get_sensor_state("binary_sensor.home_occupied")
            context["sensors"]["door_open"] = await self._get_sensor_state("binary_sensor.front_door")
        except:
            pass
        
        return context
    
    async def decide(self, context: Dict) -> Dict:
        """Make security decisions - all high-impact actions flagged for approval"""
        prompt = self._build_decision_prompt(context)
        response = await self._call_llm(prompt)
        decision = self._parse_llm_response(response)
        
        # Flag security decisions as high-impact
        decision["impact_level"] = "high"
        
        return decision
    
    def _build_decision_prompt(self, context: Dict) -> str:
        """Build prompt for security decisions"""
        return f"""
You are the Security Agent. Maintain security while minimizing false alarms.

CURRENT CONTEXT:
{self._format_context(context)}

AVAILABLE TOOLS:
- set_alarm_state(entity_id, state)  # armed_home/armed_away/disarmed
- lock_door(entity_id)
- unlock_door(entity_id)  # REQUIRES APPROVAL
- enable_camera(entity_id, motion_detection=true)

DECISION CRITERIA:
- Arm system when all occupants away >30min
- Disarm when first occupant arrives
- Lock doors at night (11 PM)
- Alert on unexpected entry when armed

HIGH-IMPACT ACTIONS (require approval):
- Unlocking doors
- Disarming alarm
- Changing to less secure state

Return JSON with reasoning and actions.
"""
    
    async def _get_sensor_state(self, entity_id: str):
        """Get sensor state"""
        try:
            state = await self.ha_client.get_states(entity_id)
            return state.get("state")
        except:
            return None
