# Optimize Agent Prompt

## Purpose
Analyzes and improves an agent's SKILLS.md file and system prompts to enhance decision-making quality and reduce LLM inference time.

## Usage
`/optimize-agent-prompt [agent-name]`

Example: `/optimize-agent-prompt heating-agent`

## Instructions for Agent

When this command is invoked:

1. **Read Current Prompt**:
   - Load agent's SKILLS.md file
   - Review system prompt in agent code
   - Analyze recent decision logs

2. **Analyze Decision Quality**:
   - Review last 20 decisions made by agent
   - Identify patterns in good decisions
   - Identify patterns in poor decisions
   - Check for hallucinations or errors
   - Measure decision consistency

3. **Performance Metrics**:
   - Average LLM inference time
   - Token count of prompts
   - Response token count
   - Success rate of decisions

4. **Optimization Strategies**:
   
   **A. Clarity and Specificity**:
   - Remove vague instructions
   - Add specific examples
   - Define clear boundaries
   - Specify exact output format
   
   **B. Reduce Token Count**:
   - Remove redundant information
   - Use concise language
   - Eliminate unnecessary examples
   - Structure with bullet points
   
   **C. Improve Context**:
   - Add relevant constraints
   - Include failure scenarios
   - Specify edge case handling
   - Add safety guidelines
   
   **D. Output Structure**:
   - Enforce JSON format
   - Define required fields
   - Add validation rules
   - Include confidence scoring

5. **Generate Optimized Prompt**:
   - Create improved SKILLS.md
   - Preserve agent's core purpose
   - Add missing guidance
   - Remove bloat
   - Test with sample contexts

6. **A/B Testing Recommendation**:
   - Suggest running both versions
   - Compare decision quality
   - Measure performance impact
   - Collect metrics for evaluation

7. **Create Backup**:
   - Save original SKILLS.md as SKILLS.md.backup
   - Document changes made
   - Note expected improvements

## Expected Outcome
- Optimized SKILLS.md file created
- Backup of original saved
- Clear documentation of changes
- Expected improvements quantified
- A/B testing plan provided

## Optimization Checklist

- [ ] Reduced unnecessary verbosity
- [ ] Added specific examples
- [ ] Clarified decision boundaries
- [ ] Specified output format
- [ ] Included safety constraints
- [ ] Added edge case handling
- [ ] Removed ambiguous language
- [ ] Structured for readability
- [ ] Token count reduced
- [ ] Core purpose preserved

## Example Improvements

**Before**:
```
You should try to keep the house comfortable but also save energy when possible.
```

**After**:
```
Maintain temperature 20-22°C when occupied, reduce to 18°C when away >2hrs.
Prioritize comfort 6am-10pm, prioritize efficiency 10pm-6am.
```

## Success Metrics
- 20-30% reduction in token count
- 10-15% faster inference time
- Higher decision consistency
- Fewer approval queue items
- Better user satisfaction
