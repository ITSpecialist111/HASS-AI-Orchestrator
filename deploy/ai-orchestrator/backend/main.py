"""
FastAPI application for AI Orchestrator backend.
Serves REST API, WebSocket connections, and static dashboard files.
"""
import os
import json
import asyncio
from typing import Dict, List
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ha_client import HAWebSocketClient
from mcp_server import MCPServer
from agents.heating_agent import HeatingAgent


# Global state
ha_client: HAWebSocketClient = None
mcp_server: MCPServer = None
heating_agent: HeatingAgent = None
dashboard_clients: List[WebSocket] = []


class AgentStatus(BaseModel):
    """Agent status response model"""
    agent_id: str
    name: str
    status: str  # connected | idle | deciding | error
    model: str
    last_decision: str | None
    decision_interval: int


class Decision(BaseModel):
    """Decision log entry"""
    timestamp: str
    agent_id: str
    action: str
    parameters: Dict
    result: str
    dry_run: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown tasks"""
    global ha_client, mcp_server, heating_agent
    
    print("🚀 Starting AI Orchestrator backend...")
    
    # Initialize Home Assistant WebSocket client
    ha_url = os.getenv("HA_URL", "http://supervisor/core")
    ha_token = os.getenv("SUPERVISOR_TOKEN", "")
    
    ha_client = HAWebSocketClient(ha_url, ha_token)
    await ha_client.connect()
    print(f"✓ Connected to Home Assistant at {ha_url}")
    
    # Initialize MCP server
    dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
    mcp_server = MCPServer(ha_client, dry_run=dry_run)
    print(f"✓ MCP Server initialized (dry_run={dry_run})")
    
    # Initialize Heating Agent
    heating_entities = os.getenv("HEATING_ENTITIES", "").split(",")
    heating_entities = [e.strip() for e in heating_entities if e.strip()]
    
    heating_agent = HeatingAgent(
        mcp_server=mcp_server,
        ha_client=ha_client,
        heating_entities=heating_entities,
        model_name=os.getenv("HEATING_MODEL", "mistral:7b-instruct"),
        decision_interval=int(os.getenv("DECISION_INTERVAL", "120"))
    )
    print(f"✓ Heating Agent initialized with {len(heating_entities)} entities")
    
    # Start agent decision loop
    asyncio.create_task(heating_agent.run_decision_loop())
    print("✓ Agent decision loop started")
    
    print("✅ AI Orchestrator ready!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down AI Orchestrator...")
    if ha_client:
        await ha_client.disconnect()
    print("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AI Orchestrator API",
    description="Home Assistant Multi-Agent Orchestration System",
    version="0.7.0",
    lifespan=lifespan
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return {
        "status": "healthy",
        "ha_connected": ha_client.connected if ha_client else False,
        "agent_active": heating_agent is not None
    }


@app.get("/api/agents", response_model=List[AgentStatus])
async def get_agents():
    """Get status of all agents"""
    if not heating_agent:
        return []
    
    last_decision_file = heating_agent.get_last_decision_file()
    last_decision = None
    if last_decision_file and last_decision_file.exists():
        with open(last_decision_file, "r") as f:
            data = json.load(f)
            last_decision = data.get("timestamp")
    
    return [
        AgentStatus(
            agent_id="heating",
            name="Heating Agent",
            status=heating_agent.status,
            model=heating_agent.model_name,
            last_decision=last_decision,
            decision_interval=heating_agent.decision_interval
        )
    ]


@app.get("/api/decisions", response_model=List[Decision])
async def get_decisions(limit: int = 100):
    """Get recent decision history"""
    decisions_dir = Path("/data/decisions/heating")
    if not decisions_dir.exists():
        return []
    
    # Get all decision files sorted by modification time
    decision_files = sorted(
        decisions_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:limit]
    
    decisions = []
    for file_path in decision_files:
        with open(file_path, "r") as f:
            data = json.load(f)
            decisions.append(Decision(**data))
    
    return decisions


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "dry_run_mode": os.getenv("DRY_RUN_MODE", "true").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "heating_model": os.getenv("HEATING_MODEL", "mistral:7b-instruct"),
        "heating_entities": os.getenv("HEATING_ENTITIES", "").split(","),
        "decision_interval": int(os.getenv("DECISION_INTERVAL", "120"))
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await websocket.accept()
    dashboard_clients.append(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "data": {
                "connected": True,
                "agent": "heating",
                "status": heating_agent.status if heating_agent else "offline"
            }
        })
        
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Echo back for now (future: handle commands)
            await websocket.send_json({"type": "echo", "data": data})
    
    except WebSocketDisconnect:
        dashboard_clients.remove(websocket)


async def broadcast_to_dashboard(message: Dict):
    """Broadcast message to all connected dashboard clients"""
    disconnected = []
    for client in dashboard_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)
    
    # Remove disconnected clients
    for client in disconnected:
        dashboard_clients.remove(client)


# Mount static files for dashboard (production)
dashboard_dist = Path("/app/dashboard/dist")
if dashboard_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(dashboard_dist / "assets")), name="assets")
    
    @app.get("/")
    async def serve_dashboard():
        """Serve React dashboard"""
        index_html = dashboard_dist / "index.html"
        if index_html.exists():
            return FileResponse(index_html)
        return {"message": "Dashboard not built. Run 'npm run build' in dashboard directory."}
else:
    @app.get("/")
    async def dashboard_not_available():
        """Dashboard not available in development"""
        return JSONResponse(
            status_code=503,
            content={
                "message": "Dashboard not available. For development, run 'npm run dev' in dashboard directory.",
                "api_docs": "/docs"
            }
        )


# Make broadcast function available to agents
app.state.broadcast_to_dashboard = broadcast_to_dashboard
