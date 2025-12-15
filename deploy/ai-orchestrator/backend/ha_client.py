"""
Home Assistant WebSocket client for real-time state subscriptions and service calls.
"""
import asyncio
import json
from typing import Dict, Callable, Optional, Any
from urllib.parse import urlparse

import websockets
import httpx


class HAWebSocketClient:
    """
    WebSocket client for Home Assistant integration.
    Handles authentication, state subscriptions, and service calls.
    """
    
    def __init__(self, ha_url: str, access_token: str):
        """
        Initialize HA WebSocket client.
        
        Args:
            ha_url: Home Assistant URL (http://supervisor/core or http://homeassistant.local:8123)
            access_token: Long-lived access token or supervisor token
        """
        self.ha_url = ha_url.rstrip("/")
        self.access_token = access_token
        self.connected = False
        self.ws = None
        self.message_id = 0
        self.subscriptions = {}
        self.pending_responses = {}
        
        # Convert HTTP URL to WebSocket URL
        parsed = urlparse(self.ha_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        self.ws_url = f"{ws_scheme}://{parsed.netloc}/api/websocket"
    
    async def connect(self):
        """Connect to Home Assistant WebSocket API and authenticate"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            
            # Receive auth_required message
            auth_required = await self.ws.recv()
            auth_data = json.loads(auth_required)
            if auth_data["type"] != "auth_required":
                raise ValueError(f"Unexpected message: {auth_data}")
            
            # Send auth message
            await self.ws.send(json.dumps({
                "type": "auth",
                "access_token": self.access_token
            }))
            
            # Receive auth result
            auth_result = await self.ws.recv()
            auth_result_data = json.loads(auth_result)
            if auth_result_data["type"] != "auth_ok":
                raise ValueError(f"Authentication failed: {auth_result_data}")
            
            self.connected = True
            
            # Start message receiver task
            asyncio.create_task(self._receive_messages())
            
        except Exception as e:
            print(f"❌ Failed to connect to Home Assistant WebSocket: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from Home Assistant WebSocket"""
        if self.ws:
            await self.ws.close()
            self.connected = False
    
    async def _send_message(self, message: Dict) -> int:
        """Send message to HA and return message ID"""
        self.message_id += 1
        message["id"] = self.message_id
        await self.ws.send(json.dumps(message))
        return self.message_id
    
    async def _receive_messages(self):
        """Continuously receive and process messages from HA"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                # Handle subscription events
                if data["type"] == "event" and data.get("id") in self.subscriptions:
                    callback = self.subscriptions[data["id"]]
                    await callback(data["event"])
                
                # Handle command responses
                elif data.get("id") in self.pending_responses:
                    future = self.pending_responses.pop(data["id"])
                    future.set_result(data)
        
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            print("⚠️ WebSocket connection closed")
        except Exception as e:
            self.connected = False
            print(f"❌ Error receiving messages: {e}")
    
    async def get_states(self, entity_id: Optional[str] = None) -> Dict | list:
        """
        Get current state of entities.
        
        Args:
            entity_id: Specific entity ID, or None for all entities
        
        Returns:
            Entity state dict or list of states
        """
        msg_id = await self._send_message({"type": "get_states"})
        
        # Wait for response
        future = asyncio.Future()
        self.pending_responses[msg_id] = future
        result = await asyncio.wait_for(future, timeout=10.0)
        
        if not result.get("success"):
            raise ValueError(f"Failed to get states: {result}")
        
        states = result["result"]
        
        if entity_id:
            # Return specific entity state
            for state in states:
                if state["entity_id"] == entity_id:
                    return state
            raise ValueError(f"Entity {entity_id} not found")
        
        return states
    
    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Call a Home Assistant service.
        
        Args:
            domain: Service domain (e.g., 'climate', 'light')
            service: Service name (e.g., 'set_temperature', 'turn_on')
            entity_id: Target entity ID
            **kwargs: Additional service data
        
        Returns:
            Service call result
        """
        service_data = kwargs.copy()
        if entity_id:
            service_data["entity_id"] = entity_id
        
        msg_id = await self._send_message({
            "type": "call_service",
            "domain": domain,
            "service": service,
            "service_data": service_data
        })
        
        # Wait for response
        future = asyncio.Future()
        self.pending_responses[msg_id] = future
        result = await asyncio.wait_for(future, timeout=10.0)
        
        if not result.get("success"):
            raise ValueError(f"Service call failed: {result}")
        
        return result["result"]
    
    async def subscribe_entities(
        self,
        entity_ids: list[str],
        callback: Callable[[Dict], Any]
    ) -> int:
        """
        Subscribe to state changes for specific entities.
        
        Args:
            entity_ids: List of entity IDs to monitor
            callback: Async function called with event data
        
        Returns:
            Subscription ID
        """
        msg_id = await self._send_message({
            "type": "subscribe_events",
            "event_type": "state_changed"
        })
        
        # Wrap callback to filter by entity IDs
        async def filtered_callback(event):
            entity_id = event["data"]["entity_id"]
            if entity_id in entity_ids:
                await callback(event)
        
        self.subscriptions[msg_id] = filtered_callback
        
        # Wait for success confirmation
        future = asyncio.Future()
        self.pending_responses[msg_id] = future
        result = await asyncio.wait_for(future, timeout=10.0)
        
        if not result.get("success"):
            raise ValueError(f"Subscription failed: {result}")
        
        return msg_id
    
    async def get_climate_state(self, entity_id: str) -> Dict:
        """
        Get climate entity state with temperature and HVAC info.
        
        Args:
            entity_id: Climate entity ID
        
        Returns:
            Dict with current_temperature, target_temperature, hvac_mode, state
        """
        state = await self.get_states(entity_id)
        
        return {
            "entity_id": entity_id,
            "state": state["state"],
            "current_temperature": state["attributes"].get("current_temperature"),
            "target_temperature": state["attributes"].get("temperature"),
            "hvac_mode": state["attributes"].get("hvac_mode"),
            "preset_mode": state["attributes"].get("preset_mode"),
            "attributes": state["attributes"]
        }
