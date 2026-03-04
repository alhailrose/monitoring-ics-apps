# Industrial Ops Glass UI Design

## Objective

Deliver a distinctive, production-ready web UI for Monitoring Hub with an "Industrial Ops Glass" visual language across Home, Jobs, and History screens.

## Approved Direction

- **Aesthetic:** command-center feel with layered glass panels, high-contrast status cues, subtle grid/texture background.
- **Tone:** professional operational dashboard (confident, data-first, modern).
- **Differentiation:** memorable panel depth + semantic status visuals designed for monitoring workflows.

## Product Scope

- Style and layout improvements for:
  - `web/src/app/page.tsx`
  - `web/src/app/jobs/page.tsx`
  - `web/src/app/history/page.tsx`
- Introduce shared styling foundation and reusable UI primitives.
- Keep existing APIs and behavior compatible:
  - `POST /api/v1/jobs`
  - `GET /api/v1/history`

## Design System

### Color and Surfaces

- Dark slate/navy base for low glare and high contrast.
- Accent pair:
  - Cyan/teal for active and informational states.
  - Amber for warning/queued emphasis.
- Semantic statuses:
  - queued, running, completed, failed as consistent tokens.
- Glass panel treatment:
  - thin border glow
  - low-radius blur
  - layered background transparency

### Typography

- Use an expressive display face for headers and a clean readable body face for data density.
- Avoid generic defaults (Inter/Roboto/Arial/system stacks).
- Preserve legibility at small sizes for tables and metadata.

### Motion

- Staggered enter animation on page load.
- Gentle lift/glow hover for cards and controls.
- Row highlight transition for tables.
- Respect reduced-motion users via `prefers-reduced-motion` fallback.

## Information Architecture

### Home (`/`)

- Hero heading and operational context.
- KPI-style summary cards:
  - queued jobs
  - runs today
  - last check status/time
- Quick links to Jobs and History.

### Jobs (`/jobs`)

- Two-column desktop layout; stacked mobile layout.
- Left: Manual run form (customer, check, profiles).
- Right: queue snapshot/status.
- Bottom: jobs table with semantic status badges.

### History (`/history`)

- Header + filter/search bar.
- History list/table with check, profile, status, timestamp.
- Clear empty state and failure state.

## Data and Interaction Design

- Manual run submit:
  - optimistic "queued" feedback
  - non-blocking success/error messaging
- History fetch:
  - initial loading skeleton/state
  - graceful fallback on fetch failure
- Active job polling:
  - lightweight interval polling only while queued/running jobs exist

## Production-Readiness Requirements

- Accessibility:
  - semantic landmarks, labels, focus-visible states, color contrast
- Responsiveness:
  - mobile-first spacing and tap targets
  - table overflow behavior with preserved readability
- Reliability:
  - all API failures surfaced with user-readable messages
  - no hard crash on malformed/empty payloads
- Maintainability:
  - centralized tokens and shared component patterns
  - avoid duplicated style rules across pages

## Testing Strategy

- Keep existing history heading test passing.
- Add focused UI tests for:
  - status badge render semantics
  - empty state render
  - form submit interaction (mocked)
- Validate full web tests via `npm test`.

## Acceptance Criteria

- UI is visually cohesive in Industrial Ops Glass style across all pages.
- Layout works on mobile and desktop.
- Status and operational state are readable at a glance.
- Existing behavior remains functional.
- Test suite remains green and includes new UI assertions.
