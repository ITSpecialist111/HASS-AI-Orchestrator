---
name: task-completion
description: Standardized workflow for marking tasks as complete in The-plan.md. Validates completion criteria, updates task status, manages dependencies, and notifies related tasks. Use when a task is finished, when verifying work completion, or when the user asks to mark a task as done.
---

# Task Completion

## Purpose

This skill provides a standardized workflow for marking tasks as complete in The-plan.md. It ensures:

- Completion criteria are verified
- Task status is properly updated
- Dependencies are managed
- Related tasks are notified
- Progress is accurately tracked

## When to Use

Use this skill when:

1. **Task is finished**: All acceptance criteria met
2. **Work is verified**: Tests pass, code reviewed
3. **Ready to mark done**: No outstanding issues
4. **User requests**: User asks to mark task complete

## Completion Workflow

### Step 1: Verify Completion Criteria

Before marking a task complete, verify:

1. **All acceptance criteria checked**: Every checkbox in acceptance criteria is marked
2. **Tests pass**: Related tests are written and passing
3. **Code quality**: Code follows project standards
4. **Documentation updated**: Relevant docs updated if needed
5. **Integration verified**: Works with other components

### Step 2: Update Task Status

Update the task in The-plan.md:

1. **Change status** from current status to `completed`
2. **Set completion date** to current date
3. **Update "Updated" date** to current date
4. **Check all acceptance criteria** checkboxes
5. **Check all subtasks** if applicable

### Step 3: Add Completion Notes

Add a completion note documenting:

- **What was completed**: Brief summary
- **Key changes**: Important modifications made
- **Files modified**: List of files changed
- **Tests added**: New tests created
- **Issues resolved**: Problems fixed
- **Next steps**: Related work or follow-ups

### Step 4: Check Dependencies

Review tasks that depend on this task:

1. **Find dependent tasks**: Search for this task ID in "Dependencies" fields
2. **Check if ready**: Verify dependencies are now met
3. **Update status**: Change from "blocked" to "pending" or "in_progress"
4. **Add note**: Explain why unblocked

### Step 5: Update Progress

Update progress in parent feature/epic:

1. **Feature level**: Update task count and completion percentage
2. **Epic level**: Update feature status if all features complete
3. **Overall progress**: Update progress overview section

## Task Update Format

When marking a task complete, update it like this:

```markdown
### T-XXX: [Task Title] ✅ COMPLETED
- **Status**: completed
- **Priority**: [Original Priority]
- **Assigned To**: [Agent/Person]
- **Dependencies**: [Original Dependencies]
- **Blocks**: [Tasks This Blocks]
- **Created**: [Original Date]
- **Updated**: 2026-01-26
- **Completed**: 2026-01-26

**Description**:  
[Original description]

**Acceptance Criteria**:
- [x] Criterion 1 ✅
- [x] Criterion 2 ✅
- [x] Criterion 3 ✅

**Notes**:
[Original notes]

**Completion Notes** (2026-01-26):
- Completed [summary]
- Modified files: `path/to/file1.py`, `path/to/file2.ts`
- Added tests: `tests/test_component.py`
- Resolved issues: [issue descriptions]
- Next steps: [related tasks or follow-ups]

**Subtasks**:
- [x] Subtask 1 ✅
- [x] Subtask 2 ✅
```

## Validation Checklist

Before marking complete, verify:

- [ ] All acceptance criteria met
- [ ] All subtasks completed
- [ ] Code follows project standards
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Integration tested
- [ ] No known bugs introduced

## Handling Partial Completion

If a task is mostly done but has minor issues:

1. **Add note** explaining what's remaining
2. **Create subtask** for remaining work
3. **Keep status** as "in_progress" or "review"
4. **Don't mark complete** until all criteria met

## Handling Blocked Tasks

If a task is blocked by this completion:

1. **Find the task** in The-plan.md
2. **Update status** from "blocked" to "pending"
3. **Add note** explaining unblocked
4. **Check dependencies** - verify all are now met
5. **Notify assigned agent** if applicable

## Integration with The-plan Skill

This skill works with The-plan skill:

- **Reads** The-plan.md to find tasks
- **Updates** task status and progress
- **Manages** dependencies and blocks
- **Tracks** completion dates

## Integration with Other Skills

- **proj-knowledge skill**: Update knowledge base when completing documentation tasks
- **Commands**: `/report-progress` uses this skill
- **Testing**: Run tests before marking complete

## Examples

### Example 1: Simple Task Completion

**Task**: T-045 - Gemini integration

**Before**:
```markdown
### T-045: Gemini Integration 🔄
- **Status**: in_progress
```

**After**:
```markdown
### T-045: Gemini Integration ✅ COMPLETED
- **Status**: completed
- **Completed**: 2026-01-25

**Completion Notes** (2026-01-25):
- Integrated Google Gemini API for dashboard generation
- Modified: `backend/providers/gemini_provider.py`, `backend/orchestrator.py`
- Added tests: `tests/test_gemini_integration.py`
- All tests passing, dashboard generation working
```

### Example 2: Task with Dependencies

**Task**: T-050 - Voice command parsing (depends on T-049)

When T-049 completes:
1. Mark T-049 as completed
2. Find T-050 (depends on T-049)
3. Update T-050 status from "blocked" to "pending"
4. Add note: "Unblocked by completion of T-049"

## Best Practices

1. **Verify thoroughly**: Don't mark complete until truly done
2. **Document well**: Completion notes help future reference
3. **Update dependencies**: Always check and update dependent tasks
4. **Be honest**: If not fully complete, don't mark as complete
5. **Celebrate**: Marking complete helps track progress accurately

## Error Handling

If unable to mark complete:

1. **Document why**: Add note explaining blocker
2. **Update status**: Change to "blocked" or keep "in_progress"
3. **Create subtask**: Break down remaining work
4. **Request help**: Use `/request-help` if stuck
