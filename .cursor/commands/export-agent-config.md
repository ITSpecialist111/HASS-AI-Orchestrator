# Export Agent Configuration

## Purpose
Exports a complete, shareable agent configuration package including SKILLS.md, agent code, tests, and documentation for community sharing or backup.

## Usage
`/export-agent-config [agent-name] [destination]`

Example: `/export-agent-config heating-agent ./exports/`

## Instructions for Agent

When this command is invoked:

1. **Validate Agent**:
   - Verify agent exists in `ai-orchestrator/backend/agents/`
   - Check agent is registered in `agents.yaml`
   - Confirm agent has SKILLS.md file

2. **Create Export Package Structure**:
   ```
   [agent-name]-export/
   ├── README.md
   ├── agent.py
   ├── skills/
   │   └── SKILLS.md
   ├── config/
   │   └── agent.yaml
   ├── tests/
   │   └── test_[agent-name].py
   └── docs/
       ├── overview.md
       ├── setup.md
       └── examples.md
   ```

3. **Export Agent Code**:
   - Copy agent Python file
   - Remove sensitive information
   - Add header with metadata:
     ```python
     """
     Agent: [name]
     Version: [version]
     Exported: [timestamp]
     Description: [description]
     """
     ```
   - Include required imports
   - Add usage examples in docstrings

4. **Export SKILLS.md**:
   - Copy complete SKILLS.md
   - Verify formatting is intact
   - Add export metadata header
   - Include version information

5. **Extract Agent Configuration**:
   - Get agent entry from agents.yaml
   - Create standalone agent.yaml
   - Include all relevant settings
   - Add comments explaining each field
   - Anonymize any sensitive values

6. **Export Tests**:
   - Copy agent test files
   - Include fixtures if needed
   - Add test data examples
   - Document how to run tests

7. **Generate Documentation**:
   
   **README.md**:
   ```markdown
   # [Agent Name]
   
   ## Description
   [What this agent does]
   
   ## Features
   - [Feature 1]
   - [Feature 2]
   
   ## Requirements
   - Home Assistant version
   - Required entities/domains
   - LLM model requirements
   - Dependencies
   
   ## Installation
   [Step-by-step instructions]
   
   ## Configuration
   [How to configure]
   
   ## Usage Examples
   [Practical examples]
   
   ## Credits
   Exported from AI Orchestrator v[version]
   ```
   
   **setup.md**:
   - Detailed installation steps
   - Configuration options
   - Entity mapping guide
   - Troubleshooting tips
   
   **examples.md**:
   - Sample decision scenarios
   - Configuration variations
   - Common use cases
   - Best practices

8. **Include Metadata**:
   - Agent version
   - Export timestamp
   - Orchestrator version
   - Author information
   - License information
   - Dependencies list

9. **Package Export**:
   - Create ZIP archive
   - Name: `[agent-name]-v[version]-[date].zip`
   - Include checksum file (SHA256)
   - Add LICENSE file if applicable

10. **Validation**:
    - Verify all files are included
    - Check no sensitive data leaked
    - Ensure documentation is complete
    - Test import instructions work

11. **Generate Import Instructions**:
    ```markdown
    ## How to Import This Agent
    
    1. Extract ZIP to AI Orchestrator directory
    2. Copy agent.py to backend/agents/
    3. Copy SKILLS.md to skills/[agent-name]/
    4. Add configuration to agents.yaml
    5. Install dependencies (if any)
    6. Restart AI Orchestrator
    7. Verify agent appears in dashboard
    ```

## Expected Outcome
- Complete agent package exported
- All necessary files included
- Documentation comprehensive
- Package ready to share or backup
- Import instructions provided
- Checksums generated

## Export Package Contents

**Essential Files**:
- [ ] Agent Python code
- [ ] SKILLS.md
- [ ] Configuration YAML
- [ ] README.md with overview

**Optional but Recommended**:
- [ ] Test files
- [ ] Setup guide
- [ ] Example configurations
- [ ] Troubleshooting guide

**Metadata**:
- [ ] Version information
- [ ] Export timestamp
- [ ] Dependencies list
- [ ] License file

## Export Formats

**Standard Export** (for sharing):
- ZIP archive
- All documentation included
- Ready to import

**Development Export** (for backup):
- Include test data
- Include decision logs
- Include performance metrics
- Git-compatible format

**Marketplace Export** (for store):
- Include screenshots
- Include demo video
- Add user reviews template
- Include changelog

## Privacy and Security

**Always Remove**:
- API tokens
- Personal entity IDs
- IP addresses
- User names
- Location data

**Anonymize**:
- Entity names (climate.bedroom → climate.room1)
- Locations (123 Main St → Address 1)
- Time zones (specific → generic)

## Use Cases

1. **Backup**: Save agent before major changes
2. **Sharing**: Share successful agent with community
3. **Migration**: Move agent to another instance
4. **Versioning**: Track agent evolution over time
5. **Marketplace**: Prepare for agent store submission
