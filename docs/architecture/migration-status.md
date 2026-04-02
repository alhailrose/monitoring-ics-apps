# Migration Status

Reference contract: `docs/architecture/target-structure-contract.md`

## Backend-interface runtime state (current)

- Runtime entrypoint now uses backend interfaces directly:
  - `monitoring-hub` console script -> `backend.interfaces.cli.main:main`
- Canonical interface/runtime modules live under `backend/`:
  - API: `backend/interfaces/api/*`
  - CLI/TUI: `backend/interfaces/cli/*`
  - Checks implementation: `backend/checks/*`
  - Runner engine: `backend/domain/engine/*`
  - Runner models: `backend/domain/models/*`
  - Report formatting: `backend/domain/formatting/reports.py`
  - Domain services: `backend/domain/services/*`
  - Config settings: `backend/config/settings.py`
  - Customer flow canonical: `backend/interfaces/cli/flows/customer.py`
- Runtime codebase no longer uses `src.*` namespace imports.

## Compatibility posture

- Legacy top-level packages have been removed from repository runtime surface:
  - removed: `monitoring_hub/*`
  - removed: `checks/*`
- Legacy `src/*` python modules have been removed from tracked runtime code.

## Validation coverage

- Integration guardrail enforces no `src.*` imports in repository python code.
- CLI/API tests target canonical backend modules directly.
- Existing unit/integration suites remain in `tests/unit` and `tests/integration`.

## Remaining follow-up (non-blocking)

1. Keep docs/runbooks synchronized with backend-only runtime namespace.

## Phase 2 scaffold + CI/CD baseline (incremental)

- Added target app scaffolds:
  - `apps/web/` (placeholder, runtime still in `web/` Vite)
  - `apps/api/main.py` (compatibility wrapper to `backend.interfaces.api.main`)
  - `apps/tui/main.py` (compatibility wrapper to `backend.interfaces.cli.main`)
- Added split CI pipelines with path-based triggers:
  - `.github/workflows/ci-frontend.yml`
  - `.github/workflows/ci-backend.yml`
- Added split CD pipelines with CI-success gate (`workflow_run`):
  - `.github/workflows/deploy-frontend.yml`
  - `.github/workflows/deploy-backend.yml`
