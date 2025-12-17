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
        planning_interval: int = 120
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
        """
        self.ha_client = ha_client
        self.mcp_server = mcp_server
        self.approval_queue = approval_queue
        self.agents = agents
        self.model_name = model_name
        self.planning_interval = planning_interval
        
        # LangGraph workflow
        self.workflow = create_workflow()
        self.compiled_workflow = self.workflow.compile()
        
        # Ollama client for planning LLM
        self.llm_client = ollama.Client()
        
        # Task and progress tracking
        self.task_ledger: List[Task] = []
        self.progress_ledger: Dict[str, Dict] = {}
        
        # Conflict resolution rules
        self.conflict_rules = self._load_conflict_rules()
        
        # Logging
        self.decision_log_dir = Path("/data/decisions/orchestrator")
        self.decision_log_dir.mkdir(parents=True, exist_ok=True)
        
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
        try:
            # 1. Gather Context
            states = await self.ha_client.get_states()
            # Summarize states to fit context (first 50 interesting ones?)
            # Simplified for chat: just list names/ids of lights/switches/climate
            relevant_domains = ['light', 'switch', 'climate', 'lock', 'cover', 'media_player', 'vacuum']
            state_desc = []
            for s in states:
                if s['entity_id'].split('.')[0] in relevant_domains:
                    friendly = s.get('attributes', {}).get('friendly_name', s['entity_id'])
                    state_desc.append(f"- {friendly} ({s['entity_id']}): {s['state']}")
            
            context_str = "\n".join(state_desc[:60]) # Limit to 60 items
            
            # 2. Build Prompt
            prompt = f"""
You are the AI Orchestrator for this home. 
The user is asking you a question or giving a command.

CURRENT HOME STATE:
{context_str}

AVAILABLE TOOLS:
- call_ha_service: Execute Home Assistant services. Params: domain, service, entity_id, service_data.

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
            response = self.llm_client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                format="json"
            )
            
            content = response["message"]["content"]
            
            # 4. Parse & Execute
            # Strip comments if any (safety)
            import re
            content = re.sub(r'//.*', '', content)
            
            data = json.loads(content)
            
            execution_results = []
            if "actions" in data:
                for action in data["actions"]:
                    if action.get("tool") == "call_ha_service" or action.get("tool") == "execute_service":
                        # Execute logic using MCP
                        # Map generic params to MCP strict structure
                        params = action.get("parameters", {})
                        
                        # Safety: Ensure entity_id is provided logic
                        if not params.get("entity_id") and not params.get("area_id"):
                             # If missing, maybe warn user? or fail?
                             pass
                             
                        res = await self.mcp_server.execute_tool(
                            tool_name="call_ha_service",
                            parameters=params,
                            agent_id="orchestrator_chat"
                        )
                        execution_results.append(res)
            
            return {
                "response": data.get("response", "Done."),
                "actions_executed": execution_results
            }

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "response": f"I encountered an error processing your request: {e}",
                "actions_executed": []
            }
