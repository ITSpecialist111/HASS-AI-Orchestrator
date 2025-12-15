"""
Heating Agent - Phase 1 MVP Implementation
Manages residential heating with comfort optimization and energy efficiency.
"""
import json
from typing import Dict, List
from datetime import datetime

from agents.base_agent import BaseAgent


class HeatingAgent(BaseAgent):
    """
    Heating Agent that controls climate entities for comfort and energy efficiency.
    """
    
    def __init__(
        self,
        mcp_server,
        ha_client,
        heating_entities: List[str],
        model_name: str = "mistral:7b-instruct",
        decision_interval: int = 120
    ):
        """
        Initialize Heating Agent.
        
        Args:
            mcp_server: MCP server for tool execution
            ha_client: Home Assistant WebSocket client
            heating_entities: List of climate entity IDs to control
            model_name: Ollama model name
            decision_interval: Seconds between decisions
        """
        super().__init__(
            agent_id="heating",
            name="Heating Agent",
            mcp_server=mcp_server,
            ha_client=ha_client,
            skills_path="/app/skills/heating/SKILLS.md",
            model_name=model_name,
            decision_interval=decision_interval
        )
        
        self.heating_entities = heating_entities
        print(f"✓ Heating Agent initialized with {len(heating_entities)} entities")
    
    async def gather_context(self) -> Dict:
        """
        Gather current heating context from Home Assistant.
        
        Returns:
            Context dict with climate states, sensors, and time info
        """
        context = {
            "timestamp": datetime.now().isoformat(),
            "climate_states": {},
            "sensors": {},
            "time_of_day": self._get_time_of_day()
        }
        
        # Get climate entity states
        for entity_id in self.heating_entities:
            try:
                state = await self.ha_client.get_climate_state(entity_id)
                context["climate_states"][entity_id] = state
            except Exception as e:
                print(f"⚠️ Failed to get state for {entity_id}: {e}")
                context["climate_states"][entity_id] = {"error": str(e)}
        
        # Get observable sensors (if configured in SKILLS.md)
        observable_entities = self.skills.get("observable_entities", [])
        for entity_id in observable_entities:
            try:
                state = await self.ha_client.get_states(entity_id)
                context["sensors"][entity_id] = {
                    "state": state.get("state"),
                    "attributes": state.get("attributes", {})
                }
            except Exception as e:
                print(f"⚠️ Failed to get observable state for {entity_id}: {e}")
        
        return context
    
    def _get_time_of_day(self) -> str:
        """Get time of day category for decision making"""
        hour = datetime.now().hour
        
        if 6 <= hour < 9:
            return "morning"
        elif 9 <= hour < 17:
            return "day"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    async def decide(self, context: Dict) -> Dict:
        """
        Make heating decision based on current context.
        
        Args:
            context: Current context from gather_context()
        
        Returns:
            Decision dict with reasoning and actions
        """
        # Build prompt for LLM
        prompt = self._build_decision_prompt(context)
        
        # Call LLM
        response = await self._call_llm(prompt, temperature=0.3)
        
        # Parse response
        try:
            decision = self._parse_llm_response(response)
            return decision
        except Exception as e:
            print(f"⚠️ Failed to parse LLM response: {e}")
            print(f"Response was: {response}")
            return {
                "reasoning": f"Failed to parse LLM response: {e}",
                "actions": []
            }
    
    def _build_decision_prompt(self, context: Dict) -> str:
        """Build prompt for heating decision"""
        # Get system prompt from skills
        system_prompt = self._build_system_prompt()
        
        # Format current context
        context_str = f"""
Current Time: {context['timestamp']}
Time of Day: {context['time_of_day']}

Climate States:
{json.dumps(context['climate_states'], indent=2)}

Observable Sensors:
{json.dumps(context['sensors'], indent=2)}
"""
        
        # Get available tools
        tools_schema = self.mcp_server.get_tool_schemas()
        tools_str = json.dumps(tools_schema, indent=2)
        
        prompt = f"""{system_prompt}

CURRENT CONTEXT:
{context_str}

AVAILABLE TOOLS:
{tools_str}

Based on the current context and your decision criteria, what action should you take?
Respond with a JSON object containing your reasoning and actions.
"""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse LLM response into structured decision.
        
        Args:
            response: Raw LLM response text
        
        Returns:
            Structured decision dict
        """
        # Try to extract JSON from response
        # LLMs sometimes wrap JSON in markdown code blocks
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first and last lines (```)
            response = "\n".join(lines[1:-1])
            # Remove language identifier if present
            if response.startswith("json"):
                response = response[4:].strip()
        
        # Parse JSON
        try:
            decision = json.loads(response)
            
            # Validate structure
            if "reasoning" not in decision:
                decision["reasoning"] = "No reasoning provided"
            if "actions" not in decision:
                decision["actions"] = []
            
            return decision
        
        except json.JSONDecodeError as e:
            # Fallback: create a no-action decision
            return {
                "reasoning": f"Failed to parse JSON response: {e}. Raw response: {response[:200]}",
                "actions": []
            }
    
    async def run_decision_loop(self):
        """Override to add dashboard broadcasting"""
        self.status = "idle"
        print(f"✓ {self.name} decision loop started (interval: {self.decision_interval}s)")
        
        # Import dynamically to avoid circular import
        from main import broadcast_to_dashboard
        
        while True:
            try:
                await asyncio.sleep(self.decision_interval)
                
                self.status = "deciding"
                
                # Broadcast status update
                try:
                    await broadcast_to_dashboard({
                        "type": "agent_status",
                        "data": {
                            "agent_id": self.agent_id,
                            "status": "deciding"
                        }
                    })
                except:
                    pass
                
                # Make decision
                context = await self.gather_context()
                decision = await self.decide(context)
                
                # Execute decision
                results = await self.execute(decision)
                
                # Log decision
                self.log_decision(context, decision, results)
                
                # Broadcast decision to dashboard
                try:
                    await broadcast_to_dashboard({
                        "type": "decision",
                        "data": {
                            "agent_id": self.agent_id,
                            "timestamp": datetime.now().isoformat(),
                            "reasoning": decision.get("reasoning", ""),
                            "actions": decision.get("actions", []),
                            "results": results
                        }
                    })
                except:
                    pass
                
                self.status = "idle"
                print(f"✓ {self.name} decision completed: {len(decision.get('actions', []))} actions")
            
            except Exception as e:
                self.status = "error"
                print(f"❌ {self.name} decision loop error: {e}")
                await asyncio.sleep(10)  # Back off on error
