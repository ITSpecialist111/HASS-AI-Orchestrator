# AI Orchestrator Debug & Coordination Subagents

This directory contains specialized subagents designed to ensure code quality, catch bugs, coordinate parallel work, and maintain system reliability for the AI Orchestrator project.

## Overview

These subagents work together as a comprehensive quality assurance and coordination pipeline for AI-driven development workflows, with special focus on async Python code, Home Assistant integration, and multi-agent systems.

## Subagent Categories

### 🔍 Code Quality & Validation

#### post-code-validator
**When:** After ANY code changes, before testing
- Validates Python syntax and imports
- Checks async/await patterns
- Verifies type hints
- Catches common coding errors
- Provides immediate fixes

#### integration-tester
**When:** After validation passes, before completion
- Tests component integration
- Validates agent communication
- Checks MCP server integration
- Ensures HA client compatibility
- Runs progressive test suites

#### holistic-reviewer
**When:** Alongside integration testing
- Reviews architectural impact
- Analyzes cross-component effects
- Assesses security & safety
- Evaluates performance implications
- Considers long-term maintainability

### 🤝 Parallel Work Coordination

#### parallel-coordinator
**When:** Before starting parallel work
- Prevents conflicts proactively
- Coordinates task distribution
- Manages resource allocation
- Tracks dependencies
- Optimizes execution strategy

#### merge-coordinator
**When:** Multiple agents working simultaneously
- Merges parallel changes intelligently
- Resolves conflicts automatically when possible
- Selects best implementations
- Validates merged code
- Documents merge decisions

### 🐛 Debugging Specialists

#### async-debugger
**When:** Async code modified or concurrency issues
- Detects missing awaits
- Finds race conditions
- Identifies deadlocks
- Tracks async tasks
- Fixes concurrency bugs

#### error-pattern-analyzer
**When:** Debugging or monitoring system health
- Analyzes error patterns
- Identifies root causes
- Predicts failures
- Recommends preventive measures
- Tracks error trends

#### ha-integration-validator
**When:** HA client or agent logic changes
- Validates entity IDs
- Checks service call formats
- Verifies WebSocket messages
- Ensures MCP tool correctness
- Prevents HA integration errors

### 🚀 Deployment & Release

#### deployment-validator
**When:** Before commit, PR, or deployment
- Final quality gate
- Configuration validation
- Security checks
- Performance validation
- Documentation review
- Deployment readiness assessment

## Usage Workflow

### Standard Development Flow

```
1. Code Implementation
   ↓
2. post-code-validator (catches syntax/pattern issues)
   ↓
3. integration-tester (validates component integration)
   ↓
4. holistic-reviewer (assesses broader impacts)
   ↓
5. deployment-validator (final sign-off)
```

### Parallel Development Flow

```
1. Task Planning
   ↓
2. parallel-coordinator (prevents conflicts)
   ↓
3. [Multiple agents work in parallel]
   ↓
4. merge-coordinator (intelligent merge)
   ↓
5. Standard validation flow (steps 2-5 above)
```

### Debugging Flow

```
1. Issue Detected
   ↓
2. error-pattern-analyzer (identify patterns)
   ↓
3. Specialized debugger (async-debugger or ha-integration-validator)
   ↓
4. Fix Applied
   ↓
5. Standard validation flow
```

## When to Use Each Subagent

### Use Proactively (Automatic Triggers)

These should run automatically without explicit request:

- **post-code-validator**: After every code change
- **integration-tester**: After validation passes
- **parallel-coordinator**: When multiple tasks assigned
- **merge-coordinator**: When parallel work completes
- **deployment-validator**: Before any commit/deploy

### Use Reactively (On-Demand)

These run when specific issues arise:

- **async-debugger**: Concurrency bugs, timing issues
- **error-pattern-analyzer**: Production issues, error spikes
- **ha-integration-validator**: HA-specific problems
- **holistic-reviewer**: Architecture decisions, major changes

## Integration with AI Orchestrator

These subagents are specifically designed for the AI Orchestrator project and understand:

- **Multi-agent architecture**: Orchestrator, specialist agents, MCP server
- **Async patterns**: asyncio, parallel execution, race conditions
- **Home Assistant**: Entity IDs, service calls, WebSocket protocol
- **LangGraph workflows**: State machines, task distribution
- **RAG integration**: Knowledge base queries, embeddings
- **FastAPI patterns**: Endpoints, async routes, error handling

## Best Practices

1. **Always validate before testing**: Run post-code-validator first
2. **Don't skip integration tests**: They catch what unit tests miss
3. **Coordinate parallel work**: Use parallel-coordinator to prevent conflicts
4. **Trust the merge coordinator**: It makes intelligent merge decisions
5. **Fix async issues immediately**: Race conditions are hard to debug later
6. **Monitor error patterns**: Catch systemic issues early
7. **Validate before deployment**: deployment-validator is your safety net

## Customization

These subagents can be customized by editing their `.md` files. Each file contains:

- **Frontmatter**: Name and description (triggers for AI)
- **System Prompt**: Instructions for the subagent's behavior
- **Processes**: Step-by-step workflows
- **Checks**: Specific validations to perform
- **Output Formats**: How to report results

## Examples

### Example 1: After Implementing New Feature

```
User: "I've added caching to the heating agent"
AI: [Automatically invokes post-code-validator]
→ Validates syntax, async patterns, imports
→ Reports: "Validation passed, but missing error handling on cache.get()"
→ [Invokes integration-tester]
→ Tests with orchestrator, MCP, HA client
→ Reports: "All integration tests pass"
→ [Invokes holistic-reviewer]
→ Reviews architecture impact, performance
→ Reports: "Good change, adds 15ms latency (acceptable)"
→ Ready for commit
```

### Example 2: Parallel Development

```
User: "Agent A optimize heating, Agent B add logging, parallel"
AI: [Invokes parallel-coordinator]
→ Analyzes tasks for conflicts
→ Detects: Both modify heating_agent.py
→ Plans: Agent A first, then Agent B
→ [Both agents work]
→ [Invokes merge-coordinator]
→ Merges changes intelligently
→ Validates merged code
→ Reports: "Merge successful, both features preserved"
```

### Example 3: Debugging Production Issue

```
User: "System has intermittent timeouts"
AI: [Invokes error-pattern-analyzer]
→ Analyzes logs, identifies pattern
→ Reports: "45 LLM timeouts during peak hours"
→ Root cause: Sequential API calls
→ [Invokes async-debugger]
→ Finds missing asyncio.gather
→ Provides fix
→ [Validates fix]
→ Reports: "Expected 80% error reduction"
```

## Contributing

When adding new subagents:

1. Follow the established format (frontmatter + system prompt)
2. Include clear trigger conditions in description
3. Provide specific, actionable output
4. Include examples and common patterns
5. Test with actual AI Orchestrator code

## Support

These subagents are part of the AI Orchestrator project tooling. For issues or improvements, consult the project knowledge base at `.cursor/skills/proj-knowledge/`.
