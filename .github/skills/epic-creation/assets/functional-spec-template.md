# Functional Specification Template

Use this template when generating the functional specification document from business discovery notes.

```markdown
# [Feature Name] — Functional Specification

**Epic Draft ID**: EPIC-DRAFT (will be renamed to EPIC-XXX after GitHub Issues creation)
**Created**: <date>
**Author**: AI SDLC — Epic Creation Agent

## Executive Summary
[2-3 sentences: what is being built, for whom, and why it matters to the business.]

## Business Case
### Problem Statement
[What problem exists today? Who is affected? What is the cost of inaction?]

### Business Value
[Quantified impact: revenue, efficiency, compliance, user satisfaction.]

### Stakeholders
| Stakeholder | Role | Interest |
|-------------|------|----------|
| [Name/Team] | [Sponsor / User / Approver] | [What they care about] |

## Functional Requirements

### FR-1: [Requirement Title]
**Description**: [What the system should do, from user perspective.]
**User Roles**: [Which roles use this?]
**Priority**: [Must Have / Should Have / Nice to Have]

**Acceptance Criteria**:
- **Given** [precondition], **When** [action], **Then** [expected outcome]
- **Given** [error condition], **When** [action], **Then** [error handling]

### FR-2: [Requirement Title]
[Repeat structure for each requirement]

## User Workflows
### Workflow 1: [Name]
[Step-by-step user journey, no technical details.]
1. User navigates to...
2. User selects...
3. System displays...

## Edge Cases & Error Handling
| Scenario | Expected Behavior |
|----------|-------------------|
| [Edge case 1] | [What happens] |
| [Error scenario 1] | [How system responds to user] |

## Success Metrics
| Metric | Baseline (Current) | Target (After) | Measurement Method |
|--------|--------------------|-----------------|--------------------|
| [Metric 1] | [Current value] | [Target value] | [How to measure] |
| [Metric 2] | [Current value] | [Target value] | [How to measure] |

## Dependencies
- [External system / team / timeline dependency]

## Out of Scope
- [Explicitly excluded items]
- [Items deferred to future iterations]

## Open Questions
- [Unresolved items that need stakeholder input]
```
