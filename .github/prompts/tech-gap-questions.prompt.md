---
agent: plan-tech-analysis
tools: ['read', 'search']
description: 'List knowns vs unknowns from Epic + codebase analysis. Ask ONLY about gaps. Skip if no gaps.'
---

Identify information gaps and ask targeted questions to resolve them.

## Tasks

### 1. List What You KNOW
From the Epic context (Step 1) and codebase analysis (Step 3), list internally:
- Business requirements understood ✅
- Tech stack identified ✅
- Architecture patterns detected ✅
- Integration points mapped ✅
- Similar implementations found ✅
- Coding guidelines scanned ✅

### 2. List What You DON'T KNOW (Gaps)
Identify unknowns that would prevent a complete technical analysis:
- Scope boundaries unclear? (e.g., which modules are in/out)
- Technical approach ambiguous? (e.g., sync vs async, new service vs extend existing)
- NFRs missing? (e.g., performance targets, scalability, security requirements)
- Dependency sequencing unclear? (e.g., which service must be built first)
- External system behavior unknown? (e.g., third-party API contract)

### 3. Decision: Ask or Skip

**If NO gaps identified:**
- Inform the user: "I have enough information from the Epic and codebase analysis to proceed. No clarification questions needed."
- Skip to the next step (tech-analysis-generate)

**If gaps exist:**
- Ask ONE question at a time
- Provide lettered options: (a), (b), (c), (d)
- Mark the recommended option with **[Recommended]** based on what the codebase suggests
- Include a code reference to justify the recommendation:
  > "Based on how `path/to/similar/file.ext` handles this, I recommend option (b)."
- Wait for the user's response before asking the next question
- After each answer, re-evaluate: do remaining gaps still need answers?
- Stop when you have enough information for a complete analysis

### 4. Fold Answers into Analysis
- Incorporate all answers into your working context for the next step
- Do NOT save a separate Q&A file -- answers feed directly into the analysis

## Rules
- NEVER ask questions that are already answered by the Epic artifacts or codebase analysis
- NEVER ask a fixed list of questions -- only gap-driven questions
- Maximum 5 questions total -- if you need more, the Epic is underspecified (suggest going back to `@plan-epic-creation`)
- If user says "I'm not sure" → note as Open Question in the analysis, move on
