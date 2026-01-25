"""
Smoke tests for agent initialization and basic functionality.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.smoke
class TestAgentSmoke:
    """Smoke tests for agent framework"""
    
    @pytest.fixture
    def mock_skills_file(self, tmp_path):
        """Create a mock SKILLS.md file"""
        skills_dir = tmp_path / "skills" / "heating"
        skills_dir.mkdir(parents=True)
        skills_file = skills_dir / "SKILLS.md"
        
        skills_content = """# Heating Agent

## 1. Identity
Test heating agent

## 2. Controllable Entities
- climate.test_room

## 3. Observable Entities
- sensor.outdoor_temp

## 4. Available Tools
- set_temperature
- get_climate_state

## 5. Decision Criteria
Maintain comfort at 19-22°C

## 6. Example Scenarios
Test scenario

## 7. Performance Targets
95% accuracy
"""
        skills_file.write_text(skills_content)
        return skills_file
    
    @pytest.mark.asyncio
    async def test_heating_agent_initialization(self, mock_ha_client, mock_skills_file):
        """Test Heating Agent can be initialized"""
        with patch('agents.base_agent.LocalProvider') as mock_provider:
            mock_provider.return_value = MagicMock()
            
            with patch('agents.base_agent.Path') as mock_path:
                mock_path.return_value = mock_skills_file
                
                from agents.heating_agent import HeatingAgent
                from mcp_server import MCPServer
                
                mcp = MCPServer(mock_ha_client, dry_run=True)
                
                agent = HeatingAgent(
                    mcp_server=mcp,
                    ha_client=mock_ha_client,
                    heating_entities=["climate.test_room"],
                    model_name="test-model",
                    decision_interval=10
                )
                
                assert agent is not None
                assert agent.agent_id == "heating"
                assert agent.name == "Heating Agent"
                assert agent.model_name == "test-model"
                assert agent.decision_interval == 10
                assert len(agent.heating_entities) == 1
    
    @pytest.mark.asyncio
    async def test_agent_gather_context(self, mock_ha_client, mock_skills_file):
        """Test agent can gather context from HA"""
        with patch('agents.base_agent.LocalProvider') as mock_provider:
            mock_provider.return_value = MagicMock()
            
            with patch('agents.base_agent.Path') as mock_path:
                mock_path.return_value = mock_skills_file
                
                from agents.heating_agent import HeatingAgent
                from mcp_server import MCPServer
                
                mcp = MCPServer(mock_ha_client, dry_run=True)
                agent = HeatingAgent(
                    mcp_server=mcp,
                    ha_client=mock_ha_client,
                    heating_entities=["climate.test_room"],
                    model_name="test-model"
                )
                
                context = await agent.gather_context()
                
                assert context is not None
                assert "timestamp" in context
                assert "climate_states" in context
                assert "sensors" in context
                assert "time_of_day" in context
                assert "climate.test_room" in context["climate_states"]
    
    @pytest.mark.asyncio
    async def test_agent_decide(self, mock_ha_client, mock_ollama_client, mock_skills_file):
        """Test agent can make decisions"""
        with patch('agents.base_agent.LocalProvider') as mock_provider_class:
            mock_provider_class.return_value = mock_ollama_client
            
            with patch('agents.base_agent.Path') as mock_path:
                mock_path.return_value = mock_skills_file
                
                from agents.heating_agent import HeatingAgent
                from mcp_server import MCPServer
                
                mcp = MCPServer(mock_ha_client, dry_run=True)
                agent = HeatingAgent(
                    mcp_server=mcp,
                    ha_client=mock_ha_client,
                    heating_entities=["climate.test_room"],
                    model_name="test-model"
                )
                
                context = {"climate_states": {}, "sensors": {}, "time_of_day": "morning"}
                decision = await agent.decide(context)
                
                assert decision is not None
                assert "reasoning" in decision
                assert "actions" in decision
                assert isinstance(decision["actions"], list)
    
    @pytest.mark.asyncio
    async def test_agent_execute_empty_actions(self, mock_ha_client, mock_skills_file):
        """Test agent handles empty action list"""
        with patch('agents.base_agent.LocalProvider') as mock_provider:
            mock_provider.return_value = MagicMock()
            
            with patch('agents.base_agent.Path') as mock_path:
                mock_path.return_value = mock_skills_file
                
                from agents.heating_agent import HeatingAgent
                from mcp_server import MCPServer
                
                mcp = MCPServer(mock_ha_client, dry_run=True)
                agent = HeatingAgent(
                    mcp_server=mcp,
                    ha_client=mock_ha_client,
                    heating_entities=["climate.test_room"],
                    model_name="test-model"
                )
                
                decision = {"reasoning": "No action needed", "actions": []}
                results = await agent.execute(decision)
                
                assert results is not None
                assert isinstance(results, list)
                assert len(results) == 0
    
    def test_skills_loading(self, mock_ha_client, mock_skills_file):
        """Test SKILLS.md file is loaded correctly"""
        with patch('agents.base_agent.LocalProvider') as mock_provider:
            mock_provider.return_value = MagicMock()
            
            with patch('agents.base_agent.Path') as mock_path:
                mock_path.return_value = mock_skills_file
                
                from agents.heating_agent import HeatingAgent
                from mcp_server import MCPServer
                
                mcp = MCPServer(mock_ha_client, dry_run=True)
                agent = HeatingAgent(
                    mcp_server=mcp,
                    ha_client=mock_ha_client,
                    heating_entities=["climate.test_room"],
                    model_name="test-model"
                )
                
                assert agent.skills is not None
                assert "identity" in agent.skills
                assert "controllable_entities" in agent.skills
                assert len(agent.skills["controllable_entities"]) > 0
