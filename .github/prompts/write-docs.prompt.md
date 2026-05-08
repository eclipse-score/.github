---
agent: code-implement
tools: ['vscode', 'read', 'edit', 'search']
description: 'Create comprehensive documentation for changes made during implementation.'
---

Produce detailed documentation reflecting implementation changes.

## Tasks

### 1. Gather Context
- Review `.stage/<ISSUE-ID>/implementationReport.md` for change details
- Review `.stage/<ISSUE-ID>/plan.md` for original requirements
- Review `.stage/<ISSUE-ID>/testResults.md` for test coverage data
- Identify all modified and new files
- If documentation files under `docs/` changed, detect the repository docs stack and follow it rather than inventing a new format

### 2. Generate Documentation with Structured Sections

#### Section 1: Overview
- **GitHub Issue**: ID, title, and link
- **Purpose**: What business problem this solves
- **Scope**: What was changed, added, or removed

#### Section 2: Architecture & Design Decisions
- High-level architecture changes (with Mermaid diagrams if applicable)
- **Decision Record (DR)** for significant decisions:
  - **Status**: Accepted / Proposed / Deprecated
  - **Context**: Why was a decision needed?
  - **Decision**: What was decided?
  - **Consequences**: Trade-offs and implications

#### Section 3: Implementation Details
- Key changes per file/module with purpose
- Relevant code snippets or usage examples
- Challenges encountered and resolutions

#### Section 3b: Documentation Stack Impact (if applicable)
- For SCORE-style repos, document docs-as-code impacts using the repository's established stack:
  - Sphinx as the primary documentation engine
  - sphinx-needs where traceability or requirement artifacts are involved
  - Markdown only where the repository already supports or uses it
  - Bazel as the preferred entry point for documentation environment or docs validation commands

#### Section 4: Interface Changes (if applicable)
- New or modified RPC, middleware, CLI, or API contracts with examples where relevant
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
- Save at: `.stage/<ISSUE-ID>/documentation.md`
- Ensure documentation adheres to project standards
- If repository docs were changed, reflect the actual docs-as-code files and validation path in the write-up
- Present for user review before finalizing
