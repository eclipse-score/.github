---
agent: code-architect
tools: ['vscode', 'execute', 'read', 'edit', 'search', 'github', 'todo']
description: 'Initialize architecture documentation through an interactive interview.'
---

Initialize the project architecture documentation.

Tasks:
- Check if `.stage/docs/architecture.md` already exists. If yes, inform the user and offer to overwrite or skip.
- Conduct an interactive interview, asking questions **one at a time**:
  1. Project name
  2. Architecture style (hexagonal, layered, clean, modular-monolith, microservices, event-driven, or custom)
  3. Interface style (gRPC, ara::com, SOME/IP, event-driven, CLI-only, or N/A)
  4. Testing strategy (testing-trophy, testing-pyramid, or custom)
  5. Additional decisions (repeat until user says no)
  6. Boundaries to enforce (repeat until user says no)
- Validate the output against the template in `.github/skills/architecture/assets/architecture-template.md`
- Create `.stage/docs/architecture.md` with all gathered decisions and boundaries
- Create `docs/design_decisions/` directory if it doesn't exist
- Invoke the `dr-expert` skill to create `docs/design_decisions/DR-001-initial-architecture.md`:
  - Title: Initial Architecture Decisions
  - Status: Accepted
  - Context: Summarize why these decisions were made
  - Decision: List all decisions and boundaries
  - Alternatives Considered: Note alternatives discussed
  - Consequences: Note trade-offs mentioned
- Present all generated files for user review before writing
- Add GitHub Issues comment: "Architecture initialized with `/arch init`"
- Update Agent Card at `.stage/<ISSUE-ID>/agent-card.json`: summary = "Architecture initialized with /arch init", status = ready_for_handoff
