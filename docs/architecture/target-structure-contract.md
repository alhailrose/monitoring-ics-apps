# Target Structure Contract

This contract defines mandatory architecture rules during migration to a scalable monitoring app structure.

## Canonical target layout

- `src/app/` for delivery channels (`cli`, `tui`, `api`)
- `src/core/` for orchestration, models, and formatting
- `src/providers/` for external services integration (AWS)
- `src/checks/` split by domain and customer
- `src/configs/` for defaults and schema
- `tests/unit` and `tests/integration`

## Non-negotiable migration rules

1. No new product feature work until migration checkpoint is marked ready.
2. Every migration batch must keep runtime behavior stable.
3. Every migration batch must include tests and pass full test suite.
4. Legacy modules may remain only as compatibility wrappers.
5. Wrapper removal is allowed only after import switch and green verification.

## Compatibility wrapper lifecycle

1. Create canonical implementation under `src/`.
2. Convert legacy module into thin re-export wrapper.
3. Switch imports progressively to canonical paths.
4. Remove wrapper after no runtime references remain.

## Quality gates

- Required before each merge:
  - `uv run --with pytest pytest`
  - CLI smoke: `monitoring-hub --help`
  - updated migration status in `docs/architecture/migration-status.md`
