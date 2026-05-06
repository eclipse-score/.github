---
name: init-ui-ux
description: Create new UI/UX specifications by analyzing codebases, documenting design patterns, and establishing design guidelines. Use when a project needs a UI/UX specification document.
---

# Init UI/UX Skill

Create comprehensive UI/UX specifications to establish design guidelines and patterns for consistent interfaces.

## When to Use

Use this skill when:
- **Creating UI/UX specifications** - Project needs a new design specification document
- **Documenting design patterns** - Capture reusable UI patterns from existing code
- **Design system work** - Creating design system documentation from scratch
- **Before implementation** - When check-ui-ux skill reports missing specification

Don't use for:
- **Updating existing specs** - Modify the specification file directly or re-run this skill
- **Checking implementations** - Use check-ui-ux skill instead
- **Implementing UI components** - Use ui-ux skill instead
- Pure backend functionality
- API design (use api-docs skill)
- Architecture decisions (use adr skill)

## Process

### 1. Check for Existing UI/UX Specification

Look for UI/UX spec file in common locations:
- `./docs/ui-ux-spec.md`
- `./ui-ux-spec.md`

If it already exists, inform the user and ask if they want to:
- Update the existing specification (continue with this skill)
- Create a new version
- Cancel the operation

If proceeding with update or it doesn't exist, create/update in `./docs/ui-ux-spec.md`.

### 2. Analyze Current Codebase

#### 2.1. Extract Design System Information

Analyze the codebase to identify:

**Component Library:**
- UI framework (React, Vue, Svelte, Angular)
- Component library (Material-UI, Ant Design, Chakra UI, custom)
- UI components in `src/components/`, `components/`, etc.

**Styling Approach:**
- CSS framework (Tailwind, Bootstrap, custom CSS)
- CSS-in-JS (styled-components, emotion, CSS modules)
- Design tokens (colors, spacing, typography)

**Accessibility Tools:**
- `eslint-plugin-jsx-a11y`
- `axe-core`
- `react-aria`, `headlessui`, `radix-ui`

#### 2.2. Identify Existing Patterns

Document patterns found in code:

**Visual Design:**
- Color palette (primary, secondary, semantic colors)
- Typography scale (font families, sizes, weights)
- Spacing system (4px, 8px grid)
- Elevation/shadows
- Border radius values
- Breakpoints for responsive design

**Component Patterns:**
- Button variants (primary, secondary, ghost, danger)
- Form input styles and validation states
- Modal/dialog patterns
- Navigation patterns
- Card layouts
- Loading states and skeletons

**Interaction Design:**
- Hover/focus states
- Animation durations and easing
- Touch targets (minimum 44×44px)
- Keyboard navigation
- Loading and error states
- Success feedback patterns

### 3. Define Design Principles

Based on analysis and user input, document:

**Accessibility Standards:**
- WCAG level target (AA or AAA)
- Color contrast requirements (4.5:1 for text)
- Focus indicators
- Screen reader support
- Semantic HTML requirements
- ARIA patterns

**Responsive Behavior:**
- Mobile-first or desktop-first approach
- Breakpoint values (sm, md, lg, xl)
- Navigation changes (hamburger menu, desktop nav)
- Layout adaptations
- Typography scaling

**User Flows:**
For key user journeys:
- Authentication flow (login, signup, password reset)
- Main user tasks
- Error handling flows
- Empty states
- Loading states

### 4. Create Specification File

Create `docs/ui-ux-spec.md` with these sections:

**Required sections:**
- Design Principles
- Component Library
- Accessibility Guidelines
- Responsive Breakpoints
- Color Palette
- Typography Scale
- Spacing System
- Component Specifications

**Include:**
- Design decisions and rationale
- Accessibility requirements
- Responsive behavior specifications
- Links to design resources (Figma, style guide)

### 5. Generate Component Specifications

For components that need documentation, create detailed specs:

