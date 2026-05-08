---
agent: code-design
tools: ['read', 'edit', 'github-enterprise/*']
description: 'Create a detailed implementation plan from GitHub issue requirements.'
---

Create a detailed implementation plan based on GitHub issue details.

## Tasks

### 1. Review Requirements
- Read `.stage/<ISSUE-ID>/plan.md` for issue requirements, acceptance criteria, and scope
- Identify all functional and non-functional requirements
- Flag any ambiguities or missing information for clarification

### 2. Decision Record (DR)
For any significant technical decision, document:
- **Status**: Proposed
- **Context**: Why is this decision needed?
- **Options Considered**: At least 2 alternatives with pros/cons
- **Decision**: Selected approach with rationale
- **Consequences**: Trade-offs, risks, and migration needs

### 3. Phased Delivery Model
Break implementation into phases:
1. **MVP (Phase 1)** — Core functionality, happy path only
2. **Core (Phase 2)** — Error handling, edge cases, validation
3. **Edge (Phase 3)** — Performance optimization, advanced features
4. **Polish (Phase 4)** — Logging, monitoring, documentation

### 4. Task Breakdown
For each phase, define:
- Task name and description
- Estimated effort (hours)
- Dependencies on other tasks or external teams
- Acceptance criteria (how to verify completion)
- Risk level: Low / Medium / High

### 5. Risk Assessment
- Technical risks with impact and mitigation strategies
- Dependency risks (external APIs, team availability)
- Timeline risks

### 6. Success Criteria
Define clear, measurable success criteria:
- All acceptance criteria from GitHub issue met
- Test coverage ≥ 80% (100% for security-critical code)
- No Critical or High security findings
- Build and lint pass cleanly
- Documentation complete

### 7. Save Plan
- Save at: `.stage/<TICKET-ID>/plan.md`
- Present for user review and approval before proceeding
