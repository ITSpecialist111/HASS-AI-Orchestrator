"""
Smoke tests for Phase 2 Multi-Agent Orchestration.
Tests orchestrator, new agents, approval queue, and integration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sqlite3


@pytest.mark.smoke
class TestOrchestratorSmoke:
    """Smoke tests for orchestrator"""
    
    @pytest.fixture
    def mock_agents(self):
        """Create mock specialist agents"""
        agents = {}
        for agent_id in ["heating", "cooling", "lighting", "security"]:
            agent = MagicMock()
            agent.agent_id = agent_id
            agent.receive_task = AsyncMock()
            agent.get_entity_states = AsyncMock(return_value={})
            agents[agent_id] = agent
        return agents
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, mock_ha_client, mock_agents):
        """Test orchestrator initializes with all agents"""
        from orchestrator import Orchestrator
        from approval_queue import ApprovalQueue
        from mcp_server import MCPServer
        
        mcp = MCPServer(mock_ha_client, dry_run=True)
        approval_queue = ApprovalQueue(db_path=":memory:")
        
        orchestrator = Orchestrator(
            ha_client=mock_ha_client,
            mcp_server=mcp,
            approval_queue=approval_queue,
            agents=mock_agents,
            model_name="test-model"
        )
        
        assert orchestrator is not None
        assert len(orchestrator.agents) == 4
        assert "heating" in orchestrator.agents
        assert "cooling" in orchestrator.agents
        assert "lighting" in orchestrator.agents
        assert "security" in orchestrator.agents
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self, mock_ha_client, mock_agents):
        """Test workflow executes through all nodes"""
        from orchestrator import Orchestrator
        from approval_queue import ApprovalQueue
        from mcp_server import MCPServer
        
        mcp = MCPServer(mock_ha_client, dry_run=True)
        approval_queue = ApprovalQueue(db_path=":memory:")
        
        orchestrator = Orchestrator(
            ha_client=mock_ha_client,
            mcp_server=mcp,
            approval_queue=approval_queue,
            agents=mock_agents
        )
        
        # Execute one workflow cycle
        with patch.object(orchestrator.llm_client, 'chat') as mock_chat:
            mock_chat.return_value = {
                "message": {"content": '{"tasks": []}'}
            }
            await orchestrator.execute_workflow()
        
        # Verify workflow completed
        assert True  # No exceptions = success
    
    @pytest.mark.asyncio
    async def test_conflict_resolution(self, mock_ha_client, mock_agents):
        """Test heating/cooling conflict detection"""
        from orchestrator import Orchestrator, OrchestratorState, Decision
        from approval_queue import ApprovalQueue
        from mcp_server import MCPServer
        
        mcp = MCPServer(mock_ha_client, dry_run=True)
        approval_queue = ApprovalQueue(db_path=":memory:")
        
        orchestrator = Orchestrator(
            ha_client=mock_ha_client,
            mcp_server=mcp,
            approval_queue=approval_queue,
            agents=mock_agents
        )
        
        # Create state with conflicting decisions
        state = OrchestratorState(
            timestamp="2025-01-01T00:00:00",
            home_state={},
            tasks=[],
            decisions=[
                Decision(
                    agent_id="heating",
                    task_id="task_1",
                    reasoning="Heat the room",
                    actions=[{"tool": "set_temperature"}],
                    confidence=0.9,
                    impact_level="medium"
                ),
                Decision(
                    agent_id="cooling",
                    task_id="task_2",
                    reasoning="Cool the room",
                    actions=[{"tool": "set_temperature"}],
                    confidence=0.9,
                    impact_level="medium"
                )
            ],
            conflicts=[],
            approval_required=False,
            approved_actions=[],
            rejected_actions=[],
            execution_results=[]
        )
        
        # Resolve conflicts
        result = await orchestrator.resolve_conflicts(state)
        
        # Should detect conflict
        assert len(result["conflicts"]) > 0
        assert result["conflicts"][0]["conflict_type"] == "mutual_exclusion"


@pytest.mark.smoke
class TestApprovalQueueSmoke:
    """Smoke tests for approval queue"""
    
    @pytest.mark.asyncio
    async def test_approval_queue_initialization(self):
        """Test approval queue initializes with database"""
        from approval_queue import ApprovalQueue
        
        queue = ApprovalQueue(db_path=":memory:")
        assert queue is not None
        assert queue.auto_approval_rules is not None
    
    @pytest.mark.asyncio
    async def test_auto_approval_lighting(self):
        """Test lighting actions auto-approve"""
        from approval_queue import ApprovalQueue
        
        queue = ApprovalQueue(db_path=":memory:")
        
        request = await queue.add_request(
            agent_id="lighting",
            action_type="turn_on_light",
            action_data={"entity_id": "light.living_room"},
            impact_level="low",
            reason="Occupancy detected"
        )
        
        assert request.status == "approved"
        assert request.approved_by == "system"
    
    @pytest.mark.asyncio
    async def test_requires_approval_security(self):
        """Test security unlock requires approval"""
        from approval_queue import ApprovalQueue
        
        queue = ApprovalQueue(db_path=":memory:")
        
        request = await queue.add_request(
            agent_id="security",
            action_type="unlock_door",
            action_data={"entity_id": "lock.front_door"},
            impact_level="critical",
            reason="User arriving home"
        )
        
        assert request.status == "pending"
        assert request.approved_by is None
    
    @pytest.mark.asyncio
    async def test_approve_request(self):
        """Test manual approval workflow"""
        from approval_queue import ApprovalQueue
        
        queue = ApprovalQueue(db_path=":memory:")
        
        request = await queue.add_request(
            agent_id="security",
            action_type="unlock_door",
            action_data={"entity_id": "lock.front_door"},
            impact_level="critical",
            reason="Test"
        )
        
        # Approve request
        result = await queue.approve(request.id, approved_by="test_user")
        
        assert result is True
        
        # Verify approved
        updated = queue.get_request(request.id)
        assert updated.status == "approved"
        assert updated.approved_by == "test_user"


@pytest.mark.smoke
class TestNewAgentsSmoke:
    """Smoke tests for new agents"""
    
    @pytest.mark.asyncio
    async def test_cooling_agent_initialization(self, mock_ha_client):
        """Test Cooling Agent initializes"""
        from agents.cooling_agent import CoolingAgent
        from mcp_server import MCPServer
        
        mcp = MCPServer(mock_ha_client, dry_run=True)
        
        agent = CoolingAgent(
            mcp_server=mcp,
            ha_client=mock_ha_client,
            cooling_entities=["climate.living_room"],
            model_name="test-model"
        )
        
        assert agent is not None
        assert agent.agent_id == "cooling"
        assert len(agent.cooling_entities) == 1
    
    @pytest.mark.asyncio
    async def test_lighting_agent_initialization(self, mock_ha_client):
        """Test Lighting Agent initializes"""
        from agents.lighting_agent import LightingAgent
        from mcp_server import MCPServer
        
        mcp = MCPServer(mock_ha_client, dry_run=True)
        
        agent = LightingAgent(
            mcp_server=mcp,
            ha_client=mock_ha_client,
            lighting_entities=["light.living_room"],
            model_name="test-model"
        )
        
        assert agent is not None
        assert agent.agent_id == "lighting"
        assert len(agent.lighting_entities) == 1
    
    @pytest.mark.asyncio
    async def test_security_agent_initialization(self, mock_ha_client):
        """Test Security Agent initializes"""
        from agents.security_agent import SecurityAgent
        from mcp_server import MCPServer
        
        mcp = MCPServer(mock_ha_client, dry_run=True)
        
        agent = SecurityAgent(
            mcp_server=mcp,
            ha_client=mock_ha_client,
            security_entities=["alarm_control_panel.home", "lock.front_door"],
            model_name="test-model"
        )
        
        assert agent is not None
        assert agent.agent_id == "security"
        assert len(agent.security_entities) == 2


@pytest.mark.smoke
class TestEnhancedMCPSmoke:
    """Smoke tests for new MCP tools"""
    
    @pytest.mark.asyncio
    async def test_mcp_has_11_tools(self, mock_ha_client):
        """Test MCP server has 11 tools (3 Phase 1 + 8 Phase 2)"""
        from mcp_server import MCPServer
        
        mcp = MCPServer(mock_ha_client, dry_run=True)
        
        assert len(mcp.tools) == 11
        
        # Verify Phase 1 tools
        assert "set_temperature" in mcp.tools
        assert "get_climate_state" in mcp.tools
        assert "set_hvac_mode" in mcp.tools
        
        # Verify Phase 2 lighting tools
        assert "turn_on_light" in mcp.tools
        assert "turn_off_light" in mcp.tools
        assert "set_brightness" in mcp.tools
        assert "set_color_temp" in mcp.tools
        
        # Verify Phase 2 security tools
        assert "set_alarm_state" in mcp.tools
        assert "lock_door" in mcp.tools
        assert "unlock_door" in mcp.tools
        assert "enable_camera" in mcp.tools
    
    @pytest.mark.asyncio
    async def test_turn_on_light_dry_run(self, mock_ha_client):
        """Test turn_on_light in dry-run mode"""
        from mcp_server import MCPServer
        
        mcp = MCPServer(mock_ha_client, dry_run=True)
        
        result = await mcp.execute_tool(
            tool_name="turn_on_light",
            parameters={
                "entity_id": "light.living_room",
                "brightness": 80,
                "color_temp": 4000
            },
            agent_id="lighting"
        )
        
        assert "error" not in result
        assert result["dry_run"] is True
        assert result["brightness"] == 80
        assert result["color_temp"] == 4000
    
    @pytest.mark.asyncio
    async def test_unlock_door_requires_approval(self, mock_ha_client):
        """Test unlock_door returns approval required"""
        from mcp_server import MCPServer
        
        mcp = MCPServer(mock_ha_client, dry_run=False)
        
        result = await mcp.execute_tool(
            tool_name="unlock_door",
            parameters={"entity_id": "lock.front_door"},
            agent_id="security"
        )
        
        assert result["requires_approval"] is True
        assert "approval" in result["message"].lower()
