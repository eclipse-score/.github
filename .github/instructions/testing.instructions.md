---
applyTo: '**'
---

# Testing Requirements — Eclipse S-CORE

## Build & Test System

All S-CORE modules use Bazel as the primary build and test system:

```bash
# Build all targets
bazel build //...

# Run all tests
bazel test //...

# Run tests with sanitizers (from score_cpp_policies)
bazel test --config=asan_ubsan_lsan //...   # Memory errors + UB + leaks
bazel test --config=tsan //...               # Thread safety (separate run)

# Run clang-tidy
bazel build --config=clang-tidy //...

# Run Clippy (Rust)
bazel build --config=clippy-strict //...     # Safety-critical code
bazel build --config=clippy-relaxed //...    # Tooling and tests
```

## Coverage

- Minimum 80% for general code
- 100% required for:
  - Safety-critical code paths
  - Platform abstraction layers
  - Security-sensitive logic
  - Communication protocol handlers

## Test Types

1. **Unit Tests** — Individual functions, utilities, components
2. **Integration Tests** — Cross-component interactions, IPC, service communication
3. **System Tests** — End-to-end flows in `reference_integration` where applicable

## Test-Driven Development (TDD)

For new features and bug fixes:
1. **RED** — Write a failing test first
2. **GREEN** — Minimal implementation to pass
3. **REFACTOR** — Improve while keeping tests green

## Test Structure

- Arrange-Act-Assert (AAA) pattern
- One logical assertion per test (max 3 related assertions)
- Descriptive test names: `test_<unit>_<scenario>_<expected>`
- Tests must be independent, isolated, deterministic (no flakiness)
- No shared mutable state between tests

## Language-Specific Frameworks

| Language | Unit | Mocking | Sanitizers | Coverage |
|----------|------|---------|------------|----------|
| C++ | GoogleTest | GoogleMock | ASan, UBSan, LSan, TSan | lcov/gcov |
| Rust | `#[test]` / cargo test | mockall | Clippy strict/relaxed | llvm-cov/grcov |
| Python | pytest | unittest.mock | N/A | pytest-cov |
| Starlark | Bazel test rules | N/A | N/A | N/A |

## Sanitizer Tags

Use tags to skip tests incompatible with specific sanitizers:

```python
cc_test(
    name = "my_test",
    srcs = ["my_test.cpp"],
    tags = ["no-tsan"],  # Skip under ThreadSanitizer
)
```

Available tags: `no-tsan`, `no-asan`, `no-lsan`, `no-ubsan`

## Test Quality

- Fast execution (unit tests < 100ms each)
- Fix implementation, not tests (unless tests are wrong)
- Never commit tests that are expected to fail without a linked issue
- Tag long-running integration tests appropriately
