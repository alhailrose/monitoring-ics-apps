# Frontend Development Plan (Living)

This is the main living plan for frontend evolution.

- Use this file as the single source of truth for phase status.
- Update checklist items before every commit.
- Run unit tests after every task completion — a phase is not closeable with failing tests.
- API contract reference: `docs/api/frontend-contract-v1.md`
- Backend plan reference: `docs/development/backend-development-plan.md`

## Scope and constraints

- Framework: Next.js 16 (App Router) + TypeScript + Tailwind CSS v4 + shadcn/ui
- Location: `frontend/` directory
- API base: `http://localhost:8000/api/v1` (configurable via `NEXT_PUBLIC_API_URL`)
- Auth mechanism: JWT stored in **httpOnly cookie** — server sets cookie on `/auth/login`, middleware reads it for route protection. No `localStorage` token storage.
- Role model: `super_user` (full access) and `user` (read-only + execute). UI enforces role-based visibility.
- Tests: Jest + `@testing-library/react` via `next/jest` preset. Run `npm test` after every task. A phase cannot be marked complete with failing tests.
- Shadcn install: `npx shadcn@latest add <component>` from within the `frontend/` directory.

## Shadcn blocks and components reference

| Phase use | shadcn item | Install command |
|---|---|---|
| Auth — login page | `login-01` block | `npx shadcn@latest add login-01` |
| Layout — sidebar | `sidebar-07` block | `npx shadcn@latest add sidebar-07` |
| Layout — dashboard shell | `dashboard-01` block | `npx shadcn@latest add dashboard-01` |
| Forms | `form`, `input`, `label` | `npx shadcn@latest add form input label` |
| Feedback | `sonner`, `alert`, `badge` | `npx shadcn@latest add sonner alert badge` |
| Data display | `table`, `card`, `skeleton` | `npx shadcn@latest add table card skeleton` |
| Navigation | `breadcrumb`, `separator` | `npx shadcn@latest add breadcrumb separator` |
| User menu | `avatar`, `dropdown-menu` | `npx shadcn@latest add avatar dropdown-menu` |
| Dialogs | `dialog`, `sheet` | `npx shadcn@latest add dialog sheet` |
| Status | `spinner`, `progress` | `npx shadcn@latest add spinner progress` |
| Select/filter | `select`, `combobox` | `npx shadcn@latest add select combobox` |
| Charts | `chart` | `npx shadcn@latest add chart` |

## Phase overview

| Phase | Goal | Status |
|---|---|---|
| 0 | Project base: test infra, API client, env config, shared component library | planned |
| 1 | Auth flow: login page, session cookie, middleware, auth context | planned |
| 2 | App shell: sidebar layout, user menu, route structure | planned |
| 3 | Dashboard page: summary widgets, run stats, findings overview | planned |
| 4 | Check execution: Specific Check (single mode) + Bundled Check (all/arbel mode) | done (→ Phase 8) |
| 5 | Customers management: list, create/edit/delete customer & account, role-aware UI | planned |
| 6 | History page: run log, per-run detail, auth error display | planned |
| 7 | Findings page: paginated findings, severity + check filter | planned |
| 8 | Metrics page: metric samples, status + check filter | planned |
| 9 | Role-aware UI: super_user admin forms (create/edit/delete customer) | planned |
| 10 | Customer report_mode & label: per-customer report format (summary/detailed) + label tag | done |
| 11 | Check output improvements: concise format_report, copy-to-clipboard on ResultsTable | done |

---

## Detailed checklist

### Phase 0 — Project base infrastructure

#### Design overview

Before writing any feature code, establish the testing framework, the API client, and environment config. Every subsequent phase depends on these primitives. This phase produces no visible UI — it is pure plumbing.

**Key decisions:**
- Vitest + @testing-library/react is the test stack (not Jest — it integrates natively with the Vite/Next setup)
- API client is a thin typed wrapper around `fetch` — no external library dependency
- Environment config: `NEXT_PUBLIC_API_URL` for the backend base URL

#### 0A — Test infrastructure

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Install Jest and testing-library | Run `npm install -D jest jest-environment-jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom @types/jest` | Test dependencies are present in `devDependencies` | Planned |
| Add `jest.config.ts` | Create `frontend/jest.config.ts` using the `next/jest` preset: `const createJestConfig = nextJest({ dir: './' })` with `testEnvironment: 'jsdom'` and `setupFilesAfterFramework: ['<rootDir>/jest.setup.ts']`. The preset handles SWC transforms, path alias `@/`, CSS modules, and `next/navigation`/`next/headers` mocks automatically. | Jest resolves imports identically to Next.js with zero manual transform config | Planned |
| Add test setup file | Create `frontend/jest.setup.ts` that imports `@testing-library/jest-dom` | All jest-dom matchers (`.toBeInTheDocument()`, `.toHaveTextContent()`, etc.) are available in all tests | Planned |
| Add test scripts to `package.json` | Add `"test": "jest --passWithNoTests"` and `"test:watch": "jest --watch"` to scripts | `npm test` runs all tests once; `npm run test:watch` runs in watch mode | Planned |
| Add smoke test | Create `frontend/__tests__/smoke.test.ts` with a trivially true assertion | `npm test` passes green from the start | Planned |
| Phase closure | Close Phase 0A after `npm test` passes | Test infra is confirmed working | Planned |

