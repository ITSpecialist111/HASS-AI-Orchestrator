# Report Progress

## Purpose
Reports work progress to the team by updating task status, documenting completed work, noting blockers, sharing discoveries, and updating The-plan.md.

## Usage
`/report-progress [task-id] [--detailed] [--update-plan]`

Parameters:
- `task-id` (optional): Specific task to report on (default: current task)
- `--detailed`: Include detailed progress information
- `--update-plan`: Automatically update The-plan.md

## Instructions for Agent

When this command is invoked:

1. **Gather Progress Information**:
   - Identify current task(s)
   - Note work completed
   - Track acceptance criteria progress
   - Measure completion percentage

2. **Document Completed Work**:
   - List files modified
   - Note features implemented
   - Document tests added
   - Record issues resolved

3. **Note Blockers**:
   - Identify any blockers
   - Explain why blocked
   - Suggest resolution steps
   - Note waiting on dependencies

4. **Share Discoveries**:
   - Document important findings
   - Note patterns discovered
   - Share knowledge gained
   - Update knowledge base if significant

5. **Update The-plan.md** (if --update-plan):
   - Update task status
   - Add progress notes
   - Update acceptance criteria checkboxes
   - Update "Updated" date
   - Update progress percentages

6. **Generate Report**:
   - Create progress summary
   - Include detailed breakdown (if --detailed)
   - Note next steps
   - Highlight blockers

## Expected Outcome

- Progress report
- Completed work summary
- Blocker list
- Discoveries shared
- Updated The-plan.md (if flag set)

## Examples

### Report current progress
```
/report-progress
```

### Detailed report
```
/report-progress --detailed
```

### Report and update plan
```
/report-progress --update-plan
```

### Report specific task
```
/report-progress T-045 --detailed --update-plan
```

## Output Format

```markdown
# Progress Report

## Task: [Task ID] - [Task Name]

### Status
- **Current Status**: [status]
- **Progress**: [percentage]%
- **Last Updated**: [date]

### Completed Work
- ✅ [Work item 1]
- ✅ [Work item 2]
- 🔄 [Work item 3] (in progress)

### Acceptance Criteria
- [x] Criterion 1 ✅
- [x] Criterion 2 ✅
- [ ] Criterion 3 (in progress)

### Files Modified
- `path/to/file1.py` - [what changed]
- `path/to/file2.ts` - [what changed]

### Tests Added
- `tests/test_feature.py` - [coverage]

### Issues Resolved
- [Issue 1]: [resolution]
- [Issue 2]: [resolution]

## Blockers
- [Blocker 1]: [description] - [resolution needed]

## Discoveries
- [Discovery 1]: [details]
- [Discovery 2]: [details]

## Next Steps
1. [Next step 1]
2. [Next step 2]
```
