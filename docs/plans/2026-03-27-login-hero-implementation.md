# LoginHero Component Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `LoginHero` component plus matching test coverage to display hero text and footer credit.

**Architecture:** Follow TDD: author Jest test first, then minimal component. Component lives under `frontend/components/auth`, test under `frontend/__tests__/components/auth`. Keep strings hard-coded.

**Tech Stack:** TypeScript, React, Jest, @testing-library/react, npm scripts.

---

### Task 1: Build LoginHero component and test

**Files:**
- Create: `frontend/__tests__/components/auth/LoginHero.test.tsx`
- Create: `frontend/components/auth/LoginHero.tsx`

**Step 1: Write the failing test**

```tsx
// frontend/__tests__/components/auth/LoginHero.test.tsx
import { render, screen } from '@testing-library/react'
import { LoginHero } from '@/components/auth/LoginHero'

describe('LoginHero', () => {
  it('shows hero copy and footer credit', () => {
    render(<LoginHero />)
    expect(screen.getByText(/Infrastructure Command Suite/i)).toBeInTheDocument()
    expect(screen.getByText(/Operational visibility for multi-region workloads/i)).toBeInTheDocument()
    expect(screen.getByText(/Made by Bagus Ganteng 😎/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npm test -- LoginHero.test.tsx`

Expected: FAIL (LoginHero component missing).

**Step 3: Write minimal implementation**

```tsx
// frontend/components/auth/LoginHero.tsx
export function LoginHero() {
  return (
    <section>
      <h2>Infrastructure Command Suite</h2>
      <p>Operational visibility for multi-region workloads.</p>
      <small>Made by Bagus Ganteng 😎</small>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- LoginHero.test.tsx`

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/components/auth/LoginHero.tsx frontend/__tests__/components/auth/LoginHero.test.tsx docs/plans/2026-03-27-login-hero-design.md docs/plans/2026-03-27-login-hero-implementation.md
git commit -m "feat: add login hero component"
```
