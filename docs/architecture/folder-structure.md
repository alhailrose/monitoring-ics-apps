# Target Folder Structure

This document defines the migration direction from the current CLI-first layout to a runner-first and web-app-ready architecture.

## Incremental scaffold (current migration step)

To keep migration safe, app-level scaffold is introduced without moving runtime in one step:

- `apps/web/` exists as migration anchor (Vite runtime still in `web/`)
- `apps/api/main.py` wraps `backend.interfaces.api.main`
- `apps/tui/main.py` wraps `backend.interfaces.cli.main`

This keeps existing execution paths stable while enabling path-based CI/CD separation per app target.

## Current high-level modules

- `backend/`: canonical API/CLI interfaces, domain runtime/services, infra, and config
- `checks/`: checker implementations
- `tests/`: test coverage for checks and report formatting

## Target structure

```text
backend/
  interfaces/
    api/
    cli/
  domain/
    runtime/
    services/
  infra/
    cloud/
    database/
    notifications/
  config/
    defaults/
      customers/
    schema/
src/
  ... compatibility wrappers only ...
tests/
  unit/
  integration/
```

## Migration rules

1. Separate migration commits into:
   - move-only commits (no behavior changes)
   - behavior commits (with tests)
2. Keep existing CLI and TUI behavior stable while introducing runner and API layers.
3. Move hardcoded customer mappings to config files under `configs/customers/`.
4. Keep report format compatibility for existing operational channels.

## Initial phases

- Phase 1: Central runner + Slack command trigger + persisted run history
- Phase 2: API endpoints for run submit/status/history
- Phase 3: Read-only dashboard, then full web app flow
