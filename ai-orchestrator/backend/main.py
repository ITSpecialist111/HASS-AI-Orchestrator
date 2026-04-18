import os
import sys

# Disable broken ChromaDB telemetry (MUST BE AT ABSOLUTE TOP)
os.environ["CHROMA_TELEMETRY_EXCEPT_OPT_OUT"] = "True"
os.environ["TELEMETRY_DISABLED"] = "1"

# NUCLEAR OPTION: Monkey-patch PostHog to silence the capture error
try:
    import posthog
    def noop_capture(*args, **kwargs): pass
    posthog.capture = noop_capture
    print("✓ PostHog monkey-patched to silence telemetry errors.")
except ImportError:
    pass

"""
FastAPI application for AI Orchestrator backend.
Serves REST API, WebSocket connections, and static dashboard files.
"""
import json
import asyncio
import httpx
import socket
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, StreamingResponse

from pydantic import BaseModel
from starlette.types import ASGIApp, Scope, Receive, Send

# Wrapper to prevent StaticFiles from crashing on WebSocket requests
class SafeStaticFiles(StaticFiles):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            # Gracefully close if a WebSocket request falls through to static handler
            await send({"type": "websocket.close", "code": 1000})
            return
        if scope["type"] != "http":
            return
        await super().__call__(scope, receive, send)

async def check_ollama_connectivity(host: str):
    """Deep network diagnostic for Ollama connectivity"""
    print(f"🔍 [NETWORK DIAG] Testing Ollama connectivity at {host}...")
    
    # 1. Parse host
    from urllib.parse import urlparse
    parsed = urlparse(host)
    ip_or_host = parsed.hostname
    port = parsed.port or 11434
    
    # 2. DNS/Resolve check
    try:
        remote_ip = socket.gethostbyname(ip_or_host)
        print(f"  ✓ DNS Resolve: {ip_or_host} -> {remote_ip}")
    except Exception as e:
        print(f"  ❌ DNS Resolve FAILED for {ip_or_host}: {e}")
        return False

    # 3. Connection (Socket level)
    try:
        print(f"  Connecting to {remote_ip}:{port}...")
        conn = socket.create_connection((remote_ip, port), timeout=3.0)
        conn.close()
        print(f"  ✓ Socket Level: Reachable!")
    except Exception as e:
        print(f"  ❌ Socket Level FAILED: {e}")
        print(f"     TIP: If this is 'No route to host', check your router/firewall or use 'host_network: true'.")

    # 4. HTTP check
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{host}/api/tags")
            if resp.status_code == 200:
                print(f"  ✓ HTTP Level: Ollama API is responding correctly.")
                return True
            else:
                print(f"  ⚠️ HTTP Level: Ollama responded with status {resp.status_code}")
    except Exception as e:
        print(f"  ❌ HTTP Level FAILED: {e}")
    
    return False

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
from external_mcp import ExternalMCPClient
from agents.deep_reasoning_agent import DeepReasoningAgent
from memory_store import MemoryStore
from native_prompts import NativePromptLibrary
from plan_executor import PlanStore
from triggers import TriggerRegistry, TriggerSpec, TriggerStore, CronExpr
import yaml

import logging

logger = logging.getLogger(__name__)

# API token for optional bearer auth (read at startup, applied via middleware)
_api_token: Optional[str] = None


