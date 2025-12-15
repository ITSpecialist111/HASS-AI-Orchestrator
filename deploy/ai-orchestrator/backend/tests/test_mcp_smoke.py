"""
Smoke tests for MCP Server.
Tests tool registration, validation, and basic execution.
"""
import pytest
from mcp_server import MCPServer, SetTemperatureParams, SetHVACModeParams


@pytest.mark.smoke
class TestMCPServerSmoke:
    """Smoke tests for MCP Server"""
    
    @pytest.mark.asyncio
    async def test_mcp_server_initialization(self, mock_ha_client):
        """Test MCP server initializes with tools"""
        mcp = MCPServer(mock_ha_client, dry_run=True)
        
        assert mcp is not None
        assert mcp.dry_run is True
        assert len(mcp.tools) == 3
        assert "set_temperature" in mcp.tools
        assert "get_climate_state" in mcp.tools
        assert "set_hvac_mode" in mcp.tools
    
    def test_tool_schemas_available(self, mock_ha_client):
        """Test tool schemas can be retrieved"""
        mcp = MCPServer(mock_ha_client, dry_run=True)
        schemas = mcp.get_tool_schemas()
        
        assert len(schemas) == 3
        assert all("name" in schema for schema in schemas)
        assert all("description" in schema for schema in schemas)
        assert all("parameters" in schema for schema in schemas)
    
    def test_set_temperature_validation_success(self):
        """Test temperature parameter validation accepts valid input"""
        params = SetTemperatureParams(
            entity_id="climate.test",
            temperature=21.5,
            hvac_mode="heat"
        )
        
        assert params.temperature == 21.5
        assert params.entity_id == "climate.test"
        assert params.hvac_mode == "heat"
    
    def test_set_temperature_validation_bounds(self):
        """Test temperature bounds validation"""
        # Too low
        with pytest.raises(ValueError):
            SetTemperatureParams(
                entity_id="climate.test",
                temperature=5.0
            )
        
        # Too high
        with pytest.raises(ValueError):
            SetTemperatureParams(
                entity_id="climate.test",
                temperature=35.0
            )
    
    def test_set_hvac_mode_validation_success(self):
        """Test HVAC mode validation accepts valid modes"""
        valid_modes = ["heat", "cool", "auto", "off"]
        
        for mode in valid_modes:
            params = SetHVACModeParams(
                entity_id="climate.test",
                hvac_mode=mode
            )
            assert params.hvac_mode == mode
    
    def test_set_hvac_mode_validation_invalid(self):
        """Test HVAC mode validation rejects invalid modes"""
        with pytest.raises(ValueError):
            SetHVACModeParams(
                entity_id="climate.test",
                hvac_mode="invalid_mode"
            )
    
    @pytest.mark.asyncio
    async def test_execute_tool_dry_run(self, mock_ha_client):
        """Test tool execution in dry-run mode"""
        mcp = MCPServer(mock_ha_client, dry_run=True)
        
        result = await mcp.execute_tool(
            tool_name="set_temperature",
            parameters={
                "entity_id": "climate.test",
                "temperature": 22.0,
                "hvac_mode": "heat"
            },
            agent_id="test_agent"
        )
        
        assert "error" not in result
        assert result["dry_run"] is True
        assert result["executed"] is False
        assert result["temperature"] == 22.0
    
    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, mock_ha_client):
        """Test executing unknown tool returns error"""
        mcp = MCPServer(mock_ha_client, dry_run=True)
        
        result = await mcp.execute_tool(
            tool_name="unknown_tool",
            parameters={},
            agent_id="test_agent"
        )
        
        assert "error" in result
        assert "Unknown tool" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_climate_state_tool(self, mock_ha_client):
        """Test get_climate_state tool execution"""
        mcp = MCPServer(mock_ha_client, dry_run=True)
        
        result = await mcp.execute_tool(
            tool_name="get_climate_state",
            parameters={"entity_id": "climate.test_room"},
            agent_id="test_agent"
        )
        
        assert "error" not in result
        assert result["entity_id"] == "climate.test_room"
        assert "current_temperature" in result
        assert "target_temperature" in result
        assert "hvac_mode" in result
    
    @pytest.mark.asyncio
    async def test_temperature_change_limit(self, mock_ha_client):
        """Test temperature change rate limiting"""
        # Set current temperature to 20°C
        mock_ha_client.get_climate_state = AsyncMock(return_value={
            "entity_id": "climate.test",
            "target_temperature": 20.0,
            "current_temperature": 20.0,
            "hvac_mode": "heat"
        })
        
        mcp = MCPServer(mock_ha_client, dry_run=False)
        
        # Try to change by 5°C (should fail, max is 3°C)
        result = await mcp.execute_tool(
            tool_name="set_temperature",
            parameters={
                "entity_id": "climate.test",
                "temperature": 25.0
            },
            agent_id="test_agent"
        )
        
        assert "error" in result
        assert "too large" in result["error"].lower()


# Import AsyncMock for async tests
from unittest.mock import AsyncMock
