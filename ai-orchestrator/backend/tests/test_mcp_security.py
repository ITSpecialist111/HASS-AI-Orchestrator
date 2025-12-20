import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from mcp_server import MCPServer

@pytest.fixture
def mock_ha_client():
    client = MagicMock()
    client.call_service = AsyncMock(return_value={"success": True})
    return client

@pytest.fixture
def mock_approval_queue():
    queue = MagicMock()
    queue.add_request = AsyncMock()
    return queue

@pytest.mark.asyncio
class TestMCPSecurity:
    """Security tests for MCP Server safety controls"""

    async def test_blocked_critical_domain(self, mock_ha_client):
        """Test that critical domains like shell_command are blocked"""
        mcp = MCPServer(mock_ha_client, dry_run=False)
        
        result = await mcp.execute_tool(
            tool_name="call_ha_service",
            parameters={
                "domain": "shell_command",
                "service": "restart_host",
                "entity_id": "none"
            }
        )
        
        assert "error" in result
        assert "blocked for security reasons" in result["error"]
        mock_ha_client.call_service.assert_not_called()

    async def test_unknown_domain_blocked(self, mock_ha_client):
        """Test that domains not in the allowlist are blocked"""
        mcp = MCPServer(mock_ha_client, dry_run=False)
        
        result = await mcp.execute_tool(
            tool_name="call_ha_service",
            parameters={
                "domain": "dangerous_domain",
                "service": "do_something",
                "entity_id": "none"
            }
        )
        
        assert "error" in result
        assert "not in the allowed list" in result["error"]
        mock_ha_client.call_service.assert_not_called()

    async def test_high_impact_service_queued(self, mock_ha_client, mock_approval_queue):
        """Test that high-impact services (lock.unlock) are queued for approval"""
        mcp = MCPServer(mock_ha_client, approval_queue=mock_approval_queue, dry_run=False)
        
        result = await mcp.execute_tool(
            tool_name="call_ha_service",
            parameters={
                "domain": "lock",
                "service": "unlock",
                "entity_id": "lock.front_door"
            }
        )
        
        assert result["status"] == "queued_for_approval"
        assert "requires manual approval" in result["message"]
        mock_approval_queue.add_request.assert_called_once()
        mock_ha_client.call_service.assert_not_called()

    async def test_cross_validation_temperature_fail(self, mock_ha_client):
        """Test that call_ha_service still respects specific tool rules (temperature range)"""
        mcp = MCPServer(mock_ha_client, dry_run=False)
        
        # Try to set temperature to 50°C via generic service call
        result = await mcp.execute_tool(
            tool_name="call_ha_service",
            parameters={
                "domain": "climate",
                "service": "set_temperature",
                "entity_id": "climate.living_room",
                "service_data": {"temperature": 50.0}
            }
        )
        
        assert "error" in result
        assert "Safety validation failed" in result["error"]
        mock_ha_client.call_service.assert_not_called()

    async def test_cross_validation_temperature_success(self, mock_ha_client):
        """Test that valid generic service calls still work"""
        mcp = MCPServer(mock_ha_client, dry_run=False)
        
        result = await mcp.execute_tool(
            tool_name="call_ha_service",
            parameters={
                "domain": "light",
                "service": "turn_on",
                "entity_id": "light.living_room",
                "service_data": {"brightness_pct": 50}
            }
        )
        
        assert "error" not in result
        assert result["executed"] is True
        mock_ha_client.call_service.assert_called_once()
