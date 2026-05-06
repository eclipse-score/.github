---
agent: test-qa
tools: ['vscode', 'execute', 'read', 'edit', 'search']
description: 'Generate unit test cases for implemented code covering key areas and edge cases.'
---

Generate comprehensive unit tests for the implementation.

## Tasks

### 1. Analyze Implementation
- Review implemented code in `.stage/<JIRA-ID>/` artifacts and source files
- Identify all public methods, API endpoints, and business logic requiring tests
- Map requirements from `.stage/<JIRA-ID>/plan.md` to testable behaviors

### 2. Generate Tests Following AAA Pattern
For each testable behavior, write tests using **Arrange-Act-Assert**:
- **Arrange**: Set up test data, mocks, and preconditions
- **Act**: Execute the method/function under test
- **Assert**: Verify the expected outcome (max 3 related assertions per test)

### 3. Test Categories (ALL required)
1. **Happy path** — Expected successful behavior for each requirement
2. **Edge cases** — Boundary values, empty inputs, max limits, zero values
3. **Error scenarios** — Invalid input, missing data, null/undefined values
4. **Negative tests** — At least one per public API method (unauthorized, forbidden, not found)
5. **Integration points** — Mock external dependencies, verify correct calls

### 4. Test Naming Convention
- Format: `methodName_scenario_expectedBehavior`
- Use `@DisplayName` (Java), `describe/it` (JS/TS), or docstrings (Python) for human-readable descriptions
- Group related tests in describe blocks or nested classes

### 5. Framework-Specific Guidance
| Language | Framework | Mocking | Assertions | Coverage Tool |
|----------|-----------|---------|------------|---------------|
| Java | JUnit 5 | Mockito | AssertJ | JaCoCo |
| TypeScript | Jest/Vitest | jest.mock | expect() | jest --coverage |
| Angular | Jasmine/Karma | jasmine.createSpy | expect() | ng test --coverage |
| Python | pytest | unittest.mock | assert/pytest.raises | pytest-cov |

### 6. Coverage Targets
- **80% minimum** for standard code
- **100%** for security-critical, authentication, and financial logic
- Flag any uncovered paths in the summary

### 7. Save and Present
- Save tests following project structure conventions
- Prepare summary: test count, categories covered, estimated coverage
- Present summary for user review before proceeding to execution
- Do NOT proceed without explicit user confirmation
