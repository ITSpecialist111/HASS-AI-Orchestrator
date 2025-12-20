"""
FastAPI application for AI Orchestrator backend.
Serves REST API, WebSocket connections, and static dashboard files.
"""
import os
import json
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel

from ha_client import HAWebSocketClient
from mcp_server import MCPServer
from approval_queue import ApprovalQueue
from orchestrator import Orchestrator
from rag_manager import RagManager
from knowledge_base import KnowledgeBase

# Agents
from agents.heating_agent import HeatingAgent
from agents.cooling_agent import CoolingAgent
from agents.lighting_agent import LightingAgent
from agents.security_agent import SecurityAgent
from agents.universal_agent import UniversalAgent
from agents.architect_agent import ArchitectAgent
from analytics import router as analytics_router
from factory_router import router as factory_router
from ingress_middleware import IngressMiddleware
import yaml


# Global state
ha_client: Optional[HAWebSocketClient] = None
mcp_server: Optional[MCPServer] = None
approval_queue: Optional[ApprovalQueue] = None
orchestrator: Optional[Orchestrator] = None
rag_manager: Optional[RagManager] = None
knowledge_base: Optional[KnowledgeBase] = None
agents: Dict[str, object] = {}
dashboard_clients: List[WebSocket] = []


class AgentStatus(BaseModel):
    """Agent status response model"""
    agent_id: str
    name: str
    status: str  # connected | idle | deciding | error
    model: str
    last_decision: Optional[str]
    decision_interval: int
    instruction: Optional[str] = None
    entities: List[str] = []


class Decision(BaseModel):
    """Decision log entry"""
    timestamp: str
    agent_id: str
    action: Optional[str] = None
    task_id: Optional[str] = None
    reasoning: Optional[str] = None
    parameters: Optional[Dict] = None
    result: Optional[str] = None
    dry_run: bool = False


