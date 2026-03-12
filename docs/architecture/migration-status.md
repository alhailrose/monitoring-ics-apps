# Migration Status

Reference contract: `docs/architecture/target-structure-contract.md`

## Full src-first runtime state (current)

- Runtime entrypoint is now src-first:
  - `monitoring-hub` console script -> `src.app.cli.main:main`
- Canonical runtime modules live under `src/`:
  - CLI/TUI: `src/app/*`
  - Runtime shared logic: `src/core/runtime/*`
  - Checks: `src/checks/*`
  - Config/provider/core models remain under `src/configs`, `src/providers`, `src/core`
- `src/` runtime code has no imports from `monitoring_hub.*` or `checks.*`.

## Compatibility posture

- Legacy top-level packages have been removed from repository runtime surface:
  - removed: `monitoring_hub/*`
  - removed: `checks/*`
- Runtime code and packaging now point only to `src/*` modules.

## Validation coverage

- Integration guardrail enforces no legacy imports in src runtime tree.
- CLI entrypoint integration test enforces src-first script target.
- Existing unit/integration suites remain in `tests/unit` and `tests/integration`.

## Remaining follow-up (non-blocking)

1. Continue planned API/dashboard implementation under `src/app/api`.

## Phase 2 scaffold + CI/CD baseline (incremental)

- Added target app scaffolds:
  - `apps/web/` (placeholder, runtime still in `web/` Vite)
  - `apps/api/main.py` (compatibility wrapper to `src.app.api.main`)
  - `apps/tui/main.py` (compatibility wrapper to CLI entrypoint)
- Added split CI pipelines with path-based triggers:
  - `.github/workflows/ci-web.yml`
  - `.github/workflows/ci-api.yml`
  - `.github/workflows/ci-tui.yml`
- Added deployment approval/rollback gate:
  - `.github/workflows/deploy-manual.yml`
  - `docs/operations/deployment-flow.md`
