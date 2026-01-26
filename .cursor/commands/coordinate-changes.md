# Coordinate Changes

## Purpose
Coordinates code changes with other agents by checking for merge conflicts, identifying affected components, testing integration, and updating documentation.

## Usage
`/coordinate-changes [--check-conflicts] [--test-integration] [--update-docs]`

Parameters:
- `--check-conflicts`: Check for merge conflicts
- `--test-integration`: Test integration with other components
- `--update-docs`: Update documentation for changes

## Instructions for Agent

When this command is invoked:

1. **Check for Merge Conflicts**:
   - Check git status
   - Identify modified files
   - Check for potential conflicts
   - Note overlapping changes

2. **Identify Affected Components**:
   - Map changed files to components
   - Identify dependent components
   - Note integration points
   - List affected tests

3. **Check Other Agents' Work**:
   - Read The-plan.md for active tasks
   - Identify overlapping work areas
   - Check for shared dependencies
   - Note potential conflicts

4. **Test Integration** (if --test-integration):
   - Run integration tests
   - Test affected components
   - Verify API contracts
   - Check data flow

5. **Update Documentation** (if --update-docs):
   - Update component docs
   - Update knowledge base
   - Note breaking changes
   - Update API docs if needed

6. **Coordinate with Team**:
   - Report changes made
   - Note affected areas
   - Suggest coordination steps
   - Update The-plan.md if needed

## Expected Outcome

- Conflict analysis report
- Affected components list
- Integration test results
- Documentation updates (if flag set)
- Coordination recommendations

## Examples

### Check for conflicts
```
/coordinate-changes --check-conflicts
```

### Full coordination check
```
/coordinate-changes --check-conflicts --test-integration --update-docs
```

### Test integration only
```
/coordinate-changes --test-integration
```

## Output Format

```markdown
# Change Coordination Report

## Modified Files
- `path/to/file1.py` - [changes made]
- `path/to/file2.ts` - [changes made]

## Conflict Analysis

### Merge Conflicts
- ❌ [File 1]: Conflict with [other changes]
- ✅ [File 2]: No conflicts

### Potential Conflicts
- ⚠️ [File 3]: Overlapping area, review needed

## Affected Components

### Directly Affected
- [Component 1]: [impact description]
- [Component 2]: [impact description]

### Dependent Components
- [Component 3]: [may need updates]
- [Component 4]: [may need updates]

## Integration Points
- [Integration 1]: [status]
- [Integration 2]: [status]

## Integration Tests (if run)
- ✅ [Test 1]: Passing
- ❌ [Test 2]: Failing - [reason]

## Coordination Recommendations
1. [Recommendation 1]
2. [Recommendation 2]

## Documentation Updates (if --update-docs)
- Updated: [doc 1]
- Updated: [doc 2]
```
