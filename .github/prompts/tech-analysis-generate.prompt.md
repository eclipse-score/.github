---
agent: plan-tech-analysis
tools: ['read', 'edit', 'search']
description: 'Generate per-repo technical analysis using the skill template. One file per repo.'
---

Generate a comprehensive technical analysis document for the analyzed repository.

## Tasks

### 1. Read Inputs
- Read `.stage/EPIC-XXX/tech-analysis/{repo-name}-codebase-notes.md`
- Read `.github/skills/tech-analysis/analysis-template.md`
- Use Epic context summary from Step 1
- Use gap answers from Step 4 (if any)

### 2. Generate Technical Analysis
- Fill the template using ONLY information from:
  - Actual codebase analysis (codebase-notes)
  - Epic artifacts (functional-spec, epic.md)
  - User answers to gap questions
- Include Mermaid diagrams for:
  - Architecture overview (component relationships)
  - Current state workflow (sequence diagram)
  - Future state workflow (sequence diagram)
- Map coding guidelines detected to recommended patterns
- Reference similar implementations found in the codebase

### 3. Quality Checklist (Verify Before Saving)
- [ ] Goal ties to business value from Epic (not technical motivation)
- [ ] All affected modules identified with specific change descriptions
- [ ] At least 2 risks with impact, likelihood, and mitigation
- [ ] Mermaid diagrams render correctly (valid syntax)
- [ ] Dependencies are concrete (team names, service names, timeline)
- [ ] Open questions and assumptions sections populated
- [ ] Zero hardcoded framework references that don't match the actual repo
- [ ] Coding guidelines section reflects what was actually detected

### 4. Save and Present
- Save to `.stage/EPIC-XXX/tech-analysis/{repo-name}-analysis.md`
- Present the full document to the user
- Ask: "Review the technical analysis. Would you like to make any changes before I slice it into stories?"

## Rules
- ONE analysis file per repo -- do not create separate backend/frontend files
- Do NOT proceed until user approves the analysis
- If user requests changes, update the file and re-present
- Ground all recommendations in the actual codebase -- no theoretical advice
