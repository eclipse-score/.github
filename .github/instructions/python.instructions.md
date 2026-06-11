---
applyTo: '**/*.py'
---

# Python Guidelines — Eclipse S-CORE

## Tooling

- Package manager: `uv` (not pip directly)
- Formatter: `ruff format`
- Linter: `ruff check`
- Type checker: `basedpyright`
- Test runner: `pytest`
- Build system: Bazel for integrated builds, `pyproject.toml` for standalone tools

## Project Structure

```
project-root/
├── pyproject.toml          # Dependencies, metadata, tool config
├── uv.lock                 # Lockfile (committed)
├── src/package_name/       # Source code
│   ├── __init__.py
│   └── module.py
└── tests/
    ├── __init__.py
    └── test_module.py
```

## Code Style

- `snake_case` for functions/variables, `CapWords` for classes, `UPPER_SNAKE_CASE` for constants
- Type hints on all public functions and methods
- Imports at top: standard library, third-party, local — blank lines between groups
- Absolute imports only; no wildcard imports (`from x import *`)
- Docstrings on all public modules, classes, and functions

## Function & Parameter Rules

- Never use mutable default arguments (`list`, `dict`) — use `None` and create inside
- No `.get()` for required dict keys — access directly so missing keys raise immediately
- Check explicitly for `None` for optional values
- Small focused functions — single responsibility

## Error Handling

- Catch specific exception types — never bare `except:`
- Use `logging` module, never `print()` in library code
- Re-raise or log with context — never silently swallow

## Dependencies

- All deps declared in `pyproject.toml`
- Use `uv sync` to install (creates deterministic lockfile)
- Virtual environments managed by `uv` automatically
- Prefer standard library; add third-party only for clear benefit

## Testing

- pytest for all testing
- `test_` prefix for files and functions
- Use fixtures for shared setup
- Happy path + edge cases + error cases
- `pytest-cov` for coverage enforcement

## Security

- No hardcoded secrets — use environment variables
- No `eval()` or `exec()` on untrusted input
- Validate and sanitize file paths — reject `..` components
- No sensitive data in logs — mask PII, tokens, passwords
- Use `secrets` module for security-sensitive random values (not `random`)
