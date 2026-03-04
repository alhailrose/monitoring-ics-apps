# AWS Monitoring Hub Frontend Rebuild Design

**Date:** 2026-03-03
**Scope:** Rebuild `web/` React + TypeScript frontend to match synchronous backend API (`/api/v1`).

## 1. Architecture

Frontend will use a lightweight SPA architecture built on React 18 + Vite with an internal pathname router (History API) and modular page components.

Key decisions:
- Replace legacy async `/jobs` flow completely with synchronous check execution pages.
- Centralize all API calls in `web/src/api/` with typed request/response helpers.
- Centralize all DTO/domain types in `web/src/types/`.
- Keep shared UI primitives in `web/src/components/ui/` and add domain components in `web/src/components/common/`.
- Keep one dark industrial theme stylesheet and extend status semantics for `OK | WARN | ERROR | ALARM | NO_DATA`.

## 2. Route & Page Model

Routes to implement:
- `/` Home (navigation cards)
- `/checks/single` Single Check execution
- `/checks/all` All Check execution
- `/checks/arbel` Arbel execution
- `/customers` Customer Management
- `/profiles` Profile Detection
- `/history` History list + detail panel

Routing behavior:
- Unknown path falls back to `/`.
- Sidebar navigation highlights active page.
- URL updates with `history.pushState` and handles browser back/forward.

## 3. Data Flow

### Shared reference data
- Fetch customers from `GET /customers` and cache in page state with manual refresh.
- Fetch available checks from `GET /checks/available` for Single Check page.

### Check execution
- POST `/checks/execute` with mode-specific payload.
- While request is in-flight, disable form controls and show long-running loading indicator.
- Render copyable plain-text output (`consolidated_output` + per-result outputs) as `<pre>` blocks.

### History
- Build query string from customer + date range + optional mode/name + pagination.
- Show paginated table using `limit/offset`.
- Clicking a row fetches `GET /history/{check_run_id}` and opens detail drawer/panel.

### Customer management
- CRUD customers and accounts directly against API.
- After mutation, refresh customer list for consistency.

### Profile detection
- Scan on demand using `GET /profiles/detect`.
- Compute mapped profile -> customer display via customer/account index in frontend.
- Provide quick-add for unmapped profiles to a selected customer.

## 4. UX & Error Handling

- Dark responsive layout with cards/panels and mobile-safe stacking.
- Status badge palette:
  - `OK` green
  - `WARN` yellow
  - `ERROR` red
  - `ALARM` orange
  - `NO_DATA` gray
- User-friendly errors from backend `detail` or fallback generic message.
- Unified toast notifications for success/error actions.
- All output areas include copy buttons.

## 5. Testing Strategy

- Replace old `/jobs` tests with new route/page tests.
- TDD focus areas:
  - Route resolver maps all 7 routes.
  - Status badge semantic mapping.
  - Single Check submits correct payload and renders output.
  - History builds query with filters/pagination and opens detail.
  - Customer page performs create/update/delete API flows (at minimum create + add account).
- Run `npm test` and `npm run build` before completion.

## 6. Migration Notes

- Existing `web/src/app/jobs/*` code and tests are removed/replaced.
- Existing style tokens are retained and expanded, not re-themed from scratch.
- API base uses same-origin `/api/v1/*` so Vite proxy remains optional.
