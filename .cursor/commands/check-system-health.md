# Check System Health

## Purpose
Performs comprehensive health check of the AI Orchestrator system, including backend, agents, LLM providers, Home Assistant connectivity, and performance metrics.

## Usage
`/check-system-health [--detailed]`

Flags:
- `--detailed` - Include extended diagnostics and performance profiling

## Instructions for Agent

When this command is invoked:

1. **Backend Health**:
   - Check if FastAPI server is running
   - Test `/health` endpoint response time
   - Verify all required services initialized
   - Check memory usage
   - Monitor CPU utilization

2. **Home Assistant Connection**:
   - Test WebSocket connection
   - Verify authentication token
   - Check API responsiveness
   - Test entity state retrieval
   - Validate service call capability

3. **LLM Provider Status**:
   
   **Ollama**:
   - Ping Ollama server
   - Verify required models are pulled:
     - deepseek-r1:8b
     - mistral:7b-instruct
     - nomic-embed-text (required for RAG)
   - Check inference speed (test prompt)
   - Monitor VRAM/RAM usage
   
   **Gemini** (if configured):
   - Validate API key
   - Test connectivity
   - Check rate limits
   - Verify quota remaining

4. **Agent Status**:
   - List all configured agents
   - Check which agents are active
   - Verify each agent's last decision time
   - Check for stuck or failed agents
   - Review error logs per agent

5. **RAG Knowledge Base**:
   - ChromaDB connection status
   - Number of documents indexed
   - Vector database size
   - Embedding model availability
   - Test retrieval query

6. **MCP Server**:
   - Verify MCP server is running
   - Check tool registration (should be 3 tools)
   - Test tool schema retrieval
   - Validate safety constraints

7. **Dashboard**:
   - Web UI accessibility
   - Frontend build status
   - Static file serving
   - WebSocket connections for live updates

8. **Performance Metrics**:
   - Average decision latency per agent
   - LLM inference time distribution
   - API response times
   - Memory usage trends
   - CPU usage patterns

9. **Storage and Resources**:
   - Disk space available
   - Database size
   - Log file sizes
   - Vector store size
   - Docker container stats (if applicable)

10. **Configuration Validation**:
    - Check all required env vars are set
    - Validate agents.yaml syntax
    - Verify config.json is valid
    - Check for deprecated settings

11. **Generate Health Report**:
    ```markdown
    # AI Orchestrator Health Report
    Generated: [timestamp]
    
    ## Overall Status: [HEALTHY|DEGRADED|CRITICAL]
    
    ## Component Status
    - Backend API: [✓|✗] [response_time]
    - Home Assistant: [✓|✗] [latency]
    - Ollama: [✓|✗] [models available]
    - Gemini: [✓|✗] [if configured]
    - ChromaDB: [✓|✗] [documents indexed]
    - MCP Server: [✓|✗] [tools available]
    - Dashboard: [✓|✗] [accessible]
    
    ## Active Agents ([N]/[total])
    [agent list with status]
    
    ## Performance
    - Avg Decision Time: [X]ms
    - LLM Inference: [X]ms
    - API Latency: [X]ms
    - Memory Usage: [X]MB / [total]MB
    - CPU Usage: [X]%
    
    ## Issues Detected
    [List any problems]
    
    ## Warnings
    [List any concerns]
    
    ## Recommendations
    [Suggested actions]
    ```

12. **Issue Detection**:
    
    **Critical Issues** (system unusable):
    - Backend not responding
    - HA connection failed
    - No LLM providers available
    - Database corruption
    
    **Major Issues** (degraded functionality):
    - Some agents failing
    - High latency (>5s)
    - Missing required models
    - Memory pressure
    
    **Minor Issues** (suboptimal):
    - Slow inference times
    - Outdated models
    - Log file buildup
    - Non-critical agent errors

13. **Provide Remediation Steps**:
    - For each issue, suggest specific fix
    - Include command to execute
    - Prioritize by severity
    - Estimate resolution time

## Expected Outcome
- Comprehensive health report displayed
- All components checked and status shown
- Any issues clearly identified with severity
- Specific remediation steps provided
- Overall system health assessment

## Health Check Categories

**Critical** (Must be working):
- Backend API
- Home Assistant connection
- At least one LLM provider
- Configuration files valid

**Important** (Should be working):
- All configured agents
- RAG knowledge base
- MCP server
- Dashboard UI

**Optional** (Nice to have):
- Multiple LLM providers
- Advanced features
- Telemetry
- Analytics

## Common Issues and Fixes

**"Ollama not responding"**:
```bash
# Check Ollama service
systemctl status ollama
# Restart if needed
systemctl restart ollama
```

**"HA connection failed"**:
- Verify HA_TOKEN is valid and not expired
- Check HA_URL is correct
- Ensure network connectivity

**"Agent stuck/not deciding"**:
- Check agent error logs
- Verify LLM is responsive
- Review decision interval
- Check entity availability

**"High memory usage"**:
- Check for memory leaks
- Review ChromaDB size
- Optimize agent intervals
- Consider model size

**"Slow inference"**:
- Use smaller/faster models
- Optimize prompts
- Check hardware resources
- Consider GPU acceleration
