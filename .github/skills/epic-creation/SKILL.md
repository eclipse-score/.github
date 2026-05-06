---
description: 'Epic creation skill -- business-focused Epic writing with structured templates and quality rules.'
---

# Epic Creation Skill

This skill provides templates and rules for creating business-focused Epics. It is loaded on-demand when an agent needs to generate functional specifications or Epic documents.

## When to Use
- During PLAN phase: when creating a new Epic from a feature idea
- When user requests structured Epic documentation

## Epic Writing Rules

### Business Focus
- Epics describe WHAT and WHY, never HOW
- Zero technical implementation details (no class names, DB schemas, API endpoints)
- All requirements written from user/business perspective
- If a requirement sounds technical, rewrite it as a business outcome

### Acceptance Criteria
- Every requirement MUST have at least one Given/When/Then acceptance criterion
- Cover happy path AND error/edge cases
- Criteria must be testable and specific -- no vague language like "should work well"

### Metrics
- Every Epic MUST define at least 2 measurable success metrics
- Each metric needs: baseline (current state) + target (after implementation)
- Metrics must tie to business outcomes, not technical KPIs
- Suggest metric categories based on feature type:
  - **Automation features**: time saved, error reduction, throughput increase
  - **Integration features**: data freshness, sync success rate, latency
  - **UI features**: task completion rate, user satisfaction, time-on-task
  - **Compliance features**: audit pass rate, violation count, coverage %

### Quality Bar
- Problem statement: clear, specific, no jargon
- Business case: quantified impact, stakeholder identified
- Scope: explicitly bounded with out-of-scope section
- Risks: at least 2 risks with impact and mitigation

## Templates
- `assets/functional-spec-template.md` -- Functional specification structure
- `assets/epic-template.md` -- Full Epic document structure
