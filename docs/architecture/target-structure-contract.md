# Target Structure Contract

This contract defines mandatory architecture rules during migration to a scalable monitoring app structure.

## Canonical target layout

- `backend/interfaces/` for delivery channels (`cli`, `api`)
- `backend/domain/` for orchestration/runtime/services
- `backend/infra/` for external integrations (AWS, DB, Slack)
- `backend/checks/` split by domain and customer (canonical)
- `backend/config/` for defaults and schema
- `tests/unit` and `tests/integration`

## Non-negotiable migration rules

1. No new product feature work until migration checkpoint is marked ready.
2. Every migration batch must keep runtime behavior stable.
3. Every migration batch must include tests and pass full test suite.
4. Do not reintroduce `src.*` runtime namespaces.
5. Any namespace/foldering change must be verified with green tests.

## Quality gates

- Required before each merge:
  - `uv run --with pytest pytest`
  - CLI smoke: `monitoring-hub --help`
  - updated migration status in `docs/architecture/migration-status.md`
