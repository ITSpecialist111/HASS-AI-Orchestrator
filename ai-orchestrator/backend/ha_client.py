"""
Home Assistant WebSocket client for real-time state subscriptions and service calls.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Callable, Optional, Any
from urllib.parse import urlparse

import websockets
import httpx


class HAWebSocketClient:
    """
    WebSocket client for Home Assistant integration.
    Handles authentication, state subscriptions, and service calls.
    """
    
    def __init__(self, ha_url: str, token: str, supervisor_token: Optional[str] = None):
        """
        Initialize HA WebSocket client.
        
        Args:
            ha_url: Home Assistant URL
            token: Token for WebSocket 'auth' packet (LLAT or Supervisor Token)
            supervisor_token: Token for Supervisor Proxy Headers (if different)
        """
        self.ha_url = ha_url.rstrip("/")
        self.token = token
        # Only an explicit Supervisor token belongs in the HTTP upgrade
        # header. Direct Core connections authenticate in the HA auth frame.
        self.supervisor_token = supervisor_token or None
        self.connected = False
        self.ws = None
        self.message_id = 0
        self.subscriptions = {}
        self.pending_responses = {}
        self.connection_attempts = 0
        self.last_error: Optional[str] = None
        self.last_error_at: Optional[str] = None
        self.last_connected_at: Optional[str] = None
        self.ha_version: Optional[str] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._connect_lock = asyncio.Lock()
        
        # Convert HTTP URL to WebSocket URL
        parsed = urlparse(self.ha_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        self.ws_url = f"{ws_scheme}://{parsed.netloc}{parsed.path}/api/websocket"
        self._closing = False

    def info(self) -> Dict[str, Any]:
        """Return credential-free connection diagnostics for health APIs."""
        return {
            "connected": self.connected,
            "mode": "supervisor_proxy" if self.supervisor_token else "direct",
            "endpoint": self.ws_url,
            "ha_version": self.ha_version,
            "connection_attempts": self.connection_attempts,
            "last_connected_at": self.last_connected_at,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
        }

    def _record_error(self, exc: BaseException) -> None:
        self.last_error = f"{type(exc).__name__}: {exc}"
        self.last_error_at = datetime.now(timezone.utc).isoformat()

    def _fail_pending(self, message: str) -> None:
        for future in list(self.pending_responses.values()):
            if not future.done():
                future.set_exception(ConnectionError(message))
        self.pending_responses.clear()
    
    async def disconnect(self):
        """Disconnect from Home Assistant"""
        self._closing = True
        self.connected = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        if self._receive_task and self._receive_task is not asyncio.current_task():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except (asyncio.CancelledError, Exception):
                pass
        self._receive_task = None
        self._fail_pending("Home Assistant disconnected")
        print("📡 HA Client disconnected")
    
    async def connect(self):
        """Connect to Home Assistant WebSocket API and authenticate"""
        async with self._connect_lock:
            if self.connected:
                return
            if not self.token:
                error = RuntimeError(
                    "No Home Assistant credential is available. Enable homeassistant_api "
                    "for the add-on or configure ha_access_token for direct access."
                )
                self._record_error(error)
                raise error
            try:
                self.connection_attempts += 1
                connect_options: Dict[str, Any] = {
                    "max_size": 10 * 1024 * 1024,
                    "ping_interval": 60,
                    "ping_timeout": 60,
                    "open_timeout": 15,
                    # HA and Supervisor are local endpoints. WebSockets 16
                    # otherwise auto-discovers environment proxies, which can
                    # incorrectly route internal hostnames.
                    "proxy": None,
                }
                if self.supervisor_token:
                    # websockets >=14 renamed ``extra_headers`` to
                    # ``additional_headers``. requirements.txt uses 16.1.
                    connect_options["additional_headers"] = {
                        "Authorization": f"Bearer {self.supervisor_token}",
                    }

                self.ws = await websockets.connect(self.ws_url, **connect_options)

                auth_required = await asyncio.wait_for(self.ws.recv(), timeout=15)
                auth_data = json.loads(auth_required)
                if auth_data.get("type") != "auth_required":
                    raise ValueError(f"Unexpected authentication message: {auth_data.get('type')}")
                self.ha_version = auth_data.get("ha_version")

                await self.ws.send(json.dumps({
                    "type": "auth",
                    "access_token": self.token,
                }))

                auth_result = await asyncio.wait_for(self.ws.recv(), timeout=15)
                auth_result_data = json.loads(auth_result)
                if auth_result_data.get("type") != "auth_ok":
                    message = auth_result_data.get("message") or auth_result_data.get("type")
                    raise ValueError(f"Authentication failed: {message}")

                self.connected = True
                self.last_error = None
                self.last_error_at = None
                self.last_connected_at = datetime.now(timezone.utc).isoformat()
                self._receive_task = asyncio.create_task(
                    self._receive_messages(),
                    name="ha-websocket-receiver",
                )
            except Exception as e:
                self._record_error(e)
                if not self._closing:
                    print(
                        f"❌ Failed to connect to Home Assistant WebSocket at "
                        f"{self.ws_url}: {self.last_error}"
                    )
                self.connected = False
                if self.ws:
                    try:
                        await self.ws.close()
                    except Exception:
                        pass
                    self.ws = None
                raise
    
    async def wait_until_connected(self, timeout: float = 30.0):
        """Wait until connection is established or timeout occurs"""
        start_time = asyncio.get_event_loop().time()
        while not self.connected:
            if asyncio.get_event_loop().time() - start_time > timeout:
                return False
            await asyncio.sleep(0.5)
        return True

    async def _send_message(self, message: Dict) -> int:
        """Send message to HA and return message ID"""
        if not self.ws or not self.connected:
            # Raising an error forces the caller to handle the disconnection immediately
            # rather than waiting for a timeout.
            raise RuntimeError(f"Cannot send message ({message.get('type')}): Home Assistant not connected")
        
        try:
            self.message_id += 1
            message["id"] = self.message_id
            # Register before sending. HA can answer immediately and the
            # receiver task may run before control returns to the caller.
            self.pending_responses[self.message_id] = (
                asyncio.get_running_loop().create_future()
            )
            await self.ws.send(json.dumps(message))
            return self.message_id
        except Exception as e:
            self.pending_responses.pop(self.message_id, None)
            print(f"❌ Error sending WebSocket message: {e}")
            self.connected = False
            self._record_error(e)
            raise RuntimeError(
                f"Failed to send Home Assistant message ({message.get('type')}): {e}"
            ) from e
    
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
                    # The requesting coroutine owns cleanup. Keeping a
                    # completed future here closes the send/receive race.
                    future = self.pending_responses[data["id"]]
                    if not future.done():
                        future.set_result(data)
        
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            self._fail_pending("Home Assistant WebSocket connection closed")
            if not self._closing:
                print("⚠️ HA WebSocket connection closed")
        except Exception as e:
            self.connected = False
            self._record_error(e)
            self._fail_pending(f"Home Assistant receive loop failed: {e}")
            if not self._closing:
                print(f"❌ Error receiving HA messages: {e}")
        finally:
            self.connected = False
    
    async def run_reconnect_loop(self):
        """Infinite loop to maintain connection to Home Assistant"""
        print("🔄 HA Reconnection loop started")
        retry_delay = 2.0
        while not self._closing:
            if not self.connected:
                print("📡 Reconnecting to Home Assistant...")
                try:
                    await self.connect()
                    print("✅ HA Reconnected successfully")
                    retry_delay = 2.0
                except Exception:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(30.0, retry_delay * 2)
                    continue
            await asyncio.sleep(5)
    
    async def get_states(self, entity_id: Optional[str] = None, timeout: float = 60.0) -> Dict | list:
        """
        Get current state of entities.
        
        Args:
            entity_id: Specific entity ID, or None for all entities
            timeout: Timeout in seconds (default: 60.0)
        
        Returns:
            Entity state dict or list of states
        """
        msg_id = await self._send_message({"type": "get_states"})
        
        # Wait for response
        future = self.pending_responses.get(msg_id)
        if future is None:  # compatibility for custom/test send overrides
            future = asyncio.get_running_loop().create_future()
            self.pending_responses[msg_id] = future
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("Timeout waiting for HA states")
        finally:
            self.pending_responses.pop(msg_id, None)
        
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
    
    async def get_services(self) -> Dict:
        """
        Get all available services from Home Assistant.
        
        Returns:
            Dictionary of domains and their services.
        """
        msg_id = await self._send_message({"type": "get_services"})
        
        # Wait for response
        future = self.pending_responses.get(msg_id)
        if future is None:
            future = asyncio.get_running_loop().create_future()
            self.pending_responses[msg_id] = future
        try:
            result = await asyncio.wait_for(future, timeout=10.0)
        except asyncio.TimeoutError:
            raise TimeoutError("Timeout waiting for HA services")
        finally:
            self.pending_responses.pop(msg_id, None)
        
        if not result.get("success"):
            raise ValueError(f"Failed to get services: {result}")
        
        return result["result"]
    
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
        future = self.pending_responses.get(msg_id)
        if future is None:
            future = asyncio.get_running_loop().create_future()
            self.pending_responses[msg_id] = future
        try:
            result = await asyncio.wait_for(future, timeout=10.0)
        finally:
            self.pending_responses.pop(msg_id, None)
        
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
        future = self.pending_responses.get(msg_id)
        if future is None:
            future = asyncio.get_running_loop().create_future()
            self.pending_responses[msg_id] = future
        try:
            result = await asyncio.wait_for(future, timeout=10.0)
        finally:
            self.pending_responses.pop(msg_id, None)
        
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
