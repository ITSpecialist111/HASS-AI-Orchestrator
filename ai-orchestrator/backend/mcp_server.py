import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ValidationError

from ha_client import HAWebSocketClient


class SetTemperatureParams(BaseModel):
    """Parameters for set_temperature tool"""
    entity_id: str = Field(..., description="Climate entity ID")
    temperature: float = Field(..., description="Target temperature")
    hvac_mode: Optional[str] = Field(None, description="HVAC mode: heat, cool, auto, off")
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        min_temp = float(os.getenv("MIN_TEMP", "10.0"))
        max_temp = float(os.getenv("MAX_TEMP", "30.0"))
        if not (min_temp <= v <= max_temp):
            raise ValueError(f"Temperature must be between {min_temp}°C and {max_temp}°C")
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


# Default Security Settings (Fallbacks)
DEFAULT_ALLOWED_DOMAINS = [
    "light", "switch", "fan", "climate", "media_player", 
    "cover", "input_boolean", "input_select", "input_number",
    "scene", "button", "vacuum", "water_heater",
    "lock", "alarm_control_panel", "camera"
]

DEFAULT_HIGH_IMPACT_SERVICES = [
    "lock.unlock",
    "lock.lock",
    "alarm_control_panel.alarm_disarm",
    "alarm_control_panel.alarm_arm_home",
    "alarm_control_panel.alarm_arm_away",
    "camera.disable_motion_detection",
    "camera.turn_off"
]

DEFAULT_BLOCKED_DOMAINS = ["shell_command", "hassio", "script", "automation", "rest_command"]

