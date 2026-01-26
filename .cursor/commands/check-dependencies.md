# Check Dependencies

## Purpose
Verifies that task dependencies are met, validates component availability, tests integration points, and reports blocking issues.

## Usage
`/check-dependencies [task-id] [--resolve] [--report-blockers]`

Parameters:
- `task-id` (optional): Specific task to check (default: all your tasks)
- `--resolve`: Attempt to resolve dependency issues
- `--report-blockers`: Generate detailed blocker report

## Instructions for Agent

When this command is invoked:

1. **Read The-plan.md**:
   - Read task definitions
   - Identify dependencies
   - Note dependency chains
   - Check task statuses

2. **Check Prerequisite Tasks**:
   - Verify dependent tasks are completed
   - Check task status (must be "completed")
   - Validate completion criteria met
   - Note any incomplete dependencies

3. **Validate Component Availability**:
   - Check if required components exist
   - Verify component functionality
   - Test component interfaces
   - Note missing or broken components

4. **Test Integration Points**:
   - Verify API contracts
   - Test data flow
   - Check error handling
   - Validate security

5. **Report Blocking Issues** (if --report-blockers):
   - List all blockers
   - Explain why blocked
   - Suggest resolution steps
   - Prioritize blockers

6. **Attempt Resolution** (if --resolve):
   - Fix simple issues automatically
   - Update task statuses
   - Unblock tasks if possible
   - Report what was resolved

## Expected Outcome

- Dependency status report
- List of met/unmet dependencies
- Component availability status
- Integration test results
- Blocker report (if flag set)
- Resolution actions (if --resolve)

## Examples

### Check all dependencies
```
/check-dependencies
```

### Check specific task
```
/check-dependencies T-045
```

### Check with blocker report
```
/check-dependencies --report-blockers
```

### Check and resolve
```
/check-dependencies --resolve
```

## Output Format

```markdown
# Dependency Check Report

## Task: [Task ID]

### Prerequisite Tasks
- ✅ T-XXX: [Task Name] - COMPLETED
- ❌ T-YYY: [Task Name] - IN_PROGRESS (blocks this task)
- ⏳ T-ZZZ: [Task Name] - PENDING

### Component Dependencies
- ✅ [Component 1]: Available and functional
- ❌ [Component 2]: Missing or broken
- ⚠️ [Component 3]: Available but needs update

### Integration Points
- ✅ [Integration 1]: Working
- ❌ [Integration 2]: Failing
- ⚠️ [Integration 3]: Needs testing

## Blockers

### Critical Blockers
1. [Blocker 1]: [description] - [resolution steps]

### Minor Blockers
1. [Blocker 1]: [description]

## Resolution Actions (if --resolve)
- [Action 1]: [what was done]
- [Action 2]: [what was done]
```