#### 0B — API client

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `lib/api/client.ts` | Typed fetch wrapper: `apiFetch(path, options)` that reads `NEXT_PUBLIC_API_URL`, attaches `Content-Type: application/json`, and throws a typed `ApiError` on non-2xx responses. No auth header logic here — that is handled server-side via cookie. | All API calls go through one consistent client | Planned |
| Add `ApiError` type | Extend `lib/api/client.ts` with `class ApiError extends Error { status: number; body: unknown }`. On 401, set a flag `isUnauthorized: true` for upstream handling. | API errors are typed and distinguishable by callers | Planned |
| Create typed API modules | Create `lib/api/auth.ts`, `lib/api/customers.ts`, `lib/api/history.ts`, `lib/api/findings.ts`, `lib/api/metrics.ts`, `lib/api/dashboard.ts` — each exporting typed functions wrapping the contract endpoints from `docs/api/frontend-contract-v1.md` | Every contract endpoint has a typed, named function | Planned |
| Unit test `apiFetch` | Test success path, 4xx error path, and 401 path using `jest.spyOn(global, 'fetch').mockResolvedValue(...)`. Assert `ApiError` is thrown with correct status. | Client error handling is unit-tested before any feature depends on it | Planned |
| Phase closure | Close Phase 0B after API client tests pass | API client is confirmed working | Planned |

#### 0C — Environment and types

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Add `.env.local.example` | Add `frontend/.env.local.example` with `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` | New devs know what env vars to set | Planned |
| Create shared type definitions | Create `lib/types/api.ts` with TypeScript interfaces mirroring the contract: `User`, `Customer`, `Account`, `CheckRun`, `CheckResult`, `Finding`, `MetricSample`, `DashboardSummary`, `TokenResponse` | All API response shapes are typed centrally | Planned |
| Phase closure | Close Phase 0C after types compile cleanly (`npm run typecheck`) | Base types are in place | Planned |

#### 0D — Shared component library

##### Design overview

All reusable UI primitives are built here — **before any page phase starts**. Every feature phase (1–9) imports from `components/common/` instead of defining its own version. This prevents badge/table/skeleton logic from being copied page-to-page.

**Rule:** If a component is used by more than one page or section, it lives in `components/common/`. Page-specific wrappers are allowed, but the core rendering logic must be shared.

Install all required shadcn primitives upfront:

```bash
npx shadcn@latest add badge table skeleton card alert tooltip select combobox spinner progress separator
```

| Task | Description | Props / variants | Expected Outcome | Status |
|---|---|---|---|---|
| `StatusBadge` | `components/common/StatusBadge.tsx` — renders a colored pill for check result statuses. | `status: 'ok' \| 'warn' \| 'error' \| 'alarm' \| 'no_data'`. Color map: ok→green-600, warn→yellow-500, error→red-600, alarm→red-500, no_data→slate-400. Uses shadcn `Badge` as base. | Used by History, Dashboard, and Check Results — never re-implemented | Planned |
| `SeverityBadge` | `components/common/SeverityBadge.tsx` — renders a colored pill for finding severity levels. | `severity: 'CRITICAL' \| 'HIGH' \| 'MEDIUM' \| 'LOW' \| 'INFO' \| 'ALARM'`. Color map: CRITICAL→red-700, HIGH→orange-500, MEDIUM→yellow-500, LOW→blue-400, INFO→slate-400, ALARM→red-500. | Used by Findings page and Dashboard findings widget — never re-implemented | Planned |
| `AuthModeBadge` | `components/common/AuthModeBadge.tsx` — renders a colored pill for AWS auth modes. | `mode: 'assume_role' \| 'sso' \| 'aws_login' \| 'access_key'`. Color map: assume_role→emerald-600, sso→sky-500, aws_login→slate-400, access_key→amber-500. | Used by Customers page and Account forms | Planned |
| `AuthErrorBadge` | `components/common/AuthErrorBadge.tsx` — targeted badge for `error_class` values from check results. | `errorClass: 'sso_expired' \| 'assume_role_failed' \| 'invalid_credentials' \| 'no_config' \| null`. Shows label + optional `loginCommand` string in a `Tooltip`. | Used by History detail, Check Results display — never re-implemented | Planned |
| `SessionStatusBadge` | `components/common/SessionStatusBadge.tsx` — pill for AWS session health status. | `status: 'ok' \| 'expired' \| 'no_config' \| 'error'`. On `expired` + `loginCommand` provided: wraps in a `Tooltip` showing the command. | Used by Customers page account rows | Planned |
| `PaginatedTable` | `components/common/PaginatedTable.tsx` — generic table with pagination controls. | `columns: ColumnDef<T>[]`, `data: T[]`, `total: number`, `page: number`, `pageSize: number`, `onPageChange: (page: number) => void`. Renders shadcn `Table` + `Pagination`. | Used by History, Findings, Metrics — no per-page table duplication | Planned |
| `LoadingRows` | `components/common/LoadingRows.tsx` — skeleton placeholder for table loading state. | `rows?: number` (default 5), `cols?: number` (default 4). Renders shadcn `Skeleton` cells at the correct table dimensions. | Used by every page that fetches a list — consistent loading experience | Planned |
| `EmptyState` | `components/common/EmptyState.tsx` — full-width empty state for list pages. | `icon?: ReactNode`, `title: string`, `description?: string`, `action?: ReactNode`. | Used by all list pages when no data returned | Planned |
| `PageHeader` | `components/common/PageHeader.tsx` — top-of-page title row with breadcrumb. | `title: string`, `description?: string`, `actions?: ReactNode`. Renders shadcn `Breadcrumb` + `Separator`. | Used by all dashboard pages — consistent page header across the app | Planned |
| `CustomerSelector` | `components/common/CustomerSelector.tsx` — shadcn `Select` populated from `GET /customers`. Updates `customer_id` search param on change via `router.replace`. | `customerId: string`, `customers: Customer[]`. | Used by Dashboard, History, Findings, Metrics — one selector, not four | Planned |
| `FilterBar` | `components/common/FilterBar.tsx` — horizontal row of filter controls with a reset button. | `children: ReactNode` (accepts any filter inputs), `onReset: () => void`. | Used by Findings and Metrics filter rows — consistent layout | Planned |
| `ConfirmDialog` | `components/common/ConfirmDialog.tsx` — generic confirmation dialog for destructive actions. | `title: string`, `description: string`, `onConfirm: () => void`, `onCancel: () => void`, `isPending?: boolean`. Uses shadcn `Dialog`. | Used by delete customer/account actions — one dialog, not per-entity | Planned |
| `InlineCode` | `components/common/InlineCode.tsx` — monospace inline code span for CLI commands. | `children: string`. Styled with JetBrains Mono, a copy-to-clipboard icon button. | Used in `AuthErrorBadge` and `SessionStatusBadge` for `login_command` display | Planned |
| Unit test all shared components | One test file per component in `__tests__/components/common/`. Test: correct variant renders correct color/text, edge cases (null/undefined props), snapshot where stable. | All shared components are tested before any feature phase uses them | Planned |
| Phase closure | Close Phase 0D after all shared components pass tests and `npm run typecheck` is clean | Shared component library is ready for all feature phases | Planned |

