# Trace Execution

## Purpose
Traces code execution for debugging by following execution paths, logging function calls, tracking variable states, identifying bottlenecks, and documenting findings.

## Usage
`/trace-execution <entry-point> [--depth N] [--log-variables] [--profile]`

Parameters:
- `entry-point`: Starting point (function, API endpoint, etc.)
- `--depth N`: Maximum call depth (default: 20)
- `--log-variables`: Track variable values at each step
- `--profile`: Include performance profiling

## Instructions for Agent

When this command is invoked:

1. **Identify Entry Point**:
   - Locate starting function/endpoint
   - Understand entry conditions
   - Note input parameters
   - Identify trigger

2. **Follow Execution Path**:
   - Step through function calls
   - Track control flow
   - Note conditional branches
   - Map async operations

3. **Log Function Calls**:
   - Record each function call
   - Note call parameters
   - Track return values
   - Log exceptions

4. **Track Variable States** (if --log-variables):
   - Capture variable values
   - Note state changes
   - Track data transformations
   - Identify unexpected values

5. **Identify Bottlenecks** (if --profile):
   - Measure execution time
   - Identify slow operations
   - Note resource usage
   - Find optimization opportunities

6. **Document Findings**:
   - Create execution trace
   - Note important observations
   - Highlight issues found
   - Suggest improvements

## Expected Outcome

- Execution trace log
- Function call sequence
- Variable state log (if flag set)
- Performance profile (if flag set)
- Bottleneck identification
- Debugging insights

## Examples

### Basic trace
```
/trace-execution "BaseAgent.decide()"
```

### Deep trace with variables
```
/trace-execution "orchestrator.plan()" --depth 30 --log-variables
```

### Trace with profiling
```
/trace-execution "POST /api/agents/{id}/decide" --profile
```

## Output Format

```markdown
# Execution Trace: [Entry Point]

## Entry Point
- **Function**: `path.to.function`
- **Parameters**: [parameter values]
- **Trigger**: [how it was called]

## Execution Path

### Step 1: [Function Name]
- **File**: `path/to/file.py:line`
- **Called From**: [caller]
- **Parameters**: [values]
- **Variables** (if --log-variables):
  - `var1`: [value]
  - `var2`: [value]
- **Duration** (if --profile): [time]
- **Return**: [return value]

### Step 2: [Function Name]
...

## Call Stack
```
[Function 1]
  └── [Function 2]
      └── [Function 3] ← Current
```

## Performance Profile (if --profile)
- **Total Duration**: [time]
- **Slowest Operations**:
  1. [Operation 1]: [time]
  2. [Operation 2]: [time]

## Bottlenecks Identified
- [Bottleneck 1]: [description] - [impact]
- [Bottleneck 2]: [description] - [impact]

## Observations
- [Observation 1]
- [Observation 2]

## Recommendations
- [Recommendation 1]
- [Recommendation 2]
```
