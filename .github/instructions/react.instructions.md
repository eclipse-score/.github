---
applyTo: '**/*.tsx,**/*.ts'
---

# React / CRA / TypeScript Guidelines

## TypeScript Safety

### Explicit Return Types on Service Functions
- All service and mock functions MUST declare an explicit return type.
- Never return a bare `null` for an object that properties will be accessed on downstream.
- When a function can return `null` OR an object with dynamic properties, use `any` for the object shape in the return type to prevent TypeScript narrowing to `never`.

```typescript
// BAD -- TypeScript infers return type as { user: null }
// After null-guard, 'user' narrows to 'never' -- every property access is a compile error
const getToken = () => ({ user: null });

// GOOD -- explicit return type prevents 'never' narrowing
const getToken = (): { user: any } => ({ user: null as any });
```

### Null Guards and Type Narrowing
- Always provide an explicit return type on any function whose return value flows into a null-guard check (`if (!x) return`).
- After narrowing away null/undefined, TypeScript must be able to resolve the remaining type to a concrete shape, not `never`.
- If the concrete shape is not yet known (e.g., dynamic API response), annotate as `any` rather than omitting the type.

---

## ESLint Compliance (CRA Build-Blocking)

Create React App (CRA / react-scripts) **treats ESLint errors as hard build failures**. Every new file must be ESLint-clean before being integrated.

### Rules to obey before committing any new file:
| Rule | What to check |
|------|--------------|
| `operator-linebreak` | `??`, `=`, `&&`, `\|\|` operators must be at the END of the line, not the start of the next |
| `implicit-arrow-linebreak` | Arrow function body must be on the SAME line as `=>`, or wrapped in `{}` braces |
| `react/jsx-curly-newline` | JSX `{expression}` — opening `{` and closing `}` must follow consistent newline rules |
| `semi-spacing` | Semicolons must be followed by a space (or newline); no adjacent import statements without whitespace |

### Pre-commit ESLint check
Run before every build:
```bash
npx eslint --max-warnings=0 src/path/to/new/file.tsx
```
If the project has persistent ESLint issues during scaffolding, add to `.env`:
```
DISABLE_ESLINT_PLUGIN=true
```
Remove this flag once all files are compliant.

---

## i18n Safety

### `returnObjects: true` is fragile — use with caution
- `t("key", { returnObjects: true })` expects the translation key to return an **array or object**.
- If the key is missing or returns a string/undefined, iterating the result causes a **silent runtime crash** (blank white page, no error boundary triggered).
- **Never** call `returnObjects: true` for data that hasn't been verified present in ALL language files.

### Safe pattern for new pages
Use inline data constants in the component file until translations are confirmed across all locales:

```typescript
// SAFE -- no runtime crash risk
const FAQ_ITEMS = [
  { question: "How do I reset my password?", answer: "Use the forgot password link." },
];

// RISKY until all locale files confirmed
const faqItems = t("contactSupport.faq", { returnObjects: true }) as FaqItem[];
```

### Adding translations
When translations ARE used, they must be added to **all** language files simultaneously (EN, DE, FR, IT, and any others the project supports) before the feature is merged.

---

## New Page / Component Safety

### First implementation: single self-contained file
When adding a brand-new page:
1. Implement it as a **single self-contained component file** — all data, sub-sections, and form logic inline.
2. Only split into sub-components once the page works end-to-end.
3. This prevents cascading failures caused by unverified sub-component dependencies.

### Sub-component dependency checklist
Before extracting sub-components:
- [ ] All i18n keys confirmed in every locale file
- [ ] All external form libraries (e.g., react-hook-form, yup) imported and tested
- [ ] All service imports resolve without TypeScript errors
- [ ] ESLint passes on every new file individually

---

## Form Libraries

- Prefer plain React `useState` for simple forms on new pages.
- Introduce `react-hook-form` + `yup` only when:
  - The form has 5+ fields, OR
  - Async validation is explicitly required
- Async validators in yup schemas can throw silently if the schema is misconfigured — always add a top-level try/catch or error boundary around form-heavy pages.

---

## Route Registration

When adding a new route in `AppRoutes.tsx` (or equivalent):
1. Verify the imported component path resolves to a real file before saving.
2. A bad import in the routes file will cause the **entire app** to fail to load.
3. Add the route only after the target component file exists and is ESLint-clean.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Risk | Correct Approach |
|---|---|---|
| Mock returning `null` without explicit type | TypeScript infers `never` after null-guard | Explicit return type with `any` |
| New file with ESLint violations | CRA build fails for entire app | Run ESLint on each file before integration |
| `t(key, { returnObjects: true })` for unverified keys | Silent runtime crash / blank page | Use inline data until translations verified |
| Multi-file page extraction before working baseline | Cascading import/render failures | Single-file first, extract after baseline works |
| Async yup validators without error boundary | Silent blank page on form render | Wrap form pages in error boundary |
