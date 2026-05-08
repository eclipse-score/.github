# `.stage/docs/architecture.md` Schema Reference

## Full Schema

```yaml
# Required
version: 1                    # Schema version, always 1
project: <string>             # Project name

# Required — flat key-value map of architectural decisions
decisions:
  architecture-style: <string>   # e.g. hexagonal, layered, clean, modular-monolith, microservices
  api-style: <string>            # e.g. grpc, ara-com, some-ip, event-driven, cli-only, n/a
  testing-strategy: <string>     # e.g. testing-trophy, testing-pyramid, ice-cream-cone
  <custom-key>: <string>         # Teams add any decision that matters to them

# Optional — list of enforceable boundary rules
boundaries:
  - name: <string>               # Human-readable boundary name
    rule: <string>               # Precise rule statement the AI can evaluate

# Optional — path to design decision directory
adrs: <string>                   # Default: docs/design_decisions/
```

## Field Details

### `version`
Always `1`. Reserved for future schema evolution.

### `project`
The project or repository name. Used for display and identification.

### `decisions`
A **flat key-value map**. No nesting. No framework-specific fields. Common keys:

| Key | Example values |
|-----|---------------|
| `architecture-style` | `hexagonal`, `layered`, `clean`, `modular-monolith`, `microservices`, `event-driven` |
| `api-style` | `grpc`, `ara-com`, `some-ip`, `event-driven`, `cli-only`, `n/a` |
| `testing-strategy` | `testing-trophy`, `testing-pyramid` |
| `build-system` | `bazel`, `bazel+cargo`, `bazel+pytest` |
| `documentation-stack` | `sphinx`, `sphinx-needs`, `markdown` |
| `error-handling` | `result-type`, `exceptions`, `error-codes` |
| `transport` | `grpc`, `some-ip`, `ara-com`, `in-process` |
| `authentication` | `mtls`, `platform-identity`, `repo-permissions`, `n/a` |

Teams may add **any key** that represents a decision worth preserving.

### `boundaries`
Each boundary has:
- `name` — short label (used in violation messages)
- `rule` — precise statement that can be checked against code (e.g. "Code in `src/domain/` must not import from `src/infrastructure/`")

### `adrs`
Path to the design decision directory relative to the project root. Defaults to `docs/design_decisions/`.

## Validation Rules

1. `version` must be `1`
2. `project` must be a non-empty string
3. `decisions` must have at least one entry
4. Each `decisions` value must be a string
5. Each `boundaries` entry must have both `name` and `rule` as non-empty strings
6. `adrs` must be a valid relative path if present
