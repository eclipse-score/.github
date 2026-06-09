# Markdown Maintenance Playbook

This repository uses a low-maintenance governance model.

## Goals

- Keep SCORE-specific governance assets concise.
- Avoid local duplication of framework-generic workflow content.
- Detect markdown hygiene issues early.

## Operating Model

1. Keep only SCORE-specific contracts and policy in this repository.
2. Inherit generic framework assets in adopter repositories.
3. Use placeholders for runtime-specific naming.
4. Validate markdown health in CI and before merge.

## Automated Checks

The script at [scripts/check_markdown_hygiene.py](/scripts/check_markdown_hygiene.py) validates:

- Duplicate markdown files by content hash.
- Broken local markdown links.

Run locally:

```bash
python3 scripts/check_markdown_hygiene.py --root . --include .github --include README.md --include profile
```

CI workflow:

- [.github/workflows/docs-hygiene.yml](/.github/workflows/docs-hygiene.yml)

## Cadence

- Pull request: automatic via CI.
- Weekly: scheduled CI run.
- Monthly: remove stale docs and confirm retained files are still SCORE-specific.

## Adopter Guidance

When porting to another repository:

1. Copy this playbook, hygiene script, and workflow.
2. Keep framework-generic assets out of the local overlay.
3. Keep only SCORE-specific deltas and schemas under `.github/references/` and `.github/score/`.
