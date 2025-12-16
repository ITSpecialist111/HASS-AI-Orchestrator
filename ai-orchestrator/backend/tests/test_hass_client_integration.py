import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from ha_client import HAWebSocketClient

# Mock WebSocket connection
class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.responses = []
        self.closed = False

    async def send(self, message):
        self.sent_messages.append(json.loads(message))

    async def recv(self):
        if self.responses:
            return self.responses.pop(0)
        return json.dumps({"type": "ping"}) # Default keep-alive, though not used in simple flow

    async def close(self):
        self.closed = True
    
    # Async iterator for receiving messages loop
    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.responses:
             # For test purposes, we yield one response and then stop to avoid infinite loops in tests not designed for it
             # OR we can wait. For basic unit tests, yielding pre-canned responses is easier.
             # However, the client loop `async for message in self.ws` expects strings.
            return self.responses.pop(0)
        raise StopAsyncIteration

@pytest.fixture
def mock_ws():
    return MockWebSocket()

@pytest.fixture
def ha_client():
    return HAWebSocketClient("http://localhost:8123", "test_token")

@pytest.mark.asyncio
async def test_connect_auth_success(ha_client, mock_ws):
    """Test successful connection and authentication flow"""
    # Setup mock responses for connection flow
    # 1. auth_required
    # 2. auth_ok
    mock_ws.responses = [
        json.dumps({"type": "auth_required", "ha_version": "2023.12.0"}),
        json.dumps({"type": "auth_ok", "ha_version": "2023.12.0"})
    ]

    with patch('websockets.connect', new=AsyncMock(return_value=mock_ws)):
        await ha_client.connect()

    assert ha_client.connected
    # Verify auth message was sent
    auth_msg = next((msg for msg in mock_ws.sent_messages if msg.get("type") == "auth"), None)
    assert auth_msg is not None
    assert auth_msg["access_token"] == "test_token"

@pytest.mark.asyncio
async def test_connect_auth_failure(ha_client, mock_ws):
    """Test connection failure on invalid auth"""
    mock_ws.responses = [
        json.dumps({"type": "auth_required", "ha_version": "2023.12.0"}),
        json.dumps({"type": "auth_invalid", "message": "Invalid password"})
    ]

    with patch('websockets.connect', new=AsyncMock(return_value=mock_ws)):
        with pytest.raises(ValueError, match="Authentication failed"):
            await ha_client.connect()
    
    assert not ha_client.connected

@pytest.mark.asyncio
async def test_get_states(ha_client, mock_ws):
    """Test fetching states"""
    # Initialize properly to set up future/msg_id mappings
    # We cheat a bit by setting ws directly since we tested connect separately
    ha_client.ws = mock_ws
    ha_client.connected = True
    
    # Mock sending message to trigger a response in the background listener
    # In a real app we'd have the background task running. 
    # For this discrete unit test, we can mock `_send_message` to return an ID, 
    # and then manually resolve the future in `pending_responses` 
    # OR we can inject the response into the listener if we start it.
    
    # Simpler approach: Mock _send_message and manually handle the pending_response future
    # But HAWebSocketClient.get_states waits on a future.
    
    # Let's mock _send_message to return ID 1
    ha_client._send_message = AsyncMock(return_value=1)
    
    # Create the task that waits
    task = asyncio.create_task(ha_client.get_states())
    
    # Give it a moment to register the future
    await asyncio.sleep(0)
    assert 1 in ha_client.pending_responses
    
    # Manually resolve the future as if the listener did it
    mock_response = {
        "id": 1, 
        "type": "result", 
        "success": True, 
        "result": [
            {"entity_id": "light.test", "state": "on", "attributes": {}},
            {"entity_id": "switch.test", "state": "off", "attributes": {}}
        ]
    }
    ha_client.pending_responses[1].set_result(mock_response)
    
    states = await task
    assert len(states) == 2
    assert states[0]["entity_id"] == "light.test"

@pytest.mark.asyncio
async def test_call_service(ha_client):
    """Test calling a service"""
    ha_client.ws = MagicMock()
    ha_client.connected = True
    ha_client._send_message = AsyncMock(return_value=2)
    
    task = asyncio.create_task(ha_client.call_service("light", "turn_on", "light.test"))
    
    await asyncio.sleep(0)
    assert 2 in ha_client.pending_responses
    
    # Simulate success
    ha_client.pending_responses[2].set_result({"id": 2, "type": "result", "success": True, "result": None})
    
    result = await task
    assert result is None # Successful service call usually returns context or None in result depending on API version, mocked as None here
    
    # Verify call args
    call_args = ha_client._send_message.call_args[0][0]
    assert call_args["type"] == "call_service"
    assert call_args["domain"] == "light"
    assert call_args["service"] == "turn_on"
    assert call_args["service_data"]["entity_id"] == "light.test"

