# Debug Agent

## Purpose
Provides comprehensive debugging information for a specific AI agent, including its decision history, context gathering, and potential issues.

## Usage
`/debug-agent [agent-name]`

Example: `/debug-agent heating-agent`

## Instructions for Agent

When this command is invoked:

1. **Locate Agent**:
   - Find agent in `ai-orchestrator/backend/agents/`
   - Check if agent is registered in `agents.yaml`
   - Verify agent is active in the orchestrator

2. **Gather Debug Information**:
   
   **A. Configuration**:
   - Agent settings from agents.yaml
   - Decision interval
   - Entity filters
   - Dry-run mode status
   
   **B. Recent Decisions** (last 10):
   - Timestamp of each decision
   - Context gathered
   - LLM response
   - Actions taken/proposed
   - Success/failure status
   
   **C. Performance Metrics**:
   - Average decision time
   - LLM inference latency
   - Context gathering time
   - Success rate of actions
   
   **D. Current State**:
   - Is agent running?
   - Last decision timestamp
   - Next scheduled decision
   - Any pending approval actions

3. **Analyze for Issues**:
   - Check for repeated failures
   - Look for timeout issues
   - Identify configuration problems
   - Check entity availability
   - Verify LLM connectivity

4. **Check Related Components**:
   - Skills file (SKILLS.md) exists and is valid
   - RAG knowledge relevant to agent
   - MCP tools available to agent
   - Home Assistant entities accessible

5. **Generate Report**:
   ```markdown
   ## Agent Debug Report: [agent-name]
   
   ### Status
   - Running: [Yes/No]
   - Last Decision: [timestamp]
   - Success Rate: [X%]
   
   ### Configuration
   - Interval: [X seconds]
   - Entities: [list]
   - Mode: [dry-run/live]
   
   ### Recent Activity
   [Decision log entries]
   
   ### Issues Detected
   [List any problems found]
   
   ### Recommendations
   [Suggested fixes]
   ```

6. **Provide Actionable Recommendations**:
   - Configuration adjustments
   - Entity filter improvements
   - Skills file enhancements
   - Performance optimizations

## Expected Outcome
- Comprehensive debug report displayed
- Issues clearly identified
- Specific recommendations provided
- Next steps for resolution outlined

## Common Issues and Fixes

- **Agent not deciding**: Check decision interval, verify LLM connection
- **Context gathering slow**: Reduce entity list, optimize filters
- **Actions failing**: Verify entity IDs, check HA permissions
- **LLM timeouts**: Adjust timeout settings, check Ollama server
- **Poor decisions**: Enhance SKILLS.md, add RAG documents
