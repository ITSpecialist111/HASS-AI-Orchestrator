# Update Configuration

## Purpose
Safely updates AI Orchestrator configuration files with validation and backup, handling agents.yaml, config.json, and environment variables.

## Usage
`/update-config [file] [key] [value]`

Examples:
- `/update-config agents.yaml heating-agent.interval 300`
- `/update-config config.json name "My AI Orchestrator"`
- `/update-config .env OLLAMA_HOST "http://192.168.1.100:11434"`

## Instructions for Agent

When this command is invoked:

1. **Identify Target Configuration**:
   - `agents.yaml` - Agent configurations
   - `config.json` - Add-on metadata
   - `.env` - Environment variables
   - `backend/requirements.txt` - Dependencies

2. **Create Backup**:
   ```bash
   cp [config-file] [config-file].backup.[timestamp]
   ```
   - Always backup before changes
   - Include timestamp in backup name
   - Keep last 5 backups

3. **Validate Input**:
   
   **For agents.yaml**:
   - Agent name exists or is being created
   - Interval is valid number (>= 5 seconds)
   - Entity IDs are valid format
   - Model name is available in Ollama
   - Decision interval is reasonable
   
   **For config.json**:
   - JSON syntax is valid
   - Version follows semver
   - Required fields present
   - Descriptions are clear
   
   **For .env**:
   - Variable name is uppercase
   - Value format is appropriate
   - No sensitive data exposed
   - URLs are valid format

4. **Apply Changes**:
   - Parse configuration file
   - Update specified key/value
   - Preserve formatting and comments
   - Validate syntax after change

5. **Validate Configuration**:
   
   **Syntax Check**:
   ```python
   # For YAML
   yaml.safe_load(file)
   
   # For JSON
   json.loads(file)
   ```
   
   **Semantic Check**:
   - Reference integrity
   - Value ranges
   - Type correctness
   - Dependency availability

6. **Test Configuration**:
   - Run configuration parser
   - Check for warnings
   - Verify no breaking changes
   - Test with dry-run if possible

7. **Document Change**:
   - Log change in CHANGELOG.md if significant
   - Add comment in config file explaining change
   - Note reason for modification

8. **Restart Affected Services**:
   - If agents.yaml changed: Reload agents
   - If config.json changed: May need add-on restart
   - If .env changed: Full backend restart required

## Expected Outcome
- Configuration successfully updated
- Backup created and stored
- Validation passed
- Services restarted if needed
- Changes documented

## Configuration Reference

### agents.yaml Structure
```yaml
agents:
  - name: agent-name
    description: "Purpose"
    decision_interval: 120
    entities:
      - domain.entity_id
    model: deepseek-r1:8b
    enabled: true
    dry_run: false
```

### config.json Structure
```json
{
  "name": "AI Orchestrator",
  "version": "0.9.47",
  "slug": "ai-orchestrator",
  "description": "...",
  "arch": ["amd64", "aarch64", "armv7"],
  "startup": "application",
  "boot": "auto",
  "options": {},
  "schema": {}
}
```

### .env Variables
```bash
# Home Assistant
HA_URL=http://supervisor/core
HA_TOKEN=your_token_here

# Ollama
OLLAMA_HOST=http://ollama:11434
HEATING_MODEL=deepseek-r1:8b
COOLING_MODEL=deepseek-r1:8b

# System
DRY_RUN_MODE=false
DECISION_INTERVAL=120
LOG_LEVEL=INFO
```

## Safety Checks

**Before Applying**:
- [ ] Backup created
- [ ] Syntax validated
- [ ] Values in acceptable ranges
- [ ] No security issues

**After Applying**:
- [ ] Configuration loads successfully
- [ ] Services restart cleanly
- [ ] No error messages in logs
- [ ] System behaves as expected

## Rollback Procedure

If issues occur:
1. Stop affected services
2. Restore from backup: `cp [backup] [original]`
3. Restart services
4. Verify functionality restored
5. Investigate root cause

## Common Configurations

**Speed up agent**:
```yaml
decision_interval: 30  # React every 30 seconds
```

**Add entity filter**:
```yaml
entities:
  - climate.thermostat_*  # Wildcard supported
```

**Enable dry-run**:
```yaml
dry_run: true  # Test without real actions
```

**Change model**:
```yaml
model: mistral:7b-instruct  # Faster, less capable
```
