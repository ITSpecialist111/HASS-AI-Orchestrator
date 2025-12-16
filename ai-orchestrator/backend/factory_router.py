from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Dict, Any
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

@router.post("/save")
async def save_agent(req: SaveRequest):
    """
    Appends the new agent config to agents.yaml and triggers a reload (optional)
    """
    config_path = "agents.yaml"
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
    config_path = "agents.yaml"
    
    try:
        # 1. Provide info to Orchestrator to stop the loop? 
        # For now, just remove from global dict
        if agent_id in request.app.state.agents:
            del request.app.state.agents[agent_id]
            
        # 2. Remove from yaml
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            if 'agents' in data:
                data['agents'] = [a for a in data['agents'] if a['id'] != agent_id]
                
                with open(config_path, 'w') as f:
                    yaml.dump(data, f, sort_keys=False)
                    
        return {"status": "success", "message": f"Agent {agent_id} deleted"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UpdateAgentRequest(BaseModel):
    instruction: Optional[str] = None
    name: Optional[str] = None
    entities: Optional[List[str]] = None
    decision_interval: Optional[int] = None

@router.patch("/agents/{agent_id}")
async def update_agent(agent_id: str, req: UpdateAgentRequest, request: Request):
    """Update an agent's configuration"""
    config_path = "agents.yaml"
    
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
        # We need access to the agent instance
        # This is tricky because we need to re-instantiate it using main.py's dependencies (mcp, ha_client)
        # For now, we simply require a restart or we can try to update the live instance attributes if possible.
        
        # Simple attribute update for immediate effect (Instruction and Interval)
        # Re-init is safer but requires importing UniversalAgent and having access to all deps.
        # Let's try simple attribute update if it exists in memory.
        
        # Access global agents dict via app state (hacky until refactored)
        # We need to expose agents in app.state in main.py first!
        # Assuming we will do that.
        
        # For now, just return success and tell user to restart or wait for hot reload implementation
        # Actually, let's try to update the running instance if we can find it.
        # We'll need to define `request.app.state.agents` in `main.py`
        
        if hasattr(request.app.state, "agents") and agent_id in request.app.state.agents:
             agent_instance = request.app.state.agents[agent_id]
             if req.instruction is not None:
                 agent_instance.instruction = req.instruction
                 # If using UniversalAgent, this is enough because it reads self.instruction every loop
             if req.decision_interval is not None and hasattr(agent_instance, "decision_interval"):
                 agent_instance.decision_interval = req.decision_interval
        
        return {"status": "success", "message": "Agent updated. Properties updated in memory."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
