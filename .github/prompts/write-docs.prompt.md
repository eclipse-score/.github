---
agent: code-implement
tools: ['vscode', 'read', 'edit', 'search']
description: 'Create comprehensive documentation for changes made during implementation.'
---

Produce detailed documentation reflecting implementation changes.

## Tasks

### 1. Gather Context
- Review `.stage/<JIRA-ID>/implementationReport.md` for change details
- Review `.stage/<JIRA-ID>/plan.md` for original requirements
- Review `.stage/<JIRA-ID>/testResults.md` for test coverage data
- Identify all modified and new files

### 2. Generate Documentation with Structured Sections

#### Section 1: Overview
- **Jira Ticket**: ID, title, and link
- **Purpose**: What business problem this solves
- **Scope**: What was changed, added, or removed

#### Section 2: Architecture & Design Decisions
- High-level architecture changes (with Mermaid diagrams if applicable)
- **Architecture Decision Record (ADR)** for significant decisions:
  - **Status**: Accepted / Proposed / Deprecated
  - **Context**: Why was a decision needed?
  - **Decision**: What was decided?
  - **Consequences**: Trade-offs and implications

#### Section 3: Implementation Details
- Key changes per file/module with purpose
- Relevant code snippets or usage examples
- Challenges encountered and resolutions

#### Section 4: API Changes (if applicable)
- New or modified endpoints with request/response examples
- Breaking changes clearly flagged
- Migration steps for consumers

#### Section 5: Testing Summary
- Test coverage percentage
- Key test scenarios covered
- Known limitations or untested areas

#### Section 6: Changelog
- List of all changes in commit-message format:
  - `feat:`, `fix:`, `refactor:`, `docs:`, `test:`

### 3. Save Documentation
- Save at: `.stage/<JIRA-ID>/documentation.md`
- Ensure documentation adheres to project standards
- Present for user review before finalizing
