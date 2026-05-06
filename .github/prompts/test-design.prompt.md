---
agent: test-qa
tools: ['vscode', 'read', 'edit', 'search', 'web', 'todo']
description: 'Systematic test design using ISTQB techniques -- derive test cases from requirements before writing code.'
---

Design a comprehensive test strategy and derive systematic test cases from requirements.

Tasks:

### 1. Analyze Requirements & Testability
- Read `.stage/<JIRA-ID>/plan.md` for ticket context and acceptance criteria
- Evaluate each requirement for **testability** (measurable, unambiguous, observable)
- Flag vague or untestable requirements back to the user
- Identify the **test scope**: which components, interfaces, and integrations are affected

### 2. Design Test Strategy
- Determine the appropriate **test levels** for each requirement:
  - **Unit tests** — isolated logic, calculations, transformations
  - **Integration tests** — component interactions, API contracts, database queries
  - **System tests** — end-to-end workflows, user journeys
- Classify requirements as **functional** or **non-functional**:
  - Functional: business logic, workflows, data processing, authorization
  - Non-functional: performance, security, accessibility, reliability
- Select **test design techniques** per requirement:
  - **Equivalence partitioning** — divide input domain into valid/invalid classes
  - **Boundary value analysis** — test at edges of equivalence classes
  - **Decision table testing** — for complex business rules with multiple conditions
  - **State transition testing** — for workflows with defined states
  - **Pairwise/combinatorial testing** — for multi-parameter interactions
- Decide **blackbox vs. whitebox** approach per test level:
  - Blackbox: test against specification (preferred for system/acceptance tests)
  - Whitebox: test internal paths, branches, conditions (preferred for unit/integration tests)

### 3. Derive Test Cases
- For each requirement, apply the selected test design technique:
  - Identify equivalence classes (valid and invalid)
  - Derive boundary values (min, min+1, max-1, max, below min, above max)
  - Build decision tables for complex rules
  - Map state transitions for workflow-based features
- Document each test case with:
  - **ID**: `TC-<feature>-NNN`
  - **Preconditions**: required system state
  - **Input / Action**: what is provided or performed
  - **Expected result**: observable, verifiable outcome
  - **Priority**: critical / high / medium / low
  - **Type**: functional / non-functional / regression
- Group test cases by feature and test level

### 4. Validate Against Acceptance Criteria
- Map every acceptance criterion to at least one test case
- Ensure **positive tests** (happy path) AND **negative tests** (error cases, invalid input)
- Verify **edge cases** are covered via boundary value analysis
- Check for **missing requirements**: gaps revealed by test design MUST be reported
- Produce a **traceability matrix**: requirement → test case mapping

### 5. Output
- Save the test design to `.stage/<JIRA-ID>/testDesign.md`
- Save the traceability matrix to `.stage/<JIRA-ID>/testTraceability.md`
- Present the test design to the user for review before proceeding to test generation

Reference `.github/instructions/testing.instructions.md` for framework-specific guidance.
