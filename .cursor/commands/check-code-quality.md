# Check Code Quality

## Purpose
Assesses code quality and standards by running linters, checking formatting, reviewing complexity, verifying documentation, and checking for security issues.

## Usage
`/check-code-quality [target-path] [--lint] [--format] [--complexity] [--docs] [--security]`

Parameters:
- `target-path` (optional): Specific file or directory (default: current changes)
- `--lint`: Run linters
- `--format`: Check code formatting
- `--complexity`: Analyze code complexity
- `--docs`: Verify documentation
- `--security`: Check for security issues

## Instructions for Agent

When this command is invoked:

1. **Identify Target**:
   - Determine files to check
   - Note file types (Python, TypeScript, etc.)
   - Identify appropriate tools

2. **Run Linters** (if --lint):
   - Run project linters (pylint, eslint, etc.)
   - Capture linting errors
   - Categorize by severity
   - Note fixable issues

3. **Check Formatting** (if --format):
   - Verify code formatting
   - Check against style guide
   - Identify formatting issues
   - Note auto-fixable issues

4. **Analyze Complexity** (if --complexity):
   - Calculate cyclomatic complexity
   - Identify complex functions
   - Note refactoring opportunities
   - Check maintainability index

5. **Verify Documentation** (if --docs):
   - Check for docstrings/comments
   - Verify API documentation
   - Check documentation completeness
   - Note missing documentation

6. **Check Security** (if --security):
   - Scan for vulnerabilities
   - Check for security anti-patterns
   - Verify input validation
   - Check dependency security

7. **Generate Report**:
   - Summarize findings
   - Prioritize issues
   - Suggest fixes
   - Provide quality score

## Expected Outcome

- Linting results
- Formatting check results
- Complexity analysis
- Documentation review
- Security scan results
- Quality score and recommendations

## Examples

### Full quality check
```
/check-code-quality --lint --format --complexity --docs --security
```

### Check specific file
```
/check-code-quality ai-orchestrator/backend/orchestrator.py --lint --format
```

### Check security only
```
/check-code-quality --security
```

## Output Format

```markdown
# Code Quality Report

## Target
- **Path**: `path/to/target`
- **Files Checked**: [count]

## Linting Results (if --lint)
- **Total Issues**: [count]
- **Errors**: [count] 🔴
- **Warnings**: [count] 🟡
- **Info**: [count] 🔵

### Top Issues
1. [Issue 1]: [severity] - [file:line]
2. [Issue 2]: [severity] - [file:line]

## Formatting (if --format)
- ✅ Formatting correct
- ❌ [File 1]: Formatting issues - [count]
- ⚠️ [File 2]: Minor formatting - [count]

## Complexity Analysis (if --complexity)
- **Average Complexity**: [score]
- **High Complexity Functions**:
  - `function_name()`: [complexity score] - [recommendation]

## Documentation (if --docs)
- **Documented Functions**: [count]/[total]
- **Missing Documentation**:
  - `function_name()` - [file:line]

## Security (if --security)
- **Vulnerabilities Found**: [count]
- **Issues**:
  - [Issue 1]: [severity] - [description]

## Quality Score
- **Overall**: [score]/10
- **Breakdown**:
  - Linting: [score]
  - Formatting: [score]
  - Complexity: [score]
  - Documentation: [score]
  - Security: [score]

## Recommendations
1. [Priority 1]: [recommendation]
2. [Priority 2]: [recommendation]
```
