# Update Knowledge

## Purpose
Updates the project knowledge base with new information, maintaining consistency and cross-references.

## Usage
`/update-knowledge <information> [--section SECTION] [--component COMPONENT]`

Parameters:
- `information`: New information to add or update
- `--section`: Target section (components, agents, patterns, etc.)
- `--component`: Specific component to update

## Instructions for Agent

When this command is invoked:

1. **Read Current Knowledge Base**:
   - Read `.cursor/skills/proj-knowledge/proj-knowledge.md`
   - Understand current structure
   - Identify relevant section
   - Check for existing entries

2. **Analyze New Information**:
   - Understand what information is being added
   - Determine if it's new or an update
   - Identify related entries
   - Note cross-references needed

3. **Update Knowledge Base**:
   - Add new entries in appropriate section
   - Update existing entries if needed
   - Maintain consistent format
   - Add cross-references
   - Update "Last Updated" date

4. **Maintain Consistency**:
   - Use consistent terminology
   - Follow established format
   - Keep structure organized
   - Ensure accuracy

5. **Cross-Reference**:
   - Link to related components
   - Update related entries
   - Maintain bidirectional links
   - Note dependencies

## Expected Outcome

- Updated knowledge-base.md
- New or updated entries
- Maintained consistency
- Added cross-references
- Confirmation of update

## Examples

### Add new component information
```
/update-knowledge "New RAG manager component at backend/rag_manager.py handles document ingestion"
```

### Update existing component
```
/update-knowledge "MCP server now has 15 tools instead of 3" --component "MCP Server"
```

### Add to specific section
```
/update-knowledge "New pattern: async context managers for HA connections" --section "Patterns & Conventions"
```

## Information Format

When providing information, include:

- **Component name**: Clear identifier
- **Location**: File path
- **Purpose**: What it does
- **Key details**: Important information
- **Relationships**: How it connects to other components

## Best Practices

1. **Be specific**: Include file paths, function names
2. **Be accurate**: Verify information before adding
3. **Be consistent**: Follow existing format
4. **Cross-reference**: Link related entries
5. **Update dates**: Keep "Last Updated" current