---

### Phase 1 — Auth flow

#### Design overview

Phase 1 implements the full login flow that the backend Phase 5 makes available. The approach mirrors the Next.js official auth guide: the backend issues a JWT, the server-side login action stores it in an `httpOnly` cookie, and the Next.js middleware reads the cookie to protect routes.

**Auth flow summary:**
1. User submits `/login` form
2. Next.js Server Action calls `POST /auth/login` on the backend
3. On success: backend returns `{ access_token, expires_at }` → Server Action sets `httpOnly` cookie `access_token` → redirect to `/dashboard`
4. On failure: Server Action returns an error message → login form shows it
5. Every protected page's API calls include `Authorization: Bearer <token>` (read from cookie in Server Components / API route layer)
6. If any API response returns 401: clear cookie → redirect to `/login`
7. Next.js middleware reads the cookie on every request to protected routes and redirects to `/login` if missing/expired

**shadcn block:** `login-01` — installed as `components/login-form.tsx`. Use this as the structural base for the login page. Customise to match the ops aesthetic (dark industrial theme, monospace inputs).

**Token storage decision (documented):** httpOnly cookie set by the Next.js server layer (not by the browser directly from the backend response). This eliminates XSS risk for token storage. CSRF is mitigated by SameSite=Lax and by the Server Action flow.

#### 1A — Install components

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Install shadcn login block | Run `npx shadcn@latest add login-01` from `frontend/` | `login-01` block files are scaffolded under `components/` | Planned |
| Install form primitives | Run `npx shadcn@latest add form input label button card sonner` | Form and feedback components are available | Planned |

#### 1B — Session utilities

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `lib/session.ts` | Server-only module: `setSessionCookie(token: string, expiresAt: string)` and `deleteSessionCookie()` using Next.js `cookies()` API. Cookie config: `httpOnly: true`, `secure: process.env.NODE_ENV === 'production'`, `sameSite: 'lax'`, `path: '/'`. | JWT is stored and removed via a single server-only utility | Planned |
| Create `lib/auth.ts` | Server-only module: `getSession()` reads the `access_token` cookie and returns the decoded payload (sub, username, role, exp) or `null`. Use `jose` (`npm install jose`) for JWT verification with `JWT_SECRET` env var. | Every server component and Server Action can call `getSession()` to get the current user | Planned |
| Add `JWT_SECRET` to env example | Add `JWT_SECRET=your-secret-here` to `.env.local.example` | Secret key is documented for local dev setup | Planned |
| Unit test `getSession` | Test: valid token returns payload, expired token returns null, missing cookie returns null. Use `jest.mock('next/headers', ...)` to mock the cookies API — `next/jest` preset sets this up automatically. | Session reading logic is covered by tests | Planned |

