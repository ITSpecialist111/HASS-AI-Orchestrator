# Test Component

## Purpose
Creates and runs tests for a component, identifying test cases, writing unit tests, running the test suite, reporting coverage, and fixing failing tests.

## Usage
`/test-component <component-path> [--create] [--run] [--coverage] [--fix]`

Parameters:
- `component-path`: Path to component to test
- `--create`: Create new tests if they don't exist
- `--run`: Run existing tests
- `--coverage`: Generate coverage report
- `--fix`: Attempt to fix failing tests

## Instructions for Agent

When this command is invoked:

1. **Identify Component**:
   - Locate component file(s)
   - Understand component structure
   - Identify public interface
   - Note dependencies

2. **Identify Test Cases**:
   - List functions/methods to test
   - Identify edge cases
   - Note error conditions
   - Map integration points

3. **Check Existing Tests**:
   - Look for existing test files
   - Review test coverage
   - Identify gaps
   - Note test quality

4. **Create Tests** (if --create or no tests exist):
   - Write unit tests for each function
   - Test happy paths
   - Test edge cases
   - Test error handling
   - Use appropriate test framework (pytest for Python, jest for JS)

5. **Run Tests** (if --run or after creation):
   - Execute test suite
   - Capture results
   - Identify failures
   - Note flaky tests

6. **Generate Coverage** (if --coverage):
   - Run coverage analysis
   - Identify uncovered code
   - Report coverage percentage
   - Suggest additional tests

7. **Fix Failing Tests** (if --fix):
   - Analyze failure reasons
   - Fix test code if broken
   - Fix component code if bug found
   - Re-run tests to verify

## Expected Outcome

- Test file created (if needed)
- Test execution results
- Coverage report (if flag set)
- Fixed tests (if --fix)
- Test quality assessment

## Examples

### Create and run tests
```
/test-component ai-orchestrator/backend/mcp_server.py --create --run
```

### Run existing tests with coverage
```
/test-component ai-orchestrator/backend/orchestrator.py --run --coverage
```

### Fix failing tests
```
/test-component ai-orchestrator/backend/agents/base_agent.py --run --fix
```

## Output Format

```markdown
# Test Report: [Component Name]

## Component
- **Path**: `path/to/component`
- **Type**: [Python module/React component/etc.]

## Test Cases Identified
- [Test case 1]
- [Test case 2]
- [Test case 3]

## Tests Created/Updated
- `tests/test_component.py` - [test count] tests

## Test Results

### Summary
- **Total Tests**: [count]
- **Passed**: [count] ✅
- **Failed**: [count] ❌
- **Skipped**: [count] ⏭️

### Test Details
- ✅ `test_function_happy_path`: Passed
- ✅ `test_function_edge_case`: Passed
- ❌ `test_function_error_handling`: Failed - [reason]

## Coverage Report (if --coverage)
- **Overall Coverage**: [percentage]%
- **Lines Covered**: [count]/[total]
- **Functions Covered**: [count]/[total]
- **Uncovered**: [list of uncovered areas]

## Fixes Applied (if --fix)
- [Fix 1]: [what was fixed]
- [Fix 2]: [what was fixed]

## Recommendations
- [Recommendation 1]
- [Recommendation 2]
```
