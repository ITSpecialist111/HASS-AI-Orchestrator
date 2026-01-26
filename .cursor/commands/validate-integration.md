# Validate Integration

## Purpose
Validates component integration by testing API contracts, verifying data flow, checking error handling, validating security, and testing edge cases.

## Usage
`/validate-integration <component1> <component2> [--test-api] [--test-data-flow] [--test-security]`

Parameters:
- `component1`: First component in integration
- `component2`: Second component in integration
- `--test-api`: Test API contracts and interfaces
- `--test-data-flow`: Verify data flow between components
- `--test-security`: Validate security measures

## Instructions for Agent

When this command is invoked:

1. **Identify Integration Points**:
   - Find how components connect
   - Identify API boundaries
   - Note data exchange points
   - Map call flows

2. **Test API Contracts** (if --test-api):
   - Verify function signatures match
   - Test parameter validation
   - Check return type compatibility
   - Validate error responses

3. **Verify Data Flow** (if --test-data-flow):
   - Trace data from source to sink
   - Verify data transformations
   - Check data integrity
   - Test data format compatibility

4. **Check Error Handling**:
   - Test error propagation
   - Verify error messages
   - Check error recovery
   - Test edge cases

5. **Validate Security** (if --test-security):
   - Check authentication/authorization
   - Verify input validation
   - Test for vulnerabilities
   - Check data sanitization

6. **Test Edge Cases**:
   - Test boundary conditions
   - Test with invalid inputs
   - Test with missing data
   - Test under load

7. **Generate Report**:
   - Summarize test results
   - Note issues found
   - Suggest improvements
   - Document integration

## Expected Outcome

- Integration test results
- API contract validation
- Data flow verification
- Security validation
- Edge case test results
- Integration documentation

## Examples

### Validate API integration
```
/validate-integration mcp_server orchestrator --test-api
```

### Full integration validation
```
/validate-integration base_agent mcp_server --test-api --test-data-flow --test-security
```

### Test data flow
```
/validate-integration ha_client agents --test-data-flow
```

## Output Format

```markdown
# Integration Validation: [Component 1] ↔ [Component 2]

## Integration Points
- [Point 1]: [description]
- [Point 2]: [description]

## API Contract Tests (if --test-api)
- ✅ Function signature match
- ✅ Parameter validation
- ❌ Return type mismatch - [issue]
- ✅ Error response format

## Data Flow Tests (if --test-data-flow)
- ✅ Data transformation correct
- ✅ Data integrity maintained
- ⚠️ Performance concern - [issue]
- ✅ Format compatibility

## Error Handling
- ✅ Errors propagate correctly
- ✅ Error messages clear
- ✅ Recovery mechanisms work
- ❌ Edge case failure - [issue]

## Security Validation (if --test-security)
- ✅ Input validation
- ✅ Authentication check
- ✅ Authorization verified
- ⚠️ Potential vulnerability - [issue]

## Edge Cases
- ✅ Boundary conditions
- ✅ Invalid inputs handled
- ✅ Missing data handled
- ❌ Load test failure - [issue]

## Issues Found
1. [Issue 1]: [severity] - [description]
2. [Issue 2]: [severity] - [description]

## Recommendations
- [Recommendation 1]
- [Recommendation 2]
```