class APIAuthMiddleware:
    """Optional bearer-token gate on /api/* routes.

    If ``api_token`` is configured, every request to ``/api/`` must include
    ``Authorization: Bearer <token>``.  Requests arriving through HA Ingress
    (identified by ``X-Ingress-Path`` header) are trusted automatically.
    Static assets and the WebSocket endpoint are always open.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and _api_token:
            path: str = scope.get("path", "")
            if path.startswith("/api/"):
                headers = dict(scope.get("headers", []))
                # Trust HA Ingress requests
                is_ingress = any(
                    k.decode("latin-1").lower() == "x-ingress-path"
                    for k, _v in scope.get("headers", [])
                )
                if not is_ingress:
                    auth = None
                    for k, v in scope.get("headers", []):
                        if k.decode("latin-1").lower() == "authorization":
                            auth = v.decode("latin-1")
                            break
                    if auth != f"Bearer {_api_token}":
                        from starlette.responses import JSONResponse
                        resp = JSONResponse({"detail": "Unauthorized"}, status_code=401)
                        await resp(scope, receive, send)
                        return
        await self.app(scope, receive, send)


# Global state
ha_client: Optional[HAWebSocketClient] = None
mcp_server: Optional[MCPServer] = None
approval_queue: Optional[ApprovalQueue] = None
orchestrator: Optional[Orchestrator] = None
rag_manager: Optional[RagManager] = None
knowledge_base: Optional[KnowledgeBase] = None
external_mcp: Optional[ExternalMCPClient] = None
deep_reasoner: Optional[DeepReasoningAgent] = None
trigger_registry: Optional[TriggerRegistry] = None
native_prompts: Optional[NativePromptLibrary] = None
agents: Dict[str, object] = {}
dashboard_clients: List[WebSocket] = []

# Load version from config.json
VERSION = "0.0.0"
try:
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        # Fallback to parent dir (local dev)
        config_path = Path(__file__).parent.parent / "config.json"
        
    if config_path.exists():
        with open(config_path, "r") as f:
            VERSION = json.load(f).get("version", VERSION)
except Exception as e:
    print(f"⚠️ Failed to load version from config.json: {e}")


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
    
    # 2. Load Configuration Options
    # Prefer reading directly from options.json for reliability in HA Add-on environment
    dry_run = True
    disable_telemetry = True
    ha_access_token_opt = ""
    
    # Gemini Options (Initialize to avoid NameError on failure)
    gemini_api_key_opt = ""
    use_gemini_dashboard_opt = False
    gemini_model_name_opt = "gemini-1.5-pro"
    
    options_path = Path("/data/options.json")
    if options_path.exists():
        try:
            with open(options_path, "r") as f:
                opts = json.load(f)
                dry_run = opts.get("dry_run_mode", True)
                disable_telemetry = opts.get("disable_telemetry", True)
                ha_access_token_opt = opts.get("ha_access_token", "").strip()
                
                # Gemini Options
                gemini_api_key_opt = opts.get("gemini_api_key", "").strip()
                use_gemini_dashboard_opt = opts.get("use_gemini_for_dashboard", False)
                gemini_model_name_opt = opts.get("gemini_model_name", "gemini-1.5-pro")

                # Deep reasoning / external MCP options (Phase 7)
                mcp_server_url_opt = opts.get("mcp_server_url", "").strip()
                mcp_server_token_opt = opts.get("mcp_server_token", "").strip()
                deep_reasoning_model_opt = opts.get("deep_reasoning_model", "qwen2.5:14b-instruct")
                anthropic_api_key_opt = opts.get("anthropic_api_key", "").strip()
                anthropic_model_opt = opts.get("anthropic_model", "claude-opus-4-7").strip()
                deep_reasoning_max_iter_opt = int(opts.get("deep_reasoning_max_iterations", 12) or 12)

                # Phase 9 — multi-provider LLM options
                llm_provider_opt = opts.get("llm_provider", "").strip()
                openai_api_key_opt = opts.get("openai_api_key", "").strip()
                openai_base_url_opt = opts.get("openai_base_url", "").strip()
                openai_model_opt = opts.get("openai_model", "gpt-4o-mini").strip()
                github_token_opt = opts.get("github_token", "").strip()
                github_model_opt = opts.get("github_model", "gpt-4o-mini").strip()
                foundry_endpoint_opt = opts.get("foundry_endpoint", "").strip()
                foundry_api_key_opt = opts.get("foundry_api_key", "").strip()
                foundry_bearer_token_opt = opts.get("foundry_bearer_token", "").strip()
                foundry_model_opt = opts.get("foundry_model", "").strip()
                foundry_agent_id_opt = opts.get("foundry_agent_id", "").strip()

                # API auth token (Phase 7 Milestone B)
                global _api_token
                _api_token_opt = opts.get("api_token", "").strip()
                if _api_token_opt:
                    _api_token = _api_token_opt

                logger.debug("Read dry_run=%s, disable_telemetry=%s, has_token=%s from options.json", dry_run, disable_telemetry, bool(ha_access_token_opt))
                logger.debug("Gemini: has_key=%s, use_for_dash=%s, model=%s", bool(gemini_api_key_opt), use_gemini_dashboard_opt, gemini_model_name_opt)
        except Exception as e:
            print(f"⚠️ Failed to read options.json: {e}")
            # Fallback to env var
            dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
    else:
        # Fallback to env var
        dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
        gemini_api_key_opt = os.getenv("GEMINI_API_KEY", "")
        use_gemini_dashboard_opt = os.getenv("USE_GEMINI_FOR_DASHBOARD", "false").lower() == "true"
        gemini_model_name_opt = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro")
        # API token from env
        _api_token = os.getenv("API_TOKEN", "").strip() or None

    # Diagnostics
    logger.debug("ENV - SUPERVISOR_TOKEN: %s", bool(os.getenv('SUPERVISOR_TOKEN')))
    logger.debug("ENV - HA_URL: %s", os.getenv('HA_URL'))
    logger.debug("ENV - HA_ACCESS_TOKEN: %s", bool(os.getenv('HA_ACCESS_TOKEN')))

    # If we are in an add-on, we MUST use the supervisor Proxy ONLY if the token is present.
    # Otherwise, fallback to Direct Core Access.
    is_addon = bool(os.getenv("SUPERVISOR_TOKEN")) or options_path.exists()
    supervisor_token = os.getenv("SUPERVISOR_TOKEN", "")
    
    ha_url = os.getenv("HA_URL")
    if is_addon and supervisor_token:
        ha_url = "http://supervisor/core"
        logger.debug("Add-on environment detected with Supervisor Token. Using Proxy: %s", ha_url)
    elif is_addon:
        # Fallback to internal DNS if supervisor token is missing
        ha_url = ha_url or "http://homeassistant:8123"
        logger.debug("Add-on environment detected but NO Supervisor Token. Falling back to Direct Access: %s", ha_url)
    elif not ha_url:
        ha_url = "http://homeassistant.local:8123"
        logger.debug("No HA_URL set and not in add-on. Defaulting to %s", ha_url)

    # Try to use a specific Long-Lived Access Token if provided, otherwise fallback to Supervisor Token
    ha_token = os.getenv("HA_ACCESS_TOKEN", "").strip() or ha_access_token_opt
    
    # Determine which token to use for headers
    if supervisor_token:
        # Supervisor Proxy Mode
        header_token = supervisor_token
        # Ensure we have a token (either manually provided or supervisor)
        if not ha_token:
             ha_token = supervisor_token
        logger.debug("Using Supervisor Proxy Mode (LLAT priority: %s)", bool(ha_access_token_opt))
    else:
        # Direct Core Access Mode
        header_token = None
        logger.debug("Using Direct Core Access Mode (Token present: %s)", bool(ha_token))

    ha_client = HAWebSocketClient(
        ha_url=ha_url,
        token=ha_token,
        supervisor_token=header_token
    )
    
    # 3. Start HA Client with Reconnection Loop
    try:
        # Start the background reconnection loop
        asyncio.create_task(ha_client.run_reconnect_loop())
        
        # Wait up to 5s for early feedback
        connected = await ha_client.wait_until_connected(timeout=5.0)
        if not connected:
            print("⚠️ HA Client did not connect within initial 5s burst. Reconnection loop will continue in background...")
        else:
            print("✅ HA Client connected successfully")
    except Exception as e:
        print(f"❌ Error during HA client background startup initialization: {e}")

    print(f"✓ HA Client configured (URL: {ha_url})")

    # 3. Initialize RAG & Knowledge Base (Phase 3)
    enable_rag = os.getenv("ENABLE_RAG", "true").lower() == "true"
    if enable_rag:
        try:
            rag_manager = RagManager(persist_dir="/data/chroma", disable_telemetry=disable_telemetry)
            # FIX: Pass lambda to resolve the global ha_client at runtime, not now (which is None)
            knowledge_base = KnowledgeBase(rag_manager, lambda: ha_client)
            print("✓ RAG Manager & Knowledge Base initialized")
            
            # Start background ingestion
            asyncio.create_task(knowledge_base.ingest_ha_registry())
            asyncio.create_task(knowledge_base.ingest_manuals())
        except Exception as e:
            print(f"⚠️ RAG initialization failed: {e}")
            rag_manager = None

    # 4. Initialize MCP server
    # FIX: Pass lambda for lazy resolution
    mcp_server = MCPServer(lambda: ha_client, approval_queue=approval_queue, rag_manager=rag_manager, dry_run=dry_run)
    print(f"✓ MCP Server initialized (dry_run={dry_run})")
    
    # 4. Initialize Approval Queue
    approval_queue = ApprovalQueue(db_path="/data/approvals.db")
    # Register callback for dashboard notifications
    approval_queue.register_callback(broadcast_approval_request)
    print("✓ Approval Queue initialized")

    # 4.5 Phase 9 — export multi-provider LLM credentials into the
    # process environment so every downstream factory (BaseAgent,
    # Orchestrator, RAG, DeepReasoningAgent) sees the same provider
    # selection and credentials regardless of construction order.
    _llm_env_map = {
        "LLM_PROVIDER": locals().get("llm_provider_opt", ""),
        "OPENAI_API_KEY": locals().get("openai_api_key_opt", ""),
        "OPENAI_BASE_URL": locals().get("openai_base_url_opt", ""),
        "OPENAI_MODEL": locals().get("openai_model_opt", ""),
        "GITHUB_TOKEN": locals().get("github_token_opt", ""),
        "GITHUB_MODEL": locals().get("github_model_opt", ""),
        "FOUNDRY_ENDPOINT": locals().get("foundry_endpoint_opt", ""),
        "FOUNDRY_API_KEY": locals().get("foundry_api_key_opt", ""),
        "FOUNDRY_BEARER_TOKEN": locals().get("foundry_bearer_token_opt", ""),
        "FOUNDRY_MODEL": locals().get("foundry_model_opt", ""),
        "FOUNDRY_AGENT_ID": locals().get("foundry_agent_id_opt", ""),
    }
    for _env_key, _env_val in _llm_env_map.items():
        if _env_val:
            os.environ[_env_key] = _env_val
    if _llm_env_map.get("LLM_PROVIDER"):
        print(f"✓ LLM provider: {_llm_env_map['LLM_PROVIDER']}")
    
    # 5. Initialize Agents
    # Helper to parse entity lists
    def get_entities(env_var: str) -> List[str]:
        raw = os.getenv(env_var, "")
        return [e.strip() for e in raw.split(",") if e.strip()]

    # 5. Initialize Agents (Phase 5: Dynamic Loading)
    def get_agents_config_path():
        # Search priority: /config/agents.yaml (Persistent) -> local agents.yaml
        config_paths = ["/config/agents.yaml", "agents.yaml"]
        # If /config exists, we are in an add-on and should prefer it for persistence
        if os.path.exists("/config"):
            return "/config/agents.yaml"
        return next((p for p in config_paths if os.path.exists(p)), "agents.yaml")

    def load_agents_from_config():
        config_path = get_agents_config_path()
        
        if not os.path.exists(config_path) and config_path == "agents.yaml":
            print(f"⚠️ No agent config found, skipping dynamic agents.")
            return
        
        print(f"🔍 Loading agents from {config_path}...")

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
                    ha_client=lambda: ha_client,
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
    print("Detecting agent configuration...")
    load_agents_from_config()
    
    # If config was empty/missing, we could optionally load default hardcoded agents here
    # but for Phase 5 we assume yaml drives the system.
    
    print(f"✓ Initialized {len(agents)} agents: {', '.join(agents.keys())}")
    
    # 6. Initialize Orchestrator
    # Use the configured model (default: mistral:7b-instruct) for the orchestrator too,
    # since the user might only have one model available on the remote Ollama.
    orchestrator = Orchestrator(
        ha_client=lambda: ha_client,
        mcp_server=mcp_server,
        approval_queue=approval_queue,
        agents=agents,
        model_name=os.getenv("ORCHESTRATOR_MODEL", "deepseek-r1:8b"),
        planning_interval=int(os.getenv("DECISION_INTERVAL", "120")),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        gemini_api_key=gemini_api_key_opt or os.getenv("GEMINI_API_KEY"),
        use_gemini_for_dashboard=use_gemini_dashboard_opt or os.getenv("USE_GEMINI_FOR_DASHBOARD", "false").lower() == "true",
        gemini_model_name=gemini_model_name_opt or os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro")
    )
    print(f"✓ Orchestrator initialized with model {orchestrator.model_name}")
    
    # 7. Start Orchestrator Loops
    asyncio.create_task(orchestrator.run_planning_loop())
    asyncio.create_task(orchestrator.run_dashboard_refresh_loop())
    print("✓ Orchestration & Dashboard loops started")
    
    # 7.5 Start Specialist Agent Loops (Autonomous Mode)
    for agent_id, agent in agents.items():
        if hasattr(agent, "run_decision_loop") and getattr(agent, "decision_interval", 0) > 0:
            asyncio.create_task(agent.run_decision_loop())
            print(f"✓ Started decision loop for {agent_id}")
    
    # 8. Initialize Architect (Phase 6)
    architect = ArchitectAgent(lambda: ha_client, rag_manager=rag_manager)
    app.state.architect = architect
    print("✓ Architect Agent initialized")

    # 9. Initialize External MCP client + Deep Reasoning Agent (Phase 7)
    global external_mcp, deep_reasoner
    mcp_url = locals().get("mcp_server_url_opt", "") or os.getenv("MCP_SERVER_URL", "")
    mcp_token = locals().get("mcp_server_token_opt", "") or os.getenv("MCP_SERVER_TOKEN", "")
    deep_model = locals().get("deep_reasoning_model_opt", "") or os.getenv("DEEP_REASONING_MODEL", "qwen2.5:14b-instruct")
    anthropic_key = locals().get("anthropic_api_key_opt", "") or os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model = locals().get("anthropic_model_opt", "") or os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7")
    max_iter = int(locals().get("deep_reasoning_max_iter_opt", 12) or 12)

    # Phase 9 — re-read provider locals (env was already exported in
    # step 4.5 so other components see the same credentials; we capture
    # them here to pass explicitly to DeepReasoningAgent).
    llm_provider = locals().get("llm_provider_opt", "") or os.getenv("LLM_PROVIDER", "")
    openai_api_key = locals().get("openai_api_key_opt", "") or os.getenv("OPENAI_API_KEY", "")
    openai_base_url = locals().get("openai_base_url_opt", "") or os.getenv("OPENAI_BASE_URL", "")
    openai_model = locals().get("openai_model_opt", "") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    github_token = locals().get("github_token_opt", "") or os.getenv("GITHUB_TOKEN", "")
    github_model = locals().get("github_model_opt", "") or os.getenv("GITHUB_MODEL", "gpt-4o-mini")
    foundry_endpoint = locals().get("foundry_endpoint_opt", "") or os.getenv("FOUNDRY_ENDPOINT", "")
    foundry_api_key = locals().get("foundry_api_key_opt", "") or os.getenv("FOUNDRY_API_KEY", "")
    foundry_bearer_token = locals().get("foundry_bearer_token_opt", "") or os.getenv("FOUNDRY_BEARER_TOKEN", "")
    foundry_model = locals().get("foundry_model_opt", "") or os.getenv("FOUNDRY_MODEL", "")
    foundry_agent_id = locals().get("foundry_agent_id_opt", "") or os.getenv("FOUNDRY_AGENT_ID", "")

    if mcp_url:
        external_mcp = ExternalMCPClient(url=mcp_url, token=mcp_token or None, name="external_mcp")
        ok = await external_mcp.connect()
        if ok:
            print(f"✓ External MCP connected: {mcp_url} ({len(external_mcp.tools)} tools)")
        else:
            print(f"⚠️ External MCP not connected ({mcp_url}); deep reasoning will run with local tools only")
    else:
        print("ℹ️ No mcp_server_url configured; deep reasoning will run with local tools only")

    try:
        memory_store = MemoryStore(rag_manager) if rag_manager is not None else None
        try:
            plan_store = PlanStore()
        except Exception as exc:
            logger.warning("Failed to initialise PlanStore, plan mode disabled: %s", exc)
            plan_store = None
        deep_reasoner = DeepReasoningAgent(
            local_mcp=mcp_server,
            external_mcp=external_mcp,
            ha_client=ha_client,
            ollama_model=deep_model,
            ollama_host=os.getenv("OLLAMA_HOST"),
            anthropic_api_key=anthropic_key or None,
            anthropic_model=anthropic_model,
            provider=llm_provider or None,
            openai_api_key=openai_api_key or None,
            openai_base_url=openai_base_url or None,
            openai_model=openai_model or None,
            github_token=github_token or None,
            github_model=github_model or None,
            foundry_endpoint=foundry_endpoint or None,
            foundry_api_key=foundry_api_key or None,
            foundry_bearer_token=foundry_bearer_token or None,
            foundry_model=foundry_model or None,
            foundry_agent_id=foundry_agent_id or None,
            max_iterations=max_iter,
            broadcast_func=broadcast_to_dashboard,
            memory_store=memory_store,
            plan_store=plan_store,
            default_mode=os.getenv("REASONING_DEFAULT_MODE", "auto"),
        )
        app.state.deep_reasoner = deep_reasoner
        orchestrator.deep_reasoner = deep_reasoner
        print(f"✓ Deep Reasoning Agent initialized (backend={deep_reasoner.llm.name}, tools={len(deep_reasoner.registry.names())}, memory={'on' if memory_store and memory_store.enabled else 'off'}, plans={'on' if plan_store else 'off'}, mode={deep_reasoner.default_mode})")
    except Exception as e:
        print(f"⚠️ Failed to initialize Deep Reasoning Agent: {e}")

    # ----------------------------------------------------------------
    # Phase 8.5 — native prompt library (always-available workflows)
    # ----------------------------------------------------------------
    global native_prompts
    try:
        builtin_dir = Path(__file__).parent / "prompts"
        user_dir_str = os.getenv("PROMPTS_DIR", "/data/prompts")
        user_dir = Path(user_dir_str)
        native_prompts = NativePromptLibrary(builtin_dir, user_dir)
        app.state.native_prompts = native_prompts
        print(f"✓ Native prompt library loaded ({len(native_prompts.list())} prompts)")
    except Exception as e:
        print(f"⚠️ Failed to load native prompt library: {e}")
        native_prompts = None

    # ----------------------------------------------------------------
    # Phase 8 / Milestone F — proactive triggers
    # ----------------------------------------------------------------
    global trigger_registry
    if deep_reasoner is not None:
        try:
            trigger_store = TriggerStore()

            async def _trigger_reasoner_call(goal: str, context: dict):
                # Triggers always go through plan/auto so the PAE
                # safety net (Milestone E) gates anything dangerous.
                return await deep_reasoner.run(goal, context, mode="auto")

            trigger_registry = TriggerRegistry(
                store=trigger_store,
                reasoner_callback=_trigger_reasoner_call,
                ha_client=ha_client,
                broadcast_func=broadcast_to_dashboard,
            )
            await trigger_registry.start()
            app.state.trigger_registry = trigger_registry
            print(f"✓ TriggerRegistry started ({len(trigger_registry.list())} configured)")
        except Exception as e:
            print(f"⚠️ Failed to initialise TriggerRegistry: {e}")
            trigger_registry = None

    print("✅ AI Orchestrator (Phase 6) ready!")

    yield

    # Shutdown
    print("🛑 Shutting down AI Orchestrator...")
    if trigger_registry:
        try:
            await trigger_registry.stop()
        except Exception as e:
            print(f"⚠️ Trigger registry stop error: {e}")
    if external_mcp:
        try:
            await external_mcp.aclose()
        except Exception as e:
            print(f"⚠️ External MCP close error: {e}")
    if ha_client:
        await ha_client.disconnect()
    print("✅ Shutdown complete")




# Create FastAPI app
app = FastAPI(
    title="AI Orchestrator API",
    description="Home Assistant Multi-Agent Orchestration System",
    version=VERSION,
    lifespan=lifespan
)

# Expose globals to state for routers
app.state.agents = agents


app.include_router(analytics_router)
app.include_router(factory_router)


# Removed broken @app.middleware("http") which caused WS to crash
# The fix is now in ingress_middleware.py loaded below
app.add_middleware(IngressMiddleware)
app.add_middleware(APIAuthMiddleware)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "online",
        "version": VERSION,
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


class ReasoningRequest(BaseModel):
    """Goal payload for the deep reasoning agent."""
    goal: str
    context: Optional[Dict] = None
    mode: Optional[str] = None  # "auto" | "plan" | "execute"


@app.get("/api/reasoning/info")
async def reasoning_info():
    """Status & tool surface of the deep reasoning agent."""
    if not deep_reasoner:
        raise HTTPException(status_code=503, detail="Deep reasoning agent not ready")
    return deep_reasoner.info()


@app.post("/api/reasoning/run")
async def reasoning_run(req: ReasoningRequest):
    """Run the deep reasoning harness on a free-form goal.

    Returns the final answer plus a step-by-step trace of the
    reasoning loop (thoughts, tool calls, tool results).
    """
    if not deep_reasoner:
        raise HTTPException(status_code=503, detail="Deep reasoning agent not ready")
    if not req.goal or not req.goal.strip():
        raise HTTPException(status_code=400, detail="goal must not be empty")
    if req.mode is not None and req.mode not in ("auto", "plan", "execute"):
        raise HTTPException(status_code=400, detail="mode must be one of auto|plan|execute")
    result = await deep_reasoner.run(req.goal, req.context, mode=req.mode)
    return {
        "run_id": getattr(result, "run_id", None),
        "episode_id": getattr(result, "episode_id", None),
        "mode": getattr(result, "mode", "execute"),
        "plan": getattr(result, "plan", None),
        "executed_inline": getattr(result, "executed_inline", False),
        "execution_results": getattr(result, "execution_results", None),
        "answer": result.answer,
        "iterations": result.iterations,
        "tool_calls": result.tool_calls,
        "stopped_reason": result.stopped_reason,
        "duration_ms": result.duration_ms,
        "recalled": getattr(result, "recalled", []),
        "trace": [
            {
                "iteration": s.iteration,
                "thought": s.thought,
                "tool_calls": s.tool_calls,
                "tool_results": s.tool_results,
                "duration_ms": s.duration_ms,
            }
            for s in result.trace
        ],
    }


@app.post("/api/reasoning/stream")
async def reasoning_stream(req: ReasoningRequest):
    """Run the deep reasoning agent with Server-Sent Events output.

    The response is ``text/event-stream``; each event has a ``data:``
    line with a JSON-encoded payload. Event types include
    ``start``, ``thought``, ``tool_call``, ``recall``, ``plan``,
    ``final``, ``error``, plus periodic ``ping`` keep-alives.
    """
    if not deep_reasoner:
        raise HTTPException(status_code=503, detail="Deep reasoning agent not ready")
    if not req.goal or not req.goal.strip():
        raise HTTPException(status_code=400, detail="goal must not be empty")
    if req.mode is not None and req.mode not in ("auto", "plan", "execute"):
        raise HTTPException(status_code=400, detail="mode must be one of auto|plan|execute")

    async def _gen():
        try:
            async for event in deep_reasoner.run_streaming(req.goal, req.context, mode=req.mode):
                payload = json.dumps(event, default=str)
                yield f"event: {event.get('type', 'message')}\ndata: {payload}\n\n"
        except Exception as exc:
            err = json.dumps({"type": "error", "error": str(exc)})
            yield f"event: error\ndata: {err}\n\n"
        # Final terminator so EventSource clients know we're done.
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# MCP prompt catalog (Milestone G2) + native built-in prompts (Phase 8.5)
# ---------------------------------------------------------------------------
@app.get("/api/reasoning/prompts")
async def reasoning_prompts():
    """List prompts available to the reasoning agent.

    Returns the union of:
      * **Native built-in prompts** shipped with the add-on (always
        available — no external server required).
      * **External MCP prompts** discovered on a connected MCP server,
        if one is configured.

    Each entry carries a ``source`` field (``"native"`` or ``"external"``)
    so the dashboard can group / label them.
    """
    prompts: List[Dict[str, Any]] = []
    native_count = 0
    if native_prompts is not None:
        for spec in native_prompts.list():
            d = spec.to_dict()
            prompts.append(d)
            native_count += 1
    external_connected = bool(external_mcp and external_mcp.connected)
    if external_connected:
        for p in external_mcp.prompt_specs():
            entry = dict(p)
            entry["source"] = "external"
            # Avoid surprising shadowing: prefix duplicates with ``ext_``
            # while keeping the original visible.
            if any(x["name"] == entry["name"] for x in prompts):
                entry["name"] = f"ext_{entry['name']}"
            prompts.append(entry)
    return {
        "prompts": prompts,
        "native_count": native_count,
        "external_connected": external_connected,
        "external_server": external_mcp.name if external_connected else None,
        # Backwards-compat alias for the dashboard:
        "connected": external_connected,
        "server": external_mcp.name if external_connected else None,
    }


class PromptRunRequest(BaseModel):
    arguments: Optional[Dict[str, Any]] = None
    mode: Optional[str] = None
    extra_context: Optional[Dict[str, Any]] = None
    stream: bool = False


def _resolve_prompt(name: str, arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Render a prompt by name, trying native first, then external MCP.

    Returns ``{ok, text, ...}`` from whichever source matched. The
    ``ext_`` prefix added by the catalog endpoint for shadowed names is
    stripped before checking the external server.
    """
    if native_prompts is not None:
        spec = native_prompts.get(name)
        if spec is not None:
            return native_prompts.render(name, arguments or {})
    if external_mcp and external_mcp.connected:
        ext_name = name[4:] if name.startswith("ext_") else name
        # Fall through to external_mcp.get_prompt asynchronously in
        # the caller; this helper only resolves native synchronously.
    return {"ok": False, "error": f"unknown_prompt:{name}"}


