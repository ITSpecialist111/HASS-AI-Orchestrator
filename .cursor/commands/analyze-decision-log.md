# Analyze Decision Log

## Purpose
Analyzes agent decision history to identify patterns, inefficiencies, conflicts, and opportunities for improvement.

## Usage
`/analyze-decision-log [timeframe] [agent-name]`

Examples:
- `/analyze-decision-log 24h` - Last 24 hours, all agents
- `/analyze-decision-log 7d heating-agent` - Last 7 days, heating agent only
- `/analyze-decision-log all lighting-agent` - All time, lighting agent

## Instructions for Agent

When this command is invoked:

1. **Retrieve Decision Log**:
   - Query backend API: `/api/decisions?limit=[N]`
   - Filter by timeframe if specified
   - Filter by agent name if specified
   - Load decision context and outcomes

2. **Calculate Key Metrics**:
   
   **A. Decision Volume**:
   - Total decisions made
   - Decisions per agent
   - Decisions per hour/day
   - Peak activity periods
   
   **B. Action Statistics**:
   - Total actions proposed
   - Actions approved
   - Actions rejected
   - Actions requiring approval
   
   **C. Performance**:
   - Average decision time
   - LLM inference latency
   - Context gathering time
   - Success rate per agent

3. **Pattern Analysis**:
   
   **A. Identify Repetitive Patterns**:
   - Same action repeated frequently
   - Time-based patterns
   - Trigger-response patterns
   - Oscillating behaviors (flip-flopping)
   
   **B. Detect Conflicts**:
   - Agents working against each other
   - Contradictory decisions
   - Resource contention
   - Priority conflicts
   
   **C. Find Inefficiencies**:
   - Redundant decisions
   - Unnecessary context gathering
   - Over-frequent intervals
   - Wasted LLM calls

4. **Quality Assessment**:
   - Decisions aligned with agent goals
   - Appropriate use of tools
   - Safety constraint adherence
   - User override frequency

5. **Generate Insights**:
   
   **A. Optimization Opportunities**:
   - Interval adjustments
   - Entity filter refinements
   - Prompt improvements
   - Tool enhancements
   
   **B. Potential Issues**:
   - Agents needing attention
   - Configuration problems
   - Resource bottlenecks
   - Safety concerns
   
   **C. Success Stories**:
   - Well-performing agents
   - Effective automations
   - High-value decisions

6. **Create Report**:
   ```markdown
   # Decision Log Analysis Report
   
   **Period**: [timeframe]
   **Agents**: [agent list]
   **Total Decisions**: [N]
   
   ## Key Metrics
   [Statistics summary]
   
   ## Patterns Detected
   [Pattern descriptions]
   
   ## Issues Found
   [Problems with severity]
   
   ## Recommendations
   [Actionable improvements]
   
   ## Top Performers
   [Well-functioning agents]
   ```

7. **Visualization Suggestions**:
   - Decision timeline chart
   - Agent activity heatmap
   - Success rate comparison
   - Response time distribution

## Expected Outcome
- Comprehensive analysis report
- Key metrics and statistics
- Patterns and anomalies identified
- Specific recommendations provided
- Actionable next steps outlined

## Analysis Dimensions

**Temporal**:
- Time of day patterns
- Day of week patterns
- Seasonal variations
- Event correlations

**Agent Performance**:
- Decision quality
- Response speed
- Resource efficiency
- Goal achievement

**System Health**:
- Error rates
- Timeout frequency
- API failures
- Resource utilization

**User Interaction**:
- Override frequency
- Approval patterns
- Chat commands
- Manual interventions

## Common Findings

**Good Signs**:
- Consistent decision patterns
- High success rates
- Low override frequency
- Efficient resource use

**Warning Signs**:
- Oscillating decisions
- Frequent failures
- High rejection rates
- Excessive API calls

**Critical Issues**:
- Agent conflicts
- Safety violations
- System errors
- Performance degradation

## Recommendations Format

For each issue, provide:
1. **Problem**: Clear description
2. **Impact**: Severity and scope
3. **Root Cause**: Technical reason
4. **Solution**: Specific fix
5. **Priority**: High/Medium/Low
