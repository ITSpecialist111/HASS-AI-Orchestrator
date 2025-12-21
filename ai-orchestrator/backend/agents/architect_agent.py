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
        self._ha_provider = ha_client
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

    async def discover_entities_from_instruction(self, instruction: str) -> List[str]:
        """
        Analyzes the natural language instruction and finds relevant entities 
        from the Home Assistant registry (Anti-Hallucination).
        """
        try:
            states = await self.ha_client.get_states()
            all_ids = [s['entity_id'] for s in states]
            
            # 1. Extract Keywords from Instruction
            stopwords = {'the', 'and', 'or', 'if', 'when', 'then', 'is', 'to', 'in', 'on', 'off', 'for', 'a', 'an', 'at', 'my', 'me', 'please', 'turn', 'switch', 'set', 'check', 'monitor', 'control', 'manage', 'automate'}
            
            # Simple tokenization
            import re
            tokens = set(re.findall(r'\b[a-z]{3,}\b', instruction.lower()))
            keywords = tokens - stopwords
            
            if not keywords:
                return []
                
            matched_entities = set()
            
            # 2. Score Entities
            # We look for entity_ids that contain the keywords
            # e.g. "kitchen" -> light.kitchen_main, binary_sensor.kitchen_motion
            
            for eid in all_ids:
                eid_lower = eid.lower()
                # Check for exact token matches in the entity_id string
                # count matches
                matches = sum(1 for k in keywords if k in eid_lower)
                
                if matches > 0:
                    matched_entities.add(eid)
                    
            # 3. Refine / Filter
            # If we matched too many (e.g. "light" matches all lights), we might need to be stricter?
            # But the user might WANT "turn off all lights".
            # So basic keyword matching is actually safer than over-filtering.
            # However, limit to reasonable count to avoid context overflow? 
            # 20 seems safe for now.
            
            result = list(matched_entities)
            # Prioritize actuators (domains we can control) vs sensors
            actuators = [e for e in result if e.split('.')[0] in ['light', 'switch', 'climate', 'cover', 'lock', 'fan', 'media_player', 'vacuum']]
            sensors = [e for e in result if e not in actuators]
            
            # Return actuators first
            return (actuators + sensors)[:50] 
            
        except Exception as e:
            self.logger.error(f"Discovery error: {e}")
            return []

    async def generate_config(self, user_prompt: str, available_entities: List[str] = None) -> Dict[str, Any]:
        """
        Generates a YAML configuration block based on user prompt.
        Uses real entity discovery.
        """
        # Discover real entities based on the prompt
        found_entities = await self.discover_entities_from_instruction(user_prompt)
        
        # Infer name/ID
        name = "Custom Agent"
        import re
        match = re.search(r"(?:name|call)\s+(?:is\s+)?([A-Za-z0-9 ]+)", user_prompt, re.IGNORECASE)
        if match:
             name = match.group(1).title()
        else:
             # Try to derive from first strong keyword?
             ignore = {'turn', 'switch', 'change', 'set', 'if', 'when', 'manager', 'supervisor', 'agent', 'bot'}
             words = [w for w in user_prompt.split() if w.lower() not in ignore and len(w) > 3]
             if words:
                 name = f"{words[0].title()} Agent"
                 
        agent_id = name.lower().replace(" ", "_").replace(".", "")
        
        generated = {
            "id": agent_id,
            "name": name,
            "model": "mistral:7b-instruct",
            "decision_interval": 120,
            "entities": found_entities,
            "instruction": user_prompt
        }
            
        return generated

    @property
    def ha_client(self):
        if callable(self._ha_provider):
            return self._ha_provider()
        return self._ha_provider
