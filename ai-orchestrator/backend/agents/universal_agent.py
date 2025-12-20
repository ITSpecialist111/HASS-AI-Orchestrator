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
        decision_interval: int = 120,
        broadcast_func: Optional[Any] = None,
        knowledge: str = ""
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
            decision_interval=decision_interval,
            broadcast_func=broadcast_func
        )
        self.instruction = instruction
        self.entities = entities
        self.knowledge = knowledge

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

# KNOWLEDGE / CONTEXT
{self.knowledge if self.knowledge else "No additional context provided."}

# CAPABILITIES & SAFETY
1. You have access to Home Assistant services via the 'call_ha_service' tool.
2. ACCESS RESTRICTIONS: You CANNOT access 'shell_command', 'hassio', 'script', or 'automation' domains.
3. APPROVAL REQUIRED: High-impact actions (e.g., unlocking doors, disarming alarms) will be queued for human approval.
4. VALIDATION: Generic service calls (e.g. set_temperature) must still adhere to safety limits (10-30°C).
        """
        return prompt

    async def _get_state_description(self) -> str:
        """
        Get state of assigned entities.
        """
        states = []
        if not self.entities:
            # Dynamic mode: find relevant entities
            try:
                # 1. Try Semantic Search if RAG is available
                if self.rag_manager:
                    try:
                        print(f"🔍 Performing semantic entity search for instruction: '{self.instruction}'")
                        
                        # run_in_executor to prevent blocking the event loop (which kills HA connection)
                        import asyncio
                        loop = asyncio.get_running_loop()
                        
                        # Define wrapper for sync RAG call
                        def _run_rag():
                            return self.rag_manager.query(
                                query_text=self.instruction,
                                collection_names=["entity_registry"],
                                n_results=10
                            )
                        
                        # Execute in thread pool
                        rag_results = await loop.run_in_executor(None, _run_rag)
                        
                        if rag_results:
                            found_entities = []
                            for res in rag_results:
                                # Parse entity_id from content or metadata
                                # Content format usually: "Entity: light.foo (Friendly Name) - Domain: light..."
                                content = res.get("content", "")
                                
                                # Ignore if content looks like an error message
                                if "nomic-embed-text" in content or "error" in content.lower():
                                    print(f"⚠️ RAG Result contained error pattern, ignoring: {content}")
                                    continue

                                # Simple extraction heuristic: look for domain.name pattern in content
                                import re
                                match = re.search(r"Entity: ([a-z0-9_]+\.[a-z0-9_]+)", content)
                                if match:
                                    found_entities.append(match.group(1))
                            
                            if found_entities:
                                self.entities = found_entities # Cache them for this run? Or keep dynamic?
                                # Keeping it dynamic is better for changing conditions, but let's use them now
                                states.append(f"Semantic Entity Discovery (Instruction-based):")
                                for eid in found_entities:
                                    try:
                                        s = await self.ha_client.get_states(eid)
                                        if s:
                                            friendly = s.get('attributes', {}).get('friendly_name', eid)
                                            states.append(f"- {friendly} ({eid}): {s['state']}")
                                    except:
                                        pass
                                
                                # If we found good semantic matches, return early + some globals
                                # Add time/sun context
                                states.append(f"- Time: {datetime.now().strftime('%H:%M')}")
                                return "\n".join(states)
                                
                    except Exception as rag_err:
                        print(f"⚠️ Semantic Search Failed (Falling back to heuristic): {rag_err}")
                        # Fall through to heuristic...

                # 2. Fallback to Heuristic Discovery (if RAG failed or found nothing)
                all_states = await self.ha_client.get_states()
                
                # Prioritize controllable domains
                control_domains = ["climate", "light", "switch", "lock", "cover"]
                sensor_domains = ["sensor", "binary_sensor"]
                
                sorted_states = sorted(
                    all_states,
                    key=lambda x: (
                        0 if x['entity_id'].split('.')[0] in control_domains else 1,
                        x['entity_id']
                    )
                )

                # Filter and take first 50
                filtered = [
                    s for s in sorted_states
                    if s['entity_id'].split('.')[0] in (control_domains + sensor_domains)
                ][:50]
                
                states.append("Dynamic Entity Discovery (Fallback Heuristic):")
                for s in filtered:
                    eid = s['entity_id']
                    friendly = s.get('attributes', {}).get('friendly_name', eid)
                    val = s['state']
                    states.append(f"- {friendly} ({eid}): {val}")
                    
                return "\n".join(states)
            except Exception as e:
                # If everything fails (including HA client), return empty to avoid breaking the agent completely
                # but log the specific error
                print(f"❌ Entity Discovery Fatal Error: {e}")
                return "Error: Could not discover entities. Please check Home Assistant connection."

        # ... (rest of method unchanged)

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
        # 1. Discover relevant services based on entities
        relevant_services_text = ""
        try:
            if self.entities:
                # Extract unique domains
                domains = set([e.split('.')[0] for e in self.entities])
                
                # Fetch all services
                all_services = await self.ha_client.get_services()
                
                # Filter for our domains
                found_services = []
                for domain in domains:
                    if domain in all_services:
                        services = all_services[domain]
                        # Just list service names, maybe descriptions if brief
                        # To save token space, just list names: "climate.set_temperature, climate.turn_on"
                        s_names = list(services.keys())
                        found_services.append(f"- {domain}: {', '.join(s_names)}")
                
                if found_services:
                    relevant_services_text = "\nAVAILABLE HA SERVICES (Use these EXACT names):\n" + "\n".join(found_services)
        except Exception as e:
            print(f"⚠️ Failed to fetch services: {e}")

        # Build prompt
        state_desc = context.get("state_description", "No state data")
        
        prompt = f"""
{self._load_skills()}

