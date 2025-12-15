"""
Base agent class providing common functionality for all specialist agents.
"""
import os
import json
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import ollama
from ha_client import HAWebSocketClient
from mcp_server import MCPServer


class BaseAgent(ABC):
    """
    Abstract base class for all specialist agents.
    Provides common functionality for LLM calls, decision logging, and tool execution.
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        mcp_server: MCPServer,
        ha_client: HAWebSocketClient,
        skills_path: str,
        model_name: str = "mistral:7b-instruct",
        decision_interval: int = 120
    ):
        """
        Initialize base agent.
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable agent name
            mcp_server: MCP server for tool execution
            ha_client: Home Assistant WebSocket client
            skills_path: Path to SKILLS.md file
            model_name: Ollama model name
            decision_interval: Seconds between decisions
        """
        self.agent_id = agent_id
        self.name = name
        self.mcp_server = mcp_server
        self.ha_client = ha_client
        self.skills_path = Path(skills_path)
        self.model_name = model_name
        self.decision_interval = decision_interval
        self.status = "initializing"
        
        # Load skills from SKILLS.md
        self.skills = self.load_skills()
        
        # Ollama client
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_client = ollama.Client(host=ollama_host)
        
        # Decision storage
        self.decision_dir = Path("/data/decisions") / agent_id
        self.decision_dir.mkdir(parents=True, exist_ok=True)
    
    def load_skills(self) -> Dict:
        """
        Load and parse SKILLS.md file.
        
        Returns:
            Dict containing parsed skill information
        """
        if not self.skills_path.exists():
            print(f"⚠️ SKILLS.md not found at {self.skills_path}, using defaults")
            return {
                "identity": f"{self.name} agent",
                "controllable_entities": [],
                "observable_entities": [],
                "tools": [],
                "decision_criteria": {},
                "performance_targets": {}
            }
        
        with open(self.skills_path, "r") as f:
            content = f.read()
        
        # Basic parsing (can be enhanced with proper markdown parser)
        skills = {
            "identity": self._extract_section(content, "Identity"),
            "controllable_entities": self._extract_list(content, "Controllable Entities"),
            "observable_entities": self._extract_list(content, "Observable Entities"),
            "tools": self._extract_section(content, "Available Tools"),
            "decision_criteria": self._extract_section(content, "Decision Criteria"),
            "performance_targets": self._extract_section(content, "Performance Targets"),
            "full_content": content
        }
        
        return skills
    
    def _extract_section(self, content: str, heading: str) -> str:
        """Extract content from a markdown section"""
        lines = content.split("\n")
        in_section = False
        section_lines = []
        
        for line in lines:
            if heading.lower() in line.lower() and line.startswith("#"):
                in_section = True
                continue
            if in_section:
                if line.startswith("#"):
                    break
                section_lines.append(line)
        
        return "\n".join(section_lines).strip()
    
    def _extract_list(self, content: str, heading: str) -> List[str]:
        """Extract list items from a markdown section"""
        section = self._extract_section(content, heading)
        items = []
        for line in section.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                items.append(line.lstrip("-*").strip().strip("`"))
        return items
    
    async def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Call Ollama LLM with streaming.
        
        Args:
            prompt: Prompt text
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text
        """
        try:
            response = self.ollama_client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                },
                stream=False
            )
            
            return response["message"]["content"]
        
        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            return f"ERROR: {str(e)}"
    
    def _build_system_prompt(self) -> str:
        """Build system prompt from SKILLS.md"""
        return f"""You are {self.skills['identity']}.

Your role is to make intelligent decisions about home automation based on current conditions.

Available Tools:
{self.skills['tools']}

Decision Criteria:
{self.skills['decision_criteria']}

Respond with a JSON object containing your decision in this format:
{{
  "reasoning": "Brief explanation of why you made this decision",
  "actions": [
    {{
      "tool": "tool_name",
      "parameters": {{
        "param1": "value1"
      }}
    }}
  ]
}}

If no action is needed, return an empty actions array.
"""
    
    @abstractmethod
    async def decide(self, context: Dict) -> Dict:
        """
        Make a decision based on current context.
        Must be implemented by specialist agents.
        
        Args:
            context: Current state and context information
        
        Returns:
            Decision dict with reasoning and actions
        """
        pass
    
    async def execute(self, decision: Dict) -> List[Dict]:
        """
        Execute decision actions using MCP tools.
        
        Args:
            decision: Decision dict from decide()
        
        Returns:
            List of execution results
        """
        actions = decision.get("actions", [])
        results = []
        
        for action in actions:
            tool_name = action["tool"]
            parameters = action["parameters"]
            
            result = await self.mcp_server.execute_tool(
                tool_name=tool_name,
                parameters=parameters,
                agent_id=self.agent_id
            )
            
            results.append({
                "tool": tool_name,
                "parameters": parameters,
                "result": result
            })
        
        return results
    
    def log_decision(self, context: Dict, decision: Dict, results: List[Dict]):
        """Save decision to log file"""
        timestamp = datetime.now()
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "agent_id": self.agent_id,
            "context": context,
            "decision": decision,
            "execution_results": results,
            "dry_run": self.mcp_server.dry_run
        }
        
        log_file = self.decision_dir / f"{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)
    
    def get_last_decision_file(self) -> Optional[Path]:
        """Get path to most recent decision log"""
        decision_files = sorted(self.decision_dir.glob("*.json"), reverse=True)
        return decision_files[0] if decision_files else None
    
    async def run_decision_loop(self):
        """Main decision loop that runs continuously"""
        self.status = "idle"
        print(f"✓ {self.name} decision loop started (interval: {self.decision_interval}s)")
        
        while True:
            try:
                await asyncio.sleep(self.decision_interval)
                
                self.status = "deciding"
                
                # Make decision
                context = await self.gather_context()
                decision = await self.decide(context)
                
                # Execute decision
                results = await self.execute(decision)
                
                # Log decision
                self.log_decision(context, decision, results)
                
                # Broadcast to dashboard
                # (main.py will hook this in)
                
                self.status = "idle"
                print(f"✓ {self.name} decision completed")
            
            except Exception as e:
                self.status = "error"
                print(f"❌ {self.name} decision loop error: {e}")
                await asyncio.sleep(10)  # Back off on error
    
    @abstractmethod
    async def gather_context(self) -> Dict:
        """
        Gather current context for decision making.
        Must be implemented by specialist agents.
        
        Returns:
            Context dict with current state
        """
        pass
