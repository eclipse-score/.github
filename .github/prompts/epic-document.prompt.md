---
agent: plan-epic-creation
tools: ['read', 'edit']
description: 'Generate the full Epic document from the approved functional specification using the epic-creation skill template.'
---

Generate a comprehensive Epic document from the approved functional specification.

## Tasks

### 1. Read Inputs
- Read `.stage/EPIC-DRAFT/functional-spec.md` (approved by user)
- Read `.stage/EPIC-DRAFT/business-discovery.md`
- Read `.github/skills/epic-creation/assets/epic-template.md`

### 2. Generate Epic Document
- Fill the template using information from the functional spec and discovery notes
- Transform functional requirements into Epic-level scope items
- Derive Pain Points from the problem statement and current state
- Derive Bright Points from the target state and success metrics
- Create a Current State vs Target State comparison table
- Map acceptance criteria from the functional spec into Epic-level ACs
- Include high-level test cases derived from acceptance criteria

### 3. Quality Checklist (Verify Before Saving)
- [ ] Definition is concise (one paragraph)
- [ ] Pain Points describe real user/business pain (not technical debt)
- [ ] Bright Points describe measurable improvements
- [ ] Current State vs Target State table has at least 2 rows
- [ ] At least 2 risks with impact, likelihood, and mitigation
- [ ] Success metrics match those in functional spec (consistent)
- [ ] Out of Scope matches functional spec (consistent)
- [ ] Assumptions section populated

### 4. Save and Present
- Save to `.stage/EPIC-DRAFT/epic.md`
- Present the full document to the user
- Ask: "Review the Epic document. Would you like to make any changes before I create it in GitHub Issues?"

## Rules
- Do NOT proceed until user approves the Epic document
- If user requests changes, update the file and re-present
- Keep consistency between functional spec and Epic -- do not introduce new requirements here
- Business language only -- zero technical details
