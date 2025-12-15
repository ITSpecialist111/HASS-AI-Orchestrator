# Smoke Test Suite

Quick validation tests for Phase 1 core functionality.

## Running Smoke Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio
```

### Run All Smoke Tests

```bash
# From backend directory
cd backend
pytest -m smoke -v
```

### Run Specific Test Files

```bash
# API tests only
pytest tests/test_api_smoke.py -v

# MCP server tests only
pytest tests/test_mcp_smoke.py -v

# Agent tests only
pytest tests/test_agent_smoke.py -v

# Configuration tests only
pytest tests/test_config_smoke.py -v
```

### Run with Coverage

```bash
pytest -m smoke --cov=. --cov-report=html
```

## Test Categories

### 🟢 Smoke Tests (`-m smoke`)
Quick, essential functionality validation:
- API endpoints respond correctly
- MCP tools are registered and validate input
- Agents initialize properly
- Configuration parses correctly

**Runtime**: ~5-10 seconds

### 🔵 Unit Tests (`-m unit`)
Isolated component tests (future):
- Individual function testing
- Mock all external dependencies

### 🟡 Integration Tests (`-m integration`)
End-to-end tests requiring external services (future):
- Real Ollama instance
- Real Home Assistant instance

## Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_api_smoke.py        # FastAPI endpoint tests
├── test_mcp_smoke.py        # MCP server tests
├── test_agent_smoke.py      # Agent framework tests
└── test_config_smoke.py     # Configuration validation tests
```

## Fixtures (conftest.py)

- `mock_ha_client`: Mocked Home Assistant WebSocket client
- `mock_ollama_client`: Mocked Ollama client
- `temp_data_dir`: Temporary directory for decision logs

## Expected Output

```
============================= test session starts =============================
collected 25 items / 0 deselected / 25 selected

tests/test_api_smoke.py::TestAPISmoke::test_health_endpoint PASSED        [  4%]
tests/test_api_smoke.py::TestAPISmoke::test_agents_endpoint PASSED        [  8%]
tests/test_api_smoke.py::TestAPISmoke::test_decisions_endpoint PASSED     [ 12%]
tests/test_api_smoke.py::TestAPISmoke::test_config_endpoint PASSED        [ 16%]
tests/test_mcp_smoke.py::TestMCPServerSmoke::test_mcp_server_initialization PASSED [ 20%]
tests/test_mcp_smoke.py::TestMCPServerSmoke::test_tool_schemas_available PASSED [ 24%]
tests/test_mcp_smoke.py::TestMCPServerSmoke::test_set_temperature_validation_success PASSED [ 28%]
tests/test_mcp_smoke.py::TestMCPServerSmoke::test_set_temperature_validation_bounds PASSED [ 32%]
tests/test_mcp_smoke.py::TestMCPServerSmoke::test_execute_tool_dry_run PASSED [ 36%]
tests/test_mcp_smoke.py::TestMCPServerSmoke::test_temperature_change_limit PASSED [ 40%]
tests/test_agent_smoke.py::TestAgentSmoke::test_heating_agent_initialization PASSED [ 44%]
tests/test_agent_smoke.py::TestAgentSmoke::test_agent_gather_context PASSED [ 48%]
tests/test_agent_smoke.py::TestAgentSmoke::test_agent_decide PASSED       [ 52%]
tests/test_agent_smoke.py::TestAgentSmoke::test_skills_loading PASSED     [ 56%]
tests/test_config_smoke.py::TestConfigSmoke::test_environment_variables_set PASSED [ 60%]
tests/test_config_smoke.py::TestConfigSmoke::test_dry_run_mode_parsing PASSED [ 64%]
tests/test_config_smoke.py::TestConfigSmoke::test_decision_interval_parsing PASSED [ 68%]

======================== 25 passed in 2.45s ================================
```

## CI/CD Integration

Add to GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run smoke tests
        run: |
          cd backend
          pytest -m smoke -v
```

## Troubleshooting

### Import Errors
```bash
# Ensure backend directory is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Async Test Warnings
```bash
# Install pytest-asyncio
pip install pytest-asyncio
```

### Missing test dependencies
```bash
# Update requirements.txt to include
pytest
pytest-asyncio
```