class ApprovalRequestResponse(BaseModel):
    """Approval request response model"""
    id: str
    timestamp: str
    agent_id: str
    action_type: str
    impact_level: str
    reason: str
    status: str
    timeout_seconds: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown tasks"""
    global ha_client, mcp_server, approval_queue, orchestrator, agents
    
    print("🚀 Starting AI Orchestrator backend (Phase 2 Multi-Agent)...")
    
    # 1. Initialize Home Assistant WebSocket client
    ha_url = os.getenv("HA_URL", "http://supervisor/core")
    supervisor_token = os.getenv("SUPERVISOR_TOKEN", "")
    
    # Try to use a specific Long-Lived Access Token if provided, otherwise fallback to Supervisor Token
    ha_token = os.getenv("HA_ACCESS_TOKEN", "").strip()
    
    # Determine which token to use for headers
    # If using LLAT (Direct Mode implies homeassistant:8123), we don't need Supervisor Proxy headers
    if ha_token:
        # Direct Core Access Mode
        header_token = None
        print(f"DEBUG: Using Direct Core Access with LLAT (No Supervisor Headers)")
    else:
        # Supervisor Proxy Mode
        ha_token = supervisor_token
        header_token = supervisor_token
        print(f"DEBUG: Using Supervisor Proxy Mode")
    
    # Pass both: 'ha_token' for the auth payload, 'header_token' for the proxy header
    ha_client = HAWebSocketClient(ha_url, token=ha_token, supervisor_token=header_token)
    try:
        await ha_client.connect()
        print(f"✓ Connected to Home Assistant at {ha_url}")
    except ValueError as e:
        if "auth_invalid" in str(e):
            print("\n" + "="*50)
            print("❌ AUTHENTICATION ERROR")
            print("="*50)
            print("The Supervisor Token was rejected by Home Assistant.")
            print("Please configure a Long-Lived Access Token (LLAT):")
            print("1. Go to your HA Profile (bottom left user icon).")
            print("2. Scroll to 'Long-Lived Access Tokens'.")
            print("3. Create a token (e.g., named 'AI Orchestrator').")
            print("4. Paste it into the 'ha_access_token' field in this Add-on's Configuration.")
            print("="*50 + "\n")
        raise e
    except Exception as e:
        print(f"❌ Failed to connect to Home Assistant: {e}")
        raise e
    
    # 2. Initialize RAG & Knowledge Base (Phase 3)
    enable_rag = os.getenv("ENABLE_RAG", "true").lower() == "true"
    if enable_rag:
        try:
            rag_manager = RagManager(persist_dir="/data/chroma")
            knowledge_base = KnowledgeBase(rag_manager, ha_client)
            print("✓ RAG Manager & Knowledge Base initialized")
            
            # Start background ingestion
            asyncio.create_task(knowledge_base.ingest_ha_registry())
            asyncio.create_task(knowledge_base.ingest_manuals())
        except Exception as e:
            print(f"⚠️ RAG initialization failed: {e}")
            rag_manager = None
    
    # 3. Initialize MCP server
    # Prefer reading directly from options.json for reliability in HA Add-on environment
    dry_run = True
    options_path = Path("/data/options.json")
    if options_path.exists():
        try:
            with open(options_path, "r") as f:
                opts = json.load(f)
                dry_run = opts.get("dry_run_mode", True)
                print(f"DEBUG: Read dry_run={dry_run} from options.json")
        except Exception as e:
            print(f"⚠️ Failed to read options.json: {e}")
            # Fallback to env var
            dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
    else:
        # Fallback to env var
        dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"

    mcp_server = MCPServer(ha_client, rag_manager=rag_manager, dry_run=dry_run)
    print(f"✓ MCP Server initialized (dry_run={dry_run})")
    
    # 4. Initialize Approval Queue
    approval_queue = ApprovalQueue(db_path="/data/approvals.db")
    # Register callback for dashboard notifications
    approval_queue.register_callback(broadcast_approval_request)
    print("✓ Approval Queue initialized")
    
    # 5. Initialize Agents
    # Helper to parse entity lists
    def get_entities(env_var: str) -> List[str]:
        raw = os.getenv(env_var, "")
        return [e.strip() for e in raw.split(",") if e.strip()]

    # 5. Initialize Agents (Phase 5: Dynamic Loading)
    def load_agents_from_config(config_path: str = "agents.yaml"):
        if not os.path.exists(config_path):
            print(f"⚠️ Config {config_path} not found, skipping dynamic agents.")
            return

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            for agent_cfg in config.get('agents', []):
                agent_id = agent_cfg['id']
                
                # Check if entities are defined in yaml, otherwise fallback to env vars (backwards compat)
                entities = agent_cfg.get('entities', [])
                if not entities:
                    # Legacy fallback
                    env_var = f"{agent_id.upper()}_ENTITIES"
                    raw = os.getenv(env_var, "")
                    entities = [e.strip() for e in raw.split(",") if e.strip()]
                
                # Create Universal Agent
                agents[agent_id] = UniversalAgent(
                    agent_id=agent_id,
                    name=agent_cfg['name'],
                    instruction=agent_cfg['instruction'],
                    mcp_server=mcp_server,
                    ha_client=ha_client,
                    entities=entities,
                    rag_manager=rag_manager,
                    model_name=agent_cfg.get('model', os.getenv("DEFAULT_MODEL", "mistral:7b-instruct")),
                    decision_interval=agent_cfg.get('decision_interval', 120),
                    broadcast_func=broadcast_to_dashboard,
                    knowledge=agent_cfg.get('knowledge', "")
                )
                print(f"  ✓ Loaded agent: {agent_cfg['name']} ({agent_id})")
                
        except Exception as e:
            print(f"❌ Failed to load agents from config: {e}")

    # Load agents
    print("Loading agents from agents.yaml...")
    load_agents_from_config()
    
    # If config was empty/missing, we could optionally load default hardcoded agents here
    # but for Phase 5 we assume yaml drives the system.
    
    print(f"✓ Initialized {len(agents)} agents: {', '.join(agents.keys())}")
    
    # 6. Initialize Orchestrator
    # Use the configured model (default: mistral:7b-instruct) for the orchestrator too,
    # since the user might only have one model available on the remote Ollama.
    orchestrator = Orchestrator(
        ha_client=ha_client,
        mcp_server=mcp_server,
        approval_queue=approval_queue,
        agents=agents,
        model_name=os.getenv("ORCHESTRATOR_MODEL", "deepseek-r1:8b"),
        planning_interval=int(os.getenv("DECISION_INTERVAL", "120"))
    )
    print(f"✓ Orchestrator initialized with model {orchestrator.model_name}")
    
    # 7. Start Orchestrator Loop
    asyncio.create_task(orchestrator.run_planning_loop())
    print("✓ Orchestration loop started")
    
    # 7.5 Start Specialist Agent Loops (Autonomous Mode)
    for agent_id, agent in agents.items():
        if hasattr(agent, "run_decision_loop") and getattr(agent, "decision_interval", 0) > 0:
            asyncio.create_task(agent.run_decision_loop())
            print(f"✓ Started decision loop for {agent_id}")
    
    # 8. Initialize Architect (Phase 6)
    architect = ArchitectAgent(ha_client, rag_manager=rag_manager)
    app.state.architect = architect
    print("✓ Architect Agent initialized")
    
    print("✅ AI Orchestrator (Phase 6) ready!")
    
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
    version="0.9.3",
    lifespan=lifespan
)

# Expose globals to state for routers
app.state.agents = agents


app.include_router(analytics_router)
app.include_router(factory_router)


# Removed broken @app.middleware("http") which caused WS to crash
# The fix is now in ingress_middleware.py loaded below
app.add_middleware(IngressMiddleware)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "online",
        "version": "0.9.3",
        "orchestrator_model": orchestrator.model_name if orchestrator else "unknown",
        "agent_count": len(orchestrator.agents) if orchestrator else 0
    }



class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_with_orchestrator(req: ChatRequest):
    """Direct chat with the Orchestrator"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    
    return await orchestrator.process_chat_request(req.message)

