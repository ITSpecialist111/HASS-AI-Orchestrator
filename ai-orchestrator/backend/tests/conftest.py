"""
Pytest configuration and shared fixtures.
"""
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set test environment variables
os.environ["HA_URL"] = "http://test-ha:8123"
os.environ["HA_TOKEN"] = "test-token"
os.environ["OLLAMA_HOST"] = "http://test-ollama:11434"
os.environ["DRY_RUN_MODE"] = "true"
os.environ["LOG_LEVEL"] = "ERROR"
os.environ["HEATING_MODEL"] = "test-model"
os.environ["HEATING_ENTITIES"] = "climate.test_room"
os.environ["DECISION_INTERVAL"] = "10"


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant WebSocket client"""
    client = AsyncMock()
    client.connected = True
    client.get_states = AsyncMock(return_value={
        "entity_id": "climate.test_room",
        "state": "heat",
        "attributes": {
            "current_temperature": 20.0,
            "temperature": 21.0,
            "hvac_mode": "heat"
        }
    })
    client.get_climate_state = AsyncMock(return_value={
        "entity_id": "climate.test_room",
        "state": "heat",
        "current_temperature": 20.0,
        "target_temperature": 21.0,
        "hvac_mode": "heat",
        "preset_mode": "none",
        "attributes": {}
    })
    client.call_service = AsyncMock(return_value={"success": True})
    client.subscribe_entities = AsyncMock(return_value=1)
    return client


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client"""
    client = MagicMock()
    client.chat = MagicMock(return_value={
        "message": {
            "content": '{"reasoning": "Test decision", "actions": []}'
        }
    })
    return client


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for tests"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    decisions_dir = data_dir / "decisions" / "heating"
    decisions_dir.mkdir(parents=True)
    
    # Monkey-patch Path to use temp directory
    original_path = Path
    
    def mock_path(path_str):
        if str(path_str).startswith("/data"):
            return original_path(str(path_str).replace("/data", str(data_dir)))
        return original_path(path_str)
    
    return data_dir
