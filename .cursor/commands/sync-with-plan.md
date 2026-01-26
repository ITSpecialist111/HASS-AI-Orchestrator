# Sync with The Plan

## Purpose
Reads The Plan, updates progress, checks for new tasks, and ensures coordination with other agents.

## Usage
`/sync-with-plan [action]`

Actions:
- `read` - Read current plan (default)
- `update` - Update your active work
- `check` - Check for conflicts or blockers
- `report` - Report completion of current task

## Instructions for Agent

When this command is invoked:

1. **Read The Plan**:
   ```bash
   Read: .cursor/skills/The-plan/The-plan.md
   ```

2. **Based on Action**:

   **For "read" (default)**:
   - Review current sprint priorities
   - Check active work section
   - Identify available tasks
   - Note any blockers or dependencies
   - Report findings to user

   **For "update"**:
   - Read current plan
   - Find your active work section (or create if needed)
   - Update with current task:
     ```markdown
     ### Agent: [your-identifier]
     - [ ] Currently working on: [task name]
     - [ ] Progress: [description]
     - [ ] Blocked by: [if applicable]
     ```
   - Save changes

   **For "check"**:
   - Read current plan
   - Check active work for conflicts
   - Verify dependencies are met
   - Check if your task is blocked
   - Report any issues found

   **For "report"**:
   - Read current plan
   - Find your active work
   - Use task-marking skill to mark complete
   - Move to completed section
   - Update any dependent tasks
   - Clear active work entry

3. **Coordination Checks**:
   - Verify no other agent is working on same task
   - Check if dependencies are complete
   - Note if you're blocking others
   - Identify if you need assistance

4. **Update Knowledge**:
   - If you discover new patterns, update proj-knowledge
   - Document important findings
   - Note architectural insights

## Expected Outcome

- Current plan status understood
- Active work updated (if action=update)
- Conflicts identified (if action=check)
- Task marked complete (if action=report)
- Coordination maintained with team

## Best Practices

### Before Starting Work
1. Run `/sync-with-plan read`
2. Check priorities
3. Verify task isn't assigned
4. Update active work with `/sync-with-plan update`

### While Working
1. Periodically check for new priorities
2. Update progress if task is long-running
3. Note blockers immediately

### After Completing Work
1. Run `/sync-with-plan report`
2. Mark task complete
3. Update knowledge base if needed
4. Check for unblocked tasks

## Common Scenarios

### Finding Next Task
1. Read plan
2. Check critical/high priority sections
3. Find unassigned tasks
4. Verify dependencies met
5. Update active work

### Reporting Blocker
1. Read plan
2. Update active work with blocker
3. Create blocker resolution task if needed
4. Notify if blocking others

### Completing Task
1. Read plan
2. Use task-marking skill
3. Move to completed section
4. Update dependent tasks
5. Clear active work

## Integration

This command works with:
- **The-plan skill**: Reads and updates plan
- **task-marking skill**: Marks tasks complete
- **proj-knowledge skill**: Updates knowledge base
- **report-progress command**: Detailed progress reporting