@app.get("/api/agents", response_model=List[AgentStatus])
async def get_agents():
    """Get status of all agents"""
    status_list = []
    
    for agent_id, agent in agents.items():
        last_decision_file = agent.get_last_decision_file()
        last_decision = None
        if last_decision_file and last_decision_file.exists():
            try:
                with open(last_decision_file, "r") as f:
                    data = json.load(f)
                    last_decision = data.get("timestamp")
            except:
                pass
        
        status_list.append(AgentStatus(
            agent_id=agent_id,
            name=agent.name,
            status=getattr(agent, "status", "unknown"),
            model=getattr(agent, "model_name", "unknown"),
            last_decision=last_decision,
            decision_interval=getattr(agent, "decision_interval", 0),
            instruction=getattr(agent, "instruction", ""),
            entities=getattr(agent, "entities", [])
        ))
    
    return status_list


@app.get("/api/decisions")
async def get_decisions(limit: int = 100, agent_id: Optional[str] = None):
    """Get recent decision history (aggregated or per agent)"""
    base_dir = Path("/data/decisions")
    all_files = []
    
    # If agent_id specified, look there. Else look in all subdirs (including orchestrator)
    if agent_id:
        target_dirs = [base_dir / agent_id]
    else:
        target_dirs = [d for d in base_dir.iterdir() if d.is_dir()]
    
    for d in target_dirs:
        if d.exists():
            all_files.extend(d.glob("*.json"))
    
    # Sort by mtime descending
    decision_files = sorted(
        all_files,
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:limit]
    
    decisions = []
    for file_path in decision_files:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                # Normalize schema if needed
                decisions.append(data)
        except:
            continue
            
    return decisions