async def _render_any_prompt(name: str, arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Async resolver covering both native and external prompts."""
    if native_prompts is not None:
        spec = native_prompts.get(name)
        if spec is not None:
            return native_prompts.render(name, arguments or {})
    if external_mcp and external_mcp.connected:
        ext_name = name[4:] if name.startswith("ext_") else name
        ext_specs = external_mcp.prompt_specs()
        if any((p.get("name") if isinstance(p, dict) else getattr(p, "name", None)) == ext_name
               for p in ext_specs):
            return await external_mcp.get_prompt(ext_name, arguments or {})
    return {"ok": False, "error": f"unknown_prompt:{name}"}


@app.post("/api/reasoning/prompts/{name}/render")
async def reasoning_prompt_render(name: str, req: PromptRunRequest):
    """Render a prompt to text without invoking the reasoner."""
    rendered = await _render_any_prompt(name, req.arguments or {})
    if not rendered.get("ok"):
        err = rendered.get("error", "render_failed")
        status = 404 if err.startswith("unknown_prompt") else 400
        raise HTTPException(status_code=status, detail=err)
    return rendered


@app.post("/api/reasoning/prompts/{name}/run")
async def reasoning_prompt_run(name: str, req: PromptRunRequest):
    """Render a prompt (native or external) and run it as a reasoning goal.

    Set ``stream=true`` for SSE streaming; otherwise blocks and
    returns the same shape as ``/api/reasoning/run``.
    """
    if not deep_reasoner:
        raise HTTPException(status_code=503, detail="Deep reasoning agent not ready")
    rendered = await _render_any_prompt(name, req.arguments or {})
    if not rendered.get("ok"):
        err = rendered.get("error", "render_failed")
        status = 404 if err.startswith("unknown_prompt") else 400
        raise HTTPException(status_code=status, detail=err)

    goal = rendered.get("text") or ""
    if not goal.strip():
        raise HTTPException(status_code=400, detail="rendered prompt is empty")
    context: Dict[str, Any] = {
        "prompt_name": name,
        "prompt_arguments": req.arguments or {},
        "prompt_source": rendered.get("source", "external"),
    }
    if req.extra_context:
        context.update(req.extra_context)

    if req.stream:
        async def _gen():
            try:
                async for event in deep_reasoner.run_streaming(goal, context, mode=req.mode):
                    payload = json.dumps(event, default=str)
                    yield f"event: {event.get('type', 'message')}\ndata: {payload}\n\n"
            except Exception as exc:
                err = json.dumps({"type": "error", "error": str(exc)})
                yield f"event: error\ndata: {err}\n\n"
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(
            _gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
        )

    result = await deep_reasoner.run(goal, context, mode=req.mode)
    return {
        "run_id": getattr(result, "run_id", None),
        "prompt": name,
        "mode": getattr(result, "mode", "execute"),
        "answer": result.answer,
        "iterations": result.iterations,
        "tool_calls": result.tool_calls,
        "stopped_reason": result.stopped_reason,
        "duration_ms": result.duration_ms,
        "plan": getattr(result, "plan", None),
        "executed_inline": getattr(result, "executed_inline", False),
        "execution_results": getattr(result, "execution_results", None),
    }


class FeedbackRequest(BaseModel):
    """Human feedback on a past reasoning run."""
    rating: int  # -1, 0, +1
    note: Optional[str] = None
@app.post("/api/reasoning/runs/{run_id}/feedback")
async def reasoning_feedback(run_id: str, req: FeedbackRequest):
    """Apply user feedback to a reasoning run.

    The feedback is stored on the corresponding memory episode and
    influences how that episode is weighted during future recall.
    """
    if not deep_reasoner:
        raise HTTPException(status_code=503, detail="Deep reasoning agent not ready")
    if req.rating not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="rating must be -1, 0, or 1")
    ok = await deep_reasoner.submit_feedback(run_id, req.rating, req.note)
    if not ok:
        raise HTTPException(status_code=404, detail="unknown run_id or memory disabled")
    return {"ok": True, "run_id": run_id, "rating": req.rating}


@app.get("/api/reasoning/memory")
async def reasoning_memory(q: Optional[str] = None, k: int = 10):
    """Search the deep-reasoner episode memory.

    * If ``q`` is supplied, performs semantic recall (top-k by
      similarity * recency * feedback).
    * Otherwise returns the most recent episodes.
    """
    if not deep_reasoner or not deep_reasoner.memory_store or not deep_reasoner.memory_store.enabled:
        raise HTTPException(status_code=503, detail="Memory store not enabled")
    k = max(1, min(50, k))
    if q:
        recalled = await deep_reasoner.memory_store.recall(q, k=k, max_age_days=None)
        return {
            "query": q,
            "results": [
                {
                    "episode_id": r.episode.id,
                    "goal": r.episode.goal,
                    "summary": r.episode.summary,
                    "timestamp": r.episode.timestamp,
                    "score": r.episode.score,
                    "similarity": round(r.similarity, 4),
                    "final_score": round(r.final_score, 4),
                }
                for r in recalled
            ],
        }
    episodes = deep_reasoner.memory_store.search_text("", limit=k)
    return {
        "query": None,
        "results": [
            {
                "episode_id": e.id,
                "goal": e.goal,
                "summary": e.summary,
                "timestamp": e.timestamp,
                "score": e.score,
            }
            for e in episodes
        ],
    }


@app.get("/api/reasoning/plans")
async def reasoning_plans(status: Optional[str] = None, limit: int = 50):
    """List recent plan proposals (newest first).

    Filter by ``status`` (``pending``, ``approved``, ``executed``,
    ``executed_with_errors``, ``rejected``).
    """
    if not deep_reasoner or deep_reasoner.plan_store is None:
        raise HTTPException(status_code=503, detail="Plan store not enabled")
    limit = max(1, min(200, limit))
    plans = deep_reasoner.plan_store.list(status=status, limit=limit)
    return {"count": len(plans), "plans": [p.to_dict() for p in plans]}


@app.get("/api/reasoning/plans/{plan_id}")
async def reasoning_plan_get(plan_id: str):
    if not deep_reasoner or deep_reasoner.plan_store is None:
        raise HTTPException(status_code=503, detail="Plan store not enabled")
    plan = deep_reasoner.plan_store.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="plan not found")
    return plan.to_dict()


@app.post("/api/reasoning/plans/{plan_id}/execute")
async def reasoning_plan_execute(plan_id: str):
    """Replay an approved plan against the real tools.

    Idempotent: if the plan has already been executed, returns the
    previously-recorded results. Reasoning is not re-run.
    """
    if not deep_reasoner or deep_reasoner.plan_store is None:
        raise HTTPException(status_code=503, detail="Plan store not enabled")
    out = await deep_reasoner.execute_plan(plan_id)
    if out is None:
        raise HTTPException(status_code=404, detail="plan not found")
    return out


@app.post("/api/reasoning/plans/{plan_id}/reject")
async def reasoning_plan_reject(plan_id: str):
    if not deep_reasoner or deep_reasoner.plan_store is None:
        raise HTTPException(status_code=503, detail="Plan store not enabled")
    ok = await deep_reasoner.reject_plan(plan_id)
    if not ok:
        raise HTTPException(status_code=404, detail="plan not found")
    return {"plan_id": plan_id, "status": "rejected"}


# ---------------------------------------------------------------------------
# Phase 8 / Milestone F — proactive triggers
# ---------------------------------------------------------------------------
class TriggerPayload(BaseModel):
    """Inbound trigger create/update body."""
    name: str
    type: str  # "cron" | "state"
    goal_template: str
    enabled: bool = True
    cron: Optional[str] = None
    entity_id: Optional[str] = None
    state_pattern: Optional[str] = None
    sustained_seconds: int = 0
    cooldown_seconds: int = 600
    mode: str = "auto"
    extra_context: Optional[Dict[str, Any]] = None


def _payload_to_spec(p: TriggerPayload, *, existing: Optional[TriggerSpec] = None) -> TriggerSpec:
    return TriggerSpec(
        id=existing.id if existing else "",
        name=p.name,
        type=p.type,
        goal_template=p.goal_template,
        enabled=p.enabled,
        cron=p.cron,
        entity_id=p.entity_id,
        state_pattern=p.state_pattern,
        sustained_seconds=p.sustained_seconds,
        cooldown_seconds=p.cooldown_seconds,
        mode=p.mode,
        extra_context=p.extra_context or {},
        created_at=existing.created_at if existing else datetime.now().isoformat(),
        last_fired_at=existing.last_fired_at if existing else None,
    )


@app.get("/api/triggers")
async def triggers_list(enabled_only: bool = False):
    if not trigger_registry:
        raise HTTPException(status_code=503, detail="Trigger registry not ready")
    return {"triggers": [t.to_dict() for t in trigger_registry.list(enabled_only=enabled_only)]}


@app.post("/api/triggers")
async def triggers_create(payload: TriggerPayload):
    if not trigger_registry:
        raise HTTPException(status_code=503, detail="Trigger registry not ready")
    try:
        spec = _payload_to_spec(payload)
        spec = await trigger_registry.add(spec)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return spec.to_dict()


@app.get("/api/triggers/fires")
async def triggers_all_fires(limit: int = 50):
    if not trigger_registry:
        raise HTTPException(status_code=503, detail="Trigger registry not ready")
    limit = max(1, min(500, limit))
    fires = trigger_registry.list_fires(limit=limit)
    return {"fires": [f.to_dict() for f in fires]}


@app.get("/api/triggers/{trigger_id}")
async def triggers_get(trigger_id: str):
    if not trigger_registry:
        raise HTTPException(status_code=503, detail="Trigger registry not ready")
    spec = trigger_registry.store.get(trigger_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="trigger not found")
    return spec.to_dict()


@app.put("/api/triggers/{trigger_id}")
async def triggers_update(trigger_id: str, payload: TriggerPayload):
    if not trigger_registry:
        raise HTTPException(status_code=503, detail="Trigger registry not ready")
    existing = trigger_registry.store.get(trigger_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="trigger not found")
    try:
        spec = _payload_to_spec(payload, existing=existing)
        spec.id = trigger_id
        await trigger_registry.update(spec)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return spec.to_dict()


@app.delete("/api/triggers/{trigger_id}")
async def triggers_delete(trigger_id: str):
    if not trigger_registry:
        raise HTTPException(status_code=503, detail="Trigger registry not ready")
    ok = await trigger_registry.delete(trigger_id)
    if not ok:
        raise HTTPException(status_code=404, detail="trigger not found")
    return {"trigger_id": trigger_id, "deleted": True}


@app.get("/api/triggers/{trigger_id}/fires")
async def triggers_fires(trigger_id: str, limit: int = 50):
    if not trigger_registry:
        raise HTTPException(status_code=503, detail="Trigger registry not ready")
    if trigger_registry.store.get(trigger_id) is None:
        raise HTTPException(status_code=404, detail="trigger not found")
    limit = max(1, min(500, limit))
    fires = trigger_registry.list_fires(trigger_id=trigger_id, limit=limit)
    return {"fires": [f.to_dict() for f in fires]}


@app.post("/api/triggers/{trigger_id}/fire")
async def triggers_test_fire(trigger_id: str):
    """Manually fire a trigger \u2014 useful for testing the goal template
    without waiting for the natural condition."""
    if not trigger_registry:
        raise HTTPException(status_code=503, detail="Trigger registry not ready")
    spec = trigger_registry.store.get(trigger_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="trigger not found")
    await trigger_registry._fire(spec, reason="manual test")
    fires = trigger_registry.list_fires(trigger_id=trigger_id, limit=1)
    return {"trigger_id": trigger_id, "last_fire": fires[0].to_dict() if fires else None}


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
            except (OSError, json.JSONDecodeError, KeyError):
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
        except (OSError, json.JSONDecodeError):
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
async def get_dynamic_dashboard(refresh: bool = False):
    """Serve the latest dynamic visual dashboard"""
    try:
        path = orchestrator.dashboard_dir / "dynamic.html"
        
        # Force refresh or auto-retry if it's an old failure page
        should_generate = refresh or not path.exists()
        
        if path.exists() and not should_generate:
            # Check if it's a failure page (contains specific error text)
            # This helps users get the new v0.9.9 diagnostics even if they have an old cache
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if "Dashboard Generation Failed" in content:
                    print("🔄 Detected failure page, attempting auto-refresh...")
                    should_generate = True

        if should_generate:
            if orchestrator:
                print("🎨 Generating dynamic dashboard...")
                await orchestrator.generate_visual_dashboard()
            else:
                if not path.exists():
                    raise HTTPException(status_code=503, detail="Dashboard not found and Orchestrator busy")
                
        if not path.exists():
            raise HTTPException(status_code=404, detail="Dashboard file could not be generated")
            
        return FileResponse(path)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Dashboard Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


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
        "version": VERSION,
        "gemini_active": orchestrator._genai_client is not None if orchestrator else False,
        "use_gemini_for_dashboard": orchestrator.use_gemini_for_dashboard if orchestrator else False,
        "gemini_model_name": orchestrator.gemini_model_name if orchestrator else "gemini-1.5-pro",
        "agents": {
            k: getattr(v, "model_name", "unknown") for k, v in agents.items()
        }
    }


class UpdateConfigRequest(BaseModel):
    dry_run_mode: Optional[bool] = None
    use_gemini_for_dashboard: Optional[bool] = None
    gemini_api_key: Optional[str] = None
    gemini_model_name: Optional[str] = None


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
            
    if orchestrator:
        if req.use_gemini_for_dashboard is not None:
            orchestrator.use_gemini_for_dashboard = req.use_gemini_for_dashboard
            print(f"🔄 Runtime Config Update: Use Gemini for Dashboard set to {req.use_gemini_for_dashboard}")
        
        if req.gemini_api_key is not None:
            orchestrator.gemini_api_key = req.gemini_api_key
            # Re-initialize Gemini client with new key using new SDK
            try:
                from google import genai as _genai_module
                orchestrator._genai_client = _genai_module.Client(api_key=req.gemini_api_key)
                orchestrator.gemini_model = True
            except ImportError:
                orchestrator._genai_client = None
                orchestrator.gemini_model = None
            print(f"🔄 Runtime Config Update: Gemini API Key updated")

        if req.gemini_model_name is not None:
            orchestrator.gemini_model_name = req.gemini_model_name
            print(f"🔄 Runtime Config Update: Gemini Model set to {req.gemini_model_name}")

    return {
        "status": "success", 
        "dry_run_mode": mcp_server.dry_run if mcp_server else None,
        "use_gemini_for_dashboard": orchestrator.use_gemini_for_dashboard if orchestrator else None,
        "gemini_model_name": orchestrator.gemini_model_name if orchestrator else None
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
    # Explicitly mount /assets to handle rewritten Ingress paths correctly
    assets_path = dashboard_path / "assets"
    if assets_path.exists():
        app.mount("/assets", SafeStaticFiles(directory=str(assets_path)), name="assets")
        print(f"  ✓ Explicitly mounted /assets from {assets_path}")
    
    app.mount("/", SafeStaticFiles(directory=str(dashboard_path), html=True), name="static")
else:
    print(f"⚠️ Dashboard bundle not found at {dashboard_path}")
    
    @app.get("/")
    async def root():
        return {
            "message": "AI Orchestrator Backend is Running",
            "status": "No dashboard found. Please ensure the frontend was built.",
            "mode": "API Only"
        }
