# Explore Project

## Purpose
Systematically explores and documents the project structure, identifying key components, mapping dependencies, and updating the project knowledge base.

## Usage
`/explore-project [target-path] [--depth N] [--update-knowledge]`

Parameters:
- `target-path` (optional): Specific directory or file to explore (default: project root)
- `--depth N`: Maximum directory depth to explore (default: 5)
- `--update-knowledge`: Automatically update knowledge base with findings

## Instructions for Agent

When this command is invoked:

1. **Scan Directory Structure**:
   - List all directories and files in target path
   - Identify key directories (backend, frontend, config, tests, etc.)
   - Note file types and organization patterns
   - Map directory hierarchy

2. **Identify Key Components**:
   - Find main entry points (main.py, index.js, etc.)
   - Identify core modules and their purposes
   - Locate configuration files
   - Find test directories
   - Note documentation files

3. **Analyze Dependencies**:
   - Read requirements.txt, package.json, etc.
   - Identify external dependencies
   - Map internal dependencies (imports)
   - Note dependency relationships

4. **Document Findings**:
   - Create structured summary of findings
   - Note important patterns discovered
   - Identify integration points
   - Highlight key files and their purposes

5. **Update Knowledge Base** (if --update-knowledge):
   - Use proj-knowledge skill to add findings
   - Update knowledge-base.md with new information
   - Cross-reference related components
   - Maintain consistent structure

## Expected Outcome

- Comprehensive directory structure map
- List of key components with purposes
- Dependency graph or list
- Updated knowledge base (if flag set)
- Summary report of findings

## Examples

### Explore entire project
```
/explore-project
```

### Explore backend only
```
/explore-project ai-orchestrator/backend
```

### Explore with knowledge update
```
/explore-project --update-knowledge
```

### Deep exploration
```
/explore-project ai-orchestrator/backend/agents --depth 10
```

## Output Format

```markdown
# Project Exploration Report

## Target Path
[path explored]

## Directory Structure
[tree or list of directories]

## Key Components
- [Component Name] (`path/to/component`)
  - Purpose: [description]
  - Type: [module/package/script/etc.]

## Dependencies
- External: [list]
- Internal: [dependency graph]

## Patterns Discovered
- [Pattern 1]
- [Pattern 2]

## Integration Points
- [Point 1]
- [Point 2]

## Recommendations
- [Suggestions for further exploration]
```