#### 1C — Login page

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `app/(auth)/login/page.tsx` | Login page using the `login-01` shadcn block as structural base. Render a Server Component wrapper containing the `LoginForm` client component. If already authenticated (cookie present), redirect to `/dashboard`. | `/login` route renders the login form | Planned |
| Create `app/(auth)/login/actions.ts` | Server Action `loginAction(formData)`: extract username/password → call `lib/api/auth.ts:login()` → on success call `setSessionCookie()` and `redirect('/dashboard')` → on failure return `{ error: 'Invalid username or password' }`. Never leak which field was wrong. | Login logic is encapsulated in a typed Server Action | Planned |
| Create `components/auth/LoginForm.tsx` | Client component: controlled form with username and password fields (shadcn `Input` + `Label`), submit `Button`, and error `Alert`. Calls `loginAction` via `useActionState`. Shows `Spinner` while pending. | Login form is interactive and shows feedback | Planned |
| Unit test `LoginForm` | Test: renders fields, submit calls action, error message appears on failure, spinner shows during pending state. Mock `loginAction` with `jest.fn()`. | Login form rendering and interaction are covered | Planned |

#### 1D — Middleware (route protection)

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `middleware.ts` | Next.js middleware at `frontend/middleware.ts`. Protected routes: all `/dashboard/*`. Public routes: `/login`, `/`. Logic: read `access_token` cookie → if missing/invalid on protected route → redirect to `/login`. If valid and on `/login` → redirect to `/dashboard`. | All protected routes redirect to `/login` when unauthenticated | Planned |
| Add matcher config | Export `config.matcher` that excludes `_next/static`, `_next/image`, `*.png`, `*.ico`, `*.svg`, `/api/*` from middleware. | Middleware only runs on page routes, not static assets | Planned |
| Unit test middleware | Test: unauthenticated request to `/dashboard` redirects to `/login`. Authenticated request to `/login` redirects to `/dashboard`. Authenticated request to `/dashboard` passes through. Mock `NextRequest` and cookie parsing. | Middleware routing logic is covered by tests | Planned |

#### 1E — Auth context

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `components/providers/AuthProvider.tsx` | Client-side React context: `AuthContext` holds `{ user: User \| null, isLoading: boolean }`. On mount, calls `GET /auth/me` via the API client. Stores result in state. Exposes `useAuth()` hook. | All client components can read the current user and role | Planned |
| Create `components/auth/LogoutButton.tsx` | Client component that calls a Server Action `logoutAction()` which runs `deleteSessionCookie()` then `redirect('/login')`. | Users can log out cleanly | Planned |
| Unit test `AuthProvider` | Test: fetches `/auth/me` on mount, exposes `user` in context, handles 401 by setting `user: null`. | Auth context is covered by tests | Planned |
| Handle global 401 | In `lib/api/client.ts`, when `ApiError.isUnauthorized` is true, import and call a `clearAuthAndRedirect()` client-side helper that clears state and does `router.push('/login')`. Use a module-level event emitter or a React context listener to avoid circular deps. | Expired sessions globally redirect to login without confusing error states | Planned |
| Phase closure | Close Phase 1 after login flow, middleware, auth context, and logout work end-to-end with tests passing | Phase 1 is officially complete | Planned |

---

### Phase 2 — App shell

#### Design overview

Implement the main layout that all authenticated pages share: a collapsible sidebar, a top header with user menu, and a content area. Use the `sidebar-07` shadcn block (collapsible to icons) as the structural starting point.

**Aesthetic direction:** Industrial ops glass — dark charcoal base (`#0f1117`), subtle grid lines, cyan accent (`#00d9ff`), monospace typeface for data values (`JetBrains Mono`), clean sans-serif for UI text (`IBM Plex Sans`). This is a monitoring dashboard — it should feel like a control room, not a SaaS landing page.

**shadcn block files already installed:**
- `components/app-sidebar.tsx` — sidebar shell (from `sidebar-07`)
- `components/nav-main.tsx` — main nav links
- `components/nav-user.tsx` — user menu at sidebar bottom
- `components/nav-projects.tsx` — secondary nav (repurpose or remove)
- `components/team-switcher.tsx` — repurpose as customer/product switcher or remove

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `app/(dashboard)/layout.tsx` | Server layout: call `getSession()` → if null redirect to `/login`. Render `<SidebarProvider>` wrapping `<AppSidebar>` and `<main>` content area. Pass user from session to layout. | All dashboard routes share the sidebar shell | Planned |
| Customise `components/app-sidebar.tsx` | Update the existing `app-sidebar.tsx` block. Nav items: Dashboard, Customers, History, Findings, Metrics. Active route highlighting via `usePathname()`. Logo / product name at top. Collapsed to icons at `lg` breakpoint. | Main navigation works across all dashboard pages | Planned |
| Create `components/layout/UserMenu.tsx` | Top-right avatar + dropdown: show username and role badge, logout button. Uses `Avatar`, `DropdownMenu` shadcn components. Role badge: `super_user` → amber, `user` → slate. | User can see their identity and log out from any page | Planned |
| Unit test `AppSidebar` | Test: all nav links render, active route is highlighted, user menu shows username. | Sidebar rendering is covered by tests | Planned |
| Phase closure | Close Phase 2 after layout renders with working nav and user menu | Phase 2 is officially complete | Planned |

---

### Phase 3 — Dashboard page

#### Design overview

