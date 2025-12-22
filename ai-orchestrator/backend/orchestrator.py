"""
Central Orchestrator for Multi-Agent Coordination.
Uses LangGraph workflow to plan, distribute tasks, resolve conflicts, and execute.
"""
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

import ollama
import os
import google.generativeai as genai
from workflow_graph import (
    OrchestratorState, Task, Decision, Conflict,
    create_workflow
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central coordinator for multi-agent system.
    Plans tasks, distributes to specialists, resolves conflicts, manages approvals.
    """
    
    def __init__(
        self,
        ha_client,
        mcp_server,
        approval_queue,
        agents: Dict[str, any],
        model_name: str = "deepseek-r1:8b",
        planning_interval: int = 120,
        ollama_host: str = "http://localhost:11434",
        gemini_api_key: Optional[str] = None,
        use_gemini_for_dashboard: bool = False,
        gemini_model_name: str = "gemini-1.5-pro"
    ):
        """
        Initialize orchestrator.
        
        Args:
            ha_client: Home Assistant WebSocket client
            mcp_server: MCP server for tool execution
            approval_queue: ApprovalQueue instance
            agents: Dict of {agent_id: agent_instance}
            model_name: Ollama model for planning (default: deepseek-r1:8b)
            planning_interval: Seconds between planning cycles
            ollama_host: Host URL for Ollama API
            gemini_api_key: Optional Google AI API Key
            use_gemini_for_dashboard: Whether to prioritize Gemini for visual dashboard
            gemini_model_name: Gemini model to use (default: gemini-1.5-pro)
        """
        self._ha_provider = ha_client
        self.mcp_server = mcp_server
        self.approval_queue = approval_queue
        
        self.agents = agents
        self.model_name = model_name
        self.planning_interval = planning_interval
        
        # LangGraph workflow
        self.workflow = create_workflow()


        self.compiled_workflow = self.workflow.compile()
        
        # Ollama client for planning LLM
        self.ollama_client = ollama.Client(host=ollama_host)
        self.llm_client = self.ollama_client # Reference for other methods
        self.ollama_host_used = ollama_host
        
        # Task and progress tracking
        self.task_ledger: List[Task] = []
        self.progress_ledger: Dict[str, Dict] = {}
        
        # Conflict resolution rules
        self.conflict_rules = self._load_conflict_rules()
        
        # Dashboard and logging
        self.decision_log_dir = Path("/data/decisions/orchestrator")
        if not os.access("/", os.W_OK) and not self.decision_log_dir.exists():
             self.decision_log_dir = Path(__file__).parent.parent / "data" / "decisions" / "orchestrator"
        self.decision_log_dir.mkdir(parents=True, exist_ok=True)
        
        self.dashboard_dir = Path("/data/dashboard")
        # Check if we are in a HA Add-on environment (which has /data)
        # On Windows, Path("/") resolves to C:\ which might exist but we want to stay in workspace for local dev
        is_addon = os.path.exists("/data") and os.access("/data", os.W_OK)
        
        if not is_addon:
             # Fallback to workspace-local data directory
             self.dashboard_dir = Path(__file__).parent.parent / "data" / "dashboard"
        
        self.dashboard_dir.mkdir(parents=True, exist_ok=True)
        
        # Gemini setup (optional)
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.use_gemini_for_dashboard = use_gemini_for_dashboard or os.getenv("USE_GEMINI_FOR_DASHBOARD", "false").lower() == "true"
        self.gemini_model_name = gemini_model_name or os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro")

        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(self.gemini_model_name)
            logger.info(f"Gemini API detected - visual dashboard configured to use {self.gemini_model_name} (Active: {self.use_gemini_for_dashboard}).")
        else:
            self.gemini_model = None
            logger.info("No Gemini API key found - visual dashboard will fallback to Ollama.")
            
        self.last_dashboard_instruction = "Mixergy-style smart home dashboard"
        self.dashboard_refresh_interval = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", "300")) # 5 minutes
        
        logger.info(f"Orchestrator initialized with model: {model_name}")
        logger.info(f"Managing {len(agents)} specialist agents: {list(agents.keys())}")
    
    def _load_conflict_rules(self) -> Dict:
        """Load conflict resolution rules"""
        return {
            "heating_cooling": {
                "agents": ["heating", "cooling"],
                "rule": "disable_both",
                "reason": "Cannot heat and cool same zone simultaneously"
            },
            "security_automation": {
                "agents": ["security", "lighting"],
                "rule": "security_priority",
                "reason": "Security settings override comfort automation"
            },
            "away_comfort": {
                "agents": ["heating", "cooling"],
                "rule": "eco_mode",
                "reason": "Away mode overrides comfort targets"
            }
        }
    
    async def run_planning_loop(self):
        """Main orchestration loop - runs every planning_interval seconds"""
        logger.info(f"Starting orchestrator planning loop (interval: {self.planning_interval}s)")
        
        while True:
            try:
                await self.execute_workflow()
                await asyncio.sleep(self.planning_interval)
            except Exception as e:
                logger.error(f"Error in planning loop: {e}", exc_info=True)
                await asyncio.sleep(self.planning_interval)

    async def run_dashboard_refresh_loop(self):
        """Periodically refresh the visual dashboard with latest states"""
        logger.info(f"Starting dashboard refresh loop (interval: {self.dashboard_refresh_interval}s)")
        # Small delay to let system initialize
        await asyncio.sleep(10)
        
        while True:
            try:
                # Only refresh if the file exists or if we have an instruction
                await self.generate_visual_dashboard(user_instruction=self.last_dashboard_instruction)
                await asyncio.sleep(self.dashboard_refresh_interval)
            except Exception as e:
                logger.error(f"Error in dashboard refresh loop: {e}")
                await asyncio.sleep(self.dashboard_refresh_interval)
    
    async def execute_workflow(self):
        """Execute one complete workflow cycle"""
        start_time = datetime.now()
        
        # Initialize state
        initial_state: OrchestratorState = {
            "timestamp": start_time.isoformat(),
            "home_state": await self._get_home_state(),
            "tasks": [],
            "decisions": [],
            "conflicts": [],
            "approval_required": False,
            "approved_actions": [],
            "rejected_actions": [],
            "execution_results": []
        }
        
        logger.info("=== Starting orchestrator workflow cycle ===")
        
        # Execute workflow through all nodes
        final_state = await self._run_workflow(initial_state)
        
        # Log cycle completion
        duration = (datetime.now() - start_time).total_seconds()
        await self._log_cycle(final_state, duration)
        
        logger.info(f"=== Workflow cycle completed in {duration:.2f}s ===")
    
    async def _run_workflow(self, initial_state: OrchestratorState) -> OrchestratorState:
        """Run workflow with actual node implementations"""
        state = initial_state
        
        # Plan: Create tasks for agents
        state = await self.plan(state)
        
        # Distribute: Send tasks to agents
        state = await self.distribute_tasks(state)
        
        # Wait: Collect agent responses
        state = await self.wait_for_agents(state)
        
        # Aggregate: Combine decisions  
        state = await self.aggregate_decisions(state)
        
        # Check conflicts: Resolve conflicting actions
        state = await self.resolve_conflicts(state)
        
        # Check approval: Route high-impact to queue
        state = await self.check_approval_requirements(state)
        
        # Execute: Run approved actions
        if state["approved_actions"]:
            state = await self.execute_approved_actions(state)
        
        return state
    
    async def plan(self, state: OrchestratorState) ->OrchestratorState:
        """Analyze home state and create tasks for specialist agents"""
        home_state = state["home_state"]
        
        # Build planning prompt
        prompt = self._build_planning_prompt(home_state)
        
        # Call LLM for high-level planning
        try:
            response = self.llm_client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an AI orchestrator for home automation. Analyze the current home state and create tasks for specialist agents (heating, cooling, lighting, security)."},
                    {"role": "user", "content": prompt}
                ],
                format="json"
            )
            
            plan = json.loads(response["message"]["content"])
            tasks = plan.get("tasks", [])
            
            # Convert to Task objects
            state["tasks"] = [
                Task(
                    task_id=f"task_{i}",
                    agent_id=task["agent"],
                    description=task["description"],
                    priority=task.get("priority", "medium"),
                    context=task.get("context", {})
                )
                for i, task in enumerate(tasks)
            ]
            
            logger.info(f"Planned {len(state['tasks'])} tasks for agents")
            
        except Exception as e:
            logger.error(f"Planning error: {e}")
            state["tasks"] = []
        
        return state
    
    def _build_planning_prompt(self, home_state: Dict) -> str:
        """Build prompt for orchestrator planning"""
        return f"""
Current Home State:
{json.dumps(home_state, indent=2)}

Available Agents:
- heating: Controls climate entities (heating mode)
- cooling: Controls climate entities (cooling mode)
- lighting: Controls lights and scenes
- security: Controls alarms, locks, cameras

Create a task list assigning work to specialist agents. Return JSON format:
{{
  "tasks": [
    {{
      "agent": "heating",
      "description": "Adjust bedroom temperature",
      "priority": "medium",
      "context": {{"target_temp": 21.0}}
    }}
  ]
}}

Only create tasks if action is needed. Return empty tasks array if everything is optimal.
"""
    
    async def distribute_tasks(self, state: OrchestratorState) -> OrchestratorState:
        """Distribute tasks to specialist agents"""
        for task in state["tasks"]:
            agent = self.agents.get(task["agent_id"])
            if agent:
                # Store in task ledger
                self.task_ledger.append(task)
                
                # Send task to agent (agent will process asynchronously)
                if hasattr(agent, 'receive_task'):
                    asyncio.create_task(agent.receive_task(task))
                    logger.debug(f"Distributed task {task['task_id']} to {task['agent_id']}")
            else:
                logger.warning(f"Agent {task['agent_id']} not found")
        
        return state
    
    async def wait_for_agents(self, state: OrchestratorState, timeout: int = 30) -> OrchestratorState:
        """Wait for all agents to respond with decisions"""
        # In real implementation, would use asyncio.gather with timeout
        # For now, simulate immediate response
        await asyncio.sleep(1)
        return state
    
    async def aggregate_decisions(self, state: OrchestratorState) -> OrchestratorState:
        """Collect decisions from all agents"""
        # Collect from progress ledger (agents update this)
        decisions = []
        for agent_id, progress in self.progress_ledger.items():
            if progress.get("decision"):
                decisions.append(progress["decision"])
        
        state["decisions"] = decisions
        logger.info(f"Aggregated {len(decisions)} decisions")
        
        return state
    
    async def resolve_conflicts(self, state: OrchestratorState) -> OrchestratorState:
        """Detect and resolve conflicts between agent decisions"""
        conflicts = []
        decisions = state["decisions"]
        
        # Check heating vs cooling conflict
        heating_active = any(d["agent_id"] == "heating" and d["actions"] for d in decisions)
        cooling_active = any(d["agent_id"] == "cooling" and d["actions"] for d in decisions)
        
        if heating_active and cooling_active:
            conflicts.append(Conflict(
                conflict_id="conflict_heating_cooling",
                agent_ids=["heating", "cooling"],
                conflict_type="mutual_exclusion",
                description="Cannot heat and cool simultaneously",
                resolution="disable_both"
            ))
            
            # Remove conflicting actions
            state["decisions"] = [
                d for d in decisions 
                if d["agent_id"] not in ["heating", "cooling"]
            ]
            logger.warning("Resolved heating/cooling conflict - disabled both")
        
        state["conflicts"] = conflicts
        return state
    
    async def check_approval_requirements(self, state: OrchestratorState) -> OrchestratorState:
        """Check if actions require human approval"""
        approved = []
        requires_approval = []
        
        for decision in state["decisions"]:
            for action in decision["actions"]:
                # Check impact level
                if decision.get("impact_level") in ["high", "critical"]:
                    requires_approval.append(action)
                else:
                    approved.append(action)
        
        if requires_approval:
            # Queue for approval
            for action in requires_approval:
                await self.approval_queue.add_request(action)
            
            state["approval_required"] = True
            logger.info(f"{len(requires_approval)} actions queued for approval")
        
        state["approved_actions"] = approved
        return state
    
    async def execute_approved_actions(self, state: OrchestratorState) -> OrchestratorState:
        """Execute approved actions via MCP server"""
        results = []
        
        for action in state["approved_actions"]:
            try:
                result = await self.mcp_server.execute_tool(
                    tool_name=action["tool"],
                    parameters=action["parameters"],
                    agent_id="orchestrator"
                )
                results.append(result)
                logger.info(f"Executed {action['tool']}: {result}")
            except Exception as e:
                logger.error(f"Execution error: {e}")
                results.append({"error": str(e)})
        
        state["execution_results"] = results
        return state
    
    async def _get_home_state(self) -> Dict:
        """Get current state of all Home Assistant entities"""
        try:
            # Get all climate entities
            climate_states = {}
            for agent_id, agent in self.agents.items():
                if hasattr(agent, 'get_entity_states'):
                    states = await agent.get_entity_states()
                    climate_states[agent_id] = states
            
            return {
                "climate": climate_states,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting home state: {e}")
            return {}
    
    async def _log_cycle(self, state: OrchestratorState, duration: float):
        """Log orchestrator cycle to file"""
        log_entry = {
            "timestamp": state["timestamp"],
            "duration_seconds": duration,
            "tasks_created": len(state["tasks"]),
            "decisions_received": len(state["decisions"]),
            "conflicts_detected": len(state["conflicts"]),
            "actions_approved": len(state["approved_actions"]),
            "actions_executed": len(state["execution_results"]),
            "approval_required": state["approval_required"]
        }
        
        log_file = self.decision_log_dir / f"{state['timestamp'].replace(':', '-')}.json"
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)
    async def process_chat_request(self, user_message: str) -> Dict[str, Any]:
        """
        Process a direct chat message from the user.
        Acts as a general-purpose home assistant.
        """
        # 1. Gather Context
        try:
            states = await self.ha_client.get_states()
            # Summarize states to fit context (first 60 interesting ones)
            relevant_domains = ['light', 'switch', 'climate', 'lock', 'cover', 'media_player', 'vacuum']
            state_desc = []
            for s in states:
                if s['entity_id'].split('.')[0] in relevant_domains:
                    friendly = s.get('attributes', {}).get('friendly_name', s['entity_id'])
                    state_desc.append(f"- {friendly} ({s['entity_id']}): {s['state']}")
            
            context_str = "\n".join(state_desc[:60]) # Limit to 60 items
        except Exception as e:
            logger.error(f"Chat Context Error: {e}")
            context_str = "Error fetching home state."

        # 2. Build Prompt
        prompt = f"""
You are the AI Orchestrator for this home. 
The user is asking you a question or giving a command.

CURRENT HOME STATE:
{context_str}

AVAILABLE TOOLS:
- call_ha_service: Execute Home Assistant services. Params: domain, service, entity_id, service_data.
- generate_visual_dashboard: Create or update the dynamic visual dashboard. Params: user_instruction (string describing the dashboard style or purpose).

USER MESSAGE: "{user_message}"

INSTRUCTIONS:
1. If this is a question, answer it based on the home state.
2. If this is a command (e.g. "Turn on light"), execute it using the 'call_ha_service' tool.
3. You can execute multiple tools if needed.
4. Respond with a JSON object:
{{
  "thought": "Reasoning here...",
  "response": "Natural language response to user...",
  "actions": [
    {{ "tool": "call_ha_service", "parameters": {{ ... }} }}
  ]
}}
5. NO COMMENTS in JSON.
"""

        # 3. Call LLM
        try:
            response = self.llm_client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                format="json"
            )
            content = response["message"]["content"]
        except Exception as e:
            logger.error(f"LLM Chat Error: {e}")
            import os
            host = os.getenv("OLLAMA_HOST", "localhost")
            return {
                "response": f"⚠️ **Communication Error**: I couldn't reach my brain ({self.model_name}).\n\nTechnical Details:\n- Host: `{host}`\n- Error: `{str(e)}`",
                "actions_executed": []
            }

        # 4. Parse & Execute
        try:
            # Strip comments if any (safety)
            import re
            content = re.sub(r'//.*', '', content)
            
            data = json.loads(content)
            
            execution_results = []
            if "actions" in data:
                for action in data["actions"]:
                    # Handle both tool naming conventions
                    tool_name = action.get("tool")
                    params = action.get("parameters", {})
                    
                    if tool_name in ["call_ha_service", "execute_service"]:
                        # Safety fallback
                        if not params.get("entity_id") and not params.get("area_id"):
                             # If missing, we might skip or let MCP catch it
                             pass
                             
                        try:
                            res = await self.mcp_server.execute_tool(
                                tool_name="call_ha_service",
                                parameters=params
                            )
                            # Create a readable summary
                            summary = f"Executed {params.get('service')} on {params.get('entity_id')}"
                            execution_results.append({"tool": summary, "result": res})
                        except Exception as tool_err:
                            execution_results.append({"tool": "Failed", "error": str(tool_err)})
                    
                    elif tool_name == "generate_visual_dashboard" or (tool_name == "execute_tool" and params.get("tool_name") == "generate_visual_dashboard"):
                        user_inst = params.get("user_instruction", self.last_dashboard_instruction)
                        self.last_dashboard_instruction = user_inst
                        try:
                            html = await self.generate_visual_dashboard(user_instruction=user_inst)
                            execution_results.append({"tool": "Generated Dashboard", "result": f"Length: {len(html)} bytes"})
                        except Exception as dash_err:
                            execution_results.append({"tool": "Dashboard Failed", "error": str(dash_err)})

            return {
                "response": data.get("response", "I've processed your request."),
                "actions_executed": execution_results
            }
            
        except json.JSONDecodeError:
            logger.error(f"LLM JSON Error: {content}")
            return {
                "response": "I had trouble structuring my thoughts (JSON Error). Please try again.",
                "actions_executed": []
            }
        except Exception as e:
            logger.error(f"Chat Execution Error: {e}")
            return {
                "response": f"I encountered an unexpected error: {str(e)}",
                "actions_executed": []
            }
    async def generate_visual_dashboard(self, user_instruction: str = "Mixergy-style smart home dashboard") -> str:
        """
        Generate a high-fidelity dashboard based on current home state and user instructions.
        Returns the generated HTML.
        """
        logger.info("🎨 Generating dynamic visual dashboard...")
        
        # 1. Gather Context
        client = self.ha_client
        if not client or not client.connected:
            logger.warning("⚠️ Cannot generate dashboard: Home Assistant not connected.")
            raise Exception("Home Assistant not connected. Please check your configuration.")

        states = await client.get_states()
        
        if not states:
            logger.warning("⚠️ No entities found in Home Assistant.")
            raise Exception("No entities found. Check if your Home Assistant user has access to any entities.")
        
        # Filter for interesting entities (Energy, Climate, Security, etc.)
        relevant_domains = ['sensor', 'climate', 'light', 'binary_sensor', 'switch', 'lock']
        relevant_states = [s for s in states if s['entity_id'].split('.')[0] in relevant_domains]
        
        # Limit context size
        data_json = json.dumps(relevant_states[:30], indent=2)
        
        # 2. Build Prompt (The 'Mixergy' style prompt)
        system_prompt = f"""
You are a World-Class Data Visualization Expert and UI Designer specializing in High-End Smart Home Dashboards.
Your goal is to create a dynamic, skeuomorphic dashboard using a standalone HTML/Tailwind CSS file.

USER REQUESTED STYLE/FUNCTION: "{user_instruction}"

DESIGN SPECIFICATION (IT MUST 'WOW' THE USER):
1. THEME: Default is "Deep Ocean" (bg-slate-900, glassmorphism, neon blue/purple accents) unless the user requested otherwise.
2. LAYOUT: Follow a 3-column grid unless specified otherwise:
    - LEFT (Control): Compact cards for binary sensors and quick toggles.
    - CENTER (Hero): A "Skeuomorphic Central Visual". For energy/water, use a pill-shaped glass tank (backdrop-blur-md) with a CSS gradient fill. 
      - CRITICAL: Add animated rising bubbles (CSS @keyframes) if state is 'charging', 'heating', or 'active'.
      - Use ring-2 glow effects for active containers.
    - RIGHT (Analytics): Cost cards and performance stats with mini-charts (using CSS/divs or simple SVG).
3. FIDELITY:
    - Use Lucide Icons (via CDN: https://unpkg.com/lucide@latest).
    - Implement heavy glassmorphism (backdrop-blur, border-white/20).
    - Every level change must have a smooth CSS transition.
    - Add "glow" accents (shadow-blue-500/50, text-shadow).

DATA INTEGRATION:
- Map the Home Assistant states provided below to these components.
- If a sensor name contains 'charge' or 'hot water', map it to the Central Tank Visual.

OUTPUT REQUIREMENTS:
- Provide ONLY the complete, standalone HTML/CSS/JS code.
- No markdown wrappers, no explanations. Just the HTML.
- Ensure all CSS and JS are embedded in the single file.
"""
        user_prompt = f"Generate the following dashboard: {user_instruction}\n\nHome Assistant Data:\n\n{data_json}"

        # 3. Call LLM (Gemini preferred, Ollama fallback)
        html_content = ""
        try:
            if self.gemini_model and self.use_gemini_for_dashboard:
                # Use Gemini for best design results
                logger.info(f"Generating dashboard using Gemini model: {self.gemini_model_name}")
                response = self.gemini_model.generate_content([system_prompt, user_prompt])
                html_content = response.text
            else:
                # Fallback to local Ollama (might be less 'poppy' but functional)
                response = self.llm_client.chat(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                html_content = response["message"]["content"]
            
            # Clean up markdown code blocks if present
            import re
            html_content = re.sub(r'^```html\s*', '', html_content, flags=re.MULTILINE)
            html_content = re.sub(r'^```\s*$', '', html_content, flags=re.MULTILINE)
            html_content = html_content.strip()
            
            # 4. Save to /data/dashboard/dynamic.html
            output_path = self.dashboard_dir / "dynamic.html"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            logger.info(f"✅ Dynamic dashboard generated at {output_path}")
            return html_content
            
        except Exception as e:
            host_info = getattr(self.ollama_client, '_client', {}).get('base_url', 'unknown') if hasattr(self.ollama_client, '_client') else 'unknown'
            logger.error(f"❌ Failed to generate dashboard: {e} (Host: {host_info})")
            fallback_html = f"""
            <html>
            <body style="background: #0f172a; color: #f1f5f9; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column;">
                <h1 style="color: #ef4444;">Dashboard Generation Failed</h1>
                <p><b>Error:</b> {str(e)}</p>
                <div style="background: #1e293b; padding: 20px; border-radius: 8px; font-family: monospace; font-size: 12px; margin-top: 20px; border-left: 4px solid #ef4444;">
                    <b>Diagnostics:</b><br/>
                    - LLM Host: <code>{host_info}</code><br/>
                    - Model: <code>{self.model_name}</code><br/>
                    - Gemini API: <code>{'Enabled' if self.gemini_model else 'Disabled (Falling back to local)'}</code>
                </div>
                <div style="margin-top: 20px; max-width: 600px; text-align: center;">
                    <p>If you see "No route to host" or "Connection refused", ensure your <b>Ollama Host</b> matches your LAN IP if running in Docker.</p>
                </div>
                <button onclick="window.location.reload()" style="margin-top: 20px; background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">Try Again</button>
            </body>
            </html>
            """
            try:
                output_path = self.dashboard_dir / "dynamic.html"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(fallback_html)
            except Exception as save_err:
                logger.error(f"Could not save fallback HTML: {save_err}")
            return fallback_html

    @property
    def ha_client(self):
        if callable(self._ha_provider):
            return self._ha_provider()
        return self._ha_provider
