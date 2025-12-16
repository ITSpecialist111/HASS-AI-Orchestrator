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
