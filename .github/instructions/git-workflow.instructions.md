---
applyTo: '**'
---

# Git Workflow — Eclipse S-CORE

## Commit Message Format

```
<prefix>(<scope>): <summary>

<optional body>

Signed-off-by: Your Name <your.email@example.com>
```

### Prefixes

`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`, `style`

### Rules

- Imperative mood: "add feature" not "added feature"
- Subject line max 72 characters
- One logical change per commit
- All commits MUST include `Signed-off-by:` (Eclipse DCO requirement)
- Run `gitlint` locally before pushing if available
- Reference related issues: `Fixes #123` or `Refs #456`

### AI Disclosure (when applicable)

Add a trailer when AI tools assisted the commit:

```
Assisted-by: GitHub Copilot <noreply@github.com>
Assisted-by: Claude Code <noreply@anthropic.com>
Assisted-by: Devin <noreply@cognition.ai>
```

## Branch Naming

Format: `<type>/<short-description>`

Examples:
- `feat/add-can-transport`
- `fix/buffer-overflow-handler`
- `docs/update-architecture`

## Pull Request Workflow

1. Create PR using the appropriate template (Bugfix or Improvement)
2. Mark as draft until ready for review
3. Include a test plan with verification steps
4. Ensure all CI checks pass before requesting review
5. Request review from CODEOWNERS (triggered automatically)
6. At least one committer must approve before merge

## Pre-Commit Checklist

- [ ] All tests pass (`bazel test //...` or equivalent)
- [ ] No lint errors (`clang-tidy`, `clippy`, `ruff check`)
- [ ] No debug output left in production code
- [ ] No TODO/FIXME without a linked issue
- [ ] Commit message follows format above
- [ ] `Signed-off-by` trailer present (ECA/DCO requirement)

## Merge Strategy

- Squash merge for single-topic PRs from one author
- Rebase/merge commit for multi-topic PRs or multiple authors
- Never merge `main` into feature branches — rebase instead

## Eclipse Foundation Requirements

- All contributors must sign the [Eclipse Contributor Agreement (ECA)](https://www.eclipse.org/legal/eca/)
- All commits must include DCO sign-off
- Commit messages must follow [Eclipse Foundation commit rules](https://www.eclipse.org/projects/handbook/#resources-commit)
