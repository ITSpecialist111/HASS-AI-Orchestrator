---
name: The-plan
description: Maintains an evolving, comprehensive multi-tier to-do list and instructions for the agent team. Planning and designer agents primarily add tasks, but any agent can add, correct, or update tasks. Use when starting work, checking priorities, coordinating with other agents, or planning new features.
---

# The Plan - Agent Team Task Management

This skill manages a comprehensive, evolving task list and instructions for the AI Orchestrator development team. It serves as the central coordination point for all agents working on the project.

## Purpose

The Plan provides:
- **Task tracking**: Multi-tier to-do lists organized by priority and category
- **Coordination**: Agents know what others are working on
- **Planning**: Long-term roadmap and short-term sprints
- **Instructions**: Step-by-step guidance for complex tasks
- **Progress tracking**: Status of all work items

## File Location

The plan is maintained at: `.cursor/skills/The-plan/The-plan.md`

## Structure

The plan should be organized hierarchically:

```markdown
# The Plan - AI Orchestrator Development

## Current Sprint: [Sprint Name/Date]

### 🔥 Critical Priority
- [ ] Task 1
- [ ] Task 2

### 🚀 High Priority
- [ ] Task 3
- [ ] Task 4

### 📋 Medium Priority
- [ ] Task 5

### 🔍 Low Priority / Research
- [ ] Task 6

## Active Work

### Agent: [Agent Name]
- [ ] Currently working on: Task X
- [ ] Blocked by: [reason]

## Completed This Sprint
- [x] Task completed on [date] by [agent]

## Backlog

### Features
- [ ] Feature 1
- [ ] Feature 2

### Bugs
- [ ] Bug 1
- [ ] Bug 2

### Technical Debt
- [ ] Refactor X
- [ ] Improve Y

## Instructions & Guidelines

### How to Add New Agents
1. Create agent class
2. Add skills file
3. Update config
4. Write tests

### How to Deploy
1. Update version
2. Run tests
3. Build Docker image
4. Update repository
```

## How to Use This Skill

### Reading The Plan

Before starting work:

1. **Read the current plan**:
   ```bash
   Read: .cursor/skills/The-plan/The-plan.md
   ```

2. **Check priorities**: Look at Critical and High priority tasks first

3. **Check active work**: See what others are doing to avoid conflicts

4. **Find your task**: Identify what you should work on

### Adding Tasks

**Planning/Designer Agents** (primary responsibility):
- Add new features to backlog
- Break down features into tasks
- Set priorities
- Create detailed instructions

**Any Agent** can:
- Add bug reports
- Suggest improvements
- Add technical debt items
- Correct or clarify existing tasks

### Updating Tasks

When updating tasks:

1. **Be specific**: Include file paths, function names, requirements
2. **Add context**: Why is this needed? What depends on it?
3. **Set dependencies**: Note if task blocks others
4. **Add instructions**: Step-by-step guidance if complex

### Marking Tasks Complete

Use the **task-marking** skill to mark tasks as done. This ensures:
- Consistent formatting
- Progress tracking
- Completion dates recorded
- Related tasks updated

## Task Format

### Standard Task
```markdown
- [ ] **Task Title**
  - Description: What needs to be done
  - Files: `path/to/file.py`
  - Dependencies: Task X must be done first
  - Estimated effort: [small/medium/large]
  - Assigned to: [agent name or "unassigned"]
```

### Feature Task
```markdown
- [ ] **Feature: [Feature Name]**
  - Description: High-level feature description
  - Acceptance criteria:
    - [ ] Criterion 1
    - [ ] Criterion 2
  - Subtasks:
    - [ ] Subtask 1
    - [ ] Subtask 2
  - Related: Links to related tasks
```

### Bug Task
```markdown
- [ ] **Bug: [Short Description]**
  - Description: What's broken
  - Steps to reproduce:
    1. Step 1
    2. Step 2
  - Expected: What should happen
  - Actual: What actually happens
  - Files: `path/to/file.py` (line X)
  - Priority: [critical/high/medium/low]
```

## Priority Levels

### 🔥 Critical Priority
- Blocks other work
- Security issues
- Production bugs
- Must be done immediately

### 🚀 High Priority
- Important features
- Significant bugs
- Performance issues
- Should be done soon

### 📋 Medium Priority
- Nice-to-have features
- Minor bugs
- Improvements
- Can wait for next sprint

### 🔍 Low Priority / Research
- Exploratory work
- Future considerations
- Nice-to-haves
- No immediate need

## Coordination Guidelines

### Before Starting Work

1. Read The Plan
2. Check if task is already assigned
3. Update "Active Work" section with your name
4. Note any blockers or dependencies

### While Working

1. Update progress in "Active Work"
2. Add findings or questions as comments
3. Note if you discover related tasks needed

### After Completing Work

1. Mark task complete using task-marking skill
2. Move to "Completed This Sprint"
3. Update "Active Work" to remove your entry
4. Note any follow-up tasks needed

### When Blocked

1. Mark task with "Blocked by: [reason]"
2. Add to "Active Work" with blocker noted
3. Create blocker resolution task if needed
4. Notify relevant agents if coordination needed

## Instructions Section

The plan should include detailed instructions for:

### Common Tasks
- How to add new agents
- How to write tests
- How to update documentation
- How to deploy changes

### Complex Workflows
- Multi-step processes
- Integration procedures
- Deployment procedures
- Testing procedures

### Conventions
- Code style guidelines
- Naming conventions
- Commit message format
- Documentation standards

## Maintenance

### Daily Updates
- Planning agents review and update priorities
- Agents update their active work
- Completed tasks moved to completed section

### Weekly Reviews
- Review completed work
- Adjust priorities
- Plan next sprint
- Archive old completed tasks

### Monthly Reviews
- Review backlog
- Reassess priorities
- Update roadmap
- Clean up outdated tasks

## Best Practices

1. **Be specific**: Vague tasks are hard to complete
2. **Break down**: Large tasks into smaller subtasks
3. **Set dependencies**: Note what must happen first
4. **Update regularly**: Keep status current
5. **Communicate**: Note blockers and questions
6. **Document**: Add instructions for complex tasks
7. **Prioritize**: Keep critical items visible

## Related Skills

- **task-marking**: Mark tasks as complete
- **proj-knowledge**: Understand project context
- **agent-communication**: Coordinate with other agents

## Example Workflow

1. Agent reads The Plan
2. Finds unassigned high-priority task
3. Updates "Active Work" section
4. Works on task
5. Uses task-marking skill to mark complete
6. Updates proj-knowledge if new patterns discovered
7. Reports progress to team
