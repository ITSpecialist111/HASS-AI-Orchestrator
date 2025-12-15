"""
Model Context Protocol (MCP) server for Home Assistant tool execution.
Provides tools for agents to interact with HA services safely.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from ha_client import HAWebSocketClient


class SetTemperatureParams(BaseModel):
    """Parameters for set_temperature tool"""
    entity_id: str = Field(..., description="Climate entity ID")
    temperature: float = Field(..., ge=10.0, le=30.0, description="Target temperature (10-30°C)")
    hvac_mode: Optional[str] = Field(None, description="HVAC mode: heat, cool, auto, off")
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        if not (10.0 <= v <= 30.0):
            raise ValueError("Temperature must be between 10°C and 30°C")
        return round(v, 1)


class SetHVACModeParams(BaseModel):
    """Parameters for set_hvac_mode tool"""
    entity_id: str = Field(..., description="Climate entity ID")
    hvac_mode: str = Field(..., description="HVAC mode: heat, cool, auto, off")
    
    @field_validator("hvac_mode")
    @classmethod
    def validate_mode(cls, v):
        valid_modes = ["heat", "cool", "auto", "off", "dry", "fan_only"]
        if v not in valid_modes:
            raise ValueError(f"Invalid HVAC mode. Must be one of: {valid_modes}")
        return v


class MCPServer:
    """
    Model Context Protocol server for Home Assistant.
    Registers and executes tools with safety checks.
    """
    
    def __init__(self, ha_client: HAWebSocketClient, dry_run: bool = True):
        """
        Initialize MCP server.
        
        Args:
            ha_client: Connected Home Assistant WebSocket client
            dry_run: If True, log actions without executing
        """
        self.ha_client = ha_client
        self.dry_run = dry_run
        self.tools = self._register_tools()
        self.log_dir = Path("/data/decisions")
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _register_tools(self) -> Dict[str, Dict]:
        """Register available tools with schemas"""
        return {
            "set_temperature": {
                "name": "set_temperature",
                "description": "Set target temperature for a climate entity",
                "parameters": SetTemperatureParams.model_json_schema(),
                "handler": self._set_temperature
            },
            "get_climate_state": {
                "name": "get_climate_state",
                "description": "Get current state of a climate entity",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Climate entity ID"
                        }
                    },
                    "required": ["entity_id"]
                },
                "handler": self._get_climate_state
            },
            "set_hvac_mode": {
                "name": "set_hvac_mode",
                "description": "Set HVAC mode for a climate entity",
                "parameters": SetHVACModeParams.model_json_schema(),
                "handler": self._set_hvac_mode
            }
        }
    
    def get_tool_schemas(self) -> list[Dict]:
        """Get tool schemas for LLM prompt"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for tool in self.tools.values()
        ]
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        agent_id: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Execute a tool with safety checks and logging.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            agent_id: ID of agent making the call
        
        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        
        tool = self.tools[tool_name]
        
        # Log tool call
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "tool": tool_name,
            "parameters": parameters,
            "dry_run": self.dry_run
        }
        
        try:
            # Execute tool handler
            result = await tool["handler"](parameters)
            log_entry["result"] = result
            log_entry["status"] = "success"
            
            # Save log
            self._save_log(agent_id, log_entry)
            
            return result
        
        except Exception as e:
            error_msg = str(e)
            log_entry["error"] = error_msg
            log_entry["status"] = "error"
            self._save_log(agent_id, log_entry)
            
            return {"error": error_msg}
    
    def _save_log(self, agent_id: str, log_entry: Dict):
        """Save tool execution log to file"""
        agent_log_dir = self.log_dir / agent_id
        agent_log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        log_file = agent_log_dir / f"{timestamp}.json"
        
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)
    
    async def _set_temperature(self, params: Dict) -> Dict:
        """Set temperature tool handler"""
        # Validate parameters
        validated = SetTemperatureParams(**params)
        
        if self.dry_run:
            return {
                "action": "set_temperature",
                "entity_id": validated.entity_id,
                "temperature": validated.temperature,
                "hvac_mode": validated.hvac_mode,
                "executed": False,
                "dry_run": True,
                "message": "Dry-run mode: Action logged but not executed"
            }
        
        # Get current state to check for large changes
        try:
            current_state = await self.ha_client.get_climate_state(validated.entity_id)
            current_temp = current_state.get("target_temperature")
            
            if current_temp is not None:
                temp_change = abs(validated.temperature - current_temp)
                if temp_change > 3.0:
                    return {
                        "error": f"Temperature change too large: {temp_change:.1f}°C (max 3°C per decision)",
                        "current": current_temp,
                        "requested": validated.temperature
                    }
        except Exception as e:
            print(f"⚠️ Could not check current temperature: {e}")
        
        # Execute service call
        service_data = {"temperature": validated.temperature}
        if validated.hvac_mode:
            service_data["hvac_mode"] = validated.hvac_mode
        
        result = await self.ha_client.call_service(
            domain="climate",
            service="set_temperature",
            entity_id=validated.entity_id,
            **service_data
        )
        
        return {
            "action": "set_temperature",
            "entity_id": validated.entity_id,
            "temperature": validated.temperature,
            "hvac_mode": validated.hvac_mode,
            "executed": True,
            "ha_result": result
        }
    
    async def _get_climate_state(self, params: Dict) -> Dict:
        """Get climate state tool handler"""
        entity_id = params["entity_id"]
        state = await self.ha_client.get_climate_state(entity_id)
        return state
    
    async def _set_hvac_mode(self, params: Dict) -> Dict:
        """Set HVAC mode tool handler"""
        validated = SetHVACModeParams(**params)
        
        if self.dry_run:
            return {
                "action": "set_hvac_mode",
                "entity_id": validated.entity_id,
                "hvac_mode": validated.hvac_mode,
                "executed": False,
                "dry_run": True,
                "message": "Dry-run mode: Action logged but not executed"
            }
        
        result = await self.ha_client.call_service(
            domain="climate",
            service="set_hvac_mode",
            entity_id=validated.entity_id,
            hvac_mode=validated.hvac_mode
        )
        
        return {
            "action": "set_hvac_mode",
            "entity_id": validated.entity_id,
            "hvac_mode": validated.hvac_mode,
            "executed": True,
            "ha_result": result
        }
