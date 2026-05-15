# Assistant Runtime Alignment

This repository aligns policy for multiple assistant runtimes (Copilot/VS Code, Codex, Claude) without duplicating governance content.

## Canonical instruction source

- AGENTS.md is the canonical, runtime-neutral policy document.
- CLAUDE.md imports AGENTS.md for Claude compatibility.
- .github/copilot-instructions.md is runtime-specific glue for Copilot.

## Plugin alignment model

- Keep one approved plugin marketplace source for the organization.
- Configure the same marketplace in runtime settings files.
- Enable a common governance plugin set where possible.

## Repository template integration

The Copier template distributes:

- AGENTS.md
- CLAUDE.md
- .github/<instructions-file>
- .claude/settings.json
- .github/copilot/settings.json

This keeps assistants aligned while preserving runtime-specific entrypoints.
