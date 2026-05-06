---
name: ui-ux
description: Implement and verify UI components against existing UI/UX specifications. Use when creating UI components, reviewing implementations, or validating design compliance.
---

# UI/UX Skill

Build and verify UI/UX implementations against existing specifications to ensure consistent, accessible, and user-friendly interfaces.

## When to Use

Use this skill when:
- **Creating new UI components** - Implement following existing design specs and patterns
- **Reviewing implementations** - Verify existing code against UI/UX guidelines
- **Accessibility audit** - Check WCAG compliance against established standards
- **UI/UX issues reported** - Users report confusing flows or poor usability
- **Implementing design system components** - Build following existing design system specs
- **Code review** - Validate components match design specifications

Don't use for:
- **Creating or updating UI/UX specifications** - Use init-ui-ux skill instead
- Pure backend functionality
- API design (use api-docs skill)
- Architecture decisions (use adr skill)

## Process

### 1. Load Existing UI/UX Specification

**REQUIRED:** This skill requires an existing UI/UX specification file. Look for it in common locations:
- `./docs/ui-ux-spec.md`
- `./ui-ux-spec.md`

If no specification exists, use the `init-ui-ux` skill first to create one.

### 2. Verify Implementation Against Spec

When reviewing UI implementations:

#### 2.1. Visual Consistency Check

Compare implementation with spec:
- ✓ Correct colors from palette
- ✓ Typography matches scale
- ✓ Spacing uses system values
- ✓ Components follow design patterns
- ✓ Icons consistent with library

#### 2.2 User Experience Review

Evaluate usability:
- Clear call-to-actions
- Obvious navigation
- Helpful error messages
- Loading states prevent confusion
- Empty states guide users
- Success feedback confirms actions


### 3. Provide Actionable Feedback

When reviewing implementations:

**Good feedback:**
```
❌ The button lacks focus indicators (WCAG 2.4.7)
Fix: Add focus-visible:ring-2 focus-visible:ring-primary-500

✓ Correct fix:
<button className="... focus-visible:ring-2 focus-visible:ring-primary-500">
```

**Bad feedback:**
```
The button doesn't look accessible
```

## Best Practices

### Do:
- ✓ Always read the existing UI/UX spec file first
- ✓ Follow established design patterns and tokens
- ✓ Provide specific, actionable feedback
- ✓ Include code examples in recommendations
- ✓ Test with keyboard navigation
- ✓ Check color contrast ratios
- ✓ Verify responsive behavior at all breakpoints
- ✓ Reference spec sections in your feedback

### Don't:
- ✗ Implement without consulting the spec first
- ✗ Give vague feedback ("make it more accessible")
- ✗ Ignore existing design patterns
- ✗ Focus only on aesthetics, ignore usability
- ✗ Forget mobile/tablet viewports
- ✗ Skip accessibility checks
- ✗ Deviate from established component specifications

## Example Workflows

**Scenario 1:** User asks "create a login page"

1. **Load existing spec:** Read `./docs/ui-ux-spec.md`
2. **Extract patterns:** Find button styles, form patterns, auth flows from spec
3. **Implement following spec:**
   - Use specified button variants and form styles
   - Follow component patterns from specification
   - Include all required states and accessibility features
   - Match color palette and typography scale
4. **Provide implementation:** Code example following spec exactly
5. **Verify against spec:** Check implementation matches all requirements

**Scenario 2:** User asks "review the LoginForm component"

1. **Load existing spec:** Read `./docs/ui-ux-spec.md`
2. **Load component:** Find and read LoginForm component files
3. **Verify against spec:** Check visual design, accessibility, responsive behavior
4. **Generate report:** List issues with severity levels (critical → low)
5. **Provide fixes:** Actionable recommendations with code examples
