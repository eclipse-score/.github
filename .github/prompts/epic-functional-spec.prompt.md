---
agent: plan-epic-creation
tools: ['read', 'edit']
description: 'Generate a functional specification from discovery notes using the epic-creation skill template.'
---

Generate a business-focused functional specification document.

## Tasks

### 1. Read Inputs
- Read `.stage/EPIC-DRAFT/business-context.md`
- Read `.stage/EPIC-DRAFT/business-discovery.md`
- Read `.github/skills/epic-creation/assets/functional-spec-template.md`

### 2. Generate Functional Specification
- Fill the template using ONLY information from the context and discovery notes
- Do NOT invent requirements that were not discussed
- Do NOT add technical implementation details (no class names, DB schemas, API endpoints)

### 3. Quality Checklist (Verify Before Saving)
- [ ] Every requirement has at least one Given/When/Then acceptance criterion
- [ ] Success metrics have baseline AND target numbers
- [ ] Out of scope section is populated (not empty)
- [ ] Edge cases table has at least 2 entries
- [ ] Zero technical jargon in requirements (no code, no architecture)
- [ ] Open questions section captures any unresolved items from discovery

### 4. Save and Present
- Save to `.stage/EPIC-DRAFT/functional-spec.md`
- Present the full document to the user
- Ask: "Review the functional specification. Would you like to make any changes before I generate the full Epic document?"

## Rules
- Do NOT proceed until user approves the functional specification
- If user requests changes, update the file and re-present
- Business language only -- if a requirement sounds technical, rewrite it as a business outcome
