---
name: dr-expert
description: Use when documenting architectural decisions. Enforces the S-CORE-style DR format used in `docs/design_decisions/`.
inference_examples:
  - "Create a DR for this decision"
  - "Document why we chose this transport binding"
  - "Write a decision record for the middleware integration"
---

# DR Standards

**Trigger**: Request for architectural documentation.

### The Project DR Format
Always generate decision records using the S-CORE-style DR structure and store them in `docs/design_decisions/`.

```markdown
# DR-[Number]-[ShortTitle]: [Decision Title]

* **Date:** [YYYY-MM-DD]

```{dec_rec} [Decision Title]
:id: dec_rec__[domain]__[slug]
:status: [accepted / proposed / superseded / deprecated]
:context: [Area]
:decision: [Short decision summary]
```

---

## 1. Context / Problem
[What problem is being solved and why a decision is required.]

## 2. Requirements
1. [Constraint or requirement]
2. [Constraint or requirement]

## 3. Options Considered
### 3.1 [Chosen option]
**Pros:**
- [Benefit]

**Cons:**
- [Cost or risk]

### 3.2 [Rejected option]
**Pros:**
- [Benefit]

**Cons:**
- [Reason rejected]

## 4. Conclusion
- [Decision summary]
- [Key trade-off]
- [Follow-up if needed]
```

### Writing Rules
- **Conciseness**: Keep the record focused and reviewable.
- **Tone**: Pragmatic and technical.
- **Naming**: `DR-XXX-kebab-case-title.md`.
- **Location**: `docs/design_decisions/`.