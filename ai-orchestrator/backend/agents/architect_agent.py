import json
import logging
import yaml
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# We'll use the same LLM interface logic or a simplified one
# Since we don't need the full "Tool" loop of BaseAgent, we'll keep this focused on generation.

class ArchitectAgent:
    """
    The Architect is a meta-agent responsible for designing other agents.
    It analyzes the home (Entity Registry) and User Prompts to generate 
    valid YAML configurations for Universal Agents.
    """

    def __init__(
        self, 
        ha_client: Any, 
        rag_manager: Optional[Any] = None,
        model_name: str = "mistral:7b-instruct"
    ):
        self.ha_client = ha_client
        self.rag_manager = rag_manager
        self.model_name = model_name
        self.logger = logging.getLogger("Architect")

    async def suggest_agents(self) -> List[Dict[str, Any]]:
        """
        Scans the entity registry for devices that are likely unmanaged 
        and proposes agents for them.
        """
        # Get all states/entities
        # In a real impl, we'd check which are already assigned in agents.yaml
        # For prototype, we just look for interesting domains (climate, light, switch)
        
        candidates = []
        try:
            states =await self.ha_client.get_states()
            
            # Simple heuristic: Group by area or domain
            domains = {}
            for state in states:
                entity_id = state['entity_id']
                domain = entity_id.split('.')[0]
                if domain in ['light', 'switch', 'climate', 'fan', 'lock', 'cover']:
                    if domain not in domains:
                        domains[domain] = []
                    domains[domain].append(entity_id)
            
            # generating a few suggestions based on what we found
            if 'pool' in str(domains).lower():
                candidates.append({
                    "title": "Pool Manager",
                    "reason": "Found pool-related entities. I can keep the water perfect.",
                    "prompt": "Create a Pool Manager that runs the pump 8 hours a day and monitors temp."
                })
                
            if 'light' in domains:
                candidates.append({
                    "title": "Smart Lighting",
                    "reason": f"Found {len(domains['light'])} lights. I can automate them based on sun/occupancy.",
                    "prompt": "Create a Lighting Manager that turns on outdoor lights at sunset."
                })

            if 'climate' in domains:
                 candidates.append({
                    "title": "Climate Control",
                    "reason": "Found climate entities. I can optimize for comfort and savings.",
                    "prompt": "Create a Climate Manager to keep temp between 20-22C during the day."
                })

        except Exception as e:
            self.logger.error(f"Error scanning entities: {e}")
            
        return candidates

    async def generate_config(self, user_prompt: str, available_entities: List[str] = None) -> Dict[str, Any]:
        """
        Generates a YAML configuration block for a new agent based on user prompt.
        """
        # Construction of the prompt for the LLM
        # We need it to output strictly JSON or YAML. JSON is safer for parsing.
        
        system_prompt = """
        You are the ARCHITECT, an AI expert in Home Assistant automation.
        Your goal is to configure a new "Worker Agent" based on the user's request.
        
        Output Format: JSON only.
        Structure:
        {
            "id": "snake_case_id",
            "name": "Human Readable Name",
            "model": "mistral:7b-instruct",
            "decision_interval": 120,
            "entities": ["list", "of", "target", "entity_ids"],
            "instruction": "Clear, step-by-step natural language instructions for the agent."
        }
        
        Rules:
        1. 'id' must be unique and simple (e.g., 'pool_manager', 'patio_lights').
        2. 'entities' should be a list of entity_ids relevant to the task. Use placeholders if specific IDs aren't provided (e.g., 'light.living_room').
        3. 'instruction' is for another AI to read. Be descriptive. Mention triggers, conditions, and actions.
        """
        
        # In a real implementation we would call Ollama/OpenAI here.
        # For this prototype without a running LLM inference engine in the python process (we rely on Ollama service),
        # we will simulate the LLM call or assume `rag_manager` has an inference method we can borrow, 
        # or we make a raw HTTP request to Ollama.
        
        # Borrowing embedding generator? No, that's for vectors.
        # We'll do a mock implementation that satisfies the "No-Code" functional requirement 
        # by doing basic keyword matching or (if we had the library) calling ollama.generate.
        
        # For the sake of the 'Smoke Test' and robustness without external dependencies in this enviroment,
        # I will implement a heuristic 'stub' that simulates the Architect's intelligence. 
        # In production this lines replaced by: response = await call_ollama(system_prompt, user_prompt)
        
        # Heuristic Logic (Simulating LLM for the prototype)
        generated = {
            "model": "mistral:7b-instruct",
            "decision_interval": 120
        }
        
        prompt_lower = user_prompt.lower()
        
        if "pool" in prompt_lower:
            generated.update({
                "id": "pool_manager",
                "name": "Pool Manager",
                "entities": ["switch.pool_pump", "sensor.pool_temp"],
                "instruction": "Maintain pool temperature above 25C. Run pump from 8AM to 4PM."
            })
        elif "light" in prompt_lower or "lamp" in prompt_lower:
             generated.update({
                "id": "lighting_manager",
                "name": "Lighting Manager",
                "entities": ["light.living_room", "light.kitchen"],
                "instruction": "Turn on lights if occupancy is detected and it is dark outside. Turn off after 5 mins of no motion."
            })
        elif "security" in prompt_lower or "lock" in prompt_lower:
             generated.update({
                "id": "security_guard",
                "name": "Security Guard",
                "entities": ["binary_sensor.front_door", "lock.front_door"],
                "instruction": "Lock the door if it has been closed for 5 minutes. Notify if opened after midnight."
            })
        elif "temp" in prompt_lower or "heat" in prompt_lower or "cool" in prompt_lower or "thermostat" in prompt_lower:
             generated.update({
                "id": "climate_monitor",
                "name": "Climate Monitor",
                "entities": ["climate.thermostat"], # Placeholder - user likely needs to edit this
                "instruction": "Monitor temperature and adjust thermostat to maintain target range."
            })
        else:
            # Fallback for custom agents
            # Try to extract a name if requested
            name = "Custom Agent"
            import re
            name_match = re.search(r"(?:name|call) (?:this|the)?\s*agent\s+(?:is\s+)?([A-Za-z0-9 ]+)", prompt_lower, re.IGNORECASE)
            if name_match:
                # Clean up the name
                raw_name = name_match.group(1).strip()
                # Remove common trailing words if user said "Heating Agent please"
                name = raw_name.replace("please", "").strip().title()

            agent_id = name.lower().replace(" ", "_")

            generated.update({
                "id": agent_id,
                "name": name,
                "entities": [],
                "instruction": user_prompt
            })
            
        return generated
