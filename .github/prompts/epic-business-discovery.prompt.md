---
agent: plan-epic-creation
tools: ['read', 'edit']
description: 'Structured business discovery Q&A -- analyze context first, ask only about gaps, save discovery notes.'
---

Conduct business discovery to gather the information needed for a comprehensive Epic.

## Tasks

### 1. Analyze What You Already Know
- Read `.stage/EPIC-DRAFT/business-context.md`
- List internally what you KNOW from the context document:
  - Problem statement? Business value? Target users? Metrics? Constraints?
- List what you DON'T KNOW -- these are your gaps.
- If the context document answers everything → skip to Task 3 (save discovery notes).

### 2. Ask Gap-Only Questions (One at a Time)
Ask ONLY about gaps identified in Task 1. Organize questions into phases:

**Phase A — Why & Impact** (skip if already clear from context):
- Why is this feature important right now?
- What problem are users experiencing today?
- What happens if we DON'T build this?
- Who is asking for this? (sponsor, end-user complaint, compliance mandate)

**Phase B — Users & Scope** (skip if already clear):
- Which user roles will use this?
- Is the workflow manual, automatic, or both?
- Which markets / teams / environments are in scope?

**Phase C — Metrics & Success** (skip if already clear):
- Which business metrics will move? Suggest categories:
  - Automation: time saved, error reduction, throughput
  - Integration: data freshness, sync success rate
  - UI: task completion rate, user satisfaction
  - Compliance: audit pass rate, violation count
- What are the current baseline numbers?
- What are the target numbers after implementation?

**Phase D — Edge Cases & Constraints** (skip if already clear):
- How should errors be handled (from user perspective)?
- Any constraints? (compliance, performance, contracts, deadlines)

**Rules for questions:**
- Ask ONE question at a time, wait for response
- Skip phases where the context document already provides answers
- If user says "I'm not sure" → note as Open Question, move on
- Adapt follow-ups based on previous answers
- Stop when you have enough for a functional spec

### 3. Save Discovery Notes
- Save to `.stage/EPIC-DRAFT/business-discovery.md`:
  - Structured notes organized by: Why, Users, Scope, Metrics, Constraints
  - Open Questions (items the user couldn't answer)
  - Assumptions (things inferred from context)
- Present the saved notes to the user for confirmation.

## Rules
- NEVER ask questions that are already answered in the context document
- Do NOT ask technical questions -- this is business discovery
- If the context document is very comprehensive, it is valid to ask ZERO questions
- Maximum 8-10 questions total across all phases
