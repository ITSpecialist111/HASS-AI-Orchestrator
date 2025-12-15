"""
Smoke tests for FastAPI application.
Tests basic endpoint availability and response structure.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.smoke
class TestAPISmoke:
    """Smoke tests for FastAPI endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies"""
        # Mock the lifespan dependencies
        with patch('main.HAWebSocketClient') as mock_ha, \
             patch('main.MCPServer') as mock_mcp, \
             patch('main.HeatingAgent') as mock_agent:
            
            # Configure mocks
            mock_ha_instance = AsyncMock()
            mock_ha_instance.connected = True
            mock_ha_instance.connect = AsyncMock()
            mock_ha_instance.disconnect = AsyncMock()
            mock_ha.return_value = mock_ha_instance
            
            mock_mcp_instance = MagicMock()
            mock_mcp.return_value = mock_mcp_instance
            
            mock_agent_instance = MagicMock()
            mock_agent_instance.status = "idle"
            mock_agent_instance.model_name = "test-model"
            mock_agent_instance.decision_interval = 120
            mock_agent_instance.get_last_decision_file = MagicMock(return_value=None)
            mock_agent_instance.run_decision_loop = AsyncMock()
            mock_agent.return_value = mock_agent_instance
            
            # Import after patching
            from main import app
            
            # Store mocked instances on app state
            app.state.ha_client = mock_ha_instance
            app.state.mcp_server = mock_mcp_instance
            app.state.heating_agent = mock_agent_instance
            
            with TestClient(app) as test_client:
                yield test_client
    
    def test_health_endpoint(self, client):
        """Test /api/health endpoint responds"""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_agents_endpoint(self, client):
        """Test /api/agents endpoint returns agent list"""
        # Patch globals after app import
        from main import heating_agent
        
        with patch('main.heating_agent') as mock_agent:
            mock_agent.status = "idle"
            mock_agent.model_name = "test-model"
            mock_agent.decision_interval = 120
            mock_agent.get_last_decision_file = MagicMock(return_value=None)
            
            response = client.get("/api/agents")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    def test_decisions_endpoint(self, client):
        """Test /api/decisions endpoint returns decision log"""
        response = client.get("/api/decisions")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_decisions_endpoint_with_limit(self, client):
        """Test /api/decisions endpoint respects limit parameter"""
        response = client.get("/api/decisions?limit=50")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 50
    
    def test_config_endpoint(self, client):
        """Test /api/config endpoint returns configuration"""
        response = client.get("/api/config")
        
        assert response.status_code == 200
        data = response.json()
        assert "ollama_host" in data
        assert "dry_run_mode" in data
        assert "log_level" in data
        assert "heating_model" in data
        assert "decision_interval" in data
    
    def test_config_values(self, client):
        """Test /api/config returns expected test values"""
        response = client.get("/api/config")
        data = response.json()
        
        assert data["ollama_host"] == "http://test-ollama:11434"
        assert data["dry_run_mode"] is True
        assert data["heating_model"] == "test-model"
        assert data["decision_interval"] == 10
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns response"""
        response = client.get("/")
        
        # Should return either dashboard or service unavailable
        assert response.status_code in [200, 503]
