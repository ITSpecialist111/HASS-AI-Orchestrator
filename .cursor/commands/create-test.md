# Create Test

## Purpose
Generates test structure and boilerplate for new features, following project testing patterns and conventions.

## Usage
`/create-test [component] [test-type]`

Arguments:
- `component` - Component to test (agent name, module name, etc.)
- `test-type` - Type of test (smoke, integration, unit)

## Instructions for Agent

When this command is invoked:

1. **Understand Requirements**:
   - What component needs testing?
   - What type of test (smoke/integration/unit)?
   - What functionality should be tested?

2. **Read Existing Test Patterns**:
   ```bash
   Read: ai-orchestrator/backend/tests/test_agent_smoke.py
   Read: ai-orchestrator/backend/tests/conftest.py
   Read: ai-orchestrator/backend/pytest.ini
   ```
   - Understand test structure
   - Note fixtures available
   - Check marker usage

3. **Read Component to Test**:
   ```bash
   Read: ai-orchestrator/backend/[component].py
   ```
   - Understand what needs testing
   - Identify test cases
   - Note dependencies to mock

4. **Generate Test File**:

   **File naming**: `test_<component>_<type>.py`

   **Structure**:
   ```python
   import pytest
   import asyncio
   from unittest.mock import AsyncMock, MagicMock
   
   # For async tests
   pytestmark = pytest.mark.asyncio
   
   # For smoke tests
   @pytest.mark.smoke
   class TestComponentSmoke:
       """Smoke tests for Component"""
       
       async def test_initialization(self):
           """Test component can be initialized"""
           # Test code
           pass
       
       async def test_basic_functionality(self):
           """Test basic functionality works"""
           # Test code
           pass
   
   # For integration tests
   @pytest.mark.integration
   class TestComponentIntegration:
       """Integration tests for Component"""
       
       async def test_full_workflow(self):
           """Test complete workflow"""
           # Test code
           pass
   ```

5. **Follow Project Patterns**:

   **Smoke Tests**:
   - Quick validation (<10s)
   - Test initialization
   - Test basic functionality
   - Use `@pytest.mark.smoke`

   **Integration Tests**:
   - Full system tests
   - May require mocks
   - Test workflows
   - Use `@pytest.mark.integration`

   **Unit Tests**:
   - Isolated component tests
   - Mock all dependencies
   - Test specific methods
   - Use `@pytest.mark.unit`

6. **Use Available Fixtures**:
   - Check `conftest.py` for fixtures
   - Use mocks for external dependencies
   - Use async fixtures for async code

7. **Add to Test Suite**:
   - Place in `ai-orchestrator/backend/tests/`
   - Follow naming convention
   - Ensure imports work

8. **Verify Test Structure**:
   - Run: `pytest tests/test_<component>_<type>.py -v`
   - Fix any import errors
   - Ensure tests are discoverable

## Expected Outcome

- Test file created with proper structure
- Follows project conventions
- Uses appropriate markers
- Includes basic test cases
- Ready for implementation

## Test Patterns

### Agent Tests
```python
@pytest.mark.smoke
class TestHeatingAgentSmoke:
    async def test_agent_initialization(self, mock_ha_client, mock_llm):
        agent = HeatingAgent(
            ha_client=mock_ha_client,
            llm_client=mock_llm
        )
        assert agent is not None
    
    async def test_gather_context(self, heating_agent):
        context = await heating_agent.gather_context()
        assert isinstance(context, dict)
```

### API Tests
```python
@pytest.mark.integration
class TestAgentAPI:
    async def test_list_agents(self, client):
        response = await client.get("/api/agents")
        assert response.status_code == 200
        assert "agents" in response.json()
```

### Component Tests
```python
@pytest.mark.unit
class TestMCPServer:
    def test_validate_tool_call(self, mcp_server):
        result = mcp_server.validate_tool_call(
            domain="light",
            service="turn_on"
        )
        assert result is True
```

## Common Test Cases

### Initialization
- Component can be created
- Required parameters validated
- Default values set correctly

### Basic Functionality
- Core methods work
- Returns expected types
- Handles normal inputs

### Error Handling
- Raises appropriate exceptions
- Handles invalid inputs
- Graceful degradation

### Integration
- Works with other components
- End-to-end workflows
- Real-world scenarios

## Best Practices

1. **Follow naming**: `test_<component>_<type>.py`
2. **Use markers**: `@pytest.mark.smoke`, etc.
3. **Mock external**: Don't depend on real services
4. **Test async**: Use `@pytest.mark.asyncio`
5. **Be specific**: Clear test names and assertions
6. **Keep fast**: Smoke tests <10s
7. **Cover edge cases**: Not just happy path

## Integration

Works with:
- **run-tests**: Execute the created tests
- **analyze-test-coverage**: Check coverage
- **proj-knowledge**: Document test patterns
