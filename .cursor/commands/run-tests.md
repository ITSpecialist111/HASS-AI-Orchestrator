# Run Test Suite

## Purpose
Executes the comprehensive test suite for the AI Orchestrator backend, including smoke tests, integration tests, and validation.

## Usage
`/run-tests [scope]`

Scopes:
- `smoke` - Quick validation tests (<10s)
- `integration` - Full integration tests
- `all` - Complete test suite
- `[file]` - Specific test file

## Instructions for Agent

When this command is invoked:

1. **Check Prerequisites**:
   - Verify Python 3.11+ is available
   - Check if pytest is installed
   - Validate test environment variables

2. **Determine Execution Method**:
   - If Python 3.11+ available locally: Run directly
   - Otherwise: Use Docker test container

3. **Run Tests Based on Scope**:
   
   **For smoke tests**:
   ```bash
   cd ai-orchestrator/backend
   pytest -m smoke -v
   ```
   
   **For integration tests**:
   ```bash
   cd ai-orchestrator/backend
   pytest tests/ -v
   ```
   
   **For specific file**:
   ```bash
   cd ai-orchestrator/backend
   pytest tests/[file].py -v
   ```

4. **Docker Execution** (if needed):
   ```bash
   docker build -t ai-orchestrator:test -f Dockerfile.test .
   docker run --rm ai-orchestrator:test pytest -m smoke -v
   ```

5. **Parse and Report Results**:
   - Show pass/fail counts
   - Highlight any failures with details
   - Report coverage if available
   - Suggest fixes for common failures

6. **Post-Test Actions**:
   - Save test output to `backend/test_output.txt`
   - Update TEST_RESULTS.md if significant changes
   - Flag any new failures for investigation

## Expected Outcome
- Test execution summary displayed
- All test results clearly shown
- Any failures explained with context
- Recommendations for fixing failures

## Common Test Failures

- **Import errors**: Missing dependencies in requirements.txt
- **Connection errors**: Mock fixtures not properly configured
- **Async errors**: Missing pytest-asyncio markers
- **Config errors**: Environment variables not set in test
