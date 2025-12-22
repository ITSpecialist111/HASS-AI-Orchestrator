from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import yaml
import os

from agents.architect_agent import ArchitectAgent
# We need access to the global architect instance, or create one per request
# Ideally accessing via app.state

router = APIRouter(prefix="/api/factory", tags=["factory"])

class GenerateRequest(BaseModel):
    prompt: str

class SaveRequest(BaseModel):
    config: Dict[str, Any]

# Helper to get architect from app state (we will set this up in main.py)
def get_architect(request: Request):
    # This assumes we attach it to app.state
    # For now, we might need to instantiate or rely on a global
    return request.app.state.architect

@router.get("/suggestions")
async def get_suggestions(request: Request): 
    architect = request.app.state.architect
    if not architect:
        raise HTTPException(status_code=503, detail="Architect not initialized")
    return await architect.suggest_agents()

@router.post("/generate")
async def generate_config(req: GenerateRequest, request: Request):
    architect = request.app.state.architect
    if not architect:
        raise HTTPException(status_code=503, detail="Architect not initialized")
    
    config = await architect.generate_config(req.prompt)
    return config

def get_config_path():
    # Priority: /config/agents.yaml (Add-on persistent storage)
    if os.path.exists("/config"):
        return "/config/agents.yaml"
    return "agents.yaml"

@router.post("/save")
async def save_agent(req: SaveRequest):
    """
    Appends the new agent config to agents.yaml and triggers a reload (optional)
    """
    config_path = get_config_path()
    new_agent = req.config
    
    try:
        # Read existing
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                if 'agents' not in data:
                    data['agents'] = []
        else:
            data = {'agents': []}
            
        # Check for duplicate ID
        for a in data['agents']:
            if a['id'] == new_agent['id']:
                # Append random suffix or error?
                # For now, error
                raise HTTPException(status_code=400, detail=f"Agent ID {new_agent['id']} already exists")
                
        # Append
        data['agents'].append(new_agent)
        
        # Write back
        with open(config_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False)
            
        return {"status": "success", "message": "Agent saved. Restart required to activate."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, request: Request):
    """Delete an agent from configuration and memory"""
    config_path = get_config_path()
    
    try:
        # 1. Provide info to Orchestrator to stop the loop? 
        # For now, just remove from global dict safely
        if hasattr(request.app.state, "agents"):
             request.app.state.agents.pop(agent_id, None)
            
        # 2. Remove from yaml
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            if 'agents' in data:
                initial_count = len(data['agents'])
                data['agents'] = [a for a in data['agents'] if a['id'] != agent_id]
                
                if len(data['agents']) == initial_count and agent_id not in request.app.state.agents:
                    # Not found in file AND not in memory (already popped)
                    # Use a warning but don't error if it's already effectively gone
                    pass

                with open(config_path, 'w') as f:
                    yaml.dump(data, f, sort_keys=False)
                    
        return {"status": "success", "message": f"Agent {agent_id} deleted"}
        
    except Exception as e:
        print(f"Error deleting agent {agent_id}: {e}") # Log to console
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")

class UpdateAgentRequest(BaseModel):
    instruction: Optional[str] = None
    name: Optional[str] = None
    entities: Optional[List[str]] = None
    decision_interval: Optional[int] = None

@router.patch("/agents/{agent_id}")
async def update_agent(agent_id: str, req: UpdateAgentRequest, request: Request):
    """Update an agent's configuration"""
    config_path = get_config_path()
    
    try:
        # 1. Update YAML
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            found = False
            if 'agents' in data:
                for agent in data['agents']:
                    if agent['id'] == agent_id:
                        if req.instruction is not None:
                            agent['instruction'] = req.instruction
                            
                            # Auto-discover entities if instruction changed and no explicit entities provided
                            # This ensures agents "see" what they are supposed to control
                            if req.entities is None:
                                try:
                                    architect = request.app.state.architect
                                    if architect:
                                        found = await architect.discover_entities_from_instruction(req.instruction)
                                        agent['entities'] = found
                                        print(f"🔄 Re-assigned entities for {agent_id}: {found}")
                                except Exception as e:
                                    print(f"⚠️ Entity discovery failed: {e}")

                        if req.name is not None:
                            agent['name'] = req.name
                        if req.entities is not None:
                            agent['entities'] = req.entities
                        if req.decision_interval is not None:
                            agent['decision_interval'] = req.decision_interval
                        found = True
                        break
            
            if not found:
                 raise HTTPException(status_code=404, detail="Agent not found in config")
                 
            with open(config_path, 'w') as f:
                yaml.dump(data, f, sort_keys=False)
        else:
            raise HTTPException(status_code=404, detail="Config file not found")

        # 2. Hot Reload in Memory
        if hasattr(request.app.state, "agents") and agent_id in request.app.state.agents:
             agent_instance = request.app.state.agents[agent_id]
             if req.instruction is not None:
                 agent_instance.instruction = req.instruction
                 
                 # Logic for memory update if we re-discovered entities
                 # We need to reload the YAML or trust the logic we just ran
                 # Re-fetching from YAML is safest or just replicate logic
                 if req.entities is None:
                      # We modified the YAML above, let's grab the discovered entities from there?
                      # Actually, simplest is to re-run discovery here or store it in a var
                      # Let's re-run for consistency or better yet, store "found" variable in outer scope
                      pass 

             # 3. Reload YAML to pick up new entities (Dirty but effective for consistency)
             # Or just update memory if we had the var. Let's rely on config reload? 
             # No, "Hot Reload" usually implies memory update.
             # We should probably pass the 'found' entities from step 1 down here.
             pass 

             if req.name is not None:
                 agent_instance.name = req.name 
             if req.decision_interval is not None and hasattr(agent_instance, "decision_interval"):
                 agent_instance.decision_interval = req.decision_interval
             
             # Re-read file to sync memory fully (specifically entities)
             if os.path.exists(config_path):
                 with open(config_path, 'r') as f:
                     new_data = yaml.safe_load(f)
                     for a in new_data.get('agents', []):
                         if a['id'] == agent_id:
                             agent_instance.entities = a.get('entities', [])
                             break
        
        return {"status": "success", "message": "Agent updated."}

    except Exception as e:
        print(f"Error updating agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
