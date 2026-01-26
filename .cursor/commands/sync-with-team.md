# Sync With Team

## Purpose
Synchronizes work with other agents by reading The-plan.md, checking for conflicts, identifying dependencies, reporting current work status, and updating progress.

## Usage
`/sync-with-team [--check-conflicts] [--update-status]`

Parameters:
- `--check-conflicts`: Check for potential conflicts with other agents' work
- `--update-status`: Update current task status in The-plan.md

## Instructions for Agent

When this command is invoked:

1. **Read The-plan.md**:
   - Read `.cursor/skills/The-plan/The-plan.md`
   - Understand current project state
   - Identify active tasks
   - Note task assignments

2. **Check Current Tasks**:
   - Find tasks assigned to you
   - Identify unassigned tasks you can take
   - Check task priorities
   - Note deadlines or milestones

3. **Check Dependencies**:
   - Verify your task dependencies are met
   - Identify blocked tasks
   - Check if you're blocking others
   - Note dependency chains

4. **Check for Conflicts** (if --check-conflicts):
   - Identify overlapping work areas
   - Check for file conflicts
   - Note potential merge conflicts
   - Identify shared dependencies

5. **Report Current Status**:
   - Document what you're working on
   - Note progress made
   - Report any blockers
   - Share discoveries

6. **Update Status** (if --update-status):
   - Update task status in The-plan.md
   - Add progress notes
   - Update "Updated" date
   - Mark blockers if needed

## Expected Outcome

- Summary of current project state
- List of your assigned tasks
- Dependency status
- Conflict report (if flag set)
- Updated task status (if flag set)

## Examples

### Basic sync
```
/sync-with-team
```

### Sync with conflict check
```
/sync-with-team --check-conflicts
```

### Sync and update status
```
/sync-with-team --update-status
```

## Output Format

```markdown
# Team Sync Report

## Current Project State
- **Active Tasks**: [count]
- **In Progress**: [count]
- **Blocked**: [count]
- **Completed Today**: [count]

## Your Tasks

### Assigned to You
- [Task ID]: [Task Name] - [Status]
- [Task ID]: [Task Name] - [Status]

### Available Tasks
- [Task ID]: [Task Name] - [Priority]
- [Task ID]: [Task Name] - [Priority]

## Dependencies

### Your Dependencies
- [Task ID]: [Status] - [Blocks your task]
- [Task ID]: [Status] - [Blocks your task]

### Tasks You Block
- [Task ID]: [Status] - [Blocked by your task]

## Conflicts (if checked)
- [Conflict 1]: [description]
- [Conflict 2]: [description]

## Current Work
- **Working on**: [Task ID]
- **Progress**: [percentage]
- **Blockers**: [list]
- **Discoveries**: [list]
```
