---
name: The-plan
description: Maintains a comprehensive, multi-tier to-do list for the HASS AI Orchestrator project. Planning and designer agents primarily add tasks, but any agent can add, update, or correct tasks. Use when planning work, tracking progress, coordinating with other agents, or when the user asks about project status, tasks, or what needs to be done.
---

# The Plan - Multi-Tier Task Management

## Purpose

This skill maintains a comprehensive, evolving task list for the HASS AI Orchestrator project. The plan serves as:

- **Central coordination point** for all agents
- **Multi-tier task hierarchy** (Epic → Feature → Task → Subtask)
- **Progress tracking** system
- **Dependency management** tool
- **Communication hub** between agents

## Plan Location

The plan is stored in `.cursor/.skills/The-plan/The-plan.md`. This file is the single source of truth for all project tasks.

## Task Hierarchy

Tasks are organized in a four-tier hierarchy:

```
Epic (Major Feature/Goal)
  └── Feature (Significant Functionality)
      └── Task (Specific Work Item)
          └── Subtask (Detailed Step)
```

### Epic
- Large-scale goals or major features
- Spans multiple features
- Example: "Voice Integration", "Mobile Companion App"

### Feature
- Significant functionality within an epic
- Composed of multiple tasks
- Example: "HA Assist Integration", "Responsive Dashboard"

### Task
- Specific work item that can be completed
- Has clear acceptance criteria
- Example: "Implement WebSocket handler for Assist", "Create mobile layout component"

### Subtask
- Detailed step within a task
- Small, actionable items
- Example: "Add event listener for voice commands", "Test on mobile device"

## Task Status

Each task can have one of these statuses:

- **pending**: Not yet started
- **in_progress**: Currently being worked on
- **blocked**: Cannot proceed (waiting on dependency)
- **review**: Completed, awaiting review
- **completed**: Finished and verified
- **cancelled**: No longer needed

## Task Structure

Each task entry follows this format:

```markdown
### [Task ID] [Status] [Priority] [Task Title]

**Epic**: [Epic Name]  
**Feature**: [Feature Name]  
**Assigned To**: [Agent/Person]  
**Dependencies**: [Task IDs that must complete first]  
**Blocks**: [Task IDs blocked by this task]  
**Created**: [Date]  
**Updated**: [Date]  
**Completed**: [Date if completed]

**Description**:  
[Clear description of what needs to be done]

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Notes**:
[Any relevant notes, discoveries, or context]

**Subtasks**:
- [ ] Subtask 1
- [ ] Subtask 2
```

## Task IDs

Task IDs follow this format:
- **Epic**: `E-001`, `E-002`, etc.
- **Feature**: `F-001`, `F-002`, etc.
- **Task**: `T-001`, `T-002`, etc.
- **Subtask**: `S-001`, `S-002`, etc.

Full task path: `E-001/F-003/T-012/S-005`

## Priority Levels

- **P0**: Critical - Blocks other work
- **P1**: High - Important for milestone
- **P2**: Medium - Should be done soon
- **P3**: Low - Nice to have

## Adding Tasks

### Planning/Designer Agents

Planning and designer agents should:

1. **Create epics** for major goals
2. **Break down into features** within epics
3. **Define tasks** for each feature
4. **Add subtasks** for complex tasks
5. **Set dependencies** between tasks
6. **Assign priorities** based on impact

### Any Agent

Any agent can:

1. **Add tasks** they discover are needed
2. **Add subtasks** to existing tasks
3. **Update task descriptions** with new information
4. **Correct errors** in task definitions
5. **Add notes** about discoveries or blockers
6. **Update dependencies** as understanding improves

## Updating Tasks

When updating a task:

1. **Update status** to reflect current state
2. **Update "Updated" date** to current date
3. **Add notes** explaining the change
4. **Check dependencies** - update if needed
5. **Update acceptance criteria** checkboxes
6. **Notify blocked tasks** if unblocked

## Marking Tasks Complete

Use the **task-completion skill** to mark tasks as complete. The process:

1. **Verify completion criteria** are met
2. **Run tests** to validate
3. **Update status** to "completed"
4. **Set completion date**
5. **Add completion notes**
6. **Check blocked tasks** - unblock if ready
7. **Update progress** in epic/feature summaries

## Dependency Management

### Setting Dependencies

When a task requires another task to complete first:

```markdown
**Dependencies**: T-045, T-052
```

### Checking Dependencies

Before starting a task:

1. **Check all dependencies** are completed
2. **If blocked**, set status to "blocked" and note why
3. **If ready**, set status to "in_progress"

### Updating Blocked Tasks

When a dependency completes:

1. **Find all tasks** that depend on it
2. **Check if ready** to proceed
3. **Update status** from "blocked" to "pending" or "in_progress"
4. **Notify assigned agent** if applicable

## Progress Tracking

### Task Level
- Track completion of acceptance criteria
- Update subtask checkboxes
- Note progress in notes section

### Feature Level
- Calculate completion percentage
- List completed tasks
- Show remaining tasks

### Epic Level
- Overall progress summary
- Feature completion status
- Timeline and milestones

## Coordination

### Before Starting Work

1. **Read The-plan.md** to understand current state
2. **Check assigned tasks** or find unassigned tasks
3. **Verify dependencies** are met
4. **Update status** to "in_progress"
5. **Add note** about starting work

### During Work

1. **Update notes** with discoveries
2. **Add subtasks** if task is more complex
3. **Update acceptance criteria** as understanding evolves
4. **Report blockers** immediately

### After Completing Work

1. **Use task-completion skill** to mark done
2. **Update related tasks** if dependencies resolved
3. **Share discoveries** that affect other tasks

## Best Practices

### Task Creation
- **Be specific**: Clear, actionable descriptions
- **Set criteria**: Define what "done" means
- **Link related**: Use dependencies and blocks
- **Assign priority**: Help prioritize work

### Task Updates
- **Update regularly**: Keep status current
- **Document changes**: Explain why status changed
- **Share context**: Notes help other agents
- **Be honest**: Mark blocked if truly blocked

### Coordination
- **Check before starting**: Avoid duplicate work
- **Communicate blockers**: Don't silently wait
- **Update dependencies**: Keep them accurate
- **Celebrate completion**: Mark done properly

## Integration with Other Skills

- **proj-knowledge skill**: Tasks reference knowledge base entries
- **task-completion skill**: Used to mark tasks complete
- **Commands**: `/sync-with-team`, `/check-dependencies`, `/report-progress` use this skill

## Maintenance

- **Review regularly**: Remove obsolete tasks
- **Consolidate duplicates**: Merge similar tasks
- **Update priorities**: Adjust as project evolves
- **Archive completed**: Move old completed tasks to archive section
- **Validate structure**: Ensure proper hierarchy