```markdown
## Component: LoginForm

### Purpose
Authenticates users via email/password.

### Visual Design
- Width: 400px max-width
- Padding: 24px
- Border radius: 8px
- Shadow: elevation-2
- Background: surface color

### Elements
1. **Heading**
   - Text: "Welcome back"
   - Typography: heading-lg (24px, semibold)
   - Color: text-primary

2. **Email Input**
   - Label: "Email address"
   - Type: email
   - Validation: Required, valid email format
   - Error message: "Please enter a valid email address"

3. **Password Input**
   - Label: "Password"
   - Type: password
   - Toggle visibility: Optional eye icon
   - Validation: Required, min 8 characters
   - Error message: "Password must be at least 8 characters"

4. **Submit Button**
   - Text: "Sign in"
   - Variant: primary
   - Width: full
   - Loading state: Spinner + "Signing in..."
   - Disabled state: Disabled when submitting

### States
- Default: Empty fields, button enabled
- Validation: Show errors on blur or submit
- Loading: Button shows spinner, fields disabled
- Error: Display error message above form
- Success: Redirect to dashboard

### Accessibility
- Form wrapped in `<form>` tag
- Labels properly associated with inputs
- Error messages linked via `aria-describedby`
- Focus order: email → password → button → link
- Submit on Enter key
- Screen reader announces errors

### Responsive
- Mobile: Full width with 16px side margins
- Tablet+: Centered, max-width 400px
```

## UI/UX Spec Template

Use this template when creating a new specification:

```markdown
# UI/UX Specification

## Design System

### Color Palette
- Primary: #[hex]
- Secondary: #[hex]
- Success: #[hex]
- Warning: #[hex]
- Error: #[hex]
- Text: #[hex]
- Background: #[hex]

### Typography
- Font family: [name]
- Scale: 12px, 14px, 16px, 20px, 24px, 32px, 48px
- Weights: 400 (regular), 500 (medium), 600 (semibold), 700 (bold)

### Spacing
- Base unit: 4px
- Scale: 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px

### Breakpoints
- sm: 640px
- md: 768px
- lg: 1024px
- xl: 1280px
- 2xl: 1536px

## Component Patterns

### Buttons
[Variants, sizes, states]

### Forms
[Input styles, validation, error handling]

### Navigation
[Header, sidebar, mobile menu]

### Modals
[Dialog patterns, animations]

## Accessibility Standards

- WCAG Level: AA
- Color contrast: 4.5:1 for text
- Focus indicators: Required
- Keyboard navigation: Full support
- Screen readers: ARIA labels required
- Semantic HTML: Enforced

## Responsive Design

- Approach: Mobile-first
- Breakpoint behavior: [describe]
- Navigation: [mobile vs desktop]
- Typography: [scaling rules]

## User Flows

### Authentication
[Login, signup, password reset flows]

### Main Tasks
[Key user journeys]

## Component Specifications

[Individual component specs]
```

## Best Practices

### Do:
- ✓ Analyze existing code before writing specs
- ✓ Extract actual design tokens from codebase
- ✓ Document rationale for design decisions
- ✓ Include accessibility requirements
- ✓ Specify responsive behavior
- ✓ Link to design resources (Figma, style guide)
- ✓ Ask users for input on design preferences
- ✓ Start with high-level patterns, then detail key components

### Don't:
- ✗ Create specs in isolation without codebase analysis
- ✗ Ignore existing patterns and conventions
- ✗ Document every minor implementation detail
- ✗ Focus only on visual design, ignore interaction patterns
- ✗ Skip accessibility considerations
- ✗ Create specifications without user input

## Example Workflow

**Scenario:** User asks "create a UI/UX specification for our project"

1. **Check for existing spec:** Look in common locations
2. **Analyze codebase:** Search for components, styling patterns, design tokens
3. **Extract patterns:** Document colors, typography, spacing, component variants
4. **Gather requirements:** Ask user about design preferences, accessibility needs
5. **Create specification:** Generate comprehensive spec following template
6. **Document components:** Create detailed specs for key components
7. **Save specification:** Write to `./docs/ui-ux-spec.md`
8. **Provide guidance:** Explain how to use with check-ui-ux skill for validation
