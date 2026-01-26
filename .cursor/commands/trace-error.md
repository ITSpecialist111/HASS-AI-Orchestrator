# Trace Error

## Purpose
Follows error stack traces, identifies root causes, and provides diagnostic information for troubleshooting.

## Usage
`/trace-error [error-message|log-file]`

Arguments:
- `error-message` - Error message or exception text
- `log-file` - Path to log file containing error

## Instructions for Agent

When this command is invoked:

1. **Gather Error Information**:
   - Error message or exception
   - Stack trace if available
   - Log file location
   - When error occurred
   - What operation was being performed

2. **Read Log Files** (if applicable):
   ```bash
   Read: ai-orchestrator/backend/test_output.txt
   Read: /data/logs/orchestrator.log  # If in add-on environment
   ```
   - Find error in logs
   - Get full stack trace
   - Note context around error

3. **Analyze Stack Trace**:
   - Identify error type
   - Find originating file and line
   - Trace call chain
   - Identify root cause

4. **Read Relevant Code**:
   ```bash
   Read: [file from stack trace]
   ```
   - Understand what code is doing
   - Check error handling
   - Identify potential issues

5. **Check Related Components**:
   - Read dependencies
   - Check configuration
   - Verify environment setup
   - Review recent changes

6. **Provide Diagnosis**:

   Format:
   ```markdown
   ## Error Diagnosis
   
   **Error Type**: [Exception type]
   **Location**: [file:line]
   **Root Cause**: [Description]
   
   **Stack Trace**:
   ```
   [Full stack trace]
   ```
   
   **Analysis**:
   - What went wrong
   - Why it happened
   - What components involved
   
   **Possible Solutions**:
   1. Solution 1
   2. Solution 2
   3. Solution 3
   
   **Related Files**:
   - `path/to/file1.py` (line X)
   - `path/to/file2.py` (line Y)
   ```

7. **Check Knowledge Base**:
   - Look for similar errors in proj-knowledge
   - Check troubleshooting section
   - Document if new error type

8. **Suggest Fixes**:
   - Provide specific code fixes
   - Suggest configuration changes
   - Recommend workarounds if needed

## Expected Outcome

- Error root cause identified
- Stack trace analyzed
- Relevant code examined
- Diagnosis provided
- Solutions suggested
- Knowledge base updated if new error

## Common Error Types

### Import Errors
- Missing dependencies
- Incorrect import paths
- Circular dependencies

### Async Errors
- Missing `await`
- Event loop issues
- Race conditions

### Connection Errors
- WebSocket disconnections
- LLM provider unavailable
- Network issues

### Configuration Errors
- Missing required config
- Invalid values
- Environment variables

### Runtime Errors
- NoneType access
- Key errors
- Type mismatches

## Diagnostic Steps

1. **Read Error Message**: Understand what failed
2. **Check Stack Trace**: Find where it failed
3. **Read Source Code**: Understand context
4. **Check Dependencies**: Verify imports and setup
5. **Check Configuration**: Verify settings
6. **Check Logs**: Look for related errors
7. **Test Fix**: Verify solution works

## Best Practices

1. **Get full context**: Don't just look at error line
2. **Check recent changes**: What changed recently?
3. **Verify environment**: Is setup correct?
4. **Check dependencies**: Are all deps installed?
5. **Test incrementally**: Fix one thing at a time
6. **Document solutions**: Update knowledge base

## Integration

Works with:
- **check-logs**: Analyze log files
- **debug-agent**: Debug specific agent issues
- **proj-knowledge**: Document error patterns
- **share-findings**: Share solutions with team

## Example Diagnoses

### Import Error
```markdown
## Error Diagnosis

**Error Type**: ModuleNotFoundError
**Location**: `agents/heating_agent.py:5`
**Root Cause**: Missing import or incorrect path

**Analysis**:
- Trying to import `base_agent` but path is wrong
- Should be `from .base_agent import BaseAgent`

**Solution**:
Fix import statement in heating_agent.py
```

### Async Error
```markdown
## Error Diagnosis

**Error Type**: RuntimeError: coroutine was never awaited
**Location**: `orchestrator.py:305`
**Root Cause**: Missing await on async call

**Analysis**:
- `agent.receive_task()` is async but not awaited
- Should use `await` or `asyncio.create_task()`

**Solution**:
Change to: `await agent.receive_task(task)`
```
