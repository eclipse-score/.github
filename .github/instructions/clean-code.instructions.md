---
applyTo: '**'
---

# Clean Code — Eclipse S-CORE

## Principles

- Code is for humans first — self-explanatory names, clear intent
- Small and focused: functions do one thing, files have one responsibility
- No duplication — extract and reuse
- KISS — reduce complexity; prefer straightforward solutions
- YAGNI — implement only what is needed now
- Boy Scout Rule — leave code cleaner than you found it
- Follow existing conventions in the file/module you are editing

## Naming

- Descriptive and unambiguous
- Functions: verbs (`parse_manifest`, `validate_input`, `send_message`)
- Types/classes: nouns (`MessageBuffer`, `ConfigEntry`, `TransportLayer`)
- Constants: `UPPER_SNAKE_CASE`
- No abbreviations unless universally understood in the domain (e.g. `ECU`, `CAN`, `SPI`)

## Functions

- Ideal: 5–15 lines, max 50
- Single responsibility — one logical step per function
- Max 3–4 parameters; group related params into a struct/dataclass
- No flag arguments — split into separate functions
- Use early returns / guard clauses to avoid deep nesting
- Max 3 levels of nesting

## Comments

- Explain *why*, not *what*
- Document assumptions, invariants, safety constraints
- Never comment out code — remove it (git preserves history)
- Public APIs must have doc comments (Doxygen for C++, `///` for Rust, docstrings for Python)

## Error Handling

- Handle errors explicitly — never silently ignore
- Use the language's idiomatic error mechanism:
  - C++: `std::expected`, error codes, or exceptions per module convention
  - Rust: `Result<T, E>` — propagate with `?`, no `.unwrap()` in production code
  - Python: specific exception types, never bare `except:`
- Log errors with sufficient context for diagnosis
- Fail fast at system boundaries

## Dependencies

- Prefer standard library over third-party
- Every dependency is a supply-chain risk — justify additions
- All deps managed via Bazel (`MODULE.bazel`) or `pyproject.toml`

## Code Smells to Fix

- Long functions (>50 lines)
- Deep nesting (>3 levels)
- Duplicated logic
- Dead code
- Magic numbers (replace with named constants)
- God objects / classes doing too many things
- Mutable shared state without synchronization