The main entry page after login. Uses `GET /dashboard/summary?customer_id=<id>&window_hours=24`. Show stat cards (runs, findings, results by status) and a customer selector.

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Install chart component | Run `npx shadcn@latest add chart` | Chart component available (all other primitives already installed in Phase 0D) | Planned |
| Create `app/(dashboard)/dashboard/page.tsx` | Server Component: read `customer_id` from search params, call `getDashboardSummary()`, pass data to client components. Default: first customer. | Dashboard page is server-rendered with summary data | Planned |
| Create `components/dashboard/StatCards.tsx` | Render 4 stat cards: Total Runs, Results (using `StatusBadge` per status), Findings by severity (using `SeverityBadge`), Metrics by status. Uses shadcn `Card`. | Key metrics are visible at a glance | Planned |
| Wire `CustomerSelector` into dashboard | Render `<CustomerSelector>` from `components/common/` at the top of the page. On change updates search param. | Customer switching reuses the shared selector | Planned |
| Create `components/dashboard/TopChecksTable.tsx` | Simple table of top checks. Uses `PaginatedTable` from `components/common/` with a small `pageSize`. Shows `LoadingRows` while fetching. | Recent check activity is visible with consistent loading state | Planned |
| Unit test dashboard components | Test: `StatCards` renders correct badge variants from mock data, `TopChecksTable` renders rows and shows `EmptyState` when empty. | Dashboard components are covered | Planned |
| Phase closure | Close Phase 3 after dashboard page is functional with live data | Phase 3 is officially complete | Planned |

---

### Phase 4 — Customers page

#### Design overview

Lists all customers and their accounts. Shows AWS auth mode per account. Read from `GET /customers`.

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `app/(dashboard)/customers/page.tsx` | Server Component: fetch customers, render `CustomerList`. Render `<PageHeader title="Customers">` from `components/common/`. | Customers page renders with all customers | Planned |
| Create `components/customers/CustomerList.tsx` | List of customer cards. Each card shows name, account count, slack status, and an expandable accounts section. Shows `<EmptyState>` when no customers returned. | Customer list is readable and expandable | Planned |
| Create `components/customers/AccountRow.tsx` | Row per account: display name, account ID, active status. Uses `<AuthModeBadge mode={account.aws_auth_mode}>` from `components/common/` — no local badge colors defined here. Uses `<SessionStatusBadge>` from `components/common/` for session health. | Account status and auth mode use shared badges — no duplication | Planned |
| Unit test customer components | Test: `CustomerList` renders all customers and shows `EmptyState` when empty, `AccountRow` uses `AuthModeBadge` and `SessionStatusBadge` with correct props. | Customer components are covered | Planned |
| Phase closure | Close Phase 4 after customers page is functional | Phase 4 is officially complete | Planned |

---

### Phase 5 — History page

#### Design overview

Paginated list of past check runs. Per-run detail view with per-account results and status. Uses `GET /history` and `GET /history/{check_run_id}`.

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `app/(dashboard)/history/page.tsx` | Server Component: read `customer_id` + `page` from search params, call `getHistory()`. Render `<PageHeader>` + `<CustomerSelector>` from `components/common/`, then `RunTable`. | History page renders with paginated runs | Planned |
| Create `components/history/RunTable.tsx` | Wraps `<PaginatedTable>` from `components/common/` with history-specific column definitions: run ID (truncated), check mode, check name, created_at, execution time, slack sent, results summary using `<StatusBadge>`. Row click navigates to detail. Shows `<LoadingRows>` while fetching, `<EmptyState>` when no runs. | Run list reuses shared table and badge components | Planned |
| Create `app/(dashboard)/history/[runId]/page.tsx` | Server Component: fetch run detail, render `RunDetail`. | Per-run detail page renders | Planned |
| Create `components/history/RunDetail.tsx` | Shows run metadata, then per-account result rows. Each row uses `<StatusBadge status={result.status}>` from `components/common/`. If `result.error_class` is present, renders `<AuthErrorBadge errorClass={result.error_class} loginCommand={...}>` from `components/common/`. | Shared badges used — no local re-implementation of status or error class colors | Planned |
| Unit test history components | Test: `RunTable` renders rows with correct `StatusBadge` props, shows `EmptyState` when empty. `RunDetail` passes correct props to `AuthErrorBadge`. | History components are covered | Planned |
| Phase closure | Close Phase 5 after history page and run detail are functional | Phase 5 is officially complete | Planned |

---

### Phase 6 — Findings page

#### Design overview

Paginated findings with severity filter and check name filter. Uses `GET /findings`.

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `app/(dashboard)/findings/page.tsx` | Server Component: read query params (customer_id, check_name, severity, page), call `getFindings()`. Render `<PageHeader>` + `<CustomerSelector>` from `components/common/`, then `FindingsFilter` wrapped in `<FilterBar>`, then `FindingsTable`. | Findings page renders with filter support | Planned |
| Create `components/findings/FindingsTable.tsx` | Wraps `<PaginatedTable>` from `components/common/` with findings-specific columns: `<SeverityBadge severity={finding.severity}>` from `components/common/` (no local color definitions), title, check name, account display name, created_at. Shows `<LoadingRows>` and `<EmptyState>` appropriately. | Findings table reuses shared table, badge, and state components | Planned |
| Create `components/findings/FindingsFilter.tsx` | Client component: two shadcn `Select` controls for check_name and severity. Rendered inside the shared `<FilterBar>` wrapper from `components/common/`. Updates search params on change. | Filter layout is consistent with other filter pages via shared `FilterBar` | Planned |
| Unit test findings components | Test: `FindingsTable` passes correct `severity` prop to `SeverityBadge`, shows `EmptyState` when empty. `FindingsFilter` updates search params on selection. | Findings components are covered | Planned |
| Phase closure | Close Phase 6 after findings page is functional | Phase 6 is officially complete | Planned |

