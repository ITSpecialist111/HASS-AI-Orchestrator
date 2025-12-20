"""
Home Assistant WebSocket client for standalone use in PoC.
"""
import asyncio
import json
from typing import Dict, Optional, Any
from urllib.parse import urlparse

import websockets


class HAWebSocketClient:
    """
    WebSocket client for Home Assistant integration.
    Handles authentication and state retrieval.
    """
    
    def __init__(self, ha_url: str, token: str):
        self.ha_url = ha_url.rstrip("/")
        self.token = token
        self.connected = False
        self.ws = None
        self.message_id = 0
        self.pending_responses = {}
        
        parsed = urlparse(self.ha_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        self.ws_url = f"{ws_scheme}://{parsed.netloc}{parsed.path}/api/websocket"
    
    async def connect(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            self.ws = await websockets.connect(
                self.ws_url, 
                extra_headers=headers,
                max_size=10 * 1024 * 1024 # 10MB
            )
            
            auth_required = await self.ws.recv()
            auth_data = json.loads(auth_required)
            if auth_data["type"] != "auth_required":
                raise ValueError(f"Unexpected message: {auth_data}")
            
            await self.ws.send(json.dumps({
                "type": "auth",
                "access_token": self.token
            }))
            
            auth_result = await self.ws.recv()
            auth_result_data = json.loads(auth_result)
            if auth_result_data["type"] != "auth_ok":
                raise ValueError(f"Authentication failed: {auth_result_data}")
            
            self.connected = True
            asyncio.create_task(self._receive_messages())
            
        except Exception as e:
            print(f"❌ Failed to connect to Home Assistant WebSocket: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.connected = False
    
    async def _send_message(self, message: Dict) -> int:
        self.message_id += 1
        message["id"] = self.message_id
        await self.ws.send(json.dumps(message))
        return self.message_id
    
    async def _receive_messages(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                if data.get("id") in self.pending_responses:
                    future = self.pending_responses.pop(data["id"])
                    future.set_result(data)
        except Exception:
            self.connected = False
    
    async def get_states(self, timeout: float = 60.0) -> list:
        msg_id = await self._send_message({"type": "get_states"})
        future = asyncio.Future()
        self.pending_responses[msg_id] = future
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            del self.pending_responses[msg_id]
            raise TimeoutError("Timeout waiting for HA states")
        
        if not result.get("success"):
            raise ValueError(f"Failed to get states: {result}")
        
        return result["result"]
