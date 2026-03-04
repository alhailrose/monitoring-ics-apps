# AWS Monitoring Hub Frontend Rebuild Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild `web/` frontend to support synchronous monitoring API with 7 production pages and complete user flows.

**Architecture:** Replace legacy `/jobs` queue UI with route-based SPA pages for checks, customers, profiles, and history. Centralize API contracts and shared UI components, then connect each page directly to `/api/v1` endpoints with resilient loading/error/copy UX.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, CSS (existing ops theme)

---

### Task 1: Prepare type-safe API layer

**Files:**
- Create: `web/src/types/api.ts`
- Create: `web/src/api/client.ts`
- Create: `web/src/api/customers.ts`
- Create: `web/src/api/checks.ts`
- Create: `web/src/api/history.ts`
- Create: `web/src/api/profiles.ts`

**Step 1: Write the failing test**
- Add API helper tests asserting error extraction and query param building in:
  - `web/src/__tests__/api-client.test.ts`

**Step 2: Run test to verify it fails**
Run: `npm test -- src/__tests__/api-client.test.ts`
Expected: FAIL because API modules do not exist.

**Step 3: Write minimal implementation**
- Implement fetch wrapper with JSON parsing and backend `detail` handling.
- Implement typed methods for all endpoints.

**Step 4: Run test to verify it passes**
Run: `npm test -- src/__tests__/api-client.test.ts`
Expected: PASS.

### Task 2: Replace shell routing + navigation

**Files:**
- Modify: `web/src/app-shell.tsx`
- Modify: `web/src/main.tsx`
- Test: `web/src/__tests__/app-shell.test.tsx`

**Step 1: Write the failing test**
- Update route resolver tests for 7 routes and fallback behavior.

**Step 2: Run test to verify it fails**
Run: `npm test -- src/__tests__/app-shell.test.tsx`
Expected: FAIL because resolver still only supports home/jobs/history.

**Step 3: Write minimal implementation**
- Build route map + sidebar navigation for all required pages.

**Step 4: Run test to verify it passes**
Run: `npm test -- src/__tests__/app-shell.test.tsx`
Expected: PASS.

### Task 3: Build shared domain components

**Files:**
- Create: `web/src/components/common/StatusBadge.tsx`
- Create: `web/src/components/common/CopyableOutput.tsx`
- Create: `web/src/components/common/LoadingState.tsx`
- Create: `web/src/components/common/ToastHost.tsx`
- Modify: `web/src/styles/ops-theme.css`
- Test: `web/src/__tests__/status-badge.test.tsx`

**Step 1: Write the failing test**
- Add status-to-class and label rendering tests.

**Step 2: Run test to verify it fails**
Run: `npm test -- src/__tests__/status-badge.test.tsx`
Expected: FAIL because component does not exist.

**Step 3: Write minimal implementation**
- Implement status badges and copyable text blocks with copy action.

**Step 4: Run test to verify it passes**
Run: `npm test -- src/__tests__/status-badge.test.tsx`
Expected: PASS.

### Task 4: Implement Home + Check pages

**Files:**
- Create: `web/src/app/checks-single/page.tsx`
- Create: `web/src/app/checks-all/page.tsx`
- Create: `web/src/app/checks-arbel/page.tsx`
- Modify: `web/src/app/page.tsx`
- Test: `web/src/__tests__/home-page.test.tsx`
- Test: `web/src/__tests__/checks-single.test.tsx`

**Step 1: Write the failing test**
- Home: verify nav cards for all sections.
- Single page: verify payload and output rendering.

**Step 2: Run test to verify it fails**
Run: `npm test -- src/__tests__/home-page.test.tsx src/__tests__/checks-single.test.tsx`
Expected: FAIL because routes/components missing.

**Step 3: Write minimal implementation**
- Build check execution forms and loading/error/result states.

**Step 4: Run test to verify it passes**
Run: `npm test -- src/__tests__/home-page.test.tsx src/__tests__/checks-single.test.tsx`
Expected: PASS.

### Task 5: Implement Customer Management + Profiles

**Files:**
- Create: `web/src/app/customers/page.tsx`
- Create: `web/src/app/profiles/page.tsx`
- Test: `web/src/__tests__/customers-page.test.tsx`
- Test: `web/src/__tests__/profiles-page.test.tsx`

**Step 1: Write the failing test**
- Customer page: create customer + add account flow.
- Profiles page: scan + unmapped quick-add interaction.

**Step 2: Run test to verify it fails**
Run: `npm test -- src/__tests__/customers-page.test.tsx src/__tests__/profiles-page.test.tsx`
Expected: FAIL due missing pages.

**Step 3: Write minimal implementation**
- CRUD forms with refresh-on-mutation.
- Profile mapping presentation and quick actions.

**Step 4: Run test to verify it passes**
Run: `npm test -- src/__tests__/customers-page.test.tsx src/__tests__/profiles-page.test.tsx`
Expected: PASS.

### Task 6: Implement History list + detail view

**Files:**
- Create: `web/src/app/history/page.tsx` (replace existing)
- Test: `web/src/__tests__/history-page.test.tsx`

**Step 1: Write the failing test**
- Query filter/pagination request and detail fetch on row click.

**Step 2: Run test to verify it fails**
Run: `npm test -- src/__tests__/history-page.test.tsx`
Expected: FAIL due page behavior mismatch.

**Step 3: Write minimal implementation**
- Filter controls, list table, pagination, detail drawer with copyable outputs.

**Step 4: Run test to verify it passes**
Run: `npm test -- src/__tests__/history-page.test.tsx`
Expected: PASS.

### Task 7: Cleanup old queue artifacts + full verification

**Files:**
- Delete/replace obsolete tests tied to `/jobs` async queue.
- Verify all changed `web/src/**` and `web/src/__tests__/**` files.

**Step 1: Run full test suite**
Run: `npm test`
Expected: PASS.

**Step 2: Run build verification**
Run: `npm run build`
Expected: PASS.

**Step 3: Review changed files**
Run: `git status --short web docs/plans`
Expected: only intended rebuild and plan/design docs changed.
