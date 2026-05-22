# Assistant Runtime Alignment

This repository aligns policy for multiple assistant runtimes (Copilot/VS Code, Codex, Claude) without duplicating governance content.

## Canonical instruction source

- AGENTS.md is the canonical, runtime-neutral policy document.
- CLAUDE.md imports AGENTS.md for Claude compatibility.
- .github/copilot-instructions.md is runtime-specific glue for Copilot.

## MCP alignment model

- Keep one approved MCP integration model for the organization.
- Configure runtime settings files for MCP-first behavior.
- Keep governance assets runtime-neutral and shared where possible.

## Repository template integration

The Copier template distributes:

- AGENTS.md
- CLAUDE.md
- .github/<instructions-file>
- .claude/settings.json
- .github/copilot/settings.json

This keeps assistants aligned while preserving runtime-specific entrypoints and MCP-first integration.