@app.get("/api/approvals", response_model=List[ApprovalRequestResponse])
async def get_approvals(status: str = "pending"):
    """Get approval requests filtered by status"""
    if not approval_queue:
        return []
    
    if status == "pending":
        requests = approval_queue.get_pending()
    else:
        # TODO: Add get_by_status to ApprovalQueue if needed
        requests = approval_queue.get_pending() 
        
    return [
        ApprovalRequestResponse(
            id=req.id,
            timestamp=req.timestamp.isoformat(),
            agent_id=req.agent_id,
            action_type=req.action_type,
            impact_level=req.impact_level,
            reason=req.reason,
            status=req.status,
            timeout_seconds=req.timeout_seconds
        )
        for req in requests
    ]


@app.post("/api/approvals/{request_id}/{action}")
async def handle_approval(request_id: str, action: str):
    """Approve or reject a request"""
    if not approval_queue:
        raise HTTPException(status_code=503, detail="Approval queue not initialized")
    
    if action == "approve":
        success = await approval_queue.approve(request_id, approved_by="user")
    elif action == "reject":
        success = await approval_queue.reject(request_id, rejected_by="user")
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
        
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or not pending")
        
    return {"status": "success", "action": action, "request_id": request_id}


@app.get("/api/dashboard/dynamic")
async def get_dynamic_dashboard():
    """Serve the latest dynamic visual dashboard"""
    path = Path("/data/dashboard/dynamic.html")
    if not path.exists():
        # Trigger an initial generation if it doesn't exist
        if orchestrator:
            await orchestrator.generate_visual_dashboard()
        else:
            raise HTTPException(status_code=404, detail="Dashboard not found and Orchestrator busy")
            
    return FileResponse(path)


@app.post("/api/dashboard/refresh")
async def refresh_dashboard():
    """Manually trigger a dashboard regeneration"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    
    html = await orchestrator.generate_visual_dashboard()
    return {"status": "success", "length": len(html)}


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "dry_run_mode": mcp_server.dry_run if mcp_server else True,
        "orchestrator_model": os.getenv("ORCHESTRATOR_MODEL", "deepseek-r1:8b"),
        "smart_model": os.getenv("SMART_MODEL", "deepseek-r1:8b"),
        "fast_model": os.getenv("FAST_MODEL", "mistral:7b-instruct"),
        "version": app.version,
        "agents": {
            k: getattr(v, "model_name", "unknown") for k, v in agents.items()
        }
    }


class UpdateConfigRequest(BaseModel):
    dry_run_mode: Optional[bool] = None


@app.patch("/api/config")
async def update_config(req: UpdateConfigRequest):
    """Update runtime configuration (in-memory only)"""
    global mcp_server
    
    if req.dry_run_mode is not None:
        if mcp_server:
            mcp_server.dry_run = req.dry_run_mode
            print(f"🔄 Runtime Config Update: Dry Run set to {req.dry_run_mode}")
        else:
            raise HTTPException(status_code=503, detail="MCP Server not initialized")
            
    return {"status": "success", "dry_run_mode": mcp_server.dry_run}


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
                "orchestrator_active": orchestrator is not None,
                "agents": list(agents.keys())
            }
        })
        
        while True:
            # Keep connection alive
            await websocket.receive_text()
            
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
    
    for client in disconnected:
        dashboard_clients.remove(client)


async def broadcast_approval_request(data: Dict):
    """Callback for new approval requests"""
    await broadcast_to_dashboard({
        "type": "approval_required",
        "data": data
    })


# Make broadcast function available to agents/orchestrator via app state if needed
app.state.broadcast_to_dashboard = broadcast_to_dashboard


# -----------------------------------------------------------------------------
# Static Files (Dashboard)
# -----------------------------------------------------------------------------
# Path to the built frontend (assuming standard add-on structure)
dashboard_path = Path(__file__).parent.parent / "dashboard" / "dist"

if dashboard_path.exists():
    print(f"✓ Mounting dashboard from {dashboard_path}")
    app.mount("/", StaticFiles(directory=str(dashboard_path), html=True), name="static")
else:
    print(f"⚠️ Dashboard bundle not found at {dashboard_path}")
    
    @app.get("/")
    async def root():
        return {
            "message": "AI Orchestrator Backend is Running",
            "status": "No dashboard found. Please ensure the frontend was built.",
            "mode": "API Only"
        }