CURRENT SITUATION:
Time: {context['timestamp']}

ENTITY STATES:
{state_desc}

{relevant_services_text}

CRITICAL RULES:
1. You MUST ONLY use entity IDs listed in 'ENTITY STATES'. Do NOT guess or hallucinate IDs.
2. If the entity you need is not listed, use the 'log' tool to report "Entity X not found".
3. Use 'call_ha_service' only for generic services. For climate/lights, prefer specialized tools like 'set_temperature' if available.
4. Respond with VALID STANDARD JSON only. NO COMMENTS (// or /*) allowed inside the JSON.
5. Do not add markdown blocks.

TOOL USAGE EXAMPLES:
- Correct (Specific): {{"tool": "set_temperature", "parameters": {{"entity_id": "climate.ethan", "temperature": 21.0}}}}
- Correct (Generic): {{"tool": "call_ha_service", "parameters": {{"domain": "light", "service": "turn_on", "entity_id": "light.living_room", "service_data": {{"brightness_pct": 50}}}}}}
- Incorrect (Wrong Tool): {{"tool": "call_ha_service", "parameters": {{"entity_id": "climate.ethan", "service": "set_target_temp", "new_temperature": 10}}}} -> There is NO 'set_target_temp' service. Use 'set_temperature' tool.
- Incorrect (Missing Domain): {{"tool": "call_ha_service", "parameters": {{"service": "turn_on", "entity_id": "light.foo"}}}} -> missing "domain": "light"

Based on your PRIMARY INSTRUCTION and the CURRENT SITUATION, determine if any action is needed.
Respond with a JSON object containing 'reasoning' and 'actions'.
Each action MUST have a 'tool' field (e.g. "set_temperature") and 'parameters'.
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
            
            # Helper to try fixing common JSON errors (comments, trailing commas)
            def loose_json_parse(text):
                import re
                # 1. Strip C-style comments (// and /* */)
                # Remove // comments
                text = re.sub(r'//.*', '', text)
                # Remove /* */ comments
                text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
                
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    # 2. Try removing trailing commas
                    text = re.sub(r',\s*}', '}', text)
                    text = re.sub(r',\s*]', ']', text)
                    return json.loads(text)
            
            data = loose_json_parse(clean_response)
            
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
            print(f"❌ JSON Parse Error on '{response}': {e}") # Log full response for debug
            return {
                "reasoning": f"Failed to parse LLM response: {e}. Raw response logged.",
                "actions": []
            }

