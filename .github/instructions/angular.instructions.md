---
applyTo: '**/*.ts'
---

# Angular / TypeScript Guidelines

## TypeScript
- Strict type checking enabled
- Prefer type inference when obvious
- Strictly avoid `any`; use `unknown` when uncertain
- Explicit return types on all public methods and getters
- Reuse extracted interfaces; replace `any` with concrete types or generics

## Angular Core
- Always use **standalone components** (do NOT set `standalone: true` -- it is default in Angular v20+)
- Use **signals** for state management
- Lazy loading for feature routes
- `changeDetection: ChangeDetectionStrategy.OnPush` on all components
- Use `input()` and `output()` functions instead of decorators
- Use `computed()` for derived state
- Host bindings inside `host` object of `@Component`/`@Directive` -- not `@HostBinding`/`@HostListener`
- `NgOptimizedImage` for all static images

## Templates
- Native control flow: `@if`, `@for`, `@switch` (not `*ngIf`, `*ngFor`)
- Async pipe for observables
- No arrow functions in templates
- No complex logic in templates
- Import pipes when used; use built-in pipes
- `trackBy` in large `@for` lists
- Do NOT use `ngClass`/`ngStyle` -- use `[class.x]` and `[style.prop]` bindings

## State Management
- Signals for local state
- `computed()` for derived state
- Pure, predictable state transformations
- Use `update` or `set` on signals, not `mutate`

## Services
- Single responsibility per service
- `providedIn: 'root'` for singletons
- `inject()` function instead of constructor injection
- Close all subscriptions on destroy via `takeUntil(onDestroy$)` or `take(1)`

## Forms
- Prefer Reactive Forms for typed/dynamic/testable forms
- Template-driven acceptable for simple static forms
- Don't set `required` attribute if `Validators.required` exists
- Centralize patching logic; avoid patching same control multiple places

## RxJS
- Suffix observables with `$`
- `takeUntil(this.onDestroy$)` or `take(1)` for cleanup
- `finalize()` / `try/finally` for loading flags
- Compose with `combineLatest`, `map` -- no nested subscribes
- Centralize store selections; reuse cached values

## Naming
- Semantic names: `ReviewMode` not `mode`
- Observable variables end with `$`
- Align property names with backend fields
- Consistent pluralization
- Data test IDs in kebab-case with module prefix

## Enums & Constants
- Replace hardcoded strings with enums
- Consolidate into central `models/enums` folder
- Use existing enums; don't create duplicates

## i18n
- `| translate` pipe and custom translation pipes
- Add translations across all language files simultaneously (EN, DE, FR, IT)

## Styling
- No inline styles; scoped BEM classes (`.coverage-table__header--highlight`)
- Remove redundant custom CSS when shared classes exist
- Consistent attribute ordering in templates

## Component Structure Order
Hosting / Inputs / Outputs / readonly props / private props / constructor / lifecycle hooks / public methods / private methods

## Accessibility
- Alt text on all images
- Must pass all AXE checks
- WCAG AA minimum: focus management, color contrast, ARIA attributes

## Anti-Patterns to Fix
- Magic strings -> enums
- Manual language branching -> translate pipes
- Nested subscribes -> RxJS operators
- Large monolithic methods -> split + early returns
- Template method calls with dynamic values -> precompute / pipes
- Missing unsubscribe -> `takeUntil`, `take(1)`, async pipe
- Duplicate `data-testid` -> enforce naming pattern
