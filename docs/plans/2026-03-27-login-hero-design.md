## LoginHero Component Design

### Context Exploration
- Reviewed existing `frontend/components` tree to confirm no `LoginHero` yet.
- Observed auth UI uses plain React components without heavy styling hooks, so new component can follow that pattern.

### Clarifications
- Copy should remain hard-coded for now; configurability to be considered later.

### Approaches Considered
1. Explicit JSX elements per line (recommended): simple, readable, easy to test and adjust individually.
2. Array-based render loop: adds indirection without immediate benefit.

Recommendation: Option 1 for clarity and alignment with current scope.

### Design Sections
**Structure**
- `LoginHero` exports a function returning a `section` wrapper.
- Inside: `h2` for “Infrastructure Command Suite”, `p` for “Operational visibility…”, and `small` (or `footer` tag) for “Made by Bagus Ganteng 😎”.
- No props, state, or context usage.

**Testing**
- Jest + Testing Library test renders component and asserts all three strings are present via `getByText`.

**Future Considerations**
- Wrapper can gain classes or props later without breaking this minimal layout.
