---
description: 'TDD workflow skill -- enforces RED → GREEN → REFACTOR cycle with coverage verification and framework-specific guidance.'
---

# TDD Workflow Skill

This skill provides deep knowledge and step-by-step guidance for Test-Driven Development. It is loaded on-demand when an agent or prompt needs to enforce TDD methodology.

## When to Use
- During TEST stage: when user opts for TDD approach
- During BUILD stage: when implementing new features with test-first methodology
- When user explicitly requests TDD workflow

## TDD Methodology

### The Three Laws of TDD
1. You may not write production code until you have written a failing unit test
2. You may not write more of a unit test than is sufficient to fail (and not compiling counts as failing)
3. You may not write more production code than is sufficient to pass the currently failing test

### Cycle: RED → GREEN → REFACTOR

#### RED Phase
1. Identify the next smallest testable behavior from requirements
2. Write a test that captures exactly that behavior
3. Use Arrange-Act-Assert (AAA) pattern:
   - **Arrange**: Set up test data and preconditions
   - **Act**: Call the method/function under test
   - **Assert**: Verify ONE expected outcome
4. Run the test — it MUST fail
5. If it passes without new code, the test is wrong — rewrite

#### GREEN Phase
1. Write the **minimum code** to make the failing test pass
2. It's okay to hardcode, use simple conditionals, or write "ugly" code
3. The goal is speed to green, not elegance
4. Run ALL tests — they must ALL pass
5. If any test fails, fix the implementation (not the test)

#### REFACTOR Phase
1. With all tests green, improve code quality:
   - Remove duplication (DRY)
   - Extract methods for readability
   - Rename for clarity
   - Apply SOLID principles
2. Run tests after EVERY refactor step
3. If tests break, revert the last refactor and try smaller
4. Never add new functionality during refactor

### When to Stop
- All acceptance criteria from requirements have corresponding tests
- Coverage meets minimum thresholds
- No obvious missing edge cases or error scenarios

## Test Quality Checklist
- [ ] Tests are independent (no shared mutable state)
- [ ] Tests are deterministic (no flaky behavior)
- [ ] Tests are fast (unit tests < 100ms each)
- [ ] Test names describe the scenario and expected behavior
- [ ] Each test has a clear AAA structure
- [ ] Max 3 related assertions per test
- [ ] Happy path, edge cases, error scenarios, and negative tests covered

## Coverage Thresholds
| Code Category | Minimum Coverage |
|---------------|-----------------|
| Standard business logic | 80% |
| Security-critical code | 100% |
| Authentication/authorization | 100% |
| Financial calculations | 100% |
| Data validation | 90% |

## Framework Quick Reference

### Java (JUnit 5 + Mockito + AssertJ)
```java
@Test
@DisplayName("should return user when valid ID provided")
void findById_validId_returnsUser() {
    // Arrange
    var expectedUser = new User(1L, "Alice");
    when(repository.findById(1L)).thenReturn(Optional.of(expectedUser));

    // Act
    var result = service.findById(1L);

    // Assert
    assertThat(result).isEqualTo(expectedUser);
}
```

### TypeScript (Jest)
```typescript
describe('UserService', () => {
  it('should return user when valid ID provided', () => {
    // Arrange
    const expectedUser = { id: 1, name: 'Alice' };
    mockRepository.findById.mockReturnValue(expectedUser);

    // Act
    const result = service.findById(1);

    // Assert
    expect(result).toEqual(expectedUser);
  });
});
```

### Python (pytest)
```python
def test_find_by_id_valid_id_returns_user(mock_repository):
    # Arrange
    expected_user = User(id=1, name="Alice")
    mock_repository.find_by_id.return_value = expected_user

    # Act
    result = service.find_by_id(1)

    # Assert
    assert result == expected_user
```

## Anti-Patterns to Avoid
- **Testing implementation details** — Test behavior, not internal structure
- **Over-mocking** — Mock only external boundaries, not internal collaborators
- **Testing getters/setters** — No value in testing trivial accessors
- **Ignoring test failures** — Every failing test is a signal; investigate before skipping
- **Writing tests after implementation** — This is "test-after", not TDD
