# Industrial Ops Glass UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a production-ready Industrial Ops Glass interface for the web app across Home, Jobs, and History with strong usability, accessibility, and reliability.

**Architecture:** Add a shared visual foundation (tokens + reusable UI primitives), then migrate each page to the new system while preserving API behavior. Implement robust state handling for loading/error/empty conditions and verify via focused UI tests. Finish with production-readiness checks and documentation updates.

**Tech Stack:** React + TypeScript, CSS variables, Vitest, Testing Library.

---

### Task 1: Create shared Industrial Ops Glass design foundation

**Files:**
- Create: `web/src/styles/ops-theme.css`
- Create: `web/src/components/ui/GlassPanel.tsx`
- Create: `web/src/components/ui/StatusPill.tsx`
- Create: `web/src/components/ui/OpsInput.tsx`
- Create: `web/src/components/ui/OpsButton.tsx`
- Test: `web/src/__tests__/status-pill.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import { StatusPill } from "../components/ui/StatusPill"

describe("StatusPill", () => {
  test("renders semantic status variant", () => {
    render(<StatusPill status="running" />)
    const el = screen.getByText(/running/i)
    expect(el).toHaveAttribute("data-status", "running")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm test -- status-pill.test.tsx`
Expected: FAIL because `StatusPill` does not exist.

**Step 3: Write minimal implementation**

```tsx
// web/src/components/ui/StatusPill.tsx
type Props = { status: "queued" | "running" | "completed" | "failed" | string }

export function StatusPill({ status }: Props) {
  return (
    <span className="ops-status-pill" data-status={status}>
      {status}
    </span>
  )
}
```

Add `ops-theme.css` token system:
- semantic colors
- spacing/radius/shadow variables
- glass surface styles
- base typography and reduced-motion behavior

**Step 4: Run test to verify it passes**

Run: `cd web && npm test -- status-pill.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add web/src/styles/ops-theme.css web/src/components/ui web/src/__tests__/status-pill.test.tsx
git commit -m "feat: add shared industrial ops glass design primitives"
```


### Task 2: Restyle Home page as command-center entrypoint

**Files:**
- Modify: `web/src/app/page.tsx`
- Test: `web/src/__tests__/home-page.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import HomePage from "../app/page"

describe("HomePage", () => {
  test("shows ops headline and quick actions", () => {
    render(<HomePage />)
    expect(screen.getByRole("heading", { name: /monitoring hub web/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /open jobs/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /view history/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm test -- home-page.test.tsx`
Expected: FAIL because quick-action links are missing.

**Step 3: Write minimal implementation**

Implement Home page with:
- hero heading + context text
- 3 KPI cards (`queued`, `runs today`, `last check`)
- quick links to `/jobs` and `/history`
- class names that use shared `ops-theme.css`

**Step 4: Run test to verify it passes**

Run: `cd web && npm test -- home-page.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add web/src/app/page.tsx web/src/__tests__/home-page.test.tsx
git commit -m "feat: redesign home page with command-center layout"
```


### Task 3: Redesign Jobs page with production form and status table

**Files:**
- Modify: `web/src/app/jobs/page.tsx`
- Test: `web/src/__tests__/jobs-page.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import JobsPage from "../app/jobs/page"

describe("JobsPage", () => {
  test("renders accessible manual run form and status table", () => {
    render(<JobsPage />)
    expect(screen.getByLabelText(/customer/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/check/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/profiles/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /run now/i })).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: /status/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm test -- jobs-page.test.tsx`
Expected: FAIL because labels/button text/layout are not implemented.

**Step 3: Write minimal implementation**

Implement Jobs page with:
- responsive two-column section (form + queue snapshot)
- accessible inputs (`id` + `htmlFor`)
- primary action button label `Run Now`
- status table using `StatusPill`
- empty/placeholder rows with clear semantics

**Step 4: Run test to verify it passes**

Run: `cd web && npm test -- jobs-page.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add web/src/app/jobs/page.tsx web/src/__tests__/jobs-page.test.tsx
git commit -m "feat: redesign jobs page with production-ready form and status table"
```


### Task 4: Upgrade History page for resilient state handling

**Files:**
- Modify: `web/src/app/history/page.tsx`
- Modify: `web/src/__tests__/history.test.tsx`
- Create: `web/src/__tests__/history-states.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen, waitFor } from "@testing-library/react"
import { describe, expect, test, vi } from "vitest"

import HistoryPage from "../app/history/page"

describe("HistoryPage states", () => {
  test("shows empty state when API returns no items", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      json: async () => ({ items: [] })
    } as Response)

    render(<HistoryPage />)
    await waitFor(() => expect(screen.getByText(/no runs yet/i)).toBeInTheDocument())
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm test -- history-states.test.tsx`
Expected: FAIL because empty-state UX is not implemented.

**Step 3: Write minimal implementation**

Enhance History page with:
- loading state
- error banner when fetch fails
- explicit empty state text (`No runs yet`)
- optional filter input (client-side search)
- status badge usage for each row/list item

**Step 4: Run test to verify it passes**

Run: `cd web && npm test -- history.test.tsx history-states.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add web/src/app/history/page.tsx web/src/__tests__/history.test.tsx web/src/__tests__/history-states.test.tsx
git commit -m "feat: improve history page states and resilience"
```


### Task 5: Apply production hardening (responsive + a11y + motion)

**Files:**
- Modify: `web/src/styles/ops-theme.css`
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/app/jobs/page.tsx`
- Modify: `web/src/app/history/page.tsx`
- Test: `web/src/__tests__/a11y-smoke.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"

import JobsPage from "../app/jobs/page"

describe("A11y smoke", () => {
  test("exposes main landmark and visible run action", () => {
    render(<JobsPage />)
    expect(screen.getByRole("main")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /run now/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm test -- a11y-smoke.test.tsx`
Expected: FAIL if landmark or semantics are incomplete.

**Step 3: Write minimal implementation**

Add/verify:
- semantic landmarks and focus-visible styles
- reduced-motion media query
- responsive breakpoints for mobile/desktop
- contrast-safe status and text colors

**Step 4: Run test to verify it passes**

Run: `cd web && npm test -- a11y-smoke.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add web/src/styles/ops-theme.css web/src/app/page.tsx web/src/app/jobs/page.tsx web/src/app/history/page.tsx web/src/__tests__/a11y-smoke.test.tsx
git commit -m "fix: harden web ui for accessibility responsiveness and motion"
```


### Task 6: Final verification and docs for production readiness

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Step 1: Run all web tests**

Run: `cd web && npm test`
Expected: PASS.

**Step 2: Run backend tests to ensure no regressions**

Run: `python -m pytest tests/ -v`
Expected: PASS.

**Step 3: Run Docker smoke**

Run: `docker compose -f infra/docker/docker-compose.yml up -d`
Expected: containers healthy.

**Step 4: Validate health endpoint and teardown**

Run: `curl http://localhost:8000/health && docker compose -f infra/docker/docker-compose.yml down`
Expected: health returns `{"status":"ok"}` then stack stops cleanly.

**Step 5: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: document production-ready industrial ops web ui"
```
