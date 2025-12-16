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
        Scans the entity registry for devices, groups them by potential area/function,
        and generates ready-to-use agent blueprints.
        """
        candidates = []
        try:
            states = await self.ha_client.get_states()
            
            # 1. Filter for controllable/interesting entities
            # We focus on actuators. Sensors are secondary (supportive).
            interesting_domains = ['light', 'switch', 'cover', 'climate', 'media_player', 'lock', 'fan', 'vacuum']
            sensor_domains = ['binary_sensor', 'sensor']
            
            controllables = []
            all_entities = []
            
            for state in states:
                eid = state['entity_id']
                domain = eid.split('.')[0]
                all_entities.append(eid)
                if domain in interesting_domains:
                    controllables.append(eid)

            # 2. Tokenize and Cluster
            # We look for common substrings in controllable entities to identify "Areas" or "Systems"
            # e.g. light.kitchen_main, switch.kitchen_fan -> "kitchen"
            
            stopwords = set([
                'light', 'switch', 'sensor', 'cover', 'media', 'player', 'main', 'ceiling', 
                'floor', 'table', 'wall', 'strip', 'bulb', 'plug', 'socket', 'power', 'energy', 
                'state', 'battery', 'link', 'quality', 'status', 'update', 'group', 'device', 
                'monitor', 'control', 'fan', 'lock', 'door', 'window', 'motion', 'occupancy'
            ])
            
            token_map = {} # token -> list of proper entity_ids
            
            for eid in controllables:
                # Remove domain
                name_part = eid.split('.')[1]
                # Split by underscore
                tokens = name_part.split('_')
                
                for token in tokens:
                    if len(token) < 3 or token in stopwords:
                        continue
                    # Check if token is digits only (e.g. light_1)
                    if token.isdigit():
                        continue
                        
                    if token not in token_map:
                        token_map[token] = []
                    token_map[token].append(eid)

            # 3. Generate Candidates from Clusters
            # Threshold: A token must appear in at least 2 distinct controllable entities to be a "Group"
            # Limit to top results
            
            # Sort tokens by count
            sorted_tokens = sorted(token_map.items(), key=lambda item: len(item[1]), reverse=True)
            
            # Limit global suggestions
            for token, eids in sorted_tokens[:15]:
                if len(eids) < 2: 
                    continue
                
                # Check if we have sensors for this token too?
                # e.g. binary_sensor.kitchen_motion
                related_sensors = [e for e in all_entities if token in e and e.startswith(('binary_sensor', 'sensor'))]
                
                # Create Blueprint
                group_name = token.title()
                
                # Heuristic Instruction
                instruction = f"Manage the {group_name} area. "
                if any('light' in e for e in eids):
                    if any('motion' in s for s in related_sensors) or any('occupancy' in s for s in related_sensors):
                        instruction += "Turn on lights when motion is detected and turn off when clear. "
                    else:
                        instruction += "Automate lighting based on time of day. "
                if any('climate' in e for e in eids):
                    instruction += "Monitor climate and optimize temperature. "
                if any('lock' in e for e in eids):
                    instruction += "Ensure doors are locked at night. "

                # Construct Config
                blueprint = {
                    "id": f"{token}_manager",
                    "name": f"{group_name} Manager",
                    "model": self.model_name,
                    "decision_interval": 120,
                    "entities": eids + related_sensors[:3], # Add up to 3 sensors
                    "instruction": instruction.strip()
                }
                
                candidates.append({
                    "title": f"{group_name} Manager",
                    "reason": f"Found {len(eids)} devices matching '{token}' (e.g., {eids[0]})",
                    "blueprint": blueprint 
                })

            # 4. Domain-Specific Fallbacks (if no strong clusters found or just good to have)
            # Climate is always good
            climate_entities = [e for e in controllables if e.startswith('climate.')]
            if climate_entities and not any(c['blueprint']['id'] == 'climate_control' for c in candidates):
                candidates.append({
                    "title": "Central Climate Control",
                    "reason": f"Found {len(climate_entities)} thermostats.",
                    "blueprint": {
                        "id": "climate_control",
                        "name": "Climate Control",
                        "model": self.model_name,
                        "decision_interval": 300,
                        "entities": climate_entities,
                        "instruction": "Maintain comfortable indoor temperatures. Adjust based on time of day to save energy."
                    }
                })

            # 5. Security Fallback
            lock_entities = [e for e in controllables if e.startswith('lock.')]
            contact_sensors = [e for e in all_entities if 'door' in e and e.startswith('binary_sensor')]
            if (lock_entities or contact_sensors) and not any('security' in c['blueprint']['id'] for c in candidates):
                 candidates.append({
                    "title": "Home Security",
                    "reason": "Found locks or door sensors.",
                    "blueprint": {
                        "id": "home_security",
                        "name": "Home Security",
                        "model": self.model_name,
                        "decision_interval": 60,
                        "entities": lock_entities + contact_sensors,
                        "instruction": "Monitor perimeter. Lock doors if unlocked for 15 minutes. Alert if intrusion detected."
                    }
                })

        except Exception as e:
            self.logger.error(f"Error scanning entities: {e}")
            
        # Cap at 20
        return candidates[:20]

    async def generate_config(self, user_prompt: str, available_entities: List[str] = None) -> Dict[str, Any]:
        """
        Generates a YAML configuration block based on user prompt (Legacy/Manual flow).
        """
        # ... logic for manual prompt generation ...
        # Simplified for brevity since main Logic is above now, but keeping existing heuristic for manual entry
        
        generated = {
            "model": "mistral:7b-instruct",
            "decision_interval": 120
        }
        
        prompt_lower = user_prompt.lower()
        
        # [Existing heuristic logic simplified/preserved]
        # We can actually fallback to the smart logic if the prompt matches a token!
        # But for now, stick to the robust mock.
        
        if "pool" in prompt_lower:
            generated.update({
                "id": "pool_manager",
                "name": "Pool Manager",
                "entities": ["switch.pool_pump", "sensor.pool_temp"],
                "instruction": "Maintain pool temperature above 25C. Run pump from 8AM to 4PM."
            })
        elif "light" in prompt_lower:
             generated.update({
                "id": "lighting_manager",
                "name": "Lighting Manager",
                "entities": ["light.living_room"], # Mock
                "instruction": "Turn on lights if occupancy is detected."
            })
        else:
            # Generic fallback
            name="Custom Agent"
            import re
            match = re.search(r"(?:name|call)\s+(?:is\s+)?([A-Za-z0-9 ]+)", prompt_lower)
            if match:
                 name = match.group(1).title()
            
            generated.update({
                "id": name.lower().replace(" ", "_"),
                "name": name,
                "entities": [],
                "instruction": user_prompt
            })
            
        return generated
