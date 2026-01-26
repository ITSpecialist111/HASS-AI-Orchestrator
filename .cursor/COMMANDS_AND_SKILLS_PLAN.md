# Commands and Skills Development Plan

## Overview
This document outlines the comprehensive set of commands and skills designed to help AI agents collaborate effectively on the HASS AI Orchestrator project. These tools enable knowledge sharing, coordination, testing, and troubleshooting across the development team.

---

## Skills (`.cursor/.skills/`)

### 1. Project Knowledge Base (`proj-knowledge/`)
**Purpose**: Build and maintain an evolving knowledge base of the project structure, components, functions, and architecture.

**Key Features**:
- Document project components as they're discovered
- Track relationships between modules
- Maintain architecture diagrams and explanations
- Store important patterns and conventions
- Version knowledge as project evolves

### 2. The Plan (`The-plan/`)
**Purpose**: Maintain a comprehensive, multi-tier to-do list that all agents can contribute to and track.

**Key Features**:
- Hierarchical task structure (Epic → Feature → Task → Subtask)
- Status tracking (pending, in_progress, blocked, completed)
- Priority levels
- Dependencies between tasks
- Agent assignments
- Progress tracking
- Planning agents can add/update tasks
- All agents can mark tasks complete

### 3. Task Completion (`task-completion/`)
**Purpose**: Standardized workflow for marking tasks as complete in The-plan.md

**Key Features**:
- Validate task completion criteria
- Update task status
- Add completion notes
- Update dependencies
- Notify related tasks

---

## Commands (`.cursor/commands/`)

### Knowledge Building Commands

#### `explore-project.md`
**Purpose**: Systematically explore and document project structure
- Scan directory structure
- Identify key components
- Document file purposes
- Map dependencies
- Update proj-knowledge skill

#### `document-component.md`
**Purpose**: Create detailed documentation for a specific component
- Analyze component code
- Document API/interface
- Explain functionality
- Note dependencies
- Add examples
- Update knowledge base

#### `update-knowledge.md`
**Purpose**: Update the project knowledge base with new information
- Add new entries
- Update existing entries
- Maintain consistency
- Cross-reference related components

#### `understand-workflow.md`
**Purpose**: Trace and document execution workflows
- Follow code execution paths
- Document decision points
- Map data flow
- Identify integration points

### Coordination Commands

#### `sync-with-team.md`
**Purpose**: Synchronize work with other agents
- Read The-plan.md for current tasks
- Check for conflicts
- Identify dependencies
- Report current work status
- Update progress

#### `check-dependencies.md`
**Purpose**: Verify task dependencies are met
- Check prerequisite tasks
- Validate component availability
- Test integration points
- Report blocking issues

#### `report-progress.md`
**Purpose**: Report work progress to the team
- Update task status
- Document completed work
- Note blockers
- Share discoveries
- Update The-plan.md

#### `coordinate-changes.md`
**Purpose**: Coordinate code changes with other agents
- Check for merge conflicts
- Identify affected components
- Test integration
- Update documentation

### Testing Commands

#### `test-component.md`
**Purpose**: Create and run tests for a component
- Identify test cases
- Write unit tests
- Run test suite
- Report coverage
- Fix failing tests

#### `validate-integration.md`
**Purpose**: Validate component integration
- Test API contracts
- Verify data flow
- Check error handling
- Validate security
- Test edge cases

#### `check-code-quality.md`
**Purpose**: Assess code quality and standards
- Run linters
- Check formatting
- Review complexity
- Verify documentation
- Check security issues

#### `run-test-suite.md`
**Purpose**: Execute full test suite with reporting
- Run all tests
- Generate coverage report
- Identify flaky tests
- Report results
- Track test trends

### Troubleshooting Commands

#### `diagnose-error.md`
**Purpose**: Diagnose and fix errors
- Analyze error logs
- Trace execution path
- Identify root cause
- Propose fixes
- Test solutions

#### `trace-execution.md`
**Purpose**: Trace code execution for debugging
- Follow execution path
- Log function calls
- Track variable states
- Identify bottlenecks
- Document findings

#### `find-conflicts.md`
**Purpose**: Find and resolve conflicts
- Check for merge conflicts
- Identify logical conflicts
- Find dependency conflicts
- Resolve issues
- Update documentation

#### `analyze-performance.md`
**Purpose**: Analyze and optimize performance
- Profile code execution
- Identify bottlenecks
- Measure resource usage
- Propose optimizations
- Validate improvements

### Communication Commands

#### `share-discovery.md`
**Purpose**: Share important discoveries with team
- Document finding
- Update knowledge base
- Notify relevant agents
- Update The-plan if needed

#### `request-help.md`
**Purpose**: Request assistance from other agents
- Document the problem
- Specify what's needed
- Update task status
- Wait for response

#### `review-code.md`
**Purpose**: Review code changes
- Analyze changes
- Check quality
- Verify tests
- Suggest improvements
- Approve or request changes

---

## Implementation Priority

### Phase 1: Core Skills (Immediate)
1. ✅ proj-knowledge skill
2. ✅ The-plan skill
3. ✅ task-completion skill

### Phase 2: Essential Commands (High Priority)
1. explore-project
2. sync-with-team
3. document-component
4. test-component
5. diagnose-error

### Phase 3: Coordination Commands (Medium Priority)
1. check-dependencies
2. report-progress
3. coordinate-changes
4. validate-integration

### Phase 4: Advanced Commands (Lower Priority)
1. understand-workflow
2. trace-execution
3. analyze-performance
4. review-code

---

## Usage Patterns

### Daily Workflow
1. Start: `/sync-with-team` - Check current tasks
2. Work: Use relevant commands as needed
3. Progress: `/report-progress` - Update status
4. Complete: Use task-completion skill to mark done

### Knowledge Building
1. `/explore-project` - Discover new areas
2. `/document-component` - Document findings
3. `/update-knowledge` - Add to knowledge base

### Troubleshooting
1. `/diagnose-error` - Identify issue
2. `/trace-execution` - Understand flow
3. `/test-component` - Verify fix

### Testing
1. `/test-component` - Create tests
2. `/validate-integration` - Check integration
3. `/run-test-suite` - Full validation

---

## File Structure

```
.cursor/
├── .commands/
│   ├── explore-project.md
│   ├── document-component.md
│   ├── update-knowledge.md
│   ├── understand-workflow.md
│   ├── sync-with-team.md
│   ├── check-dependencies.md
│   ├── report-progress.md
│   ├── coordinate-changes.md
│   ├── test-component.md
│   ├── validate-integration.md
│   ├── check-code-quality.md
│   ├── run-test-suite.md
│   ├── diagnose-error.md
│   ├── trace-execution.md
│   ├── find-conflicts.md
│   ├── analyze-performance.md
│   ├── share-discovery.md
│   ├── request-help.md
│   └── review-code.md
└── .skills/
    ├── proj-knowledge/
    │   └── SKILL.md
    ├── The-plan/
    │   └── SKILL.md
    └── task-completion/
        └── SKILL.md
```

---

## Success Metrics

- Knowledge base grows with project
- Tasks are tracked and completed systematically
- Agents coordinate without conflicts
- Code quality improves over time
- Errors are diagnosed and fixed quickly
- Test coverage increases
- Development velocity improves