---

### Phase 7 — Metrics page

#### Design overview

Paginated metric samples for a customer. Filter by check name, metric name, status. Uses `GET /metrics`.

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `app/(dashboard)/metrics/page.tsx` | Server Component: read query params, call `getMetrics()`. Render `<PageHeader>` + `<CustomerSelector>` from `components/common/`, then `MetricsFilter` wrapped in `<FilterBar>`, then `MetricsTable`. | Metrics page renders with consistent layout | Planned |
| Create `components/metrics/MetricsTable.tsx` | Wraps `<PaginatedTable>` from `components/common/` with metrics-specific columns: metric name, value + unit, `<StatusBadge status={metric.metric_status}>` from `components/common/` (no local color definitions), resource info (service_type, resource_id, role), account, created_at. Shows `<LoadingRows>` and `<EmptyState>`. | Metrics table reuses shared table and status badge — metric_status → StatusBadge maps as ok/warn/error | Planned |
| Create `components/metrics/MetricsFilter.tsx` | Client component: `Select` filters for metric_status and check_name, rendered inside `<FilterBar>` from `components/common/`. Same layout pattern as `FindingsFilter`. | Filter pattern is consistent across Findings and Metrics via shared `FilterBar` | Planned |
| Unit test metrics components | Test: `MetricsTable` passes correct `status` prop to `StatusBadge`, shows `EmptyState` when empty. `MetricsFilter` updates search params. | Metrics components are covered | Planned |
| Phase closure | Close Phase 7 after metrics page is functional | Phase 7 is officially complete | Planned |

---

### Phase 8 — Check execution UI

#### Design overview

Tabbed interface with four check modes: Specific, Bundled, Arbel (dedicated), and Huawei (dedicated). Uses `POST /checks/execute`. Results shown inline with expandable detail per account row.

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Create `ChecksTabs.tsx` | Tab container with Specific / Bundled / Arbel / Huawei tabs. Server-fetches customers, filters arbel/huawei customers, passes props to child forms. | Users can switch between check modes | Done |
| Create `SpecificCheckForm.tsx` | 9 check type cards (GuardDuty, CloudWatch, Notifications, Backup, Cost, RDS Util, EC2 Util, Alarm Verification, Daily Budget). Collapsible customer sections with search filter. Toggle buttons for account selection. Time window selector (1h/3h/12h) for utilization checks. Alarm names preview for alarm_verification. | Users can run one check on selected accounts with granular control | Done |
| Create `BundledCheckForm.tsx` | Mode select (All Checks / Arbel Suite). Customer toggle buttons. Hidden inputs for form state. Progress indicator during execution. | Users can run bundled check suites across multiple customers | Done |
| Create `DedicatedCheckForm.tsx` | Reusable form for Arbel and Huawei dedicated checks. Two modes: account-based (shows account toggles, derives customer_ids) and customer-based (shows customer toggles). Visual check cards with icons. Time window selector for utilization checks. Progress indicator. | Dedicated checks run with correct customer_ids and check_params | Done |
| Create `ResultsTable.tsx` | Flat table with Account / Check / Status / Summary columns. Click-to-expand detail view showing full `output` text. Consolidated report section for bundled/arbel modes. | Users can see per-account results and drill into detail | Done |
| Create `CheckProgress.tsx` | Animated progress component with step indicators, elapsed timer, and progress bar. Used across all check forms during execution. | Users see visual progress during long-running checks | Done |
| Create `actions.ts` server action | `runChecks(formData)` extracts mode, customer_ids, check_name, account_ids, check_params (window_hours). Calls `executeChecks` API. | Check execution is a typed Server Action with check_params support | Done |
| Backend: separate RDS/EC2 checks | Added `daily-arbel-rds` and `daily-arbel-ec2` to `AVAILABLE_CHECKS` using `functools.partial(DailyArbelChecker, section_scope=...)`. Added `error_class` to `CheckResultResponse`. | RDS and EC2 utilization checks can be run independently with correct scope | Done |
| Unit tests (40 tests) | SpecificCheckForm: check cards, collapsible headers, search, time window, disabled states. DedicatedCheckForm: account mode, customer mode, time window, check cards. BundledCheckForm: mode select, toggle buttons. ResultsTable: expand/collapse, consolidated outputs. CheckProgress: labels, steps. | All check execution UI components are covered by tests | Done |
| Phase closure | Close Phase 8 after check execution and results display are functional | Phase 8 is officially complete | Done |

---

### Phase 9 — Role-aware UI and admin features

#### Design overview

