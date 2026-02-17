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

- Legacy top-level packages are retained as compatibility shims:
  - `monitoring_hub/*` wrappers re-export from `src.*`
  - `checks/*` wrappers re-export from `src.checks.*`
- Existing command behavior is preserved for CLI/TUI while runtime source of truth is `src/`.

## Validation coverage

- Integration guardrail enforces no legacy imports in src runtime tree.
- CLI entrypoint integration test enforces src-first script target.
- Existing unit/integration suites remain in `tests/unit` and `tests/integration`.

## Remaining follow-up (non-blocking)

1. Remove legacy wrapper packages in a future major version after downstream import consumers are migrated.
2. Continue planned API/dashboard implementation under `src/app/api`.
