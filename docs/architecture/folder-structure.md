# Target Folder Structure

This document defines the migration direction from the current CLI-first layout to a runner-first and web-app-ready architecture.

## Current high-level modules

- `monitoring_hub/`: CLI, interactive flows, orchestration, reports
- `checks/`: checker implementations
- `tests/`: test coverage for checks and report formatting

## Target structure

```text
src/
  app/
    cli/
    tui/
    api/
  core/
    engine/
    models/
    formatting/
  providers/
    aws/
      auth.py
      clients.py
      services/
  checks/
    generic/
    customers/
  configs/
    defaults/
      customers/
    schema/
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
