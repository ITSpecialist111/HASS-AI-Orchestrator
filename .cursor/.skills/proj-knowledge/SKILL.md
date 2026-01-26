---
name: proj-knowledge
description: Builds and maintains an evolving knowledge base documenting the HASS AI Orchestrator project structure, components, functions, architecture, and patterns. Use when exploring the codebase, documenting new components, understanding system architecture, or when the user asks about project structure, components, or how things work.
---

# Project Knowledge Base

## Purpose

This skill helps agents build and maintain a comprehensive, evolving knowledge base of the HASS AI Orchestrator project. The knowledge base documents:

- Project structure and organization
- Component purposes and responsibilities
- Function signatures and behaviors
- Architecture patterns and design decisions
- Integration points and dependencies
- Important conventions and patterns
- Agent capabilities and workflows

## Knowledge Base Location

The knowledge base is stored in `.cursor/.skills/proj-knowledge/knowledge-base.md`. This file should be updated whenever new information is discovered or components change.

## When to Update

Update the knowledge base when:

1. **Exploring new areas**: After using `/explore-project` or `/document-component`
2. **Discovering patterns**: When identifying common patterns or conventions
3. **Understanding workflows**: After tracing execution paths
4. **Component changes**: When components are modified or added
5. **Integration discovery**: When understanding how components interact
6. **Error resolution**: When fixing bugs reveals important information

## Knowledge Base Structure

The knowledge base uses a hierarchical structure:

```markdown
# HASS AI Orchestrator - Project Knowledge Base

## Project Overview
[High-level description, purpose, architecture]

## Directory Structure
[Key directories and their purposes]

## Core Components

### Component Name
- **Location**: `path/to/component`
- **Purpose**: [What it does]
- **Key Functions**: [Main functions/methods]
- **Dependencies**: [What it depends on]
- **Used By**: [What depends on it]
- **Patterns**: [Design patterns used]

## Agents

### Agent Name
- **Location**: `path/to/agent`
- **Purpose**: [Agent's role]
- **Capabilities**: [What it can do]
- **Tools**: [MCP tools it uses]
- **Decision Logic**: [How it makes decisions]

## Integration Points
[How components connect]

## Patterns & Conventions
[Common patterns, coding standards]

## Important Notes
[Critical information, gotchas, warnings]
```

## Adding Knowledge

### For New Components

1. **Read the component code** to understand its purpose
2. **Identify key functions** and their signatures
3. **Document dependencies** (imports, required services)
4. **Note usage patterns** (how it's called, when it's used)
5. **Add to knowledge base** in appropriate section

### For Workflows

1. **Trace execution path** through code
2. **Document decision points** and conditions
3. **Map data flow** (inputs, transformations, outputs)
4. **Note integration points** with other components
5. **Add workflow diagram** or description

### For Patterns

1. **Identify recurring patterns** in code
2. **Document the pattern** with examples
3. **Note when to use** the pattern
4. **Link to related components** using the pattern

## Knowledge Quality Standards

- **Be specific**: Include file paths, function names, actual code examples
- **Be current**: Update when code changes
- **Be cross-referenced**: Link related components
- **Be actionable**: Include information agents can use
- **Be organized**: Use consistent structure and formatting

## Example Entry

```markdown
### MCP Server (`ai-orchestrator/backend/mcp_server.py`)
- **Purpose**: Model Context Protocol server that safely executes agent decisions
- **Key Functions**:
  - `_register_tools()`: Registers available MCP tools
  - `execute_tool()`: Executes tool calls with validation
  - `_set_temperature()`: Sets climate entity temperature (10-30°C bounds)
- **Dependencies**: `ha_client`, `approval_queue`, `rag_manager`
- **Used By**: All agents via `orchestrator.mcp_server`
- **Patterns**: Tool registration pattern, safety validation pattern
- **Important**: All tool calls go through safety validation; dry-run mode logs without executing
```

## Maintenance

- **Review regularly**: Check for outdated information
- **Update on changes**: Modify entries when code changes
- **Consolidate duplicates**: Merge similar information
- **Remove obsolete**: Delete information about removed components
- **Cross-reference**: Link related entries

## Using the Knowledge Base

When working on tasks:

1. **Check knowledge base first** for existing information
2. **Reference relevant entries** when making changes
3. **Update entries** if you discover new information
4. **Add new entries** for newly understood components

## Integration with Other Skills

- **The-plan skill**: Knowledge base helps understand task context
- **Task-completion skill**: Update knowledge base when completing documentation tasks
- **Commands**: `/document-component` and `/update-knowledge` use this skill
