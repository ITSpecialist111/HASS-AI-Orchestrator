import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from agents.universal_agent import UniversalAgent
from mcp_server import MCPServer

@pytest.fixture
def mock_ha_client():
    client = MagicMock()
    client.get_state = AsyncMock()
    client.call_service = AsyncMock()
    # Ensure success response for call_service to avoid "executed" check failures
    client.call_service.return_value = {"success": True}
    return client

@pytest.fixture
def agent(mock_ha_client):
    return UniversalAgent(
        agent_id="test_agent",
        name="Test Agent",
        instruction="Turn on the lights if it's dark",
        mcp_server=MCPServer(mock_ha_client, dry_run=False), # False to allow HA calls
        ha_client=mock_ha_client,
        entities=["light.test_light", "sensor.light_level"],
        model_name="test-model",
        llm_provider=MagicMock()
    )

@pytest.mark.asyncio
async def test_agent_fetches_initial_state(agent, mock_ha_client):
    """Verify gather_context calls get_state for entities"""
    mock_ha_client.get_state.side_effect = [
        {"entity_id": "light.test_light", "state": "off", "attributes": {"friendly_name": "Test Light"}},
        {"entity_id": "sensor.light_level", "state": "10", "attributes": {"friendly_name": "Light Level"}}
    ]
    
    context = await agent.gather_context()
    
    assert "timestamp" in context
    assert "state_description" in context
    assert "Test Light (light.test_light): off" in context["state_description"]
    assert "Light Level (sensor.light_level): 10" in context["state_description"]
    assert mock_ha_client.get_state.call_count == 2

@pytest.mark.asyncio
async def test_agent_decide_and_execute(agent, mock_ha_client):
    """Verify decide (via mocked LLM) and execute flow"""
    # Mock LLM response for decide()
    mock_response = json.dumps({
        "reasoning": "It is dark (10 lx), turning on lights.",
        "actions": [
            {
                "tool": "call_ha_service",
                "parameters": {
                    "domain": "light",
                    "service": "turn_on",
                    "entity_id": "light.test_light"
                }
            }
        ]
    })
    
    # Patch _call_llm to avoid actual Ollama call
    with patch.object(agent, '_call_llm', new=AsyncMock(return_value=mock_response)):
        # Create context
        context = {
            "timestamp": "2023-01-01T12:00:00",
            "state_description": "Light Level: 10",
            "instruction": "Turn on lights"
        }
        
        # Decide
        decision = await agent.decide(context)
        assert len(decision["actions"]) == 1
        
        # Execute
        results = await agent.execute(decision)
        
        assert len(results) == 1
        assert results[0]["result"]["executed"] is True
        assert results[0]["result"]["action"] == "call_ha_service"
        
        # Verify HA client called
        mock_ha_client.call_service.assert_called_once()
        call_args = mock_ha_client.call_service.call_args
        assert call_args[0][0] == "light" # domain
        assert call_args[0][1] == "turn_on" # service
        assert call_args[0][2]["entity_id"] == "light.test_light"
