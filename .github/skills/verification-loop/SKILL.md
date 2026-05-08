---
description: 'Verification loop skill -- comprehensive pre-PR verification with build, lint, test, security, and git checks.'
---

# Verification Loop Skill

This skill provides deep knowledge for running comprehensive pre-PR verification loops. It is loaded on-demand when an agent or prompt needs to verify code readiness.

## When to Use
- Before creating a pull request (DEPLOY stage)
- When user invokes `verify` prompt
- After completing implementation and testing
- As a final quality gate before code review

## Verification Pipeline

### Step 1: Build Verification
Detect build system and run:
| Build System | Command | Pass Criteria |
|-------------|---------|---------------|
| CMake (C++) | `cmake --build build` | Exit code 0 |
| Bazel (C++) | `bazel build //:all` | Exit code 0 |
| pip (Python) | `python -m py_compile src/**/*.py` | Exit code 0 |
| Poetry (Python) | `poetry build` | Exit code 0 |
| Cargo (Rust) | `cargo build` | Exit code 0 |
| Go | `go build ./...` | Exit code 0 |

### Step 2: Type Checking
| Language | Command | Pass Criteria |
|----------|---------|---------------|
| C++ | Compiler flags `-Werror` | Zero errors |
| Python (mypy) | `mypy src/ --strict` | Zero errors |
| Rust | `cargo check` | Zero errors |
| Go | `go build ./...` | Zero errors |

### Step 3: Lint Verification
| Linter | Command | Pass Criteria |
|--------|---------|---------------|
| clang-format (C++) | `bazel test //:format.check` | Zero violations |
| Ruff (Python) | `ruff check .` | Zero errors |
| clippy (Rust) | `cargo clippy --all-targets` | Zero warnings |
| go vet (Go) | `go vet ./...` | Zero errors |

### Step 4: Test Verification
| Framework | Command | Pass Criteria |
|-----------|---------|---------------|
| GoogleTest (C++) | `bazel test //:all` or `ctest` | All pass, coverage ≥ 80% |
| pytest (Python) | `pytest --cov=src --cov-report=term-missing` | All pass, coverage ≥ 80% |
| cargo test (Rust) | `cargo test --verbose` | All pass, coverage ≥ 80% |
| go test (Go) | `go test -cover ./...` | All pass, coverage ≥ 80% |

Coverage thresholds:
- 80% minimum for standard code
- 100% for security-critical, auth, and financial code

### Step 5: Security Verification
1. **Secrets scan**: Search for hardcoded secrets in changed files
2. **Dependency audit**:
   - Python: `pip-audit`
   - Rust: `cargo audit`
   - Go: `nancy` (github.com/sonatype-nexus-community/nancy)
   - C++: OWASP Dependency-Check (if configured)
3. **Input validation check**: Verify all API boundaries validate input
4. Pass criteria: Zero Critical or High findings

### Step 6: Git Status Verification
1. Clean working tree: `git status --porcelain` returns empty
2. Branch rebased on latest base: `git log --oneline base..HEAD`
3. Commit message format: `type(scope): description`
4. No merge conflicts

## Verification Report Template

```markdown
# Verification Report — <ISSUE-ID>

| Check | Status | Details |
|-------|--------|---------|
| Build | ✅ PASS / ❌ FAIL | [error count or clean] |
| Types | ✅ PASS / ❌ FAIL / ➖ N/A | [error count or clean] |
| Lint | ✅ PASS / ❌ FAIL | [warning/error count] |
| Tests | ✅ PASS / ❌ FAIL | [X/Y passed, coverage Z%] |
| Security | ✅ PASS / ❌ FAIL | [finding count by severity] |
| Git | ✅ PASS / ❌ FAIL | [clean/dirty, commit format] |

**Overall: ✅ READY FOR PR / ❌ NOT READY**

### Failures (if any)
[Detailed description of each failure with recommended fix]
```

## Decision Matrix
| Scenario | Recommendation |
|----------|---------------|
| All checks PASS | Proceed to PR creation |
| Build FAIL | Use `build-fix` prompt to resolve |
| Tests FAIL | Return to TEST stage or use `tdd` prompt |
| Security FAIL (Critical) | Block PR, fix immediately |
| Security FAIL (High) | Block PR, fix before merge |
| Lint FAIL | Auto-fix if possible, manual fix otherwise |
| Git FAIL | Commit changes, rebase, fix messages |
