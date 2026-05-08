---
agent: code-architect
tools: ['vscode', 'execute', 'read', 'edit', 'search', 'github-enterprise/*', 'atlassian/*', 'todo']
description: 'Review code or implementation plans against documented architectural decisions.'
---

Review code against documented architectural decisions and boundaries.

Prerequisites:
- `.stage/docs/architecture.md` must exist. If not, inform the user to run `/arch init` first.

Tasks:
- Read `.stage/docs/architecture.md` and all DRs with status "accepted"
- Determine what to review:
  - If `.stage/<ISSUE-ID>/plan.md` exists → review the implementation plan for violations
  - If the user specifies file paths → review those files
  - If the user specifies a branch or PR → review changes there
  - Default → review staged/unstaged git changes
- For each boundary, check whether the code (or planned code) violates the `rule`
- For each decision, check whether the code contradicts the documented approach

Report format -- for each finding:
```
⚠️ VIOLATION: <boundary name or decision key>
   File: <path>:<line>
   Rule: <the documented rule>
   Issue: <what the code does wrong>
  Suggestion: <how to fix it, referencing the relevant DR>
```

If no violations:
```
✅ No architectural violations detected. Code aligns with documented decisions.
```

- End with summary: what was reviewed, violations found, boundaries/decisions checked
- Add GitHub Issues comment: "Architecture review completed -- N violations found"