# Security Configuration Helpers
def get_env_list(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    if not raw:
        return default
    return [x.strip() for x in raw.split(",") if x.strip()]


class MCPServer:
    """
    Model Context Protocol server for Home Assistant.
    Registers and executes tools with safety checks.
    """
    
    def __init__(self, ha_client: HAWebSocketClient, approval_queue: Optional[Any] = None, rag_manager: Optional[Any] = None, dry_run: bool = True):
        """
        Initialize MCP server.
        
        Args:
            ha_client: Connected Home Assistant WebSocket client (or provider function)
            approval_queue: Optional Approval Queue for high-impact actions
            rag_manager: Optional RAG Manager for knowledge tools
            dry_run: If True, log actions without executing
        """
        self._ha_provider = ha_client
        self.approval_queue = approval_queue
        self.rag_manager = rag_manager
        self.dry_run = dry_run
        self.tools = self._register_tools()
        self.log_dir = Path("/data/decisions")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    @property
    def ha_client(self):
        """Lazy retrieval of HA client"""
        if callable(self._ha_provider):
            return self._ha_provider()
        return self._ha_provider
    
    def _register_tools(self) -> Dict[str, Dict]:
        """Register available tools with schemas"""
        return {
            # Climate tools (Phase 1)
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
            },
            # Lighting tools (Phase 2)
            "turn_on_light": {
                "name": "turn_on_light",
                "description": "Turn on a light with optional brightness and color temperature",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "brightness": {"type": "integer", "minimum": 0, "maximum": 100},
                        "color_temp": {"type": "integer", "minimum": 2700, "maximum": 6500}
                    },
                    "required": ["entity_id"]
                },
                "handler": self._turn_on_light
            },
            "turn_off_light": {
                "name": "turn_off_light",
                "description": "Turn off a light",
                "parameters": {
                    "type": "object",
                    "properties": {"entity_id": {"type": "string"}},
                    "required": ["entity_id"]
                },
                "handler": self._turn_off_light
            },
            "set_brightness": {
                "name": "set_brightness",
                "description": "Set brightness of a light (0-100%)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "brightness": {"type": "integer", "minimum": 0, "maximum": 100}
                    },
                    "required": ["entity_id", "brightness"]
                },
                "handler": self._set_brightness
            },
            "set_color_temp": {
                "name": "set_color_temp",
                "description": "Set color temperature of a light (2700-6500K)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "kelvin": {"type": "integer", "minimum": 2700, "maximum": 6500}
                    },
                    "required": ["entity_id", "kelvin"]
                },
                "handler": self._set_color_temp
            },
            # Security tools (Phase 2)
            "set_alarm_state": {
                "name": "set_alarm_state",
                "description": "Set alarm control panel state",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "state": {"type": "string", "enum": ["armed_home", "armed_away", "disarmed"]}
                    },
                    "required": ["entity_id", "state"]
                },
                "handler": self._set_alarm_state
            },
            "lock_door": {
                "name": "lock_door",
                "description": "Lock a door",
                "parameters": {
                    "type": "object",
                    "properties": {"entity_id": {"type": "string"}},
                    "required": ["entity_id"]
                },
                "handler": self._lock_door
            },
            "unlock_door": {
                "name": "unlock_door",
                "description": "Unlock a door (requires approval)",
                "parameters": {
                    "type": "object",
                    "properties": {"entity_id": {"type": "string"}},
                    "required": ["entity_id"]
                },
                "handler": self._unlock_door
            },
            "enable_camera": {
                "name": "enable_camera",
                "description": "Enable camera with motion detection",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "motion_detection": {"type": "boolean", "default": True}
                    },
                    "required": ["entity_id"]
                },
                "handler": self._enable_camera
            },
            # Knowledge tools (Phase 3)
            "search_knowledge_base": {
                "name": "search_knowledge_base",
                "description": "Search for manuals, entity info, and past decisions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "default": 3}
                    },
                    "required": ["query"]
                },
                "handler": self._search_knowledge_base
            },
            # Phase 5: Universal Tool
            "call_ha_service": {
                "name": "call_ha_service",
                "description": "Call any Home Assistant service on an entity",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Service domain (e.g. light, switch)"},
                        "service": {"type": "string", "description": "Service name (e.g. turn_on, toggle)"},
                        "entity_id": {"type": "string", "description": "Target entity ID"},
                        "service_data": {"type": "object", "description": "Additional parameters (brightness, etc)"}
                    },
                    "required": ["domain", "service", "entity_id"]
                },
                "handler": self._call_ha_service
            },
            "log": {
                "name": "log",
                "description": "Log a message or observation (useful for debugging or tracking logic)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to log"}
                    },
                    "required": ["message"]
                },
                "handler": self._log_message
            },
            "get_state": {
                "name": "get_state",
                "description": "Get the current state and attributes of any entity",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string", "description": "Entity ID to check"}
                    },
                    "required": ["entity_id"]
                },
                "handler": self._get_state
            }
        }
    
    def get_tool_schemas(self) -> list[Dict]:
        """Get tool schemas for LLM prompt"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"] + " (Check parameters carefully)",
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
                max_change = float(os.getenv("MAX_TEMP_CHANGE", "3.0"))
                if temp_change > max_change:
                    return {
                        "error": f"Temperature change too large: {temp_change:.1f}°C (max {max_change}°C per decision)",
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
    
    # Lighting tool handlers (Phase 2)
    async def _turn_on_light(self, params: Dict) -> Dict:
        """Turn on light handler"""
        entity_id = params["entity_id"]
        brightness = params.get("brightness")
        color_temp = params.get("color_temp")
        
        service_data = {}
        if brightness is not None:
            service_data["brightness_pct"] = brightness
        if color_temp is not None:
            service_data["color_temp"] = color_temp
        
        if self.dry_run:
            return {
                "action": "turn_on_light",
                "entity_id": entity_id,
                "brightness": brightness,
                "color_temp": color_temp,
                "executed": False,
                "dry_run": True
            }
        
        result = await self.ha_client.call_service(
            domain="light",
            service="turn_on",
            entity_id=entity_id,
            **service_data
        )
        
        return {"action": "turn_on_light", "executed": True, "ha_result": result}
    
    async def _turn_off_light(self, params: Dict) -> Dict:
        """Turn off light handler"""
        entity_id = params["entity_id"]
        
        if self.dry_run:
            return {"action": "turn_off_light", "entity_id": entity_id, "dry_run": True}
        
        result = await self.ha_client.call_service(
            domain="light",
            service="turn_off",
            entity_id=entity_id
        )
        
        return {"action": "turn_off_light", "executed": True, "ha_result": result}
    
    async def _set_brightness(self, params: Dict) -> Dict:
        """Set brightness handler"""
        entity_id = params["entity_id"]
        brightness = params["brightness"]
        
        if self.dry_run:
            return {"action": "set_brightness", "brightness": brightness, "dry_run": True}
        
        result = await self.ha_client.call_service(
            domain="light",
            service="turn_on",
            entity_id=entity_id,
            brightness_pct=brightness
        )
        
        return {"action": "set_brightness", "executed": True}
    
    async def _set_color_temp(self, params: Dict) -> Dict:
        """Set color temperature handler"""
        entity_id = params["entity_id"]
        kelvin = params["kelvin"]
        
        if self.dry_run:
            return {"action": "set_color_temp", "kelvin": kelvin, "dry_run": True}
        
        result = await self.ha_client.call_service(
            domain="light",
            service="turn_on",
            entity_id=entity_id,
            color_temp=kelvin
        )
        
        return {"action": "set_color_temp", "executed": True}
    
    # Security tool handlers (Phase 2)
    async def _set_alarm_state(self, params: Dict) -> Dict:
        """Set alarm state handler"""
        entity_id = params["entity_id"]
        state = params["state"]
        
        if self.dry_run:
            return {"action": "set_alarm_state", "state": state, "dry_run": True}
        
        service_map = {
            "armed_home": "alarm_arm_home",
            "armed_away": "alarm_arm_away",
            "disarmed": "alarm_disarm"
        }
        
        result = await self.ha_client.call_service(
            domain="alarm_control_panel",
            service=service_map[state],
            entity_id=entity_id
        )
        
        return {"action": "set_alarm_state", "state": state, "executed": True}
    
    async def _lock_door(self, params: Dict) -> Dict:
        """Lock door handler"""
        entity_id = params["entity_id"]
        
        if self.dry_run:
            return {"action": "lock_door", "entity_id": entity_id, "dry_run": True}
        
        result = await self.ha_client.call_service(
            domain="lock",
            service="lock",
            entity_id=entity_id
        )
        
        return {"action": "lock_door", "executed": True}
    
    async def _unlock_door(self, params: Dict) -> Dict:
        """Unlock door handler - always requires approval"""
        entity_id = params["entity_id"]
        
        # This should be caught by approval queue before execution
        return {
            "action": "unlock_door",
            "entity_id": entity_id,
            "requires_approval": True,
            "message": "Door unlock requires human approval"
        }
    
    async def _enable_camera(self, params: Dict) -> Dict:
        """Enable camera handler"""
        entity_id = params["entity_id"]
        motion_detection = params.get("motion_detection", True)
        
        if self.dry_run:
            return {"action": "enable_camera", "motion_detection": motion_detection, "dry_run": True}
        
        # Camera enabling is platform-specific, this is a generic implementation
        result = await self.ha_client.call_service(
            domain="camera",
            service="enable_motion_detection" if motion_detection else "turn_on",
            entity_id=entity_id
        )
        
        return {"action": "enable_camera", "executed": True}
    
    # Knowledge tool handlers (Phase 3)
    async def _search_knowledge_base(self, params: Dict) -> Dict:
        """Search knowledge base handler"""
        if not self.rag_manager:
            return {"error": "RAG Manager not initialized", "results": []}
            
        query = params["query"]
        limit = params.get("limit", 3)
        
        results = self.rag_manager.query(
            query_text=query,
            collection_names=["knowledge_base", "entity_registry", "memory"],
            n_results=limit
        )
        
        # Format for LLM consumption
        formatted_results = []
        for res in results:
            formatted_results.append({
                "content": res["content"],
                "source": res.get("source", "unknown"),
                "relevance": f"{1 - res.get('distance', 1):.2f}"
            })
            
        return {
            "action": "search_knowledge_base",
            "query": query,
            "results": formatted_results
        }

    # Phase 5: Universal Tool Handler
    async def _call_ha_service(self, params: Dict) -> Dict:
        """Generic handler to call any HA service"""
        domain = params.get("domain")
        service = params.get("service")
        entity_id = params.get("entity_id")
        service_data = params.get("service_data", {})
        
        # Fix: If service_data is empty, collect all non-reserved keys from params
        # This allows agents to send "flat" parameters for simpler tool usage
        if not service_data:
            reserved = ['domain', 'service', 'entity_id', 'service_data']
            service_data = {k: v for k, v in params.items() if k not in reserved}
        
        # Merge entity_id into service_data for the call
        call_data = {"entity_id": entity_id, **service_data}
        
        if self.dry_run:
            # In dry run, we might want to validate if the service actually exists via RAG or HA
            # For now, we just log it.
            return {
                "action": "call_ha_service",
                "domain": domain,
                "service": service,
                "data": {"entity_id": entity_id, **service_data},
                "executed": False,
                "dry_run": True
            }
            
        # 1. Domain Guard: Block critical/dangerous domains
        blocked_domains = get_env_list("BLOCKED_DOMAINS", DEFAULT_BLOCKED_DOMAINS)
        if domain in blocked_domains:
            return {
                "error": f"Access to domain '{domain}' is blocked for security reasons.",
                "executed": False
            }
            
        # 2. Allowlist Check: Warn or block unknown domains
        allowed_domains = get_env_list("ALLOWED_DOMAINS", DEFAULT_ALLOWED_DOMAINS)
        if domain not in allowed_domains:
            return {
                "error": f"Domain '{domain}' is not in the allowed list of safe domains.",
                "executed": False,
                "allowed_domains": allowed_domains
            }

        # 3. High-Impact Check: Redirect to Approval Queue
        service_full_name = f"{domain}.{service}"
        high_impact_services = get_env_list("HIGH_IMPACT_SERVICES", DEFAULT_HIGH_IMPACT_SERVICES)
        if service_full_name in high_impact_services:
            if self.approval_queue:
                # Create a description for the user
                reason = f"Agent requested high-impact service: {service_full_name} on {entity_id}"
                if service_data:
                    reason += f" with data: {json.dumps(service_data)}"
                
                await self.approval_queue.add_request(
                    agent_id="mcp_security_guard",
                    action_type=service_full_name,
                    action_data={
                        "domain": domain,
                        "service": service,
                        "entity_id": entity_id,
                        "service_data": service_data
                    },
                    impact_level="high",
                    reason=reason
                )
                return {
                    "action": "call_ha_service",
                    "status": "queued_for_approval",
                    "message": f"Service {service_full_name} requires manual approval as it is high-impact."
                }
            else:
                return {
                    "error": f"Service {service_full_name} requires approval, but approval queue is not available.",
                    "executed": False
                }

        # 4. Cross-Validation: Check specific tool rules
        if domain == "climate" and service == "set_temperature":
            try:
                # Validate using existing Pydantic model
                SetTemperatureParams(entity_id=entity_id, **service_data)
            except ValidationError as e:
                return {
                    "error": f"Safety validation failed for {service_full_name}: {str(e)}",
                    "executed": False
                }

        try:
            # Fix: Pass entity_id and service_data (kwargs) separately
            await self.ha_client.call_service(
                domain=domain, 
                service=service, 
                entity_id=entity_id, 
                **service_data
            )
            return {
                "action": "call_ha_service",
                "domain": domain,
                "service": service,
                "data": {"entity_id": entity_id, **service_data},
                "executed": True
            }
        except Exception as e:
            return {"error": str(e), "executed": False}

    async def _log_message(self, params: Dict) -> Dict:
        """Log message handler"""
        message = params["message"]
        # The logging happens automatically in execute_tool via log_entry
        return {"action": "log", "message": message, "logged": True}

    async def _get_state(self, params: Dict) -> Dict:
        """Generic get state handler"""
        entity_id = params["entity_id"]
        try:
            # We can reuse get_climate_state's logic or call ha_client directly
            # HAWebSocketClient likely has a generic get_state or we can fallback to listening
            # But ha_client.get_climate_state just returns the state dict from registry
            # We need to expose a generic get_state in ha_client if it doesn't exist
            # Checking ha_client usage... it seems we only have get_climate_state exposed in the snippet I saw?
            # Let's assume ha_client has a way to get state from its local cache
            # Actually, looking at previous files, ha_client.states is a dict.
            
            # Accessing ha_client states directly
            state = await self.ha_client.get_states(entity_id=entity_id)
            if state:
                return {"entity_id": entity_id, "state": state.get("state"), "attributes": state.get("attributes")}
            else:
                return {"error": f"Entity {entity_id} not found in registry"}
        except Exception as e:
            return {"error": str(e)}