Show or hide write actions based on the current user's role. `super_user` gets create/edit/delete customer controls. `user` sees a read-only view.

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Add role guard hook | Create `hooks/useRole.ts`: reads role from `AuthContext`, returns `{ isSuperUser: boolean, canWrite: boolean }`. | Role checking is a single-import hook | Planned |
| Hide write actions for `user` role | In `CustomerList`, `AccountRow`: conditionally render "Edit" / "Delete" / "Add Account" buttons only if `isSuperUser`. Use CSS `hidden` not conditional mount to avoid layout shift. | `user`-role sessions do not see write controls | Planned |
| Create `components/customers/CustomerFormDialog.tsx` | Dialog (shadcn `Dialog` from Phase 0D) for creating/editing a customer. Fields: name, display_name, checks (multi-select), slack_enabled, slack_channel. Submit calls `createCustomerAction` / `updateCustomerAction`. Guarded: only renders if `isSuperUser`. | `super_user` can create and edit customers | Planned |
| Create `components/customers/AccountFormDialog.tsx` | Dialog for adding/editing an account. Fields: profile_name, display_name, account_id, is_active, `aws_auth_mode` (select showing `<AuthModeBadge>` per option from `components/common/`), conditional fields per mode (role_arn + external_id for `assume_role`, access_key fields for `access_key`). | `super_user` can manage accounts with full auth mode config using shared auth mode badge | Planned |
| Create `components/customers/DeleteCustomerButton.tsx` | Renders a delete icon button that opens `<ConfirmDialog>` from `components/common/` with a destructive confirmation. On confirm calls `deleteCustomerAction`. Only renders if `isSuperUser`. | Delete flow uses shared confirm dialog — no per-entity dialog re-implementation | Planned |
| Create server actions for customer CRUD | `createCustomerAction`, `updateCustomerAction`, `deleteCustomerAction`, `createAccountAction`, `updateAccountAction`. Each checks role server-side before calling API. Return typed results. | All write operations are guarded server-side | Planned |
| Unit test role-aware components | Test: write controls hidden for `user` role, visible for `super_user`. `AccountFormDialog` shows/hides conditional fields per `aws_auth_mode`. `DeleteCustomerButton` opens `ConfirmDialog` on click. | Role-based UI is covered by tests | Planned |
| Phase closure | Close Phase 9 after role-aware UI is complete and all tests pass | Phase 9 is officially complete | Planned |

---

### Phase 10 — Customer report_mode & label

#### Design overview

Each customer now has two new fields:
- **report_mode** (`summary` | `detailed`): Controls the format of consolidated reports in bundled/arbel check modes. "summary" produces a condensed WhatsApp-friendly output; "detailed" produces the full monitoring report with recommendations.
- **label** (optional string): A free-text tag shown on customer cards (e.g. "Enterprise", "Trial", "Internal").

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Backend: DB model + migration | Add `report_mode` (String(32), default "summary") and `label` (String(256), nullable) to Customer model. Create Alembic migration `d5e6f7a8b9c0`. | New columns exist in DB | Done |
| Backend: API routes | Add `report_mode` and `label` to `CreateCustomerRequest` and `UpdateCustomerRequest` Pydantic models. Pass through to service and repository. | API accepts and returns new fields | Done |
| Backend: Serialization | Add `report_mode` and `label` to `_serialize_customer()` in CustomerService. | GET /customers returns new fields | Done |
| Backend: Summary report builder | Add `_build_summary_report()` to check_executor.py — condensed report format. Wire `customer.report_mode` to choose between summary and detailed in `execute()`. | Bundled/arbel checks respect per-customer report_mode | Done |
| Frontend: Type update | Add `ReportMode` type and `report_mode`, `label` fields to `Customer` interface in `lib/types/api.ts`. | TypeScript types match API response | Done |
| Frontend: Server actions | Update `createCustomer` and `updateCustomer` server actions to pass `report_mode` and `label` from FormData. | Create/update forms send new fields to API | Done |
| Frontend: CustomerSheet form | Add label input and report_mode Select to CustomerSheet form (between SSO session and Checks sections). | Users can set report_mode and label when creating/editing customers | Done |
| Frontend: CustomerList badges | Show label badge (outline) and report_mode badge (blue for detailed, muted for summary) on customer cards. | Customer cards display report_mode and label at a glance | Done |
| Phase closure | Close Phase 10 after report_mode and label are fully functional | Phase 10 is officially complete | Done |

### Phase 11 — Check output improvements

#### Design overview

Improve check execution output quality and usability. Backend format_report() methods rewritten to produce concise, data-only per-account output (not duplicating consolidated report style). Frontend ResultsTable gets copy-to-clipboard buttons on both per-account output and consolidated report sections.

**Changes:**
- Backend: Rewrote format_report() for cost_anomalies, guardduty, backup_status, daily_arbel to produce concise data output
- Frontend: Added CopyButton component to ResultsTable for output and consolidated report sections

| Task | Description | Expected Outcome | Status |
|---|---|---|---|
| Rewrite cost_anomalies format_report | Strip verbose EXECUTIVE SUMMARY/RECOMMENDATIONS, output concise data | Concise per-account cost anomaly data | Done |
| Rewrite guardduty format_report | Strip verbose report boilerplate | Concise findings list with severity/type/title | Done |
| Rewrite backup_status format_report | Simplify to job counts + failed details | Concise backup status per account | Done |
| Rewrite daily_arbel format_report | Replace WhatsApp-style report with raw metrics data | Raw metric values per instance, not formatted report | Done |
| Add copy button to ResultsTable | CopyButton on expanded output rows and consolidated report sections | Users can copy output/report text with one click | Done |
| Phase closure | Close Phase 11 | Phase 11 is officially complete | Done |

---

## Testing workflow

### After every task

