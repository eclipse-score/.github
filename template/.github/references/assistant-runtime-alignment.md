# Assistant Runtime Alignment

This repository distributes one shared policy across multiple assistant runtimes.

## Canonical instruction source

- AGENTS.md is the canonical, runtime-neutral project policy.
- CLAUDE.md imports AGENTS.md for Claude Code compatibility.
- .github/<instructions-file> is runtime-specific glue (for example copilot-instructions.md).

## Why this layout

- Codex reads AGENTS.md directly and supports layered AGENTS files.
- Claude Code reads CLAUDE.md and recommends importing AGENTS.md when both are used.
- VS Code agent plugins and Codex plugins share compatible plugin concepts (skills, agents, hooks, MCP), so marketplace settings can be aligned.

## Plugin marketplace alignment

The template includes marketplace recommendation stubs in:

- .claude/settings.json
- .github/copilot/settings.json

Both point to the same marketplace and default plugin identifier so teams can keep tool capabilities aligned.

## Adoption checklist

1. Keep AGENTS.md as the source of truth for shared behavioral policy.
2. Keep CLAUDE.md minimal and import-first.
3. Keep .github/<instructions-file> minimal and runtime-specific.
4. Configure one approved plugin marketplace for all assistant runtimes.
5. Use copier update to roll out governance and alignment updates.
