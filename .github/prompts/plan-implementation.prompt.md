---
agent: code-design
tools: ['read', 'edit', 'github-enterprise/*']
description: 'Create a detailed implementation plan from Jira ticket requirements.'
---

Create a detailed implementation plan based on Jira ticket details.

## Tasks

### 1. Review Requirements
- Read `.stage/<JIRA-ID>/plan.md` for ticket requirements, acceptance criteria, and scope
- Identify all functional and non-functional requirements
- Flag any ambiguities or missing information for clarification

### 2. Architecture Decision Record (ADR)
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
- All acceptance criteria from Jira ticket met
- Test coverage ≥ 80% (100% for security-critical code)
- No Critical or High security findings
- Build and lint pass cleanly
- Documentation complete

### 7. Save Plan
- Save at: `.stage/<JIRA-ID>/plan.md`
- Present for user review and approval before proceeding

## CRA / React Risk Identification (required for all front-end tickets)

If the ticket involves React/TypeScript files, include a risk section in the plan covering:
- **TypeScript type safety** — flag mock/service functions returning `null` without explicit return types
- **ESLint compliance** — list all new `.ts`/`.tsx` files, each needs pre-integration ESLint check
- **i18n risk** — flag any `returnObjects: true` usage for unverified translation keys
- **New page architecture** — single self-contained file first, extract sub-components after baseline works
- **Dependency risk** — flag new npm packages (form libraries, async validators) as error boundary candidates

> Full CRA safety rules are in `.github/instructions/react.instructions.md` (auto-applied for `.tsx`/`.ts` files).