- [ ] Run `npm test` from `frontend/`
- [ ] All existing tests must pass before the task is marked complete
- [ ] Add or update tests for any new component or utility introduced

### At phase completion

- [ ] Run `npm run typecheck` — zero TypeScript errors
- [ ] Run `npm run lint` — zero lint errors
- [ ] Run `npm test` — all tests pass
- [ ] Update the phase status in the Phase overview table above

### Test file conventions

- Component tests: `__tests__/<ComponentName>.test.tsx`
- Utility tests: `__tests__/lib/<module>.test.ts`
- All tests use `@testing-library/react` for component rendering
- Mock API calls with `jest.spyOn(global, 'fetch').mockResolvedValue(...)` or `jest.mock('../lib/api/...')`
- Mock Next.js navigation with `jest.mock('next/navigation', () => ({ useRouter: () => ({ push: jest.fn(), replace: jest.fn() }) }))` — `next/jest` preset auto-mocks `next/navigation` and `next/headers` so Server Component imports don't break tests

---

## File structure target

```
frontend/
├── app/
│   ├── (auth)/
│   │   └── login/
│   │       ├── page.tsx          # Login page (Server Component)
│   │       └── actions.ts        # loginAction Server Action
│   └── (dashboard)/
│       ├── layout.tsx            # Authenticated shell (sidebar + user menu)
│       ├── dashboard/
│       │   └── page.tsx
│       ├── customers/
│       │   └── page.tsx
│       ├── history/
│       │   ├── page.tsx
│       │   └── [runId]/page.tsx
│       ├── findings/
│       │   └── page.tsx
│       ├── metrics/
│       │   └── page.tsx
│       └── checks/
│           └── actions.ts
├── components/
│   ├── common/                   # ← ALL reusable primitives live here
│   │   ├── StatusBadge.tsx       # ok/warn/error/alarm/no_data
│   │   ├── SeverityBadge.tsx     # CRITICAL/HIGH/MEDIUM/LOW/INFO/ALARM
│   │   ├── AuthModeBadge.tsx     # assume_role/sso/aws_login/access_key
│   │   ├── AuthErrorBadge.tsx    # error_class values + login_command tooltip
│   │   ├── SessionStatusBadge.tsx# ok/expired/no_config/error + login_command tooltip
│   │   ├── PaginatedTable.tsx    # generic table + pagination
│   │   ├── LoadingRows.tsx       # skeleton rows for table loading
│   │   ├── EmptyState.tsx        # empty list state
│   │   ├── PageHeader.tsx        # title + breadcrumb
│   │   ├── CustomerSelector.tsx  # shared customer switcher (Select + router.replace)
│   │   ├── FilterBar.tsx         # filter row wrapper + reset button
│   │   ├── ConfirmDialog.tsx     # generic destructive action dialog
│   │   └── InlineCode.tsx        # monospace CLI command with copy button
│   ├── auth/                     # LoginForm, LogoutButton
│   ├── layout/                   # AppSidebar, UserMenu
│   ├── providers/                # AuthProvider
│   ├── dashboard/                # StatCards, TopChecksTable
│   ├── customers/                # CustomerList, AccountRow, CustomerFormDialog, AccountFormDialog, DeleteCustomerButton
│   ├── history/                  # RunTable, RunDetail
│   ├── findings/                 # FindingsTable, FindingsFilter
│   ├── metrics/                  # MetricsTable, MetricsFilter
│   ├── checks/                   # RunCheckDialog, ResultsDisplay
│   └── ui/                       # shadcn primitives (auto-generated)
├── hooks/
│   └── useRole.ts
├── lib/
│   ├── api/
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   ├── customers.ts
│   │   ├── history.ts
│   │   ├── findings.ts
│   │   ├── metrics.ts
│   │   └── dashboard.ts
│   ├── session.ts                # httpOnly cookie read/write (server-only)
│   ├── auth.ts                   # getSession() (server-only)
│   └── types/
│       └── api.ts
├── middleware.ts                 # Route protection
├── __tests__/
│   ├── smoke.test.ts
│   ├── middleware.test.ts
│   ├── lib/
│   └── components/
├── jest.config.ts
└── jest.setup.ts
```

---

## Commit and docs workflow

### Before every commit

- [ ] Update relevant checklist items in this file
- [ ] Ensure item statuses match actual implementation
- [ ] Run `npm test` — all tests pass

### At phase completion only

- [ ] Update phase overview status table
- [ ] Append a change log entry with date and summary

---

## Change log

- 2026-03-21: Initial living plan created. Covers Phase 0–9 with auth flow as Phase 1 priority. Aligned with backend Phase 5 JWT/role contract and `docs/api/frontend-contract-v1.md`. Shadcn blocks: `login-01`, `sidebar-07`, `dashboard-01` as primary structural primitives.
- 2026-03-21: Added Phase 0D — shared component library. Defined 13 reusable primitives in `components/common/` (StatusBadge, SeverityBadge, AuthModeBadge, AuthErrorBadge, SessionStatusBadge, PaginatedTable, LoadingRows, EmptyState, PageHeader, CustomerSelector, FilterBar, ConfirmDialog, InlineCode). Updated all feature phases (3–9) to import from `components/common/` instead of redefining badge colors, table logic, or filter layouts locally.
