---
agent: code-architect
tools: ['vscode', 'execute', 'read', 'edit', 'search', 'github-enterprise/*', 'atlassian/*', 'todo']
description: 'Initialize architecture documentation through an interactive interview.'
---

Initialize the project architecture documentation.

Tasks:
- Check if `.stage/docs/architecture.md` already exists. If yes, inform the user and offer to overwrite or skip.
- Conduct an interactive interview, asking questions **one at a time**:
  1. Project name
  2. Architecture style (hexagonal, layered, clean, modular-monolith, microservices, event-driven, or custom)
  3. API style (REST, GraphQL, gRPC, or N/A)
  4. Testing strategy (testing-trophy, testing-pyramid, or custom)
  5. Additional decisions (repeat until user says no)
  6. Boundaries to enforce (repeat until user says no)
- Validate the output against the template in `.github/skills/architecture/assets/architecture-template.md`
- Create `.stage/docs/architecture.md` with all gathered decisions and boundaries
- Create `docs/adr/` directory if it doesn't exist
- Invoke the `adr-expert` skill to create `docs/adr/ADR-0001-initial-architecture.md`:
  - Title: Initial Architecture Decisions
  - Status: Accepted
  - Context: Summarize why these decisions were made
  - Decision: List all decisions and boundaries
  - Alternatives Considered: Note alternatives discussed
  - Consequences: Note trade-offs mentioned
- Present all generated files for user review before writing
- Add Jira comment: "Architecture initialized with `/arch init`"
