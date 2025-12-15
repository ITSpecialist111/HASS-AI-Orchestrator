"""
Smoke tests for configuration and environment setup.
"""
import pytest
import os


@pytest.mark.smoke
class TestConfigSmoke:
    """Smoke tests for configuration"""
    
    def test_environment_variables_set(self):
        """Test required environment variables are set"""
        required_vars = [
            "HA_URL",
            "HA_TOKEN",
            "OLLAMA_HOST",
            "DRY_RUN_MODE",
            "LOG_LEVEL",
            "HEATING_MODEL"
        ]
        
        for var in required_vars:
            assert os.getenv(var) is not None, f"Environment variable {var} not set"
    
    def test_dry_run_mode_parsing(self):
        """Test dry run mode parses correctly"""
        dry_run = os.getenv("DRY_RUN_MODE", "false").lower() == "true"
        assert isinstance(dry_run, bool)
    
    def test_decision_interval_parsing(self):
        """Test decision interval parses to integer"""
        interval = int(os.getenv("DECISION_INTERVAL", "120"))
        assert isinstance(interval, int)
        assert interval > 0
    
    def test_heating_entities_parsing(self):
        """Test heating entities can be parsed"""
        entities = os.getenv("HEATING_ENTITIES", "").split(",")
        entities = [e.strip() for e in entities if e.strip()]
        
        assert isinstance(entities, list)
    
    def test_ollama_host_format(self):
        """Test Ollama host has valid format"""
        host = os.getenv("OLLAMA_HOST")
        
        assert host.startswith("http://") or host.startswith("https://")
    
    def test_ha_url_format(self):
        """Test HA URL has valid format"""
        url = os.getenv("HA_URL")
        
        assert url.startswith("http://") or url.startswith("https://")
    
    def test_log_level_valid(self):
        """Test log level is valid"""
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        assert log_level in valid_levels
