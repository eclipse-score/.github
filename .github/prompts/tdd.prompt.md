---
agent: test-qa
tools: ['vscode', 'execute', 'read', 'edit', 'search']
description: 'Enforce test-driven development workflow. Write tests FIRST, then implement minimal code to pass. Ensure 80%+ coverage.'
---

Enforce Test-Driven Development (TDD) for the current implementation.

## TDD Cycle: RED → GREEN → REFACTOR

### Phase 1: RED — Write Failing Tests First
- Review `.stage/<JIRA-ID>/plan.md` for requirements and acceptance criteria
- Identify the first testable behavior from the requirements
- Write a **minimal failing test** that captures the expected behavior:
  - Use Arrange-Act-Assert (AAA) pattern
  - Use descriptive test name: `methodName_scenario_expectedBehavior`
  - Include exactly ONE logical assertion
- Run the test — confirm it **FAILS** (red)
- If the test passes without implementation, the test is wrong — rewrite it

### Phase 2: GREEN — Write Minimal Implementation
- Write the **smallest amount of code** that makes the failing test pass
- Do NOT add features beyond what the test requires
- Do NOT optimize or refactor yet
- Run all tests — confirm they **ALL PASS** (green)
- If any test fails, fix the implementation (not the test) unless the test is wrong

### Phase 3: REFACTOR — Improve While Green
- With all tests passing, improve code quality:
  - Extract methods, rename variables, remove duplication
  - Apply SOLID principles and patterns from `.github/instructions/clean-code.instructions.md`
  - Apply language-specific guidelines from `.github/instructions/`
- Run all tests after every refactor step — they must stay **GREEN**
- If a refactor breaks a test, revert and try a smaller refactor

### Repeat
- Pick the next testable behavior from requirements
- Repeat RED → GREEN → REFACTOR until all requirements are covered

## Coverage & Test Categories

> Coverage thresholds, test categories, and framework reference are in `.github/instructions/testing.instructions.md` (auto-applied globally). Follow those requirements exactly.

Ensure each TDD cycle covers: happy path, edge cases, error scenarios, and at least one negative test per public API method.

## Rules
- Never write implementation before the test
- Never skip the RED phase — tests must fail first
- Never modify a test to make it pass — fix the implementation
- Present test results after each cycle for user review
- Do NOT proceed to next cycle without user confirmation
