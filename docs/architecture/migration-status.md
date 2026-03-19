# Migration Status

Reference contract: `docs/architecture/target-structure-contract.md`

## Backend-interface runtime state (current)

- Runtime entrypoint now targets backend interfaces:
  - `monitoring-hub` console script -> `backend.interfaces.cli.main:main`
- Canonical interface/runtime modules live under `backend/`:
  - API: `backend/interfaces/api/*`
  - CLI/TUI: `backend/interfaces/cli/*`
  - Domain services: `backend/domain/services/*`
  - Config settings: `backend/config/settings.py`
- `src/` runtime code has no imports from `monitoring_hub.*` or `checks.*`.

## Compatibility posture

- Legacy top-level packages have been removed from repository runtime surface:
  - removed: `monitoring_hub/*`
  - removed: `checks/*`
- Runtime code and packaging now point to `backend/*` interface paths, with `src/app/*` maintained as compatibility wrappers.

## Validation coverage

- Integration guardrail enforces no legacy imports in src runtime tree.
- CLI entrypoint integration test enforces backend interface script target.
- Existing unit/integration suites remain in `tests/unit` and `tests/integration`.

## Remaining follow-up (non-blocking)

1. Continue wrapper cleanup by migrating remaining non-interface `src/*` modules into `backend/*` layers.

## Phase 2 scaffold + CI/CD baseline (incremental)

- Added target app scaffolds:
  - `apps/web/` (placeholder, runtime still in `web/` Vite)
  - `apps/api/main.py` (compatibility wrapper to `backend.interfaces.api.main`)
  - `apps/tui/main.py` (compatibility wrapper to `backend.interfaces.cli.main`)
- Added split CI pipelines with path-based triggers:
  - `.github/workflows/ci-web.yml`
  - `.github/workflows/ci-api.yml`
  - `.github/workflows/ci-tui.yml`
- Added deployment approval/rollback gate:
  - `.github/workflows/deploy-manual.yml`
  - `docs/operations/deployment-flow.md`
