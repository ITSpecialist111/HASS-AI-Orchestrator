# Understand Workflow

## Purpose
Traces and documents execution workflows, following code execution paths, documenting decision points, mapping data flow, and identifying integration points.

## Usage
`/understand-workflow <entry-point> [--follow-calls] [--depth N] [--document]`

Parameters:
- `entry-point`: Starting point (function, API endpoint, agent method)
- `--follow-calls`: Follow function calls recursively
- `--depth N`: Maximum call depth to follow (default: 10)
- `--document`: Create workflow documentation

## Instructions for Agent

When this command is invoked:

1. **Identify Entry Point**:
   - Locate the starting function/endpoint
   - Understand entry conditions
   - Note input parameters
   - Identify trigger conditions

2. **Trace Execution Path**:
   - Follow function calls step by step
   - Map control flow (if/else, loops, etc.)
   - Note async operations and awaits
   - Track exception handling

3. **Document Decision Points**:
   - Identify conditional branches
   - Note decision criteria
   - Map different execution paths
   - Document edge cases

4. **Map Data Flow**:
   - Track data transformations
   - Note state changes
   - Identify data sources and sinks
   - Map parameter passing

5. **Identify Integration Points**:
   - Find external service calls
   - Note database operations
   - Identify API calls
   - Map component boundaries

6. **Create Documentation** (if --document):
   - Write workflow description
   - Create flow diagram (text-based)
   - Document decision points
   - Note important details

## Expected Outcome

- Execution path trace
- Decision point map
- Data flow diagram
- Integration points list
- Workflow documentation (if flag set)

## Examples

### Trace agent decision workflow
```
/understand-workflow "BaseAgent.decide()" --follow-calls
```

### Trace API endpoint
```
/understand-workflow "POST /api/agents/{agent_id}/decide" --document
```

### Deep trace with documentation
```
/understand-workflow "orchestrator.plan()" --depth 15 --document
```

## Output Format

```markdown
# Workflow: [Workflow Name]

## Entry Point
- **Function**: `path.to.function`
- **Trigger**: [how it's called]
- **Input**: [input parameters]

## Execution Path

### Step 1: [Step Name]
- **Function**: `function_name()`
- **Action**: [what happens]
- **Data**: [data at this point]
- **Decision**: [if applicable]

### Step 2: [Step Name]
...

## Decision Points

1. **Decision Point 1**
   - Condition: [condition]
   - Path A: [if true]
   - Path B: [if false]

## Data Flow

```
Input → [Transformation 1] → [Transformation 2] → Output
```

## Integration Points

- [Integration 1]: [description]
- [Integration 2]: [description]

## Notes
[Important details, gotchas, performance considerations]
```
