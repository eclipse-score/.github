---
agent: plan-epic-creation
tools: ['read', 'edit', 'search']
description: 'Collect feature idea, business domain context, and optional codebase reference. Save to .stage/EPIC-DRAFT/.'
---

Collect the inputs needed to create a business Epic.

## Tasks

### 1. Ask for the Feature Idea
- Ask the user: "Describe the feature or capability you want to build in 1-2 sentences."
- This is the seed for the entire Epic -- it does not need to be detailed yet.

### 2. Ask for Business Domain Context
- Ask the user: "Do you have a business context document? You can:
  - **Paste** the text directly into chat
  - **Point to a file** (provide path to a `.md` or `.txt` file in the workspace)
  - **Describe it verbally** if no document exists"
- Read the document/text and extract: business domain, key terms, stakeholders, existing processes.
- If no context document is provided, proceed with what the user described verbally.

### 3. Ask for Codebase (OPTIONAL)
- Ask: "Do you have a repository or codebase related to this feature? (Optional -- you can skip this)"
- If provided: note the repo path for later use by `@plan-tech-analysis`
- If skipped: proceed without. PO/BA does not need code access to define a business Epic.

### 4. Save Context
- Create folder: `.stage/EPIC-DRAFT/`
- Save to `.stage/EPIC-DRAFT/business-context.md`:
  - Feature idea (verbatim from user)
  - Business domain context (extracted from document or verbal description)
  - Repo path (if provided, otherwise "Not provided")
- Present the saved context to the user for confirmation.

## Rules
- Accept `.md` and `.txt` files only -- never PDF or .docx
- Do NOT ask technical questions -- this is a business context step
- If user provides a very detailed feature description, capture it all -- do not summarize or lose information
