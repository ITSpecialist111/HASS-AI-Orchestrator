# Diagnose Error

## Purpose
Diagnoses and fixes errors by analyzing error logs, tracing execution paths, identifying root causes, proposing fixes, and testing solutions.

## Usage
`/diagnose-error [error-message] [--trace] [--fix] [--test]`

Parameters:
- `error-message` (optional): Error message or log entry to diagnose
- `--trace`: Trace execution path to error
- `--fix`: Attempt to fix the error automatically
- `--test`: Test the fix after applying

## Instructions for Agent

When this command is invoked:

1. **Analyze Error Logs**:
   - Read error messages
   - Identify error type
   - Note stack traces
   - Check recent changes

2. **Trace Execution Path** (if --trace):
   - Follow code execution to error
   - Identify failing function
   - Map call stack
   - Note variable states

3. **Identify Root Cause**:
   - Analyze error context
   - Check input data
   - Verify dependencies
   - Identify trigger conditions

4. **Propose Fixes**:
   - Suggest code changes
   - Note alternative solutions
   - Consider edge cases
   - Document fix approach

5. **Apply Fix** (if --fix):
   - Implement the fix
   - Update code
   - Add error handling if needed
   - Update tests

6. **Test Solution** (if --test):
   - Run relevant tests
   - Verify fix works
   - Check for regressions
   - Validate error handling

## Expected Outcome

- Error analysis report
- Root cause identification
- Execution trace (if flag set)
- Proposed fixes
- Applied fix (if --fix)
- Test results (if --test)

## Examples

### Diagnose from error message
```
/diagnose-error "TypeError: 'NoneType' object has no attribute 'execute'"
```

### Diagnose with trace
```
/diagnose-error --trace
```

### Diagnose and fix
```
/diagnose-error "Connection timeout" --fix --test
```

## Output Format

```markdown
# Error Diagnosis Report

## Error Information
- **Error Type**: [TypeError/ValueError/etc.]
- **Error Message**: [message]
- **Location**: [file:line]
- **Timestamp**: [when it occurred]

## Execution Trace (if --trace)
1. [Function 1] - [file:line]
2. [Function 2] - [file:line]
3. [Function 3] - [file:line] ← **Error occurred here**

## Root Cause Analysis
- **Primary Cause**: [description]
- **Contributing Factors**: [list]
- **Trigger Conditions**: [when it happens]

## Proposed Fixes

### Fix 1: [Title]
- **Approach**: [how to fix]
- **Code Changes**: [what to change]
- **Risk**: [low/medium/high]

### Fix 2: [Title] (Alternative)
- **Approach**: [how to fix]
- **Code Changes**: [what to change]
- **Risk**: [low/medium/high]

## Applied Fix (if --fix)
- **Fix Applied**: [which fix]
- **Files Modified**: [list]
- **Changes Made**: [description]

## Test Results (if --test)
- ✅ Original error fixed
- ✅ No regressions
- ✅ Error handling improved
```
