---
name: task-marking
description: Marks tasks as complete in The-plan.md. All agents use this skill to update task status, record completion dates, and move tasks to completed sections. Use when finishing a task, updating progress, or tracking work completion.
---

# Task Marking

This skill provides a standardized way for all agents to mark tasks as complete in The Plan, ensuring consistent formatting and proper tracking.

## Purpose

The task-marking skill ensures:
- **Consistent formatting**: All completions follow the same format
- **Progress tracking**: Completed work is properly recorded
- **Coordination**: Other agents know what's been finished
- **History**: Completion dates and details are preserved

## When to Use

Use this skill when:
- You've completed a task
- A subtask within a larger feature is done
- You need to update task status
- Moving tasks between sections

## How to Mark a Task Complete

### Step 1: Read The Plan

First, read the current plan to see the task format:

```bash
Read: .cursor/skills/The-plan/The-plan.md
```

### Step 2: Find the Task

Locate the task you've completed. It should be in format:
```markdown
- [ ] **Task Title**
  - Description: ...
  - Files: ...
```

### Step 3: Mark Complete

Change the checkbox and add completion details:

```markdown
- [x] **Task Title** ✅ Completed [YYYY-MM-DD]
  - Description: ...
  - Files: ...
  - Completed by: [Your agent identifier/name]
  - Notes: [Any relevant notes about completion]
```

### Step 4: Move to Completed Section

If there's a "Completed This Sprint" section, move the task there:

```markdown
## Completed This Sprint

- [x] **Task Title** ✅ Completed [YYYY-MM-DD]
  - Completed by: [Agent name]
  - Notes: [Completion notes]
```

### Step 5: Update Active Work

If the task was in "Active Work", remove it:

```markdown
## Active Work

### Agent: [Agent Name]
- [x] ~~Currently working on: Task X~~ ✅ Completed
```

## Task Completion Formats

### Simple Task
```markdown
- [x] **Task Title** ✅ Completed 2025-01-26
```

### Task with Details
```markdown
- [x] **Task Title** ✅ Completed 2025-01-26
  - Completed by: agent-name
  - Files modified: `path/to/file.py`
  - Notes: Fixed issue with async handling
```

### Feature Task
```markdown
- [x] **Feature: Feature Name** ✅ Completed 2025-01-26
  - Completed by: agent-name
  - Subtasks completed: 3/3
  - Files: `path/to/file1.py`, `path/to/file2.py`
  - Notes: All acceptance criteria met
```

### Partial Completion
For large tasks with subtasks:

```markdown
- [ ] **Feature: Feature Name** (2/5 subtasks complete)
  - [x] Subtask 1 ✅ Completed 2025-01-26
  - [x] Subtask 2 ✅ Completed 2025-01-26
  - [ ] Subtask 3
  - [ ] Subtask 4
  - [ ] Subtask 5
```

## Completion Notes

When marking complete, include helpful information:

### What Was Done
```markdown
- Notes: Implemented async context gathering for heating agent
```

### Files Changed
```markdown
- Files: `agents/heating_agent.py`, `tests/test_heating_agent.py`
```

### Testing Status
```markdown
- Notes: Implementation complete, tests passing, ready for review
```

### Dependencies Resolved
```markdown
- Notes: Completed, unblocks Task X and Task Y
```

### Issues Encountered
```markdown
- Notes: Completed, but note: async race condition in edge case (see issue #123)
```

## Moving Tasks

### From Active to Completed

1. Mark task complete in original location
2. Copy to "Completed This Sprint" section
3. Remove from "Active Work" section
4. Update any related task dependencies

### From Backlog to Completed

If a backlog item was completed directly:

1. Mark complete in backlog
2. Add to "Completed This Sprint"
3. Note if it was ahead of schedule

## Updating Related Tasks

When completing a task, check for:

### Dependent Tasks
If Task B depends on Task A:
```markdown
- [ ] **Task B**
  - Dependencies: ~~Task A~~ ✅ (completed 2025-01-26)
```

### Blocked Tasks
If your completion unblocks others:
```markdown
- [ ] **Task C** (was blocked, now unblocked)
  - Blocked by: ~~Task A~~ ✅ (completed 2025-01-26)
```

### Related Features
Note if completion affects other features:
```markdown
- Notes: Completed. Enables Feature X and Feature Y.
```

## Best Practices

1. **Be specific**: Include completion date and your identifier
2. **Add notes**: Help others understand what was done
3. **Update dependencies**: Mark related tasks as unblocked
4. **Move appropriately**: Place in completed section
5. **Clean up**: Remove from active work sections
6. **Test status**: Note if tests pass/fail
7. **Documentation**: Note if docs were updated

## Common Patterns

### Quick Completion
For simple, straightforward tasks:
```markdown
- [x] **Task** ✅ Completed [date]
```

### Detailed Completion
For complex tasks:
```markdown
- [x] **Task** ✅ Completed [date]
  - Completed by: agent-name
  - Files: `file1.py`, `file2.py`
  - Tests: All passing
  - Notes: Implementation complete, ready for review
```

### Partial with Progress
For large tasks:
```markdown
- [ ] **Task** (Progress: 60%)
  - [x] Phase 1 ✅
  - [x] Phase 2 ✅
  - [ ] Phase 3 (in progress)
  - [ ] Phase 4
```

## Error Prevention

### Before Marking Complete

1. ✅ Verify task is actually done
2. ✅ Check all subtasks if applicable
3. ✅ Ensure tests pass
4. ✅ Verify no breaking changes
5. ✅ Check dependencies are met

### Common Mistakes to Avoid

- ❌ Marking complete before work is done
- ❌ Forgetting to update dependent tasks
- ❌ Not moving from active work section
- ❌ Missing completion date
- ❌ Not noting important details

## Integration with Other Skills

### With The-plan Skill
- Read The Plan before marking complete
- Update appropriate sections
- Maintain task relationships

### With proj-knowledge Skill
- If you discovered new patterns, update proj-knowledge
- Document architectural insights
- Note important findings

### With report-progress Command
- Use report-progress to document details
- Mark complete after reporting
- Keep both in sync

## Example Workflow

1. Agent completes implementation
2. Runs tests (all pass)
3. Reads The Plan to find task
4. Marks task complete with details:
   ```markdown
   - [x] **Implement async context gathering** ✅ Completed 2025-01-26
     - Completed by: dev-agent
     - Files: `agents/heating_agent.py`
     - Tests: All passing
     - Notes: Uses asyncio.gather for parallel state fetching
   ```
5. Moves to "Completed This Sprint"
6. Updates dependent task: "Task X (unblocked)"
7. Updates proj-knowledge with new pattern discovered

## Troubleshooting

### Task Not Found
- Check spelling and exact title
- Look in different sections (backlog, active, etc.)
- May have been renamed or moved

### Format Issues
- Follow the exact format shown above
- Use `[x]` for completed checkboxes
- Include date in YYYY-MM-DD format

### Conflicts
- If another agent is working on same task, coordinate
- Check "Active Work" section first
- Resolve conflicts before marking complete
