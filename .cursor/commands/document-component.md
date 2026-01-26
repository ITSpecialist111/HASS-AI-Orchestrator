# Document Component

## Purpose
Creates detailed documentation for a specific component, including API/interface, functionality, dependencies, and usage examples.

## Usage
`/document-component <component-path> [--format markdown|api] [--update-knowledge]`

Parameters:
- `component-path`: Path to component file or directory to document
- `--format`: Output format - markdown (default) or API documentation
- `--update-knowledge`: Automatically add to project knowledge base

## Instructions for Agent

When this command is invoked:

1. **Read Component Code**:
   - Read the component file(s)
   - Understand the code structure
   - Identify classes, functions, and methods
   - Note imports and dependencies

2. **Analyze Functionality**:
   - Understand what the component does
   - Identify key functions and their purposes
   - Map data flow (inputs, processing, outputs)
   - Note side effects and state changes

3. **Document API/Interface**:
   - List all public functions/methods
   - Document parameters and return types
   - Note exceptions and error conditions
   - Include type hints if available

4. **Document Dependencies**:
   - List required imports
   - Note external dependencies
   - Identify components that use this component
   - Map dependency relationships

5. **Create Examples**:
   - Write usage examples
   - Show common patterns
   - Include error handling examples
   - Note best practices

6. **Update Knowledge Base** (if --update-knowledge):
   - Use proj-knowledge skill
   - Add component entry to knowledge-base.md
   - Cross-reference with related components
   - Maintain consistent format

## Expected Outcome

- Comprehensive component documentation
- API reference (if --format api)
- Usage examples
- Dependency map
- Updated knowledge base entry (if flag set)

## Examples

### Document a Python module
```
/document-component ai-orchestrator/backend/orchestrator.py
```

### Document with knowledge update
```
/document-component ai-orchestrator/backend/mcp_server.py --update-knowledge
```

### Generate API documentation
```
/document-component ai-orchestrator/backend/agents/base_agent.py --format api
```

## Output Format

```markdown
# [Component Name] Documentation

## Location
`path/to/component`

## Purpose
[What this component does]

## API Reference

### Classes

#### ClassName
- **Description**: [class purpose]
- **Methods**:
  - `method_name(param1: type, param2: type) -> return_type`
    - Description: [what it does]
    - Parameters: [parameter descriptions]
    - Returns: [return value description]
    - Raises: [exceptions]

### Functions

#### function_name
- **Signature**: `function_name(param: type) -> return_type`
- **Description**: [function purpose]
- **Parameters**: [parameter details]
- **Returns**: [return value details]

## Dependencies

### Required
- [dependency 1]
- [dependency 2]

### Used By
- [component 1]
- [component 2]

## Usage Examples

\`\`\`python
# Example 1: Basic usage
[code example]

# Example 2: Advanced usage
[code example]
\`\`\`

## Patterns

- [Pattern 1]: [description]
- [Pattern 2]: [description]

## Notes
[Important notes, gotchas, warnings]
```
