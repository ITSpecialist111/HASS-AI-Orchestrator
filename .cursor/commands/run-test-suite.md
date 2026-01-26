# Run Test Suite

## Purpose
Executes the full test suite with reporting, generating coverage reports, identifying flaky tests, reporting results, and tracking test trends.

## Usage
`/run-test-suite [--coverage] [--verbose] [--filter PATTERN] [--report]`

Parameters:
- `--coverage`: Generate coverage report
- `--verbose`: Show detailed test output
- `--filter PATTERN`: Run only tests matching pattern
- `--report`: Generate detailed test report

## Instructions for Agent

When this command is invoked:

1. **Identify Test Suite**:
   - Locate test directories
   - Find test configuration files
   - Identify test frameworks used
   - Note test categories

2. **Run Test Suite**:
   - Execute all tests
   - Capture output
   - Track execution time
   - Note test failures

3. **Generate Coverage** (if --coverage):
   - Run coverage analysis
   - Calculate coverage percentages
   - Identify uncovered areas
   - Generate coverage report

4. **Identify Flaky Tests**:
   - Note tests that fail intermittently
   - Identify slow tests
   - Check for test dependencies
   - Note environment-specific failures

5. **Generate Report** (if --report):
   - Summarize test results
   - Categorize failures
   - Note test trends
   - Provide recommendations

6. **Track Trends**:
   - Compare with previous runs
   - Note new failures
   - Track coverage changes
   - Monitor test performance

## Expected Outcome

- Test execution results
- Coverage report (if flag set)
- Flaky test identification
- Detailed test report (if flag set)
- Test trend analysis

## Examples

### Run all tests
```
/run-test-suite
```

### Run with coverage
```
/run-test-suite --coverage --report
```

### Run specific tests
```
/run-test-suite --filter "test_mcp" --verbose
```

### Full test run
```
/run-test-suite --coverage --verbose --report
```

## Output Format

```markdown
# Test Suite Report

## Test Execution Summary
- **Total Tests**: [count]
- **Passed**: [count] ✅
- **Failed**: [count] ❌
- **Skipped**: [count] ⏭️
- **Duration**: [time]

## Test Results by Category

### Unit Tests
- Passed: [count]
- Failed: [count]
- [Failure details]

### Integration Tests
- Passed: [count]
- Failed: [count]
- [Failure details]

### Smoke Tests
- Passed: [count]
- Failed: [count]
- [Failure details]

## Coverage Report (if --coverage)
- **Overall Coverage**: [percentage]%
- **By Module**:
  - [Module 1]: [percentage]%
  - [Module 2]: [percentage]%

## Flaky Tests
- ⚠️ `test_name`: Failed [X] times in last [Y] runs

## Test Failures

### Critical Failures
1. [Test name]: [error message] - [file:line]

### Minor Failures
1. [Test name]: [error message] - [file:line]

## Test Trends
- **New Failures**: [count]
- **Fixed Tests**: [count]
- **Coverage Change**: [+/-X]%

## Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
```
