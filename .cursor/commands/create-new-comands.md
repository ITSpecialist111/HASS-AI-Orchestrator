# Create New Command

## Purpose
This command instructs AI agents to create new Cursor commands that provide specialized tools and workflows for the HASS AI Orchestrator project.

## Usage
`/create-new-commands`

## Instructions for Agent

When this command is invoked, you should:

1. **Analyze the project context** to understand what commands would be most valuable
2. **Create a new command file** in `.cursor/commands/` with a descriptive name (kebab-case)
3. **Follow the standard command structure**:
   - Clear title/purpose
   - Usage syntax
   - Detailed instructions for the agent
   - Examples if applicable
   - Expected outcomes

4. **Command Structure Template**:
```markdown
# [Command Name]

## Purpose
[1-2 sentence description of what this command does]

## Usage
`/command-name [optional-args]`

## Instructions for Agent

When this command is invoked:

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Expected Outcome
[What the user should see/get after running this command]

## Examples
[Optional: Show example usage scenarios]
```

5. **Best Practices**:
   - Make commands action-oriented and specific
   - Include safety checks for destructive operations
   - Provide clear feedback to the user
   - Reference relevant project files and structure
   - Consider agent capabilities and limitations

6. **Categories to Consider**:
   - Development workflow (testing, deployment)
   - Code quality (linting, formatting, documentation)
   - Agent management (creating, testing, debugging agents)
   - Configuration management
   - Knowledge base management (RAG)
   - Dashboard operations
   - Testing and validation
   - Git operations

## Expected Outcome
A new command file created in `.cursor/commands/` that other agents can use to perform specialized tasks.
