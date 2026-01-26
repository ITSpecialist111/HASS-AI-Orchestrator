# The Plan - AI Orchestrator Development

*Last Updated: 2025-01-26*
*This is the central task management and coordination document for the agent team.*

## Current Sprint: Foundation Setup (2025-01-26)

### 🔥 Critical Priority

- [ ] **Setup project knowledge base structure**
  - Description: Create initial knowledge base with project overview
  - Files: `.cursor/skills/proj-knowledge/proj-knowledge.md`
  - Status: In progress
  - Assigned to: system

- [ ] **Create core skills (proj-knowledge, The-plan, task-marking)**
  - Description: Implement the three core skills for agent coordination
  - Files: `.cursor/skills/*/SKILL.md`
  - Status: In progress
  - Assigned to: system

### 🚀 High Priority

- [ ] **Create essential knowledge-building commands**
  - Description: Commands for exploring project structure and understanding codebase
  - Files: `.cursor/commands/explore-project-structure.md`, `analyze-codebase.md`, etc.
  - Dependencies: Core skills must be complete
  - Estimated effort: medium

- [ ] **Create coordination commands**
  - Description: Commands for agent coordination and collaboration
  - Files: `.cursor/commands/sync-with-plan.md`, `report-progress.md`, etc.
  - Dependencies: The-plan skill must be complete
  - Estimated effort: medium

- [ ] **Create testing commands**
  - Description: Commands for creating and running tests
  - Files: `.cursor/commands/create-test.md`, `analyze-test-coverage.md`
  - Estimated effort: small

### 📋 Medium Priority

- [ ] **Create troubleshooting commands**
  - Description: Commands for debugging and error tracing
  - Files: `.cursor/commands/trace-error.md`, `check-logs.md`, etc.
  - Estimated effort: medium

- [ ] **Create specialized skills**
  - Description: Additional skills for specific domains
  - Files: `.cursor/skills/agent-communication/`, `code-patterns/`, etc.
  - Estimated effort: large

### 🔍 Low Priority / Research

- [ ] **Research agent communication protocols**
  - Description: Explore best practices for multi-agent coordination
  - Status: Research phase
  - Estimated effort: small

## Active Work

### Agent: system
- [x] Currently working on: Creating core skills and knowledge base
- [ ] Next: Create essential commands

## Completed This Sprint

- [x] **Created comprehensive commands and skills plan** ✅ Completed 2025-01-26
  - Completed by: system
  - Files: `.cursor/COMMANDS_AND_SKILLS_PLAN.md`
  - Notes: Full plan document created with all proposed commands and skills

- [x] **Created proj-knowledge skill** ✅ Completed 2025-01-26
  - Completed by: system
  - Files: `.cursor/skills/proj-knowledge/SKILL.md`, `proj-knowledge.md`
  - Notes: Skill and initial knowledge base created

- [x] **Created The-plan skill** ✅ Completed 2025-01-26
  - Completed by: system
  - Files: `.cursor/skills/The-plan/SKILL.md`, `The-plan.md`
  - Notes: Skill and initial plan document created

- [x] **Created task-marking skill** ✅ Completed 2025-01-26
  - Completed by: system
  - Files: `.cursor/skills/task-marking/SKILL.md`
  - Notes: Standardized task completion skill created

## Backlog

### Features

- [ ] **Enhanced agent coordination**
  - Description: Improve inter-agent communication and task distribution
  - Priority: High
  - Estimated effort: large

- [ ] **Advanced testing framework**
  - Description: Expand test coverage and add performance benchmarks
  - Priority: Medium
  - Estimated effort: medium

- [ ] **Automated documentation generation**
  - Description: Auto-generate docs from code and agent findings
  - Priority: Low
  - Estimated effort: medium

### Bugs

*No bugs currently tracked*

### Technical Debt

- [ ] **Refactor orchestrator workflow**
  - Description: Simplify workflow graph and improve error handling
  - Priority: Medium
  - Estimated effort: medium

- [ ] **Improve test coverage**
  - Description: Increase coverage for agents and core components
  - Priority: High
  - Estimated effort: large

## Instructions & Guidelines

### How to Add New Agents

1. **Create agent class** in `ai-orchestrator/backend/agents/`:
   - Inherit from `BaseAgent`
   - Implement `gather_context()` and `decide()` methods
   - Add proper error handling and logging

2. **Create skills file** in `ai-orchestrator/skills/<agent-name>/SKILLS.md`:
   - Define agent purpose and role
   - List available tools and capabilities
   - Provide decision-making guidelines

3. **Update configuration**:
   - Add to `agents.yaml` or register via factory
   - Set reasonable decision interval
   - Configure relevant entity filters

4. **Write tests**:
   - Add test file in `ai-orchestrator/backend/tests/`
   - Include smoke tests for initialization
   - Test context gathering and decision making

5. **Update documentation**:
   - Add entry to README if significant
   - Document any new dependencies
   - Update proj-knowledge with new patterns

### How to Deploy

1. **Update version** in `ai-orchestrator/config.json`
2. **Run full test suite**: `pytest tests/ -v`
3. **Build Docker image**: `docker build -t ai-orchestrator .`
4. **Update repository**: Commit and push changes
5. **Test in Home Assistant**: Install and verify functionality

### How to Write Tests

1. **Follow naming convention**: `test_<component>_<type>.py`
2. **Use pytest markers**: `@pytest.mark.smoke`, `@pytest.mark.integration`
3. **For async tests**: Use `@pytest.mark.asyncio` and `pytest-asyncio`
4. **Mock external dependencies**: Use fixtures from `conftest.py`
5. **Test both success and failure cases**

### Code Style Guidelines

- **Python**: Follow PEP 8, use type hints
- **Async**: Use `asyncio` for all I/O operations
- **Error handling**: Log errors with context, use specific exceptions
- **Documentation**: Docstrings for all classes and public methods
- **Naming**: Clear, descriptive names following project conventions

### Commit Message Format

```
<type>: <subject>

<body>

Types: feat, fix, docs, test, refactor, chore
```

Example:
```
feat: add async context gathering to heating agent

Implement parallel state fetching using asyncio.gather for improved
performance. Includes error handling and logging.
```

## Coordination Notes

### Current Focus
- Setting up foundational skills and commands for agent coordination
- Building knowledge base of project architecture
- Establishing task management system

### Blockers
- None currently

### Dependencies
- Core skills must be complete before creating coordination commands
- Knowledge base should be populated before advanced features

### Next Steps
1. Complete core skills setup
2. Create essential knowledge-building commands
3. Create coordination commands
4. Begin populating knowledge base with detailed findings
