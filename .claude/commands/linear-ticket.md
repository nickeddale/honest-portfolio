---
description: "Pull a Linear ticket, draft an implementation plan, and update the ticket"
argument-hint: "[ticket-id|'next']"
---

## Linear Ticket Workflow

Pull a ticket from Linear and create a detailed implementation plan.

### Arguments
- If no argument or "next": Get the first ticket from Todo or Backlog
- If ticket ID provided (e.g., "ND-8"): Get that specific ticket

**Ticket requested:** $ARGUMENTS

### Workflow Steps

1. **Fetch the ticket from Linear**
   - If no argument or "next" was provided, use `mcp__linear-server__list_issues` with state "Todo" first
   - If no Todo issues, check "Backlog"
   - Get the first ticket from the list
   - If a specific ticket ID was provided, use `mcp__linear-server__get_issue` to fetch it
   - Display the ticket title, description, and labels

2. **Explore the codebase**
   - Based on the ticket title and description, use the Explore agent to find relevant code
   - Identify files that need to be modified
   - Understand existing patterns and architecture
   - Search for related functionality, similar implementations, or affected components

3. **Draft implementation plan**
   - Create a detailed plan including:
     - **Summary**: Brief description of the task
     - **Root cause** (for bugs) or **Requirements** (for features)
     - **Files to modify**: List specific file paths
     - **Implementation steps**: Numbered, actionable steps
     - **Testing approach**: How to verify the fix/feature works
   - Include these Linear status milestones in the plan:
     - First step: Update Linear ticket to "In Progress"
     - Middle steps: Implementation and testing
     - After testing: Update Linear ticket to "In Review"
     - After merge/completion: Update Linear ticket to "Done"

4. **Present plan for approval**
   - Show the complete plan to the user
   - Ask: "Does this plan look good? Should I proceed with updating the Linear ticket?"
   - Wait for user approval before making any changes

5. **On approval: Update Linear ticket**
   - Use `mcp__linear-server__update_issue` to set status to "In Progress"
   - Use `mcp__linear-server__update_issue` to append the implementation plan to the ticket description
   - Format the plan as a "## Implementation Plan" section in the description

### Important Notes
- Always read the full ticket details before planning
- Explore the codebase thoroughly to understand context
- Ask clarifying questions if the ticket is ambiguous
- The plan should be actionable and specific to this codebase
- Do NOT make any code changes during planning - only research and plan
